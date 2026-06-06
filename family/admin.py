from django.contrib import admin

from family.models import ParentMagicLink


@admin.register(ParentMagicLink)
class ParentMagicLinkAdmin(admin.ModelAdmin):
    list_display = ("parent_email", "created_at", "expires_at", "used_at", "ip_address")
    list_filter = ("used_at",)
    search_fields = ("parent_email",)
    readonly_fields = ("token", "created_at", "expires_at", "used_at", "ip_address", "parent_email")
