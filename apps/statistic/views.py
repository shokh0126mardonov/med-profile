from apps.application.models import Applications, ApplicationAssignment
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q, CharField
from django.db.models.functions import Cast
from django.contrib.auth import get_user_model
from django.http import Http404
from drf_spectacular.utils import extend_schema, OpenApiParameter  # Swagger uchun

from apps.users.models import SickModel

User = get_user_model()

class ApplicationStatisticsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Umumiy yoki aniq bir ariza bo'yicha statistika",
        description="Agar application_id yuborilsa, faqat o'sha arizani shifokorlar qanday ko'rganini chiqaradi.",
        parameters=[
            OpenApiParameter(name='application_id', type=int, description="Konkret ariza IDsi (ixtiyoriy)", required=False)
        ],
        responses={200: dict}
    )
    def get(self, request, *args, **kwargs):
        # 💡 URL'dan ?application_id=... parametrini tekshiramiz
        application_id = request.query_params.get('application_id')

        # =====================================================================
        # 🎯 VARIANT A: OPERATOR ANIQ BITTA ARIZANI SO'RAGANDA (?application_id=2)
        # =====================================================================
        if application_id:
            try:
                application = Applications.objects.get(pk=application_id)
            except Applications.DoesNotExist:
                raise Http404("Bunday ariza topilmadi!")

            assignments = ApplicationAssignment.objects.filter(application=application)

            total_accepted = assignments.filter(doctor_response_text__isnull=False).exclude(doctor_response_text='').count()
            total_unseen = assignments.filter(Q(doctor_response_text__isnull=True) | Q(doctor_response_text='')).count()
            total_rejected = 1 if application.status == 'REJECTED' else 0

            # Ko'rmagan shifokorlar kimligi
            unseen_doctor_ids = assignments.filter(
                Q(doctor_response_text__isnull=True) | Q(doctor_response_text='')
            ).values_list('doctor_id', flat=True)

            unseen_doctors = User.objects.filter(id__in=unseen_doctor_ids).annotate(
                phone_str=Cast('phone', output_field=CharField())
            ).values('id', 'username', 'first_name', 'last_name', 'phone_str')

            formatted_unseen_doctors = []
            for doc in unseen_doctors:
                doc['phone'] = doc.pop('phone_str')
                formatted_doctors_stats = [] # xavfsizlik uchun bo'sh ro'yxat
                formatted_unseen_doctors.append(doc)

            return Response({
                "mode": "single_application_stats",
                "application_id": application.id,
                "text": application.text,
                "status": application.status,
                "statistics": {
                    "total_doctors_assigned": assignments.count(),
                    "accepted_count": total_accepted,
                    "unseen_count": total_unseen,
                    "rejected_count": total_rejected
                },
                "unseen_doctors_details": formatted_unseen_doctors
            })

        # =====================================================================
        # 📊 VARIANT B: HECH NARSA YUBORILMASA – UMUMIY GLOBAL STATISTIKA
        # =====================================================================
        sick_stats = SickModel.objects.aggregate(
            total_sicks=Count('id'),
            arrived_sicks=Count('id', filter=Q(to_come=True)),
            not_arrived_sicks=Count('id', filter=Q(to_come=False))
        )

        total_doctors_count = User.objects.filter(role='DOCTOR').count()

        global_stats = Applications.objects.aggregate(
            total_applications=Count('id'),
            new_count=Count('id', filter=Q(status='NEW')),
            assigned_count=Count('id', filter=Q(status='ASSIGNED')),
            rejected_count=Count('id', filter=Q(status='REJECTED')),
            completed_count=Count('id', filter=Q(status='COMPLETED')),
            closed_count=Count('id', filter=Q(status='CLOSED'))
        )

        unseen_doctor_ids = ApplicationAssignment.objects.filter(
            Q(doctor_response_text__isnull=True) | Q(doctor_response_text='')
        ).values_list('doctor_id', flat=True).distinct()

        pending_doctors_list = User.objects.filter(
            id__in=unseen_doctor_ids,
            role='DOCTOR'
        ).annotate(
            phone_str=Cast('phone', output_field=CharField())
        ).values('id', 'username', 'first_name', 'last_name', 'phone_str')

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

        formatted_doctors_stats = []
        for doc in doctors_stats:
            doc['phone'] = doc.pop('phone_str')
            formatted_doctors_stats.append(doc)

        formatted_pending_doctors = []
        for doc in pending_doctors_list:
            doc['phone'] = doc.pop('phone_str')
            formatted_pending_doctors.append(doc)

        return Response({
            "mode": "global_stats",
            "global_stats": {
                "total_applications": global_stats['total_applications'],
                "new_count": global_stats['new_count'],
                "assigned_count": global_stats['assigned_count'],
                "rejected_count": global_stats['rejected_count'],
                "completed_count": global_stats['completed_count'],
                "closed_count": global_stats['closed_count'],
                "total_doctors": total_doctors_count,                 
                "total_registered_patients": sick_stats['total_sicks'], 
                "arrived_patients_count": sick_stats['arrived_sicks'],  
                "not_arrived_patients_count": sick_stats['not_arrived_sicks']
            },
            "unseen_doctors_details": formatted_pending_doctors,
            "doctors_stats": formatted_doctors_stats
        })