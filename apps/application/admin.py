from django.contrib import admin
from .models import Applications,ApplicationAssignment


admin.site.register(
    ApplicationAssignment
)

@admin.register(Applications)
class ApplicationsAdmin(admin.ModelAdmin):
    fields = [
        'sick', 'text', 'status', 'user_file_url', 
        'operator_response', 'created_at', 'updated_at'
    ]
    readonly_fields = ['user_file_url', 'created_at', 'updated_at']
    list_display = ['id', 'sick', 'status', 'created_at']