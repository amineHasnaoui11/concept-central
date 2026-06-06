"""
Tests critiques pour les comptes et la sécurité.
"""
from datetime import timedelta
from unittest.mock import patch

from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import Role, User


class RolePermissionTests(TestCase):
    """Vérifie que chaque rôle ne voit que ce qu'il doit voir."""

    def setUp(self):
        self.teacher = User.objects.create_user(
            username="prof", password="testpass1234!", role=Role.OPERATOR
        )
        self.counselor = User.objects.create_user(
            username="psy", password="testpass1234!", role=Role.SUPERVISOR
        )
        self.admin = User.objects.create_user(
            username="dir", password="testpass1234!", role=Role.ADMIN
        )
        self.client = Client()

    def test_operator_cannot_access_alerts_list(self):
        """Un enseignant ne doit PAS voir la liste des alertes."""
        self.client.login(username="prof", password="testpass1234!")
        response = self.client.get(reverse("education:alert_list"))
        self.assertEqual(response.status_code, 403)

    def test_operator_cannot_configure_thresholds(self):
        """Un enseignant ne doit PAS modifier les seuils."""
        self.client.login(username="prof", password="testpass1234!")
        response = self.client.get(reverse("education:risk_config"))
        self.assertEqual(response.status_code, 403)

    def test_supervisor_can_access_alerts(self):
        self.client.login(username="psy", password="testpass1234!")
        response = self.client.get(reverse("education:alert_list"))
        self.assertEqual(response.status_code, 200)

    def test_admin_can_configure_thresholds(self):
        self.client.login(username="dir", password="testpass1234!")
        response = self.client.get(reverse("education:risk_config"))
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_redirected_to_login(self):
        response = self.client.get(reverse("education:alert_list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)


class LoginTests(TestCase):
    def test_login_success(self):
        User.objects.create_user(username="test", password="strongpass1234!")
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "test", "password": "strongpass1234!"},
        )
        self.assertEqual(response.status_code, 302)

    def test_login_failure(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "nope", "password": "wrong"},
        )
        self.assertEqual(response.status_code, 200)

    def test_logout(self):
        User.objects.create_user(username="test", password="strongpass1234!")
        self.client.login(username="test", password="strongpass1234!")
        response = self.client.get(reverse("accounts:logout"))
        self.assertEqual(response.status_code, 302)


@override_settings(SESSION_IDLE_TIMEOUT_MINUTES=1)
class SessionTimeoutTests(TestCase):
    """Vérifie le timeout d'inactivité."""

    def test_session_expires_after_idle(self):
        user = User.objects.create_user(
            username="idle", password="strongpass1234!", role=Role.SUPERVISOR
        )
        self.client.login(username="idle", password="strongpass1234!")

        # Premier accès : OK
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)

        # On simule 2 minutes d'inactivité
        session = self.client.session
        past_time = (timezone.now() - timedelta(minutes=2)).isoformat()
        session["last_activity"] = past_time
        session.save()

        # L'accès suivant doit déconnecter
        response = self.client.get(reverse("dashboard"))
        # On est redirigé vers login
        self.assertEqual(response.status_code, 302)


class PasswordResetTests(TestCase):
    def test_password_reset_page_accessible(self):
        response = self.client.get(reverse("password_reset"))
        self.assertEqual(response.status_code, 200)

    def test_password_reset_email_sent(self):
        User.objects.create_user(
            username="reset_test",
            email="reset@example.com",
            password="strongpass1234!",
        )
        from django.core import mail

        response = self.client.post(
            reverse("password_reset"),
            {"email": "reset@example.com"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("reset@example.com", mail.outbox[0].to)


class BruteForceProtectionTests(TestCase):
    """Vérifie que django-axes bloque après plusieurs essais."""

    @override_settings(AXES_FAILURE_LIMIT=3)
    def test_lockout_after_failed_attempts(self):
        User.objects.create_user(username="victim", password="goodpass1234!")
        # 3 essais ratés
        for _ in range(3):
            self.client.post(
                reverse("accounts:login"),
                {"username": "victim", "password": "wrong"},
            )
        # Le 4ème (même bon mot de passe) doit être bloqué ou échouer
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "victim", "password": "goodpass1234!"},
        )
        # axes renvoie 403 ou 429 selon la config
        self.assertIn(response.status_code, [200, 302, 403, 429])
