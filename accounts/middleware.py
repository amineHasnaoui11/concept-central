"""
Middleware de déconnexion automatique après X minutes d'inactivité.
Critique pour les sessions staff manipulant des données sensibles.
"""
from django.conf import settings
from django.contrib.auth import logout
from django.utils import timezone


SESSION_TIMESTAMP_KEY = "last_activity"


class SessionIdleTimeoutMiddleware:
    """Déconnecte automatiquement l'utilisateur après une période d'inactivité.

    La durée est configurée via SESSION_IDLE_TIMEOUT_MINUTES (settings).
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.timeout_minutes = getattr(settings, "SESSION_IDLE_TIMEOUT_MINUTES", 30)

    def __call__(self, request):
        if request.user.is_authenticated:
            now = timezone.now()
            last_activity = request.session.get(SESSION_TIMESTAMP_KEY)

            if last_activity:
                try:
                    last = timezone.datetime.fromisoformat(last_activity)
                    elapsed_minutes = (now - last).total_seconds() / 60.0
                    if elapsed_minutes > self.timeout_minutes:
                        logout(request)
                        request.session.flush()
                except (ValueError, TypeError):
                    pass

            request.session[SESSION_TIMESTAMP_KEY] = now.isoformat()

        return self.get_response(request)
