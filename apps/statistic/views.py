from apps.application.models import Applications, ApplicationAssignment
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q, CharField
from django.db.models.functions import Cast
from django.contrib.auth import get_user_model
from django.http import Http404
from drf_spectacular.utils import extend_schema, OpenApiParameter

from apps.users.models import SickModel

User = get_user_model()

class ApplicationStatisticsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Umumiy, ariza yoki shifokor bo'yicha statistika",
        description="Filtrlar orqali umumiy, bitta ariza ichidagi shifokorlar holati yoki bitta shifokorga tegishli arizalar ro'yxatini olish.",
        parameters=[
            OpenApiParameter(name='application_id', type=int, description="Konkret ariza IDsi (ixtiyoriy)", required=False),
            OpenApiParameter(name='doctor_id', type=int, description="Konkret shifokor IDsi (ixtiyoriy)", required=False)
        ],
        responses={200: dict}
    )
    def get(self, request, *args, **kwargs):
        application_id = request.query_params.get('application_id')
        doctor_id = request.query_params.get('doctor_id')

        # =====================================================================
        # 🎯 VARIANT C: ANIQ SHIFOKOR BO'YICHA ARIZALAR RO'YXATI VA STATISTIKASI
        # =====================================================================
# =====================================================================
        # 🎯 VARIANT C: ANIQ SHIFOKOR BO'YICHA ARIZALAR ID RO'YXATI (100% TO'G'RILANDI)
        # =====================================================================
        if doctor_id:
            try:
                doctor = User.objects.get(pk=doctor_id, role='DOCTOR')
            except User.DoesNotExist:
                raise Http404("Bunday shifokor topilmadi yoki foydalanuvchi shifokor emas!")

            # Shifokorning barcha biriktiruvlarini olamiz
            doctor_assignments = ApplicationAssignment.objects.filter(doctor=doctor).select_related('application')

            unseen_application_ids = []
            accepted_application_ids = []
            rejected_application_ids = []

            for asn in doctor_assignments:
                app = asn.application
                if not app:
                    continue

                # Global status qanday bo'lishidan qat'iy nazar, faqat shifokor munosabatiga qaraymiz!
                if asn.status == 'ACCEPTED':
                    accepted_application_ids.append(app.id)
                elif asn.status == 'REJECTED':
                    rejected_application_ids.append(app.id)
                elif asn.status == 'UNSEEN':
                    # 🚀 MANA ENERGIYANI KO'TARADIGAN JOX: Ortiqcha global status shartini olib tashladik!
                    unseen_application_ids.append(app.id)

            return Response({
                "mode": "single_doctor_stats",
                "doctor": {
                    "id": doctor.id,
                    "username": doctor.username,
                    "phone": str(doctor.phone) if hasattr(doctor, 'phone') else None,
                },
                "statistics": {
                    "total_assigned_cases": doctor_assignments.count(),
                    "unseen_count": len(unseen_application_ids),
                    "accepted_count": len(accepted_application_ids),
                    "rejected_count": len(rejected_application_ids)
                },
                "applications": {
                    "unseen": unseen_application_ids,       # Endi [30] deb aniq chiqadi!
                    "accepted": accepted_application_ids,   
                    "rejected": rejected_application_ids    
                }
            })

        # =====================================================================
        # 🎯 VARIANT A: ANIQ ARIZA BO'YICHA STATISTIKA (SHIFOKORLAR HOLATI)
        # =====================================================================
        if application_id:
            try:
                application = Applications.objects.get(pk=application_id)
            except Applications.DoesNotExist:
                raise Http404("Bunday ariza topilmadi!")

            assignments = ApplicationAssignment.objects.filter(application=application).select_related('doctor')

            total_unseen = 0
            total_accepted = 0
            total_rejected = 0
            doctors_details = []

            for asn in assignments:
                doc = asn.doctor
                if not doc:
                    continue
                phone_num = str(doc.phone) if hasattr(doc, 'phone') else None
                
                if asn.status == 'UNSEEN':
                    total_unseen += 1
                elif asn.status == 'ACCEPTED':
                    total_accepted += 1
                elif asn.status == 'REJECTED':
                    total_rejected += 1

                doctors_details.append({
                    "assignment_id": asn.id,
                    "id": doc.id,
                    "username": doc.username,
                    "phone": phone_num,
                    "status": asn.status,  
                    "response": asn.doctor_response_text if asn.doctor_response_text else None
                })

            return Response({
                "mode": "single_application_stats",
                "application_id": application.id,
                "status": application.status,
                "statistics": {
                    "total_assigned": assignments.count(),
                    "unseen": total_unseen,
                    "accepted": total_accepted,
                    "rejected": total_rejected
                },
                "doctors": doctors_details 
            })

        # =====================================================================
        # 📊 VARIANT B: UMUMIY GLOBAL STATISTIKA (BOSH SAHIFA UCHUN)
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
            status='UNSEEN'
        ).values_list('doctor_id', flat=True).distinct()

        pending_doctors_list = User.objects.filter(
            id__in=unseen_doctor_ids,
            role='DOCTOR'
        ).annotate(
            phone_str=Cast('phone', output_field=CharField())
        ).values('id', 'username', 'phone_str')

        doctors_stats = User.objects.filter(role='DOCTOR').annotate(
            phone_str=Cast('phone', output_field=CharField()),
            total_assigned=Count('assigned_cases', distinct=True), 
            unseen_count=Count('assigned_cases', filter=Q(assigned_cases__status='UNSEEN'), distinct=True),
            accepted_count=Count('assigned_cases', filter=Q(assigned_cases__status='ACCEPTED'), distinct=True),
            rejected_count=Count('assigned_cases', filter=Q(assigned_cases__status='REJECTED'), distinct=True)
        ).values(
            'id', 'username', 'phone_str',
            'total_assigned', 'unseen_count', 'accepted_count', 'rejected_count'
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
                "total_applications": global_stats['total_applications'] or 0,
                "new_count": global_stats['new_count'] or 0,
                "assigned_count": global_stats['assigned_count'] or 0,
                "rejected_count": global_stats['rejected_count'] or 0,
                "completed_count": global_stats['completed_count'] or 0,
                "closed_count": global_stats['closed_count'] or 0,
                "total_doctors": total_doctors_count,                 
                "total_registered_patients": sick_stats['total_sicks'] or 0, 
                "arrived_patients_count": sick_stats['arrived_sicks'] or 0,  
                "not_arrived_patients_count": sick_stats['not_arrived_sicks'] or 0
            },
            "unseen_doctors_details": formatted_pending_doctors,
            "doctors_stats": formatted_doctors_stats
        })