from django.contrib import admin

from .models import Applications

admin.site.register(
    [
        Applications
    ]
)