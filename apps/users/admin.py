from django.contrib import admin

from .models import User,SickModel

admin.site.register(
    [
        User,SickModel
    ]
)