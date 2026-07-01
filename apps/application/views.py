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
            # 💡 Shifokor o'zi aniq rad etgan (status='REJECTED') arizalarni ro'yxatda ko'rmaydi.
            # Lekin hali ko'rmagan (UNSEEN), qabul qilgan (ACCEPTED) yoki javob bergan (RESPONDED) arizalari ko'rinadi.
            queryset = queryset.filter(
                assignments__doctor=user
            ).exclude(
                assignments__doctor=user,
                assignments__status='REJECTED'
            )
            
        return queryset.distinct()

    # 1. SHIFOKOR ARIZANI RAD ETISHI (O'ZGARTIRILDI 🚀)
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsDoctor])
    def not_my_case(self, request, pk=None):
        application = self.get_object()
        user = request.user

        # O'rta jadvaldan joriy shifokor biriktiruvini topamiz
        assignment = ApplicationAssignment.objects.filter(application=application, doctor=user).first()
        if not assignment:
            return Response({"error": "Siz ushbu arizaga biriktirilmagansiz!"}, status=status.HTTP_400_BAD_REQUEST)

        if assignment.status == 'RESPONDED':
            return Response({"error": "Siz allaqachon javob bergan arizani rad eta olmaysiz!"}, status=status.HTTP_400_BAD_REQUEST)

        # Eski mantiqiy ManyToMany maydonni ham yangilab qo'yamiz
        application.rejected_by_doctors.add(user)

        # Statusni REJECTED ga o'tkazamiz
        assignment.status = 'REJECTED'
        assignment.save()
            
        return Response({"message": "Ariza rad etildi. U sizga boshqa ko'rinmaydi va statistikaga qo'shildi."})

    # 2. SHIFOKOR ARIZANI QABUL QILISHI (O'ZGARTIRILDI 🚀)
    @extend_schema(request=None)
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsDoctor])
    def accept_application(self, request, pk=None):
        application = self.get_object()
        user = request.user

        assignment = ApplicationAssignment.objects.filter(application=application, doctor=user).first()
        if not assignment:
            return Response({"error": "Siz ushbu arizaga biriktirilmagansiz!"}, status=status.HTTP_400_BAD_REQUEST)

        if assignment.status == 'ACCEPTED':
            return Response({"error": "Siz bu arizani allaqachon qabul qilgansiz va u jarayonda!"}, status=status.HTTP_400_BAD_REQUEST)
        
        if assignment.status == 'RESPONDED':
            return Response({"error": "Siz bu arizaga allaqachon tashxis yozib bo'lgansiz!"}, status=status.HTTP_400_BAD_REQUEST)

        # Status UNSEEN dan ACCEPTED (Qabul qildi) holatiga o'tadi
        assignment.status = 'ACCEPTED'
        assignment.save()

        return Response({"message": "Siz ushbu bemor arizasini muvaffaqiyatli qabul qildingiz!"})

    # 3. SHIFOKOR TASHXIS YOZISHI (O'ZGARTIRILDI 🚀)
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsDoctor], serializer_class=DoctorResponseSerializer)
    def doctor_respond(self, request, pk=None):
        application = self.get_object()
        user = request.user

        assignment = ApplicationAssignment.objects.filter(application=application, doctor=user).first()
        if not assignment:
            return Response({"error": "Siz ushbu arizaga biriktirilmagansiz!"}, status=status.HTTP_403_FORBIDDEN)

        # Faqat qabul qilingan (ACCEPTED) arizalargagina tashxis yozishga ruxsat beramiz
        if assignment.status != 'ACCEPTED':
            return Response(
                {"error": "Tashxis yozishdan oldin arizani qabul qilishingiz (accept_application) shart!"}, 
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
        
        # 🚀 Status ACCEPTED dan RESPONDED (Javob berdi) holatiga o'tadi
        serializer.save(responded_at=timezone.now(), status='RESPONDED')

        return Response({"message": "Tashxis va hujjat muvaffaqiyatli saqlandi! Status 'RESPONDED' holatiga o'tdi."})
    
    # 4. OPERATOR IZOHI (O'ZGARTIRILDI 🚀)
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsOperator])
    def operator_respond(self, request, pk=None):
        application = self.get_object()

        # Arizaga kamida bitta shifokor javob berganligini tekshiramiz
        has_response = application.assignments.filter(status='RESPONDED').exists()
        if not has_response:
            return Response(
                {"error": "Ushbu arizaga hali biror bir shifokor javob yozmagan (RESPONDED bo'lmagan)!"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = OperatorResponseSerializer(instance=application, data=request.data)
        serializer.is_valid(raise_exception=True)

        application.operator_response = serializer.validated_data['operator_response']
        application.save()

        return Response({
            "message": "Operator izohi saqlandi. 'send_to_user' orqali bemorga yuborishingiz mumkin."
        })

    # 5. BEMORGA YUBORISH (KO'P FAYLLI REJIM UCHUN YANGILANDI 🚀)
    @extend_schema(request=None)
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsOperator])
    def send_to_user(self, request, pk=None):
        application = self.get_object()

        if not application.operator_response:
            return Response(
                {"error": "Bemorga yuborishdan oldin operator izohini yozish shart!"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Faqat javob yozgan (RESPONDED) shifokorlarni olamiz
        assignments = application.assignments.filter(status='RESPONDED').select_related('doctor')
        if not assignments.exists():
            return Response(
                {"error": "Kamida bitta shifokor RESPONDED statusida bo'lishi kerak!"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1. Shifokorlar tashxislarini matnga jamlaymiz
        shifokorlar_javobi = ""
        for idx, assign in enumerate(assignments, 1):
            doc_name = assign.doctor.get_full_name() if assign.doctor.get_full_name() else assign.doctor.username
            shifokorlar_javobi += f"\n👨‍⚕️ {idx}-Shifokor ({doc_name}):\n{assign.doctor_response_text}\n"

        try:
            bemor_telegram_id = application.sick.telegram_id
            javob_matni = (
                "🎉 **Sizning arizangiz ko'rib chiqildi!**\n"
                f"{shifokorlar_javobi}\n"
                f"📋 **Operator izohi:**\n{application.operator_response}\n\n"
                "Sog'ligingizga e'tiborli bo'ling!"
            )
            
            # 2. Birinchi bo'lib umumiy matnli xabarni bemorga yuboramiz
            asyncio.run(send_to_user_bot(bemor_telegram_id, javob_matni))

            # 3. 🔥 SHIFOKORLARNING FAYLLARINI KETMA-KET YUBORISH MANTIQI
            for assign in assignments:
                doc_name = assign.doctor.get_full_name() if assign.doctor.get_full_name() else assign.doctor.username
                
                # Agar shifokor bot orqali fayl yuborgan bo'lsa (Telegram File ID bor bo'lsa)
                if assign.doctor_response_file_id:
                    caption_text = f"📄 Fayl: Dr. {doc_name} tashxisi uchun"
                    asyncio.run(send_to_user_bot(bemor_telegram_id, text_message=caption_text, file_to_send=assign.doctor_response_file_id))
                
                # Agar shifokor sayt orqali fayl yuklagan bo'lsa (FileField fayli bor bo'lsa)
                elif assign.doctor_response_file:
                    caption_text = f"📄 Fayl: Dr. {doc_name} tashxisi uchun"
                    # Django fayl obyekti yoki uning URL manzilini botga uzatamiz
                    asyncio.run(send_to_user_bot(bemor_telegram_id, text_message=caption_text, file_to_send=assign.doctor_response_file))

            return Response({"message": "Ariza muvaffaqiyatli yakunlandi, matn va barcha fayllar bemorga yuborildi!"})
            
        except Exception as e:
            return Response({
                "message": "Operatsiya bajarildi, lekin Telegram bot orqali yuborishda xatolik yuz berdi.",
                "details": str(e)
            }, status=status.HTTP_207_MULTI_STATUS)

    # 6. XAVFSIZ FAYL PROXY (MUTLAQO DAXLSID 🔒 - QAT'IY TOPSHIRIQ)
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