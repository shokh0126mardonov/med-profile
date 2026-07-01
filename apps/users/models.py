from django.db import models

from django.contrib.auth.models import AbstractUser
from phonenumber_field.modelfields import PhoneNumberField

class UserRole(models.TextChoices):
    OPERATOR = 'OPERATOR','Operator'
    DOCTOR = 'DOCTOR','Doctor'

class User(AbstractUser):
    role = models.CharField(choices=UserRole.choices)
    phone = PhoneNumberField(unique=True, region="UZ", blank=True, null=True)

    def __str__(self):
        return f"{self.pk} {self.username}"

    class Meta:
        ordering = ['-pk']



class SickModel(models.Model):
    full_name = models.CharField(max_length=256)
    telegram_id = models.BigIntegerField(unique=True,null=True,blank=True)
    phone = PhoneNumberField(unique=True, region="UZ", blank=True, null=True)
    to_come = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.pk} and {self.full_name }and {self.phone} "
    

    class Meta:
        ordering = ['-pk']