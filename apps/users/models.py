from django.db import models

from django.contrib.auth.models import AbstractUser


class UserRole(models.TextChoices):
    USER = 'USER','User'
    OPERATOR = 'OPERATOR','Operator'
    DOCTOR = 'DOCTOR','Doctor'

class User(AbstractUser):
    role = models.CharField(choices=UserRole.choices)