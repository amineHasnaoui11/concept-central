from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.decorators import role_required
from accounts.models import Role
from audit.models import AuditLog, log_event
from meetings.forms import (
    MeetingProposalForm,
    StudentCancelMeetingForm,
    StudentResponseForm,
)
from meetings.models import Meeting
from notifications.models import Notification
from notifications.services import notify
from students.models import Student
from wellbeing.access import can_manage_psych_dossier
from wellbeing.models import PsychDossier, add_timeline_event


# ============================================================
# CÔTÉ CONSEILLER : proposer / annuler un RDV
# ============================================================
@login_required
@role_required(Role.SUPERVISOR)
def propose_meeting(request, dossier_id):
    """Le conseiller propose un RDV à l'élève dans le cadre d'un dossier."""
    dossier = get_object_or_404(PsychDossier, pk=dossier_id)

    # Vérifie que l'élève a bien un compte
    if not dossier.student.user:
        messages.warning(
            request,
            "L'élève n'a pas encore de compte de connexion. "
            "Générez d'abord une invitation pour qu'il puisse créer son compte.",
        )
        return redirect("accounts:invitation_generate", student_id=dossier.student.pk)

    if not can_manage_psych_dossier(request.user):
        raise PermissionDenied("Seul le conseiller peut proposer un RDV.")

    # Pré-remplissage si on vient d'une contre-proposition
    initial = {}
    if request.method == "GET" and "suggest" in request.GET:
        initial["scheduled_at"] = request.GET["suggest"]

    if request.method == "POST":
        form = MeetingProposalForm(request.POST)
        if form.is_valid():
            meeting = form.save(commit=False)
            meeting.dossier = dossier
            meeting.student = dossier.student
            meeting.counselor = request.user
            meeting.save()

            notify(
                event=Notification.Event.INTERVENTION_PLANNED,
                recipient_user=dossier.student.user,
                title="📅 Nouveau rendez-vous proposé",
                message=(
                    f"Le conseiller vous propose un RDV : "
                    f"{meeting.topic} le {meeting.scheduled_at:%d/%m/%Y à %H:%M}."
                ),
                link=f"/meetings/{meeting.pk}/",
                also_email=True,
            )

            add_timeline_event(
                dossier, request.user,
                "RDV proposé",
                f"{meeting.topic} le {meeting.scheduled_at:%d/%m/%Y %H:%M}",
            )

            messages.success(request, "RDV proposé. L'élève recevra une notification.")
            return redirect("meetings:detail", pk=meeting.pk)
    else:
        form = MeetingProposalForm(initial=initial)

    return render(
        request,
        "meetings/propose.html",
        {"form": form, "dossier": dossier},
    )


# ============================================================
# CÔTÉ ÉLÈVE : approuver / refuser / proposer alternative
# ============================================================
@login_required
@role_required(Role.STUDENT)
def respond_to_meeting(request, pk):
    """L'élève approuve, refuse ou propose une date alternative."""
    meeting = get_object_or_404(Meeting, pk=pk)

    if not hasattr(request.user, "student_profile") or request.user.student_profile != meeting.student:
        raise PermissionDenied("Ce n'est pas votre RDV.")

    if meeting.status != Meeting.Status.PROPOSED:
        messages.info(
            request,
            f"Ce RDV a déjà reçu une réponse ({meeting.get_status_display()}).",
        )
        return redirect("meetings:detail", pk=pk)

    if request.method == "POST":
        form = StudentResponseForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data["action"]
            message = form.cleaned_data["message"]

            if action == "approve":
                meeting.approve(message=message)
                notify(
                    event=Notification.Event.INTERVENTION_PLANNED,
                    recipient_user=meeting.counselor,
                    title="✅ RDV approuvé par l'élève",
                    message=(
                        f"{meeting.student} a approuvé le RDV du "
                        f"{meeting.scheduled_at:%d/%m/%Y à %H:%M}."
                    ),
                    link=f"/meetings/{meeting.pk}/",
                    also_email=True,
                )
                messages.success(request, "RDV approuvé. Le conseiller a été notifié.")

            elif action == "reject":
                meeting.reject(message=message)
                notify(
                    event=Notification.Event.INTERVENTION_PLANNED,
                    recipient_user=meeting.counselor,
                    title="❌ RDV refusé par l'élève",
                    message=f"{meeting.student} a refusé le RDV proposé.",
                    link=f"/meetings/{meeting.pk}/",
                    also_email=True,
                )
                messages.info(request, "RDV refusé. Le conseiller a été notifié.")

            elif action == "propose_alternate":
                alt = form.cleaned_data["alternative_datetime"]
                meeting.propose_alternative(alt, message=message)
                notify(
                    event=Notification.Event.INTERVENTION_PLANNED,
                    recipient_user=meeting.counselor,
                    title="📅 Contre-proposition de l'élève",
                    message=(
                        f"{meeting.student} propose une autre date : "
                        f"{alt:%d/%m/%Y à %H:%M}."
                    ),
                    link=f"/meetings/{meeting.pk}/",
                    also_email=True,
                )
                messages.success(
                    request,
                    "Votre proposition a été envoyée au conseiller.",
                )

            return redirect("meetings:detail", pk=pk)
    else:
        form = StudentResponseForm()

    return render(
        request,
        "meetings/respond.html",
        {"meeting": meeting, "form": form},
    )


