from django.contrib import admin

from wellbeing.models import CaseTimelineEvent, DossierAttachment, FollowUpSession, PsychDossier


class SessionInline(admin.TabularInline):
    model = FollowUpSession
    extra = 0


class AttachmentInline(admin.TabularInline):
    model = DossierAttachment
    extra = 0


@admin.register(PsychDossier)
class PsychDossierAdmin(admin.ModelAdmin):
    list_display = ("student", "status", "opened_by", "created_at", "retention_until")
    inlines = [SessionInline, AttachmentInline]


@admin.register(CaseTimelineEvent)
class TimelineAdmin(admin.ModelAdmin):
    list_display = ("dossier", "action", "actor", "created_at")
