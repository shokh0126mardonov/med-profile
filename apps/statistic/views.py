from apps.application.models import Applications
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q, CharField
from django.db.models.functions import Cast
from django.contrib.auth import get_user_model

from apps.users.models import SickModel  # 💡 Bemorlar modelini import qilamiz

User = get_user_model()

class ApplicationStatisticsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        
        sick_stats = SickModel.objects.aggregate(
            total_sicks=Count('id'),
            arrived_sicks=Count('id', filter=Q(to_come=True)),
            not_arrived_sicks=Count('id', filter=Q(to_come=False))
        )

        # 2. SHIFOKORLARNING UMUMIY SONI
        total_doctors_count = User.objects.filter(role='DOCTOR').count() # 💡 Jami shifokorlar soni

        # 3. ARIZALAR STATISTIKASI (Statuslar bo'yicha)
        global_stats = Applications.objects.aggregate(
            total_applications=Count('id'),
            new_count=Count('id', filter=Q(status='NEW')),
            assigned_count=Count('id', filter=Q(status='ASSIGNED')),
            rejected_count=Count('id', filter=Q(status='REJECTED')),
            completed_count=Count('id', filter=Q(status='COMPLETED')),
            closed_count=Count('id', filter=Q(status='CLOSED'))
        )

        # 4. SHIFOKORLAR KESIMIDAGI STATISTIKA (Har bir shifokor ish unumdorligi)
        doctors_stats = User.objects.filter(role='DOCTOR').annotate(
            phone_str=Cast('phone', output_field=CharField()),
            total_assigned=Count('doctor_applications'),
            pending_response=Count('doctor_applications', filter=Q(doctor_applications__status='ASSIGNED')),
            completed_response=Count('doctor_applications', filter=Q(doctor_applications__status='COMPLETED')),
            closed_response=Count('doctor_applications', filter=Q(doctor_applications__status='CLOSED')),
            total_answered=Count('doctor_applications', filter=Q(doctor_applications__status__in=['COMPLETED', 'CLOSED']))
        ).values(
            'id', 'username', 'first_name', 'last_name', 'phone_str',
            'total_assigned', 'pending_response', 'completed_response', 'closed_response', 'total_answered'
        )

        # Telefon raqam formatini to'g'rilash (JSON serializable qilish)
        formatted_doctors_stats = []
        for doc in doctors_stats:
            doc['phone'] = doc.pop('phone_str')
            formatted_doctors_stats.append(doc)

        # 5. YAKUNIY BIZNES JAVOBNI FORMATLAB QAYTARISH
        return Response({
            "global_stats": {
                "total_applications": global_stats['total_applications'],
                "new_count": global_stats['new_count'],
                "assigned_count": global_stats['assigned_count'],
                "rejected_count": global_stats['rejected_count'],
                "completed_count": global_stats['completed_count'],
                "closed_count": global_stats['closed_count'],
                
                # 💡 Yangi qo'shilgan ko'rsatkichlar:
                "total_doctors": total_doctors_count,                 # Jami shifokorlar
                "total_registered_patients": sick_stats['total_sicks'], # Jami ro'yxatdan o'tgan bemorlar
                "arrived_patients_count": sick_stats['arrived_sicks'],  # Markazga kelgan bemorlar (to_come=True)
                "not_arrived_patients_count": sick_stats['not_arrived_sicks'] # Markazga kelmagan bemorlar
            },
            "doctors_stats": formatted_doctors_stats
        })