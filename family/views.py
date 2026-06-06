from datetime import date, timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django_ratelimit.decorators import ratelimit
from django_ratelimit.exceptions import Ratelimited

from audit.models import AuditLog, log_event
from education.models import Alert, Intervention, WeeklyEntry
from family.decorators import (
    current_parent_email,
    parent_login,
    parent_logout,
    parent_required,
)
from family.forms import RequestAccessForm
from family.models import ParentMagicLink
from students.models import Student
from wellbeing.models import FollowUpSession


def _client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


@ratelimit(key="ip", rate=settings.FAMILY_RATE_LIMIT, method="POST", block=False)
def request_access(request):
    """Étape 1 : le parent saisit son email pour recevoir un lien.

    Protégé par rate-limiting (par défaut 5/heure/IP).
    """
    # Vérifier le rate-limit après le décorateur
    if getattr(request, "limited", False):
        return render(request, "family/rate_limited.html", status=429)

    if current_parent_email(request):
        return redirect("family:dashboard")

    form = RequestAccessForm(request.POST or None)
    dev_link = None

    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["parent_email"]
        exists = Student.objects.filter(parent_email__iexact=email).exists()

        if exists:
            link_obj = ParentMagicLink.objects.create(
                parent_email=email,
                ip_address=_client_ip(request),
            )
            access_url = request.build_absolute_uri(
                reverse("family:verify", args=[link_obj.token])
            )
            try:
                send_mail(
                    subject="Votre accès au portail famille",
                    message=(
                        "Bonjour,\n\n"
                        "Voici votre lien d'accès au portail famille "
                        "(valable 15 minutes, à usage unique) :\n\n"
                        f"{access_url}\n\n"
                        "Si vous n'êtes pas à l'origine de cette demande, "
                        "ignorez ce message."
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=True,
                )
            except Exception:
                pass

            if settings.DEBUG:
                dev_link = access_url

        return render(request, "family/link_sent.html", {
            "email": email,
            "dev_link": dev_link,
        })

    return render(request, "family/request_access.html", {"form": form})


def verify(request, token):
    """Étape 2 : le parent clique sur le lien dans son email."""
    link_obj = get_object_or_404(ParentMagicLink, token=token)

    if not link_obj.is_valid:
        return render(request, "family/link_invalid.html", {
            "expired": link_obj.is_expired,
            "used": link_obj.is_used,
        })

    link_obj.mark_used()
    parent_login(request, link_obj.parent_email)

    log_event(
        AuditLog.EventType.ACCESS_DENIED,
        f"Connexion portail famille pour {link_obj.parent_email}",
        event="family_portal_login",
        email=link_obj.parent_email,
        ip=link_obj.ip_address,
    )
    return redirect("family:dashboard")


@parent_required
def dashboard(request):
    email = current_parent_email(request)
    children = list(Student.objects.filter(parent_email__iexact=email))

    summaries = []
    four_weeks_ago = date.today() - timedelta(weeks=4)

    for child in children:
        recent_entries = WeeklyEntry.objects.filter(
            student=child, week_start__gte=four_weeks_ago
        ).order_by("-week_start")
        total_absences = sum(e.absences for e in recent_entries)

        family_interventions = (
            Intervention.objects.filter(
                alert__student=child,
                intervention_type=Intervention.Type.FAMILY_CONTACT,
            )
            .select_related("alert")
            .order_by("-planned_date")[:5]
        )

        upcoming_sessions = FollowUpSession.objects.filter(
            dossier__student=child,
            status=FollowUpSession.Status.PLANNED,
            scheduled_at__gte=timezone.now(),
        ).order_by("scheduled_at")[:5]

        has_active_followup = Alert.objects.filter(
            student=child,
            status__in=[Alert.Status.PENDING, Alert.Status.VALIDATED],
        ).exists()

        summaries.append({
            "child": child,
            "total_absences_4w": total_absences,
            "weeks_with_data": recent_entries.count(),
            "family_interventions": family_interventions,
            "upcoming_sessions": upcoming_sessions,
            "has_active_followup": has_active_followup,
        })

    return render(request, "family/dashboard.html", {
        "parent_email": email,
        "summaries": summaries,
    })


def logout_view(request):
    parent_logout(request)
    return redirect("family:request_access")
