from django.urls import path

from .views import SickComeViews,UserViewSet
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet,LoginView

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="token_obtain_pair"),
    path(
        "Sick-Come/<int:pk>/",SickComeViews.as_view()
    ),
    path('', include(router.urls)),

]
