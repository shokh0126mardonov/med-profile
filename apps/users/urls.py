from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

from rest_framework.routers import DefaultRouter
from .views import UserViewSet,LoginView,SickModelViewSet,SickComeViews


router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'sicks', SickModelViewSet, basename='sick')

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="token_obtain_pair"),
    path(
        "Sick-Come/<int:pk>/",SickComeViews.as_view()
    ),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('', include(router.urls)),
    path('', include(router.urls)),
]

