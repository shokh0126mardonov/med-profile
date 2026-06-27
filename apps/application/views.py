from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
import asyncio

from handlers import send_to_user as send_to_user_bot
from .models import Applications
from .serializers import (
    ApplicationListRetrieveSerializer, 
    DoctorResponseSerializer, 
    OperatorResponseSerializer
)
from .permissions import IsDoctor, IsOperator

class ApplicationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Faqat GET (list va retrieve) ishlaydi. 
    Umumiy POST, PUT, PATCH, DELETE so'rovlari mutlaqo bloklangan.
    """
    serializer_class = ApplicationListRetrieveSerializer
    permission_classes = [IsAuthenticated] 

    def get_queryset(self):
        user = self.request.user
        queryset = Applications.objects.all()

        if user.is_authenticated and getattr(user, 'role', None) == 'DOCTOR':
            queryset = queryset.exclude(rejected_by_doctors=user)
            
        return queryset

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def not_my_case(self, request, pk=None):
        application = self.get_object()
        user = request.user

        if getattr(user, 'role', None) != 'DOCTOR':
            return Response({"error": "Faqat shifokorlar arizani rad eta oladi!"}, status=status.HTTP_403_FORBIDDEN)

        application.rejected_by_doctors.add(user)

        if application.doctor == user:
            application.doctor = None
            application.status = 'NEW'
        
        application.save()

        return Response({"message": "Ariza rad etildi. U sizga boshqa ko'rinmaydi va umumiy ro'yxatga qaytarildi."})

    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsDoctor])
    def accept_application(self, request, pk=None):
        application = self.get_object()

        # Arizaning statusi faqat NEW bo'lsagina shifokor qabul qila oladi
        if application.status != 'NEW':
            return Response(
                {"error": "Bu ariza allaqachon qabul qilingan yoki rad etilgan!"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Arizani shifokorning o'ziga biriktiramiz va statusni o'zgartiramiz
        application.doctor = request.user
        application.status = 'ASSIGNED'
        application.save()

        return Response({"message": "Siz ushbu bemor arizasini muvaffaqiyatli qabul qildingiz!"})

# 2-ETAP YANGILANDI: Shifokor javob (tashxis) yozadi yoki uni tahrirlaydi
    # POST /api/applications/<id>/doctor_respond/
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsDoctor])
    def doctor_respond(self, request, pk=None):
        application = self.get_object()

        # Faqat arizani o'ziga biriktirgan shifokor javob bera oladi/tahrirlay oladi
        if application.doctor != request.user:
            return Response(
                {"error": "Siz bu arizaga javob bera olmaysiz, chunki u sizga biriktirilmagan!"}, 
                status=status.HTTP_403_FORBIDDEN
            )

        # 💡 Ariza yopilmagan (status CLOSED bo'lmagan) bo'lsa, shifokor o'zgartirishi mumkin
        if application.status not in ['ASSIGNED', 'COMPLETED']:
            return Response(
                {"error": "Ariza yopilgan yoki hali qabul qilinmagan, unga tashxis yozib bo'lmaydi!"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = DoctorResponseSerializer(instance=application, data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Tashxisni yangilaymiz va statusni COMPLETED (operator kutilmoqda) holatiga o'tkazamiz
        application.doctor_response = serializer.validated_data['doctor_response']
        application.status = 'COMPLETED'
        application.save()

        return Response({"message": "Tashxis muvaffaqiyatli saqlandi/yangilandi!"})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsOperator])
    def operator_respond(self, request, pk=None):
        application = self.get_object()

        # Faqat shifokor tekshirib bo'lgan arizalarga yozish mumkin (Yopilgan bo'lsa ham bo'lmaydi)
        if application.status not in ['COMPLETED']:
            return Response(
                {"error": "Ushbu arizaga shifokor javob bermagan yoki ariza allaqachon bemorga yuborilgan!"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = OperatorResponseSerializer(instance=application, data=request.data)
        serializer.is_valid(raise_exception=True)

        # Izohni saqlaymiz, lekin status hamon COMPLETED ligicha qoladi (Yuborilgani yoq)
        application.operator_response = serializer.validated_data['operator_response']
        application.save()

        return Response({
            "message": "Operator izohi loyha sifatida saqlandi. "
                       "Uni tekshirib, 'send_to_user' API orqali bemorga yuborishingiz mumkin."
        })


    # 🔥 4-ETAP (YANGI ALOHIDA API): Izohni tekshirib, bemorga yuborish va arizani yopish
    # POST /api/applications/<id>/send_to_user/
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsOperator])
    def send_to_user(self, request, pk=None):
        application = self.get_object()

        if application.status != 'COMPLETED':
            return Response(
                {"error": "Bu arizani yuborib bo'lmaydi (yoki shifokor yozmagan, yoki allaqachon yopilgan)."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Agar operator izoh yozishni esdan chiqarib, srazi yubormoqchi bo'lsa cheklaymiz
        if not application.operator_response:
            return Response(
                {"error": "Bemorga yuborishdan oldin operator izohini (operator_response) yozish shart!"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1. Statusni rasman yopamiz (Endi umuman tahrirlab bo'lmaydi)
        application.status = 'CLOSED'
        application.save()

        # 2. 🤖 Telegram bot orqali xabar yuborish
        # 2. 🤖 Telegram bot orqali xabar yuborish
        try:
            bemor_telegram_id = application.sick.telegram_id
            
            javob_matni = (
                "🎉 **Sizning arizangiz ko'rib chiqildi!**\n\n"
                f"👨‍⚕️ **Shifokor tashxisi:**\n{application.doctor_response}\n\n"
                f"📋 **Operator izohi:**\n{application.operator_response}\n\n"
                "Sog'ligingizga e'tiborli bo'ling!"
            )

            asyncio.run(
                send_to_user_bot(
                    bemor_telegram_id,javob_matni
                )
            )
                 
            return Response({"message": "Ariza muvaffaqiyatli yopildi va bemorga Telegram orqali yuborildi!"})

        except Exception as e:
            # Agar botda muammo bo'lsa (masalan user botni bloklagan bo'lsa), status baribir CLOSED qoladi, lekin xato qaytadi
            return Response({
                "message": "Ariza tizimda yopildi, lekin Telegram bot orqali yuborishda xatolik yuz berdi.",
                "details": str(e)
            }, status=status.HTTP_207_MULTI_STATUS)