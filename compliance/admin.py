from django.contrib import admin

from compliance.models import DataAccessRequest


@admin.register(DataAccessRequest)
class DataAccessRequestAdmin(admin.ModelAdmin):
    list_display = ("student", "request_type", "status", "requester_email", "created_at")
    list_filter = ("request_type", "status")
