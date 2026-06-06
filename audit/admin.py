from django.contrib import admin

from audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("event_type", "user", "student", "created_at")
    list_filter = ("event_type",)
    readonly_fields = ("created_at",)
