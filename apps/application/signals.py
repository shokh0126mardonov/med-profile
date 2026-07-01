from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from apps.application.models import Applications, ApplicationAssignment

User = get_user_model()

@receiver(post_save, sender=Applications)
def create_assignments_for_all_doctors(sender, instance, created, **kwargs):
    if created:
        doctors = User.objects.filter(role='DOCTOR')
        
        assignments_to_create = [
            ApplicationAssignment(
                application=instance,
                doctor=doctor,
                status='UNSEEN' 
            )
            for doctor in doctors
        ]
        
        if assignments_to_create:
            ApplicationAssignment.objects.bulk_create(assignments_to_create)