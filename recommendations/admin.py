from django.contrib import admin

from recommendations.models import InterventionRecommendation


@admin.register(InterventionRecommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ("alert", "urgency", "model_used", "created_at")
    readonly_fields = ("anonymized_payload", "created_at")
