import json

from django.conf import settings

from audit.models import AuditLog, log_event
from education.models import Alert
from recommendations.models import DISCLAIMER, InterventionRecommendation


def build_anonymized_context(alert: Alert) -> dict:
    student = alert.student
    entry = alert.weekly_entry
    profile = student.anonymized_profile()
    profile.update({
        "risk_score": alert.risk_score,
        "risk_level": alert.level,
        "alert_summary": alert.summary,
        "absences_this_week": entry.absences,
        "behavioral_incident": entry.behavioral_incident,
        "grade_context": {
            "control_grade": float(entry.control_grade) if entry.control_grade else None,
            "previous_grade": float(entry.previous_grade) if entry.previous_grade else None,
        },
    })
    return profile


def _call_ollama(prompt: str) -> tuple[str, str]:
    try:
        import requests
        ollama_url = getattr(settings, "OLLAMA_URL", "http://localhost:11434")
        model_name = getattr(settings, "OLLAMA_MODEL", "llama3.2")

        response = requests.post(
            f"{ollama_url}/api/generate",
            json={
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.7, "num_predict": 800},
            },
            timeout=60,
        )

        if response.status_code != 200:
            return "", "fallback"

        data = response.json()
        text = data.get("response", "")
        return text, f"ollama-{model_name}"
    except Exception:
        return "", "fallback"


def _fallback_recommendation(ctx: dict) -> dict:
    score = ctx.get("risk_score", 0)
    urgency = "élevée" if score >= 75 else "modérée" if score >= 50 else "standard"
    return {
        "text": (
            f"Pour {ctx.get('pseudonym')}, un entretien individuel avec le conseiller "
            f"est recommandé (urgence {urgency}). Score : {score}/100."
        ),
        "urgency": urgency,
        "actions": [
            "Entretien individuel sous 7 jours",
            "Évaluation du contexte familial",
            "Suivi des notes et absences sur 3 semaines",
        ],
    }


def generate_intervention_recommendation(alert: Alert):
    if InterventionRecommendation.objects.filter(alert=alert).exists():
        return None

    ctx = build_anonymized_context(alert)
    assert "first_name" not in ctx and "last_name" not in ctx, "Fuite de données !"

    prompt = f"""Tu es un assistant pour conseillers scolaires en Tunisie.
Profil ANONYMISÉ (aucun nom réel) :
{json.dumps(ctx, ensure_ascii=False, indent=2)}

Propose une intervention concrète en JSON avec les clés :
- intervention_type (entretien, contact_famille, orientation)
- urgency (standard, modérée, élevée, critique)
- actions (liste de 3 actions courtes)
- rationale (paragraphe court en français)

Réponds uniquement en JSON valide."""

    raw, model_used = _call_ollama(prompt)
    if raw:
        try:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            data = json.loads(raw[start:end])
            rec = InterventionRecommendation.objects.create(
                alert=alert,
                anonymized_payload=ctx,
                recommendation_text=data.get("rationale", raw),
                urgency=data.get("urgency", ""),
                suggested_actions=data.get("actions", []),
                model_used=model_used,
            )
            log_event(
                AuditLog.EventType.LLM_RECOMMENDATION,
                f"Recommandation LLM générée ({model_used})",
                student=alert.student,
                alert_id=alert.pk,
            )
            return rec
        except (json.JSONDecodeError, ValueError):
            pass

    fb = _fallback_recommendation(ctx)
    rec = InterventionRecommendation.objects.create(
        alert=alert,
        anonymized_payload=ctx,
        recommendation_text=fb["text"],
        urgency=fb["urgency"],
        suggested_actions=fb["actions"],
        model_used="fallback",
    )
    log_event(
        AuditLog.EventType.LLM_RECOMMENDATION,
        "Recommandation générée (mode local / fallback)",
        student=alert.student,
        alert_id=alert.pk,
    )
    return rec
