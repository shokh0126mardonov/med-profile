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
        # 🎯 VARIANT C: ANIQ SHIFOKOR BO'YICHA ARIZALAR RO'YXATI
        # =====================================================================
        if doctor_id:
            try:
                doctor = User.objects.get(pk=doctor_id, role='DOCTOR')
            except User.DoesNotExist:
                raise Http404("Bunday shifokor topilmadi yoki foydalanuvchi shifokor emas!")

            doctor_assignments = ApplicationAssignment.objects.filter(doctor=doctor).select_related('application', 'application__sick')

            unseen_applications = []
            accepted_applications = []
            rejected_applications = []

            for asn in doctor_assignments:
                app = asn.application
                app_data = {
                    "application_id": app.id,
                    "patient_phone": str(app.sick.phone) if hasattr(app.sick, 'phone') else None,
                    "global_status": app.status,
                    "text": app.text[:100] + "..." if app.text else "",
                    "responded_at": asn.responded_at
                }

                if asn.status == 'ACCEPTED':
                    app_data["response_text"] = asn.doctor_response_text
                    accepted_applications.append(app_data)
                elif asn.status == 'REJECTED':
                    rejected_applications.append(app_data)
                elif asn.status == 'UNSEEN':
                    # 💡 SIZ AYTGAN SHART: Qolgan barcha ko'rmaganlari ichidan faqat 'NEW' bo'lganlarini UNSEEN qilamiz
                    if app.status == 'NEW':
                        unseen_applications.append(app_data)

            return Response({
                "mode": "single_doctor_stats",
                "doctor": {
                    "id": doctor.id,
                    "username": doctor.username,
                    "phone": str(doctor.phone) if hasattr(doctor, 'phone') else None,
                },
                "statistics": {
                    "total_assigned_cases": doctor_assignments.count(),
                    "unseen_count": len(unseen_applications),
                    "accepted_count": len(accepted_applications),
                    "rejected_count": len(rejected_applications)
                },
                "applications": {
                    "unseen": unseen_applications,       
                    "accepted": accepted_applications,   
                    "rejected": rejected_applications    
                }
            })

        # =====================================================================
        # 🎯 VARIANT A: ANIQ ARIZA BO'YICHA STATISTIKA (BARCHA SHIFOKORLAR UCHUN)
        # =====================================================================
        # =====================================================================
        # 🎯 VARIANT A: ANIQ ARIZA BO'YICHA STATISTIKA (SIGNALDAN KEYINGI HOLAT)
        # =====================================================================
        if application_id:
            try:
                application = Applications.objects.get(pk=application_id)
            except Applications.DoesNotExist:
                raise Http404("Bunday ariza topilmadi!")

            # 🚀 Endi bazada hamma shifokor uchun yozuv borligi aniq!
            assignments = ApplicationAssignment.objects.filter(application=application).select_related('doctor')

            total_unseen = 0
            total_accepted = 0
            total_rejected = 0
            
            doctors_details = []

            for asn in assignments:
                doc = asn.doctor
                phone_num = str(doc.phone) if hasattr(doc, 'phone') else None
                
                if asn.status == 'UNSEEN':
                    total_unseen += 1
                elif asn.status == 'ACCEPTED':
                    total_accepted += 1
                elif asn.status == 'REJECTED':
                    total_rejected += 1

                doctors_details.append({
                    "id": doc.id,
                    "username": doc.username,
                    "phone": phone_num,
                    "status": asn.status, # UNSEEN, ACCEPTED, REJECTED
                    "response": asn.doctor_response_text if asn.doctor_response_text else None
                })

            return Response({
                "mode": "single_application_stats",
                "application_id": application.id,
                "status": application.status,
                "statistics": {
                    "total_assigned": assignments.count(), # Jami shifokorlar soni chiqadi
                    "unseen": total_unseen,
                    "accepted": total_accepted,
                    "rejected": total_rejected
                },
                "doctors": doctors_details 
            })

        # =====================================================================
        # 📊 VARIANT B: UMUMIY GLOBAL STATISTIKA
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