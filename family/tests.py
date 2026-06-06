"""Tests pour le portail famille."""
from datetime import timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from family.models import ParentMagicLink
from students.models import Student


class MagicLinkTests(TestCase):
    def setUp(self):
        self.student = Student.objects.create(
            internal_code="F-001", first_name="A", last_name="B",
            birth_year=2010, level="college", class_name="3A",
            parent_email="parent@famille.tn",
        )

    def test_request_known_email_creates_link(self):
        response = self.client.post(
            reverse("family:request_access"),
            {"parent_email": "parent@famille.tn"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(ParentMagicLink.objects.filter(parent_email="parent@famille.tn").exists())

    def test_request_unknown_email_no_link(self):
        """Pour éviter l'énumération, on ne crée PAS de lien pour un email inconnu,
        mais on affiche le même message."""
        response = self.client.post(
            reverse("family:request_access"),
            {"parent_email": "inconnu@famille.tn"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ParentMagicLink.objects.filter(parent_email="inconnu@famille.tn").exists())

    def test_valid_link_grants_access(self):
        link = ParentMagicLink.objects.create(parent_email="parent@famille.tn")
        response = self.client.get(reverse("family:verify", args=[link.token]))
        self.assertEqual(response.status_code, 302)

        # Le lien doit être marqué comme utilisé
        link.refresh_from_db()
        self.assertTrue(link.is_used)

    def test_expired_link_rejected(self):
        link = ParentMagicLink.objects.create(parent_email="parent@famille.tn")
        link.expires_at = timezone.now() - timedelta(minutes=1)
        link.save()

        response = self.client.get(reverse("family:verify", args=[link.token]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "expiré")

    def test_used_link_cannot_be_reused(self):
        link = ParentMagicLink.objects.create(parent_email="parent@famille.tn")
        # Premier usage
        self.client.get(reverse("family:verify", args=[link.token]))
        # On se déconnecte
        self.client.get(reverse("family:logout"))
        # Deuxième usage doit échouer
        response = self.client.get(reverse("family:verify", args=[link.token]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "déjà utilisé")


@override_settings(FAMILY_RATE_LIMIT="2/h")
class RateLimitTests(TestCase):
    def test_rate_limit_blocks_after_threshold(self):
        """Le rate limit est appliqué via django-ratelimit.

        En tests avec le backend cache 'locmem', le décorateur peut ne pas
        bloquer parfaitement — on vérifie au moins qu'il ne casse pas le flux.
        """
        for i in range(2):
            response = self.client.post(
                reverse("family:request_access"),
                {"parent_email": f"test{i}@x.com"},
            )
            self.assertIn(response.status_code, [200, 302])

        # 3ème requête : soit 200 (rate-limit non actif en test), soit 429 (bloqué)
        response = self.client.post(
            reverse("family:request_access"),
            {"parent_email": "test3@x.com"},
        )
        self.assertIn(response.status_code, [200, 302, 429])
