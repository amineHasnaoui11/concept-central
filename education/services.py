from django.utils import timezone

from audit.models import AuditLog, log_event
from education.models import Alert, Intervention, RiskThreshold, WeeklyEntry
from education.risk_engine import RiskLevel, apply_risk_to_entry
from recommendations.services import generate_intervention_recommendation


def process_weekly_entry(entry: WeeklyEntry):
    score, level, reasons = apply_risk_to_entry(entry)
    alert = None

    if level in (RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL):
        thresholds = RiskThreshold.get_active()
        alert_level = (
            Alert.Level.CRITICAL
            if level == RiskLevel.CRITICAL
            else Alert.Level.HIGH
            if level == RiskLevel.HIGH
            else Alert.Level.MEDIUM
        )
        summary = "; ".join(reasons) or "Signaux de risque détectés"
        suggests_psych = score >= thresholds.critical_score

        # Évite les doublons sur la même entrée
        if not Alert.objects.filter(weekly_entry=entry).exists():
            alert = Alert.objects.create(
                student=entry.student,
                weekly_entry=entry,
                level=alert_level,
                risk_score=score,
                summary=summary,
                suggests_psych_dossier=suggests_psych,
            )
            log_event(
                AuditLog.EventType.ALERT_CREATED,
                f"Alerte {alert_level} générée (score {score})",
                user=entry.recorded_by,
                student=entry.student,
                alert_id=alert.pk,
                reasons=reasons,
            )
            try:
                generate_intervention_recommendation(alert)
            except Exception as e:
                print(f"⚠️  LLM error: {e}")

    return entry, alert


def validate_alert(alert: Alert, user):
    alert.status = Alert.Status.VALIDATED
    alert.validated_by = user
    alert.validated_at = timezone.now()
    alert.save()
    return alert


def resolve_alert(alert: Alert, user):
    alert.status = Alert.Status.RESOLVED
    alert.resolved_at = timezone.now()
    if not alert.validated_by:
        alert.validated_by = user
    alert.save()
    return alert


def plan_intervention(alert, intervention_type, planned_date, notes, user):
    intervention = Intervention.objects.create(
        alert=alert,
        intervention_type=intervention_type,
        planned_date=planned_date,
        notes=notes,
        planned_by=user,
    )
    log_event(
        AuditLog.EventType.INTERVENTION_PLANNED,
        f"Intervention {intervention.get_intervention_type_display()} planifiée",
        user=user,
        student=alert.student,
        intervention_id=intervention.pk,
    )
    if alert.status == Alert.Status.PENDING:
        validate_alert(alert, user)
    return intervention
