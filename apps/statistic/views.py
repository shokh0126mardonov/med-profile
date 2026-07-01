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
        summary="Umumiy, ariza yoki shifokor bo'yicha yangi statistika",
        description="Filtrlar orqali umumiy, bitta ariza ichidagi shifokorlar holati yoki bitta shifokorga tegishli arizalar ID ro'yxatini olish.",
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
        # 🎯 VARIANT C: ANIQ SHIFOKOR BO'YICHA YANGI STATUSLI ARIZALAR ID RO'YXATI
        # =====================================================================
        if doctor_id:
            try:
                doctor = User.objects.get(pk=doctor_id, role='DOCTOR')
            except User.DoesNotExist:
                raise Http404("Bunday shifokor topilmadi yoki foydalanuvchi shifokor emas!")

            doctor_assignments = ApplicationAssignment.objects.filter(doctor=doctor)

            unseen_ids = []
            accepted_ids = []
            rejected_ids = []
            responded_ids = []

            for asn in doctor_assignments:
                if asn.status == 'UNSEEN':
                    unseen_ids.append(asn.application_id)
                elif asn.status == 'ACCEPTED':
                    accepted_ids.append(asn.application_id)
                elif asn.status == 'REJECTED':
                    rejected_ids.append(asn.application_id)
                elif asn.status == 'RESPONDED':
                    responded_ids.append(asn.application_id)

            return Response({
                "mode": "single_doctor_stats",
                "doctor": {
                    "id": doctor.id,
                    "username": doctor.username,
                    "phone": str(doctor.phone) if hasattr(doctor, 'phone') else None,
                },
                "statistics": {
                    "total_assigned_cases": doctor_assignments.count(),
                    "unseen_count": len(unseen_ids),
                    "accepted_count": len(accepted_ids),
                    "rejected_count": len(rejected_ids),
                    "responded_count": len(responded_ids)  # 🚀 Yangi status statistikasi
                },
                "applications": {
                    "unseen": unseen_ids,       
                    "accepted": accepted_ids,   
                    "rejected": rejected_ids,    
                    "responded": responded_ids   # 🚀 Faqat IDlar ro'yxati qaytadi
                }
            })

        # =====================================================================
        # 🎯 VARIANT A: ANIQ ARIZA BO'YICHA SHIFOKORLARNING HOLATI STATISTIKASI
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
            total_responded = 0
            doctors_details = []

            for asn in assignments:
                doc = asn.doctor
                if not doc:
                    continue
                
                if asn.status == 'UNSEEN':
                    total_unseen += 1
                elif asn.status == 'ACCEPTED':
                    total_accepted += 1
                elif asn.status == 'REJECTED':
                    total_rejected += 1
                elif asn.status == 'RESPONDED':
                    total_responded += 1

                doctors_details.append({
                    "assignment_id": asn.id,
                    "id": doc.id,
                    "username": doc.username,
                    "phone": str(doc.phone) if hasattr(doc, 'phone') else None,
                    "status": asn.status,  # UNSEEN, ACCEPTED, REJECTED, RESPONDED
                    "response": asn.doctor_response_text if asn.doctor_response_text else None
                })

            return Response({
                "mode": "single_application_stats",
                "application_id": application.id,
                "statistics": {
                    "total_assigned_doctors": assignments.count(),
                    "unseen": total_unseen,
                    "accepted": total_accepted,
                    "rejected": total_rejected,
                    "responded": total_responded  # 🚀 Yangi hisoblagich
                },
                "doctors": doctors_details 
            })

        # =====================================================================
        # 📊 VARIANT B: UMUMIY GLOBAL STATISTIKA (BOSH SAHIFA UCHUN)
        # =====================================================================
        
        # 1. Bemorlar statistikasi
        sick_stats = SickModel.objects.aggregate(
            total_sicks=Count('id'),
            arrived_sicks=Count('id', filter=Q(to_come=True)),
            not_arrived_sicks=Count('id', filter=Q(to_come=False))
        )

        total_doctors_count = User.objects.filter(role='DOCTOR').count()
        total_applications_count = Applications.objects.count()

        # 2. Kamida bitta arizani hali KO'RMAGAN (UNSEEN) shifokorlar ro'yxati
        unseen_doctor_ids = ApplicationAssignment.objects.filter(
            status='UNSEEN'
        ).values_list('doctor_id', flat=True).distinct()

        pending_doctors_list = User.objects.filter(
            id__in=unseen_doctor_ids,
            role='DOCTOR'
        ).annotate(
            phone_str=Cast('phone', output_field=CharField())
        ).values('id', 'username', 'phone_str')

        # 3. Barcha shifokorlarning shaxsiy munosabat ko'rsatkichlari (YANGILANDI 🚀)
        doctors_stats = User.objects.filter(role='DOCTOR').annotate(
            phone_str=Cast('phone', output_field=CharField()),
            total_assigned=Count('assigned_cases', distinct=True), 
            unseen_count=Count('assigned_cases', filter=Q(assigned_cases__status='UNSEEN'), distinct=True),
            accepted_count=Count('assigned_cases', filter=Q(assigned_cases__status='ACCEPTED'), distinct=True),
            rejected_count=Count('assigned_cases', filter=Q(assigned_cases__status='REJECTED'), distinct=True),
            responded_count=Count('assigned_cases', filter=Q(assigned_cases__status='RESPONDED'), distinct=True) # 🚀 Qo'shildi
        ).values(
            'id', 'username', 'phone_str',
            'total_assigned', 'unseen_count', 'accepted_count', 'rejected_count', 'responded_count'
        )

        # Telefon formatlarini to'g'rilash
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
                "total_applications": total_applications_count,
                "total_doctors": total_doctors_count,                 
                "total_registered_patients": sick_stats['total_sicks'] or 0, 
                "arrived_patients_count": sick_stats['arrived_sicks'] or 0,  
                "not_arrived_patients_count": sick_stats['not_arrived_sicks'] or 0
            },
            "unseen_doctors_details": formatted_pending_doctors, # Hali biror arizani ochib ko'rmagan doktorlar
            "doctors_stats": formatted_doctors_stats # Har bir doktor qancha unseeen, qancha responded qilgani
        })