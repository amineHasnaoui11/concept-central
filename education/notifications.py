"""Système de notifications email automatiques"""
from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

from accounts.models import Role, User
from education.models import Alert


def get_counselor_emails():
    return [u.email for u in User.objects.filter(role=Role.SUPERVISOR) if u.email]


def get_admin_emails():
    return [u.email for u in User.objects.filter(role=Role.ADMIN) if u.email]


def send_alert_notification(alert: Alert):
    if alert.level != Alert.Level.CRITICAL:
        return False

    recipients = get_counselor_emails()
    if not recipients:
        return False

    subject = f"🚨 Alerte Critique : {alert.student.first_name} {alert.student.last_name}"
    context = {
        "alert": alert,
        "student": alert.student,
        "entry": alert.weekly_entry,
        "alert_url": f"{settings.SITE_URL}/education/alertes/{alert.pk}/",
    }
    html_message = render_to_string("emails/alert_notification.html", context)

    try:
        email = EmailMessage(
            subject=subject,
            body=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipients,
        )
        email.content_subtype = "html"
        email.send(fail_silently=False)
        return True
    except Exception as e:
        print(f"❌ Erreur email : {e}")
        return False


def send_intervention_reminder(intervention):
    counselor = intervention.planned_by
    if not counselor or not counselor.email:
        return False

    subject = f"📅 Rappel : Intervention prévue le {intervention.planned_date}"
    context = {
        "intervention": intervention,
        "alert": intervention.alert,
        "student": intervention.alert.student,
    }
    html_message = render_to_string("emails/intervention_reminder.html", context)

    try:
        email = EmailMessage(
            subject=subject,
            body=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[counselor.email],
        )
        email.content_subtype = "html"
        email.send(fail_silently=False)
        return True
    except Exception:
        return False
