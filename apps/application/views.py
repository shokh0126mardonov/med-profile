from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
import asyncio
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from django.http import Http404, StreamingHttpResponse
import requests

from decouple import config

from handlers import send_to_user as send_to_user_bot
from .models import Applications, ApplicationAssignment 
from .serializers import (
    ApplicationListRetrieveSerializer, 
    DoctorResponseSerializer, 
    OperatorResponseSerializer
)
from .permissions import IsDoctor, IsOperator
class ApplicationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Faqat GET (list va retrieve) ishlaydi. 
    Uchrashadigan barcha jarayonlar custom action'lar orqali boshqariladi.
    """
    serializer_class = ApplicationListRetrieveSerializer
    permission_classes = [IsAuthenticated] 

    def get_queryset(self):
        user = self.request.user
        
        queryset = Applications.objects.select_related('sick').prefetch_related(
            'doctors',
            'assignments',
            'assignments__doctor'
        )

        if user.is_authenticated and getattr(user, 'role', None) == 'DOCTOR':
            # 💡 Agar shifokor o'rta jadvalda rad etgan bo'lsa (status='REJECTED'), unga ro'yxatda ko'rinmaydi
            queryset = queryset.filter(
                Q(status__in=['NEW', 'ASSIGNED']) |                     
                Q(doctors=user)
            ).exclude(
                assignments__doctor=user,
                assignments__status='REJECTED'
            )
            
        return queryset.distinct()

    # 1. SHIFOKOR ARIZANI RAD ETISHI (O'ZGARTIRILDI 🚀)
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def not_my_case(self, request, pk=None):
        application = self.get_object()
        user = request.user

        if getattr(user, 'role', None) != 'DOCTOR':
            return Response({"error": "Faqat shifokorlar arizani rad eta oladi!"}, status=status.HTTP_403_FORBIDDEN)

        # Qora ro'yxatga (ManyToManyField) ham qo'shib qo'yamiz (eski mantiq buzilmasligi uchun)
        application.rejected_by_doctors.add(user)

        # 💡 YANGI MANTIQ: O'rta jadvaldagi biriktiruvni o'chirmaymiz, statusini 'REJECTED' qilamiz!
        assignment, created = ApplicationAssignment.objects.get_or_create(
            application=application, 
            doctor=user
        )
        assignment.status = 'REJECTED'
        assignment.save()
            
        # Agar arizada faol (UNSEEN yoki ACCEPTED) shifokor qolmagan bo'lsa, statusni NEW qilamiz
        active_assignments = application.assignments.exclude(status='REJECTED')
        if not active_assignments.exists():
            application.status = 'NEW'
            application.save()

        return Response({"message": "Ariza rad etildi. U sizga boshqa ko'rinmaydi va statistikaga qo'shildi."})

    # 2. SHIFOKOR ARIZANI QABUL QILISHI (O'ZGARTIRILDI 🚀)
    @extend_schema(request=None)
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsDoctor])
    def accept_application(self, request, pk=None):
        application = self.get_object()
        user = request.user

        # Allaqachon o'ziga faol biriktirganmi tekshiramiz
        existing_assignment = ApplicationAssignment.objects.filter(application=application, doctor=user).first()
        if existing_assignment and existing_assignment.status in ['UNSEEN', 'ACCEPTED']:
            return Response({"error": "Siz bu arizani allaqachon o'zingizga biriktirgan ekansiz!"}, status=status.HTTP_400_BAD_REQUEST)

        # 💡 O'rta jadval orqali shifokorni bog'laymiz va statusni 'ACCEPTED' qilamiz
        if existing_assignment:
            existing_assignment.status = 'ACCEPTED'
            existing_assignment.save()
        else:
            ApplicationAssignment.objects.create(application=application, doctor=user, status='ACCEPTED')

        # Global statusni o'zgartiramiz
        application.status = 'ASSIGNED'
        application.save()

        return Response({"message": "Siz ushbu bemor arizasini muvaffaqiyatli qabul qildingiz!"})

    # 3. SHIFOKOR TASHXIS YOZISHI
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsDoctor], serializer_class=DoctorResponseSerializer)
    def doctor_respond(self, request, pk=None):
        application = self.get_object()
        user = request.user

        # O'rta jadvaldan joriy shifokorning biriktiruvini qidiramiz
        assignment = ApplicationAssignment.objects.filter(application=application, doctor=user).first()
        if not assignment or assignment.status == 'REJECTED':
            return Response(
                {"error": "Siz bu arizaga javob bera olmaysiz, chunki u sizga biriktirilmagan yoki rad etgansiz!"}, 
                status=status.HTTP_403_FORBIDDEN
            )

        if application.status not in ['ASSIGNED', 'COMPLETED']:
            return Response(
                {"error": "Ariza yopilgan yoki hali qabul qilinmagan, unga tashxis yozib bo'lmaydi!"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        doctor_response_text = request.data.get('doctor_response_text', '').strip()
        if not doctor_response_text:
            return Response(
                {"doctor_response_text": ["Tashxis matnini yuborish majburiy! Bo'sh bo'lishi mumkin emas."]},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = DoctorResponseSerializer(instance=assignment, data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # O'rta jadvaldagi ma'lumotlarni saqlaymiz (status 'ACCEPTED'ligicha qoladi)
        serializer.save(responded_at=timezone.now(), status='ACCEPTED')

        # Arizaning barcha shifokorlar ko'rgan umumiy holatini yangilaymiz
        application.status = 'COMPLETED'
        application.save()

        return Response({"message": "Tashxis va hujjat muvaffaqiyatli saqlandi!"})
    
    # 4. OPERATOR IZOHI (O'zgarishsiz qoladi)
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsOperator])
    def operator_respond(self, request, pk=None):
        application = self.get_object()

        if application.status not in ['COMPLETED']:
            return Response(
                {"error": "Ushbu arizaga hali shifokorlar javob bermagan yoki ariza allaqachon yopilgan!"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = OperatorResponseSerializer(instance=application, data=request.data)
        serializer.is_valid(raise_exception=True)

        application.operator_response = serializer.validated_data['operator_response']
        application.save()

        return Response({
            "message": "Operator izohi saqlandi. 'send_to_user' orqali bemorga yuborishingiz mumkin."
        })

    # 5. BEMORGA YUBORISH (O'zgarishsiz qoladi)
    @extend_schema(request=None)
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsOperator])
    def send_to_user(self, request, pk=None):
        application = self.get_object()

        if application.status != 'COMPLETED':
            return Response(
                {"error": "Bu arizani yuborib bo'lmaydi."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not application.operator_response:
            return Response(
                {"error": "Bemorga yuborishdan oldin operator izohini yozish shart!"},
                status=status.HTTP_400_BAD_REQUEST
            )

        application.status = 'CLOSED'
        application.save()

        shifokorlar_javobi = ""
        # Faqat javob yozgan (ACCEPTED) shifokorlar javoblarini matnga jamlaymiz
        assignments = application.assignments.filter(status='ACCEPTED', doctor_response_text__isnull=False)
        
        for idx, assign in enumerate(assignments, 1):
            shifokorlar_javobi += f"\n👨‍⚕️ {idx}-Shifokor ({assign.doctor.get_full_name()}):\n{assign.doctor_response_text}\n"

        try:
            bemor_telegram_id = application.sick.telegram_id
            javob_matni = (
                "🎉 **Sizning arizangiz ko'rib chiqildi!**\n"
                f"{shifokorlar_javobi}\n"
                f"📋 **Operator izohi:**\n{application.operator_response}\n\n"
                "Sog'ligingizga e'tiborli bo'ling!"
            )
            asyncio.run(send_to_user_bot(bemor_telegram_id, javob_matni))
            return Response({"message": "Ariza muvaffaqiyatli yopildi va bemorga Telegram orqali yuborildi!"})
        except Exception as e:
            return Response({
                "message": "Ariza tizimda yopildi, lekin Telegram bot orqali yuborishda xatolik yuz berdi.",
                "details": str(e)
            }, status=status.HTTP_207_MULTI_STATUS)

    # 6. XAVFSIZ FAYL PROXY (O'zgarishsiz qoladi)
    @action(detail=True, methods=['get'], url_path='view_file', permission_classes=[])
    def view_file(self, request, pk=None):
        try:
            application = Applications.objects.get(pk=pk)
        except Applications.DoesNotExist:
            raise Http404("Ariza topilmadi!")

        user_file_url = getattr(application, 'user_file_url', None)
        if not user_file_url:
            raise Http404("Ushbu arizaga fayl biriktirilmagan!")

        token = config('TOKEN')
        telegram_file_url = f"https://api.telegram.org/file/bot{token}/{user_file_url}" if not str(user_file_url).startswith('http') else user_file_url

        try:
            tg_response = requests.get(telegram_file_url, stream=True, timeout=10)
            if tg_response.status_code != 200:
                raise Http404("Telegram faylni berishni rad etdi.")
            
            response = StreamingHttpResponse(tg_response.iter_content(chunk_size=8192), content_type=tg_response.headers.get('Content-Type', 'application/octet-stream'))
            response['Content-Disposition'] = 'inline'
            return response
        except Exception:
            raise Http404("Faylni yuklashda ichki xatolik.")