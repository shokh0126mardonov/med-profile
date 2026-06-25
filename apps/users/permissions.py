from rest_framework import permissions
from .models import UserRole

class IsOperatorUser(permissions.BasePermission):
    """
    Faqat Operator rolidagi foydalanuvchilarga ruxsat beradi.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role == UserRole.OPERATOR
        )