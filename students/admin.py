from django.contrib import admin

from students.models import ParentConsent, Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("internal_code", "last_name", "first_name", "class_name", "level")
    search_fields = ("internal_code", "last_name", "first_name")
    list_filter = ("level", "class_name")


@admin.register(ParentConsent)
class ParentConsentAdmin(admin.ModelAdmin):
    list_display = ("student", "consent_type", "granted", "granted_at", "revoked_at")
    list_filter = ("consent_type", "granted")
    search_fields = ("student__internal_code", "student__last_name")
