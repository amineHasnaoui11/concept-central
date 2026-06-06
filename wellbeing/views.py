from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import role_required
from accounts.models import Role
from audit.models import AuditLog, log_event
from education.models import Alert
from students.models import Student
from wellbeing.access import can_manage_psych_dossier, can_view_psych_dossier
from wellbeing.forms import AttachmentForm, DossierForm, SessionForm
from wellbeing.models import PsychDossier, add_timeline_event
from wellbeing.services import mark_missed_sessions


def _deny_operator_psych_access(request, student, dossier):
    log_event(
        AuditLog.EventType.ACCESS_DENIED,
        (
            f"Tentative d'accès au dossier psychologique par "
            f"{request.user.username} (rôle Opérateur)."
        ),
        user=request.user,
        student=student,
        reason="violation_de_role",
        resource="psych_dossier",
        dossier_id=dossier.pk,
    )
    raise PermissionDenied(
        "Accès refusé : les dossiers psychologiques sont réservés au conseiller."
    )


@login_required
def dossier_detail(request, pk):
    dossier = get_object_or_404(
        PsychDossier.objects.select_related("student"), pk=pk
    )
    if not can_view_psych_dossier(request.user):
        _deny_operator_psych_access(request, dossier.student, dossier)

    mark_missed_sessions()

    session_form = SessionForm(request.POST or None)
    attachment_form = AttachmentForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and can_manage_psych_dossier(request.user):
        action = request.POST.get("action", "session")
        if action == "session" and session_form.is_valid():
            session = session_form.save(commit=False)
            session.dossier = dossier
            session.save()
            add_timeline_event(
                dossier, request.user,
                "Séance planifiée",
                f"Prévue le {session.scheduled_at:%d/%m/%Y %H:%M}",
            )
            messages.success(request, "Séance planifiée.")
            return redirect("wellbeing:dossier_detail", pk=pk)
        elif action == "attachment" and attachment_form.is_valid():
            attachment = attachment_form.save(commit=False)
            attachment.dossier = dossier
            attachment.uploaded_by = request.user
            attachment.save()
            add_timeline_event(
                dossier, request.user,
                "Pièce jointe ajoutée",
                attachment.description or attachment.filename,
            )
            messages.success(request, "Pièce jointe ajoutée.")
            return redirect("wellbeing:dossier_detail", pk=pk)

    return render(
        request,
        "wellbeing/dossier_detail.html",
        {
            "dossier": dossier,
            "sessions": dossier.sessions.all(),
            "attachments": dossier.attachments.all(),
            "timeline": dossier.timeline_events.select_related("actor")[:20],
            "session_form": session_form if can_manage_psych_dossier(request.user) else None,
            "attachment_form": attachment_form if can_manage_psych_dossier(request.user) else None,
        },
    )


@login_required
@role_required(Role.SUPERVISOR)
def create_dossier(request, student_id):
    student = get_object_or_404(Student, pk=student_id)
    if hasattr(student, "psych_dossier"):
        messages.info(request, "Un dossier existe déjà pour cet élève.")
        return redirect("wellbeing:dossier_detail", pk=student.psych_dossier.pk)

    alert = Alert.objects.filter(student=student).order_by("-created_at").first()
    form = DossierForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        dossier = form.save(commit=False)
        dossier.student = student
        dossier.opened_by = request.user
        dossier.opened_from_alert = alert
        dossier.save()
        add_timeline_event(
            dossier, request.user,
            "Ouverture du dossier",
            form.cleaned_data.get("summary", "") or "Pont éducation — santé mentale",
        )
        log_event(
            AuditLog.EventType.DOSSIER_OPENED,
            "Dossier psychologique ouvert",
            user=request.user,
            student=student,
            dossier_id=dossier.pk,
            from_alert=alert.pk if alert else None,
        )
        messages.success(request, "Dossier psychologique créé.")
        return redirect("wellbeing:dossier_detail", pk=dossier.pk)

    return render(
        request,
        "wellbeing/create_dossier.html",
        {"student": student, "form": form, "alert": alert},
    )


@login_required
@role_required(Role.SUPERVISOR, Role.ADMIN)
def dossier_list(request):
    dossiers = PsychDossier.objects.select_related("student").order_by("-created_at")
    return render(request, "wellbeing/dossier_list.html", {"dossiers": dossiers})
