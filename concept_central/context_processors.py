from django.conf import settings


def site_context(request):
    return {
        "SITE_NAME": getattr(settings, "SITE_NAME", "Concept Central"),
        "LLM_DISCLAIMER": "Aide à la décision — validation humaine obligatoire",
    }
