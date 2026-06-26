from django.urls import path
from .views import ApplicationStatisticsAPIView

urlpatterns = [
    path('applications/statistics/', ApplicationStatisticsAPIView.as_view(), name='application-stats'),
]