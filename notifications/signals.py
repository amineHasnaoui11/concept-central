from django.db.models.signals import post_save
from django.urls import NoReverseMatch, reverse

from notifications.models import Notification
from notifications.services import notify


def _safe_reverse(name, *args, **kwargs):
    try:
        return reverse(name, args=args, kwargs=kwargs)
    except NoReverseMatch:
        return ""


def _supervisors_and_admins():
    from accounts.models import Role, User
    return User.objects.filter(role__in=[Role.SUPERVISOR, Role.ADMIN], is_active=True)


def _on_alert_created(sender, instance, created, **kwargs):
    if not created:
        return
    link = _safe_reverse("education:alert_detail", instance.pk)
    for user in _supervisors_and_admins():
        notify(
            event=Notification.Event.ALERT_CREATED,
            recipient_user=user,
            title=f"Nouvelle alerte · {instance.get_level_display()}",
            message=f"{instance.student} — score {instance.risk_score}",
            link=link,
            payload={"alert_id": instance.pk, "level": instance.level, "score": instance.risk_score},
        )


def _on_audit_log(sender, instance, created, **kwargs):
    if not created:
        return

    if instance.event_type == "session_missed":
        student = instance.student
        for user in _supervisors_and_admins():
            notify(
                event=Notification.Event.SESSION_MISSED,
                recipient_user=user,
                title="Séance manquée",
                message=instance.message,
                link=_safe_reverse("wellbeing:dossier_list"),
                payload=dict(instance.metadata),
            )
        if student and student.parent_email:
            notify(
                event=Notification.Event.SESSION_MISSED,
                recipient_email=student.parent_email,
                title="Rendez-vous manqué",
                message=(
                    f"Bonjour, un rendez-vous prévu pour {student.first_name} "
                    f"n'a pas eu lieu. Le conseiller scolaire vous recontactera."
                ),
            )

    elif instance.event_type == "dossier_opened":
        for user in _supervisors_and_admins():
            notify(
                event=Notification.Event.DOSSIER_OPENED,
                recipient_user=user,
                title="Dossier psychologique ouvert",
                message=instance.message,
                link=_safe_reverse("wellbeing:dossier_list"),
            )

    elif instance.event_type == "intervention_planned":
        for user in _supervisors_and_admins():
            notify(
                event=Notification.Event.INTERVENTION_PLANNED,
                recipient_user=user,
                title="Intervention planifiée",
                message=instance.message,
            )


def connect_signals():
    try:
        from education.models import Alert
        post_save.connect(_on_alert_created, sender=Alert, dispatch_uid="notif_alert_created")
    except Exception:
        pass

    try:
        from audit.models import AuditLog
        post_save.connect(_on_audit_log, sender=AuditLog, dispatch_uid="notif_audit_log")
    except Exception:
        pass


connect_signals()