@login_required
@role_required(Role.STUDENT)
def student_cancel_meeting(request, pk):
    """L'élève annule un RDV qu'il avait approuvé (avant qu'il ait lieu)."""
    meeting = get_object_or_404(Meeting, pk=pk)

    if not hasattr(request.user, "student_profile") or request.user.student_profile != meeting.student:
        raise PermissionDenied("Ce n'est pas votre RDV.")

    if meeting.status != Meeting.Status.APPROVED:
        messages.error(request, "Vous ne pouvez annuler qu'un RDV approuvé.")
        return redirect("meetings:detail", pk=pk)

    if meeting.is_past:
        messages.error(request, "Ce RDV est déjà terminé — impossible à annuler.")
        return redirect("meetings:detail", pk=pk)

    if request.method == "POST":
        form = StudentCancelMeetingForm(request.POST)
        if form.is_valid():
            reason = form.cleaned_data.get("reason", "")
            if reason:
                meeting.student_message = (
                    (meeting.student_message + "\n\n" if meeting.student_message else "")
                    + f"[Annulation] {reason}"
                )
            meeting.cancel(by_user=request.user)
            notify(
                event=Notification.Event.INTERVENTION_PLANNED,
                recipient_user=meeting.counselor,
                title="🚫 RDV annulé par l'élève",
                message=(
                    f"{meeting.student} a annulé le RDV du "
                    f"{meeting.scheduled_at:%d/%m/%Y à %H:%M}."
                    + (f" Raison : {reason}" if reason else "")
                ),
                link=f"/meetings/{meeting.pk}/",
                also_email=True,
            )
            messages.info(request, "RDV annulé. Le conseiller a été notifié.")
            return redirect("meetings:list")
    else:
        form = StudentCancelMeetingForm()

    return render(
        request,
        "meetings/cancel.html",
        {"meeting": meeting, "form": form},
    )


# ============================================================
# DÉTAIL D'UN RDV (vue partagée counselor / student)
# ============================================================
@login_required
def meeting_detail(request, pk):
    meeting = get_object_or_404(Meeting, pk=pk)
    if not meeting.can_be_accessed_by(request.user):
        log_event(
            AuditLog.EventType.ACCESS_DENIED,
            f"Tentative d'accès non autorisée au RDV #{meeting.pk}",
            user=request.user,
            student=meeting.student,
            event="meeting_access_denied",
        )
        raise PermissionDenied("Vous n'êtes pas autorisé à voir ce RDV.")

    is_counselor = request.user == meeting.counselor
    is_student = hasattr(request.user, "student_profile") and request.user.student_profile == meeting.student

    # Annulation possible par le conseiller (avant approbation ou après mais avant l'heure)
    if request.method == "POST" and is_counselor:
        action = request.POST.get("action")
        if action == "cancel" and meeting.status in [Meeting.Status.PROPOSED, Meeting.Status.APPROVED]:
            meeting.cancel()
            notify(
                event=Notification.Event.INTERVENTION_PLANNED,
                recipient_user=meeting.student.user,
                title="RDV annulé",
                message=f"Le RDV du {meeting.scheduled_at:%d/%m/%Y %H:%M} a été annulé.",
                link=f"/meetings/{meeting.pk}/",
                also_email=True,
            )
            messages.info(request, "RDV annulé.")
            return redirect("meetings:detail", pk=pk)

    return render(
        request,
        "meetings/detail.html",
        {
            "meeting": meeting,
            "is_counselor": is_counselor,
            "is_student": is_student,
        },
    )


