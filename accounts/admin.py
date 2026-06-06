from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from accounts.invitations import StudentInvitation
from accounts.models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "role", "is_staff")
    list_filter = ("role", "is_staff")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Concept Central", {"fields": ("role",)}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Concept Central", {"fields": ("role",)}),
    )


@admin.register(StudentInvitation)
class StudentInvitationAdmin(admin.ModelAdmin):
    list_display = ("code", "student", "created_by", "created_at", "expires_at", "used_at")
    list_filter = ("used_at",)
    search_fields = ("code", "student__internal_code", "student__last_name")
    readonly_fields = ("code", "created_at", "used_at", "used_by_user")
