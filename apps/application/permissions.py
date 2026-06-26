from rest_framework import permissions

class IsDoctor(permissions.BasePermission):
    """ Faqat shifokorlar uchun ruxsat """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'DOCTOR')

class IsOperator(permissions.BasePermission):
    """ Faqat operatorlar uchun ruxsat """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'OPERATOR')