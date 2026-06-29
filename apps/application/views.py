import os
import django
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
import asyncio
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema

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
        queryset = Applications.objects.all()

        # 💡 SHIFOKORLAR UCHUN FILTR:
        if user.is_authenticated and getattr(user, 'role', None) == 'DOCTOR':
            queryset = queryset.filter(
                Q(status='NEW') |                     
                Q(doctors=user)  # 💡 Many-to-Many'da o'zi biriktirilgan arizalar
            ).exclude(
                rejected_by_doctors=user
            ).distinct() # Takrorlanishlarning oldini olish uchun
            
        return queryset

    # 1. SHIFOKOR ARIZANI RAD ETISHI
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def not_my_case(self, request, pk=None):
        application = self.get_object()
        user = request.user

        if getattr(user, 'role', None) != 'DOCTOR':
            return Response({"error": "Faqat shifokorlar arizani rad eta oladi!"}, status=status.HTTP_403_FORBIDDEN)

        # Qora ro'yxatga qo'shamiz (boshqa unga ko'rinmaydi)
        application.rejected_by_doctors.add(user)

        # 💡 Agar o'rta jadvalda shu shifokor biriktirilgan bo'lsa, o'chirib tashlaymiz
        assignment = ApplicationAssignment.objects.filter(application=application, doctor=user).first()
        if assignment:
            assignment.delete()
            
            # Agar arizada boshqa shifokor qolmagan bo'lsa, statusni NEW qilamiz
            if not application.doctors.exists():
                application.status = 'NEW'
                application.save()

        return Response({"message": "Ariza rad etildi. U sizga boshqa ko'rinmaydi."})

    @extend_schema(request=None)
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsDoctor])
    def accept_application(self, request, pk=None):
        application = self.get_object()
        user = request.user

        # Allaqachon o'ziga biriktirganmi tekshiramiz
        if application.doctors.filter(id=user.id).exists():
            return Response({"error": "Siz bu arizani allaqachon o'zingizga biriktirgan ekansiz!"}, status=status.HTTP_400_BAD_REQUEST)

        # 💡 O'rta jadval orqali shifokorni bog'laymiz
        ApplicationAssignment.objects.create(application=application, doctor=user)

        # Statusni o'zgartiramiz
        application.status = 'ASSIGNED'
        application.save()

        return Response({"message": "Siz ushbu bemor arizasini muvaffaqiyatli qabul qildingiz!"})

    # 3. SHIFOKOR TASHXIS (MATN + FAYL) YUBORISHI / TAHRIRLASHI
    # 3. SHIFOKOR TASHXIS (MATN + FAYL) YUBORISHI / TAHRIRLASHI
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsDoctor])
    def doctor_respond(self, request, pk=None):
        application = self.get_object()
        user = request.user

        # O'rta jadvaldan joriy shifokorning biriktiruvini qidiramiz
        assignment = ApplicationAssignment.objects.filter(application=application, doctor=user).first()
        if not assignment:
            return Response(
                {"error": "Siz bu arizaga javob bera olmaysiz, chunki u sizga biriktirilmagan!"}, 
                status=status.HTTP_403_FORBIDDEN
            )

        if application.status not in ['ASSIGNED', 'COMPLETED']:
            return Response(
                {"error": "Ariza yopilgan yoki hali qabul qilinmagan, unga tashxis yozib bo'lmaydi!"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # 💡 1-QADAM: Matn kelganini va u bo'sh emasligini API darajasida ham qattiq tekshiramiz
        doctor_response_text = request.data.get('doctor_response_text', '').strip()
        if not doctor_response_text:
            return Response(
                {"doctor_response_text": ["Tashxis matnini yuborish majburiy! Bo'sh bo'lishi mumkin emas."]},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 💡 2-QADAM: partial=True ni olib tashladik, endi validation to'liq ishlaydi
        serializer = DoctorResponseSerializer(instance=assignment, data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # O'rta jadvaldagi ma'lumotlarni saqlaymiz
        serializer.save(responded_at=timezone.now())

        # Arizaning barcha shifokorlar ko'rgan umumiy holatini yangilaymiz
        application.status = 'COMPLETED'
        application.save()

        return Response({"message": "Tashxis va hujjat muvaffaqiyatli saqlandi!"})
    
    # 4. OPERATOR IZOHI
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

        # 1. Statusni CLOSED qilamiz
        application.status = 'CLOSED'
        application.save()

        # 2. Barcha shifokorlar javoblarini matnga jamlaymiz
        shifokorlar_javobi = ""
        assignments = application.assignments.filter(doctor_response_text__isnull=False)
        
        for idx, assign in enumerate(assignments, 1):
            shifokorlar_javobi += f"\n👨‍⚕️ {idx}-Shifokor ({assign.doctor.get_full_name()}):\n{assign.doctor_response_text}\n"

        # 3. 🤖 Telegram bot orqali xabar yuborish
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