# ============================================================
# REJOINDRE LE SALON JITSI (à l'heure prévue)
# ============================================================
@login_required
def join_meeting(request, pk):
    """Page contenant l'iframe Jitsi.

    Accessible uniquement :
    - aux 2 parties autorisées
    - dans la fenêtre temporelle [scheduled - 10min, scheduled + 90min]
    - si le RDV est APPROVED
    """
    meeting = get_object_or_404(Meeting, pk=pk)

    if not meeting.can_be_accessed_by(request.user):
        log_event(
            AuditLog.EventType.ACCESS_DENIED,
            f"Tentative non autorisée de rejoindre le RDV #{meeting.pk}",
            user=request.user, student=meeting.student,
            event="meeting_join_denied",
        )
        raise PermissionDenied("Vous n'êtes pas autorisé à rejoindre ce RDV.")

    if meeting.status != Meeting.Status.APPROVED:
        messages.error(request, "Ce RDV n'est pas (ou plus) actif.")
        return redirect("meetings:detail", pk=pk)

    if not meeting.is_joinable_now:
        if timezone.now() < meeting.access_open_at:
            mins = meeting.minutes_until_start
            messages.warning(
                request,
                f"Le salon ouvre 10 minutes avant l'heure. Revenez dans environ {mins} minutes.",
            )
        else:
            messages.warning(request, "Le créneau de ce RDV est terminé.")
        return redirect("meetings:detail", pk=pk)

    # Marquer la connexion
    now = timezone.now()
    is_counselor = request.user == meeting.counselor
    if is_counselor and not meeting.counselor_joined_at:
        meeting.counselor_joined_at = now
        meeting.save(update_fields=["counselor_joined_at"])
    elif not is_counselor and not meeting.student_joined_at:
        meeting.student_joined_at = now
        meeting.save(update_fields=["student_joined_at"])

    log_event(
        AuditLog.EventType.INTERVENTION_PLANNED,
        f"{request.user.username} a rejoint le RDV #{meeting.pk}",
        user=request.user, student=meeting.student,
        event="meeting_joined",
    )

    # Nom affiché dans Jitsi
    if is_counselor:
        display_name = f"{request.user.first_name or 'Conseiller'} (conseiller)"
    else:
        display_name = meeting.student.first_name

    return render(
        request,
        "meetings/join.html",
        {
            "meeting": meeting,
            "display_name": display_name,
            "is_counselor": is_counselor,
        },
    )


# ============================================================
# LISTE DES RDV (vue partagée selon le rôle)
# ============================================================
@login_required
def meeting_list(request):
    """Liste des RDV de l'utilisateur (élève ou conseiller)."""
    user = request.user

    if user.role == Role.STUDENT:
        if not hasattr(user, "student_profile"):
            messages.error(request, "Aucun profil élève associé à votre compte.")
            return redirect("dashboard")
        qs = Meeting.objects.filter(student=user.student_profile)
        role_label = "élève"
    elif user.role == Role.SUPERVISOR:
        qs = Meeting.objects.filter(counselor=user)
        role_label = "conseiller"
    elif user.role == Role.ADMIN:
        qs = Meeting.objects.all()
        role_label = "admin"
    else:
        raise PermissionDenied("Vous n'avez pas accès aux RDV.")

    upcoming = qs.filter(
        status=Meeting.Status.APPROVED,
        scheduled_at__gte=timezone.now(),
    ).order_by("scheduled_at")

    pending = qs.filter(status=Meeting.Status.PROPOSED).order_by("scheduled_at")

    past = qs.filter(
        status__in=[
            Meeting.Status.COMPLETED, Meeting.Status.MISSED,
            Meeting.Status.CANCELLED, Meeting.Status.REJECTED,
        ]
    ).order_by("-scheduled_at")[:20]

    return render(
        request,
        "meetings/list.html",
        {
            "upcoming": upcoming,
            "pending": pending,
            "past": past,
            "role_label": role_label,
        },
    )


# ============================================================
# DASHBOARD ÉLÈVE
# ============================================================
@login_required
@role_required(Role.STUDENT)
def student_dashboard(request):
    """Tableau de bord pour l'élève (connecté avec son compte)."""
    user = request.user
    if not hasattr(user, "student_profile"):
        messages.error(request, "Aucun profil élève associé à votre compte.")
        return redirect("accounts:logout")

    student = user.student_profile
    now = timezone.now()

    pending_meetings = Meeting.objects.filter(
        student=student, status=Meeting.Status.PROPOSED
    ).order_by("scheduled_at")

    upcoming_meetings = Meeting.objects.filter(
        student=student,
        status=Meeting.Status.APPROVED,
        scheduled_at__gte=now,
    ).order_by("scheduled_at")[:5]

    joinable_now = [m for m in upcoming_meetings if m.is_joinable_now]

    return render(
        request,
        "meetings/student_dashboard.html",
        {
            "student": student,
            "pending_meetings": pending_meetings,
            "upcoming_meetings": upcoming_meetings,
            "joinable_now": joinable_now,
        },
    )
