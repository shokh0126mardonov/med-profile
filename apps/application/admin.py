# apps/application/admin.py

from django.contrib import admin
from .models import Applications

@admin.register(Applications)
class ApplicationsAdmin(admin.ModelAdmin):
    fields = [
        'sick', 'text', 'status', 'file_id', 
        'operator_response', 'created_at', 'updated_at'
    ]
    readonly_fields = ['file_id', 'created_at', 'updated_at']
    list_display = ['id', 'sick', 'status', 'created_at']