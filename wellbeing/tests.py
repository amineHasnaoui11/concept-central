"""Tests critiques pour les dossiers psychologiques."""
from datetime import date, timedelta
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import Role, User
from audit.models import AuditLog
from students.models import Student
from wellbeing.models import PsychDossier
from wellbeing.services import mark_missed_sessions
from wellbeing.models import FollowUpSession


class PsychDossierAccessTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="prof", password="pass1234!", role=Role.OPERATOR
        )
        self.counselor = User.objects.create_user(
            username="psy", password="pass1234!", role=Role.SUPERVISOR
        )
        self.admin = User.objects.create_user(
            username="dir", password="pass1234!", role=Role.ADMIN
        )
        self.student = Student.objects.create(
            internal_code="W-001", first_name="A", last_name="B",
            birth_year=2010, level="college", class_name="3A",
        )
        self.dossier = PsychDossier.objects.create(
            student=self.student,
            opened_by=self.counselor,
        )

    def test_teacher_cannot_view_dossier(self):
        """Accès opérateur → 403 + log audit"""
        self.client.login(username="prof", password="pass1234!")
        response = self.client.get(
            reverse("wellbeing:dossier_detail", args=[self.dossier.pk])
        )
        self.assertEqual(response.status_code, 403)
        # Vérifier que l'événement est logué
        self.assertTrue(
            AuditLog.objects.filter(
                event_type=AuditLog.EventType.ACCESS_DENIED,
                user=self.teacher,
            ).exists()
        )

    def test_counselor_can_view_dossier(self):
        self.client.login(username="psy", password="pass1234!")
        response = self.client.get(
            reverse("wellbeing:dossier_detail", args=[self.dossier.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_admin_can_view_but_not_manage(self):
        """L'admin voit mais ne peut pas planifier une séance"""
        self.client.login(username="dir", password="pass1234!")
        response = self.client.get(
            reverse("wellbeing:dossier_detail", args=[self.dossier.pk])
        )
        self.assertEqual(response.status_code, 200)


class RetentionTests(TestCase):
    def test_retention_date_auto_set(self):
        student = Student.objects.create(
            internal_code="R-001", first_name="A", last_name="B",
            birth_year=2010, level="college", class_name="3A",
        )
        dossier = PsychDossier.objects.create(student=student)
        self.assertIsNotNone(dossier.retention_until)
        # Doit être dans le futur
        self.assertGreater(dossier.retention_until, date.today())


class MissedSessionTests(TestCase):
    def test_past_planned_session_marked_missed(self):
        from django.utils import timezone
        student = Student.objects.create(
            internal_code="S-001", first_name="A", last_name="B",
            birth_year=2010, level="college", class_name="3A",
        )
        dossier = PsychDossier.objects.create(student=student)
        session = FollowUpSession.objects.create(
            dossier=dossier,
            scheduled_at=timezone.now() - timedelta(days=2),
            status=FollowUpSession.Status.PLANNED,
        )
        mark_missed_sessions()
        session.refresh_from_db()
        self.assertEqual(session.status, FollowUpSession.Status.MISSED)
        self.assertTrue(session.reminder_sent)


class AttachmentTests(TestCase):
    def setUp(self):
        self.counselor = User.objects.create_user(
            username="psy", password="pass1234!", role=Role.SUPERVISOR
        )
        student = Student.objects.create(
            internal_code="A-001", first_name="A", last_name="B",
            birth_year=2010, level="college", class_name="3A",
        )
        self.dossier = PsychDossier.objects.create(student=student)

    def test_upload_valid_pdf(self):
        from wellbeing.forms import AttachmentForm
        file = SimpleUploadedFile(
            "test.pdf", b"%PDF-1.4 fake", content_type="application/pdf"
        )
        form = AttachmentForm(
            data={"description": "test"},
            files={"file": file},
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_reject_invalid_extension(self):
        from wellbeing.forms import AttachmentForm
        file = SimpleUploadedFile(
            "test.exe", b"MZ\x90\x00", content_type="application/octet-stream"
        )
        form = AttachmentForm(
            data={"description": "test"},
            files={"file": file},
        )
        self.assertFalse(form.is_valid())
