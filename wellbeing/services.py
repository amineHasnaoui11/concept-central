from django.utils import timezone

from audit.models import AuditLog, log_event
from wellbeing.models import FollowUpSession, add_timeline_event


def mark_missed_sessions():
    """Marque les séances manquées et déclenche les rappels."""
    now = timezone.now()
    qs = FollowUpSession.objects.filter(
        status=FollowUpSession.Status.PLANNED,
        scheduled_at__lt=now,
    )
    for session in qs:
        session.status = FollowUpSession.Status.MISSED
        session.save(update_fields=["status"])
        if not session.reminder_sent:
            session.reminder_sent = True
            session.save(update_fields=["reminder_sent"])
            add_timeline_event(
                session.dossier, None,
                "Rappel / référencement automatique",
                "Séance manquée — action de suivi déclenchée.",
            )
            log_event(
                AuditLog.EventType.SESSION_MISSED,
                f"Séance manquée pour dossier #{session.dossier_id}",
                student=session.dossier.student,
                session_id=session.pk,
            )
