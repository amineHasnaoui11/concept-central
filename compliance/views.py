from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render
from django.utils import timezone

from accounts.decorators import role_required
from accounts.models import Role
from audit.models import AuditLog
from compliance.models import DataAccessRequest
from students.models import ParentConsent, Student
from wellbeing.models import PsychDossier


@login_required
@role_required(Role.ADMIN)
def compliance_dashboard(request):
    """Tableau de bord conformité pour la direction."""
    today = timezone.now().date()
    in_30 = today + timedelta(days=30)

    # Consentements
    consent_stats = (
        ParentConsent.objects.values("consent_type", "granted")
        .annotate(count=Count("id"))
    )

    # Élèves sans consentement
    students_without_consent = (
        Student.objects.exclude(
            consents__consent_type=ParentConsent.ConsentType.DATA_PROCESSING,
            consents__granted=True,
        ).count()
    )

    # Dossiers approchant la rétention
    dossiers_expiring_soon = PsychDossier.objects.filter(
        retention_until__lte=in_30,
        retention_until__gte=today,
    ).exclude(status=PsychDossier.Status.ARCHIVED).select_related("student")

    dossiers_expired = PsychDossier.objects.filter(
        retention_until__lt=today,
    ).exclude(status=PsychDossier.Status.ARCHIVED).select_related("student")

    # Demandes d'accès en attente
    pending_requests = DataAccessRequest.objects.filter(
        status=DataAccessRequest.Status.PENDING
    ).select_related("student")

    # Logs d'accès récents (30 derniers jours)
    recent_access_denied = AuditLog.objects.filter(
        event_type=AuditLog.EventType.ACCESS_DENIED,
        created_at__gte=timezone.now() - timedelta(days=30),
    ).select_related("user", "student")[:20]

    return render(
        request,
        "compliance/dashboard.html",
        {
            "consent_stats": consent_stats,
            "students_without_consent": students_without_consent,
            "dossiers_expiring_soon": dossiers_expiring_soon,
            "dossiers_expired": dossiers_expired,
            "pending_requests": pending_requests,
            "recent_access_denied": recent_access_denied,
        },
    )
