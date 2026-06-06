from django.db import models

from education.models import Alert

DISCLAIMER = "Aide à la décision — validation humaine obligatoire"


class InterventionRecommendation(models.Model):
    alert = models.OneToOneField(
        Alert, on_delete=models.CASCADE, related_name="llm_recommendation"
    )
    anonymized_payload = models.JSONField(
        help_text="Données envoyées au LLM (sans nom réel)."
    )
    recommendation_text = models.TextField()
    urgency = models.CharField(max_length=20, blank=True)
    suggested_actions = models.JSONField(default=list, blank=True)
    model_used = models.CharField(max_length=80, default="fallback")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Recommandation LLM"
        verbose_name_plural = "Recommandations LLM"

    def __str__(self):
        return f"Recommandation alerte #{self.alert_id}"
