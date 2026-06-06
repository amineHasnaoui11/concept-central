"""Génération automatique de rapports hebdomadaires"""
from datetime import datetime, timedelta

from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

from education.models import Alert, Intervention, WeeklyEntry
from education.notifications import get_admin_emails
from students.models import Student


def generate_weekly_statistics():
    today = datetime.now().date()
    week_start = today - timedelta(days=7)

    stats = {
        "total_alerts": Alert.objects.filter(created_at__gte=week_start).count(),
        "critical_alerts": Alert.objects.filter(
            created_at__gte=week_start, level=Alert.Level.CRITICAL
        ).count(),
        "high_alerts": Alert.objects.filter(
            created_at__gte=week_start, level=Alert.Level.HIGH
        ).count(),
        "pending_alerts": Alert.objects.filter(status=Alert.Status.PENDING).count(),
        "validated_alerts": Alert.objects.filter(
            created_at__gte=week_start, status=Alert.Status.VALIDATED
        ).count(),
        "resolved_alerts": Alert.objects.filter(
            created_at__gte=week_start, status=Alert.Status.RESOLVED
        ).count(),
        "planned_interventions": Intervention.objects.filter(
            created_at__gte=week_start
        ).count(),
        "completed_interventions": Intervention.objects.filter(
            completed=True, completed_at__gte=week_start
        ).count(),
        "weekly_entries": WeeklyEntry.objects.filter(created_at__gte=week_start).count(),
        "high_risk_entries": WeeklyEntry.objects.filter(
            created_at__gte=week_start, risk_score__gte=50
        ).count(),
        "total_students": Student.objects.count(),
        "students_with_alerts": Alert.objects.filter(created_at__gte=week_start)
        .values("student")
        .distinct()
        .count(),
        "period_start": week_start,
        "period_end": today,
    }

    stats["top_risk_students"] = (
        WeeklyEntry.objects.filter(created_at__gte=week_start, risk_score__gte=50)
        .select_related("student")
        .order_by("-risk_score")[:5]
    )

    old_date = today - timedelta(days=7)
    stats["old_unresolved_alerts"] = (
        Alert.objects.filter(
            created_at__lte=old_date,
            status__in=[Alert.Status.PENDING, Alert.Status.VALIDATED],
        )
        .select_related("student")
        .count()
    )

    return stats


def send_weekly_report():
    admin_emails = get_admin_emails()
    if not admin_emails:
        return False

    stats = generate_weekly_statistics()
    subject = f"📊 Rapport Hebdomadaire - Semaine du {stats['period_start'].strftime('%d/%m/%Y')}"
    context = {"stats": stats, "site_url": settings.SITE_URL}
    html_message = render_to_string("emails/weekly_report.html", context)

    try:
        email = EmailMessage(
            subject=subject,
            body=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=admin_emails,
        )
        email.content_subtype = "html"
        email.send(fail_silently=False)
        return True
    except Exception as e:
        print(f"❌ Erreur rapport : {e}")
        return False
