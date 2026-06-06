"""Signaux Django pour automatiser la création des alertes."""
from django.db.models.signals import post_save
from django.dispatch import receiver

from education.models import Alert, WeeklyEntry
from education.notifications import send_alert_notification
from education.risk_engine import apply_risk_to_entry
from recommendations.services import generate_intervention_recommendation


@receiver(post_save, sender=WeeklyEntry)
def create_alert_on_high_risk(sender, instance, created, **kwargs):
    if not created:
        return

    score, level, reasons = apply_risk_to_entry(instance)
    if score < 50:
        return
    if Alert.objects.filter(weekly_entry=instance).exists():
        return

    if score >= 75:
        alert_level = Alert.Level.CRITICAL
        suggests_psych = True
    else:
        alert_level = Alert.Level.HIGH
        suggests_psych = False

    alert = Alert.objects.create(
        student=instance.student,
        weekly_entry=instance,
        level=alert_level,
        risk_score=score,
        summary=f"Score : {score}/100. Raisons : {', '.join(reasons)}",
        suggests_psych_dossier=suggests_psych,
    )

    try:
        generate_intervention_recommendation(alert)
    except Exception as e:
        print(f"⚠️  Erreur LLM : {e}")

    try:
        send_alert_notification(alert)
    except Exception as e:
        print(f"⚠️  Erreur email : {e}")
