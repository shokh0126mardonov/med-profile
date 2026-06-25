from django.urls import path

from .views import SickComeViews

urlpatterns = [
    path(
        "Sick-Come/<int:pk>/",SickComeViews.as_view()
    )
]
