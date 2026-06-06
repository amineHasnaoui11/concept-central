from django.contrib import admin

from meetings.models import Meeting


@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ("student", "counselor", "scheduled_at", "status", "topic")
    list_filter = ("status",)
    search_fields = ("student__internal_code", "student__last_name", "topic")
    readonly_fields = ("room_token", "created_at", "responded_at",
                       "counselor_joined_at", "student_joined_at", "completed_at")
