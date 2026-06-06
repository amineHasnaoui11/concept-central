from django.contrib import admin

from education.models import (
    Alert,
    DailyAttendance,
    Intervention,
    RiskThreshold,
    SubjectGrade,
    TeacherRequest,
    WeeklyEntry,
)


@admin.register(RiskThreshold)
class RiskThresholdAdmin(admin.ModelAdmin):
    list_display = ("name", "max_absences", "critical_score", "is_active")


@admin.register(WeeklyEntry)
class WeeklyEntryAdmin(admin.ModelAdmin):
    list_display = ("student", "week_start", "absences", "risk_score", "risk_level")
    list_filter = ("risk_level",)


@admin.register(SubjectGrade)
class SubjectGradeAdmin(admin.ModelAdmin):
    list_display = ("weekly_entry", "subject", "grade", "previous_grade")
    list_filter = ("subject",)


@admin.register(DailyAttendance)
class DailyAttendanceAdmin(admin.ModelAdmin):
    list_display = ("student", "date", "status")
    list_filter = ("status",)


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ("student", "level", "risk_score", "status", "created_at")
    list_filter = ("status", "level")


@admin.register(Intervention)
class InterventionAdmin(admin.ModelAdmin):
    list_display = ("alert", "intervention_type", "planned_date", "completed", "effectiveness_rating")
    list_filter = ("intervention_type", "completed")


@admin.register(TeacherRequest)
class TeacherRequestAdmin(admin.ModelAdmin):
    list_display = ("subject", "student", "teacher", "priority", "status", "created_at")
    list_filter = ("status", "priority")
