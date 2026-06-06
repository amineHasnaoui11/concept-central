from django.contrib import admin

from notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("event", "title", "recipient_user", "recipient_email", "channel", "created_at", "read_at")
    list_filter = ("event", "channel", "read_at")
    search_fields = ("title", "message", "recipient_email")
    readonly_fields = ("created_at", "sent_via_email_at")
