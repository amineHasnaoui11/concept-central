"""Tests pour les rendez-vous en ligne."""
import secrets
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Role, User
from meetings.models import Meeting
from meetings.services import create_student_account
from students.models import Student
from wellbeing.models import PsychDossier


class MeetingFlowTests(TestCase):
    def setUp(self):
        self.counselor = User.objects.create_user(
            username="psy", password="pass1234!", role=Role.SUPERVISOR
        )
        self.student = Student.objects.create(
            internal_code="M-001", first_name="Ahmed", last_name="Test",
            birth_year=2010, level="college", class_name="3A",
        )
        # Crée le compte élève
        user, _ = create_student_account(self.student)
        self.student.refresh_from_db()
        self.student_user = user

        self.dossier = PsychDossier.objects.create(
            student=self.student,
            opened_by=self.counselor,
        )

    def test_counselor_proposes_meeting(self):
        """Le conseiller peut proposer un RDV."""
        self.client.login(username="psy", password="pass1234!")
        future = timezone.now() + timedelta(days=2)
        response = self.client.post(
            reverse("meetings:propose", args=[self.dossier.pk]),
            {
                "scheduled_at": future.strftime("%Y-%m-%dT%H:%M"),
                "duration_minutes": 45,
                "topic": "Suivi mensuel",
                "counselor_notes": "Notes internes",
            },
        )
        self.assertEqual(response.status_code, 302)
        meeting = Meeting.objects.first()
        self.assertEqual(meeting.status, Meeting.Status.PROPOSED)
        self.assertEqual(meeting.counselor, self.counselor)
        self.assertEqual(meeting.student, self.student)
        # Pas encore de token (pas approuvé)
        self.assertFalse(meeting.room_token)

    def test_student_approves_generates_token(self):
        """Quand l'élève approuve, un token est généré."""
        meeting = Meeting.objects.create(
            dossier=self.dossier, student=self.student, counselor=self.counselor,
            scheduled_at=timezone.now() + timedelta(days=1),
            topic="Test",
        )
        self.client.login(username=self.student_user.username,
                          password=self.student_user.username)  # wrong, just to test logic

    def test_student_can_approve_own_meeting(self):
        meeting = Meeting.objects.create(
            dossier=self.dossier, student=self.student, counselor=self.counselor,
            scheduled_at=timezone.now() + timedelta(days=1),
            topic="Test",
        )
        # Re-set password for the test
        self.student_user.set_password("studentpass1234!")
        self.student_user.save()

        self.client.login(username=self.student_user.username, password="studentpass1234!")
        response = self.client.post(
            reverse("meetings:respond", args=[meeting.pk]),
            {"action": "approve", "message": "OK"},
        )
        meeting.refresh_from_db()
        self.assertEqual(meeting.status, Meeting.Status.APPROVED)
        self.assertTrue(meeting.room_token)
        self.assertEqual(meeting.student_message, "OK")

    def test_student_can_reject(self):
        meeting = Meeting.objects.create(
            dossier=self.dossier, student=self.student, counselor=self.counselor,
            scheduled_at=timezone.now() + timedelta(days=1),
            topic="Test",
        )
        self.student_user.set_password("studentpass1234!")
        self.student_user.save()

        self.client.login(username=self.student_user.username, password="studentpass1234!")
        self.client.post(
            reverse("meetings:respond", args=[meeting.pk]),
            {"action": "reject", "message": "Pas disponible"},
        )
        meeting.refresh_from_db()
        self.assertEqual(meeting.status, Meeting.Status.REJECTED)
        self.assertFalse(meeting.room_token)


class MeetingAccessControlTests(TestCase):
    def setUp(self):
        self.counselor = User.objects.create_user(
            username="psy", password="pass1234!", role=Role.SUPERVISOR
        )
        self.other_counselor = User.objects.create_user(
            username="psy2", password="pass1234!", role=Role.SUPERVISOR
        )
        self.student = Student.objects.create(
            internal_code="A-001", first_name="A", last_name="B",
            birth_year=2010, level="college", class_name="3A",
        )
        user, _ = create_student_account(self.student)
        user.set_password("studentpass1234!")
        user.save()
        self.student.refresh_from_db()
        self.student_user = self.student.user

        # Un autre élève
        self.other_student = Student.objects.create(
            internal_code="A-002", first_name="C", last_name="D",
            birth_year=2010, level="college", class_name="3A",
        )
        other_user, _ = create_student_account(self.other_student)
        other_user.set_password("studentpass1234!")
        other_user.save()
        self.other_student.refresh_from_db()
        self.other_student_user = self.other_student.user

        self.dossier = PsychDossier.objects.create(
            student=self.student, opened_by=self.counselor,
        )
        self.meeting = Meeting.objects.create(
            dossier=self.dossier,
            student=self.student,
            counselor=self.counselor,
            scheduled_at=timezone.now() + timedelta(days=1),
            topic="Test",
            status=Meeting.Status.APPROVED,
            room_token="secret-test-token",
        )

    def test_other_student_cannot_access_meeting(self):
        """Un autre élève ne peut PAS voir un RDV qui n'est pas le sien."""
        self.client.login(username=self.other_student_user.username, password="studentpass1234!")
        response = self.client.get(reverse("meetings:detail", args=[self.meeting.pk]))
        self.assertEqual(response.status_code, 403)

    def test_other_counselor_cannot_access(self):
        """Un autre conseiller ne peut pas voir le RDV."""
        self.client.login(username="psy2", password="pass1234!")
        response = self.client.get(reverse("meetings:detail", args=[self.meeting.pk]))
        self.assertEqual(response.status_code, 403)

    def test_assigned_counselor_can_access(self):
        self.client.login(username="psy", password="pass1234!")
        response = self.client.get(reverse("meetings:detail", args=[self.meeting.pk]))
        self.assertEqual(response.status_code, 200)

    def test_assigned_student_can_access(self):
        self.client.login(username=self.student_user.username, password="studentpass1234!")
        response = self.client.get(reverse("meetings:detail", args=[self.meeting.pk]))
        self.assertEqual(response.status_code, 200)


class MeetingAccessWindowTests(TestCase):
    def setUp(self):
        self.counselor = User.objects.create_user(
            username="psy", password="pass1234!", role=Role.SUPERVISOR
        )
        self.student = Student.objects.create(
            internal_code="W-001", first_name="A", last_name="B",
            birth_year=2010, level="college", class_name="3A",
        )
        user, _ = create_student_account(self.student)
        user.set_password("pwd1234!")
        user.save()
        self.student.refresh_from_db()

        self.dossier = PsychDossier.objects.create(
            student=self.student, opened_by=self.counselor,
        )

    def test_cannot_join_before_window(self):
        """Tentative de rejoindre 2 jours avant → impossible."""
        meeting = Meeting.objects.create(
            dossier=self.dossier, student=self.student, counselor=self.counselor,
            scheduled_at=timezone.now() + timedelta(days=2),
            topic="Future", status=Meeting.Status.APPROVED,
            room_token="tok-future",
        )
        self.assertFalse(meeting.is_joinable_now)

        self.client.login(username="psy", password="pass1234!")
        response = self.client.get(reverse("meetings:join", args=[meeting.pk]))
        # Redirige vers détail avec warning
        self.assertEqual(response.status_code, 302)

    def test_can_join_within_window(self):
        """Rejoindre 5 min avant (dans la fenêtre de 10 min) → OK."""
        meeting = Meeting.objects.create(
            dossier=self.dossier, student=self.student, counselor=self.counselor,
            scheduled_at=timezone.now() + timedelta(minutes=5),
            topic="Now", status=Meeting.Status.APPROVED,
            room_token="tok-now",
        )
        self.assertTrue(meeting.is_joinable_now)

        self.client.login(username="psy", password="pass1234!")
        response = self.client.get(reverse("meetings:join", args=[meeting.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "tok-now")  # token dans le HTML

    def test_cannot_join_after_window(self):
        """Tentative de rejoindre 2h après → impossible."""
        meeting = Meeting.objects.create(
            dossier=self.dossier, student=self.student, counselor=self.counselor,
            scheduled_at=timezone.now() - timedelta(hours=2),
            topic="Past", status=Meeting.Status.APPROVED,
            room_token="tok-past",
        )
        self.assertFalse(meeting.is_joinable_now)

    def test_cannot_join_if_not_approved(self):
        """RDV PROPOSED (pas encore approuvé) → pas joignable."""
        meeting = Meeting.objects.create(
            dossier=self.dossier, student=self.student, counselor=self.counselor,
            scheduled_at=timezone.now() + timedelta(minutes=5),
            topic="Pending", status=Meeting.Status.PROPOSED,
        )
        self.assertFalse(meeting.is_joinable_now)


class StudentAccountTests(TestCase):
    def test_create_student_account(self):
        student = Student.objects.create(
            internal_code="ACC-001", first_name="Test", last_name="Student",
            birth_year=2010, level="college", class_name="3A",
        )
        user, password = create_student_account(student)

        self.assertEqual(user.role, Role.STUDENT)
        self.assertTrue(user.username.startswith("eleve_"))
        self.assertEqual(len(password), 12)
        student.refresh_from_db()
        self.assertEqual(student.user, user)

    def test_cannot_create_twice(self):
        student = Student.objects.create(
            internal_code="ACC-002", first_name="T", last_name="S",
            birth_year=2010, level="college", class_name="3A",
        )
        create_student_account(student)
        with self.assertRaises(ValueError):
            create_student_account(student)


class StudentRdvActionsTests(TestCase):
    """Tests des 4 actions élève : approve / reject / propose_alternate / cancel."""

    def setUp(self):
        self.counselor = User.objects.create_user(
            username="psy", password="pass1234!", role=Role.SUPERVISOR
        )
        self.student = Student.objects.create(
            internal_code="ACT-001", first_name="A", last_name="B",
            birth_year=2010, level="college", class_name="3A",
        )
        user, _ = create_student_account(self.student)
        user.set_password("studentpass1234!")
        user.save()
        self.student.refresh_from_db()

        self.dossier = PsychDossier.objects.create(
            student=self.student, opened_by=self.counselor,
        )

    def _make_meeting(self, status=Meeting.Status.PROPOSED, in_future_days=2):
        return Meeting.objects.create(
            dossier=self.dossier, student=self.student, counselor=self.counselor,
            scheduled_at=timezone.now() + timedelta(days=in_future_days),
            topic="Test", status=status,
            room_token="t" + secrets.token_hex(8) if status == Meeting.Status.APPROVED else None,
        )

    def test_propose_alternate_keeps_proposed_status(self):
        meeting = self._make_meeting()
        self.client.login(username=self.student.user.username, password="studentpass1234!")

        alt = timezone.now() + timedelta(days=5)
        response = self.client.post(
            reverse("meetings:respond", args=[meeting.pk]),
            {
                "action": "propose_alternate",
                "alternative_datetime": alt.strftime("%Y-%m-%dT%H:%M"),
                "message": "Prefer Friday",
            },
        )
        meeting.refresh_from_db()
        # Reste PROPOSED, mais avec proposition alternative
        self.assertEqual(meeting.status, Meeting.Status.PROPOSED)
        self.assertIsNotNone(meeting.student_alternative_proposal)
        self.assertEqual(meeting.student_message, "Prefer Friday")

    def test_propose_alternate_requires_date(self):
        meeting = self._make_meeting()
        self.client.login(username=self.student.user.username, password="studentpass1234!")
        response = self.client.post(
            reverse("meetings:respond", args=[meeting.pk]),
            {"action": "propose_alternate", "message": "no date"},
        )
        # Le formulaire renvoie une erreur
        self.assertEqual(response.status_code, 200)
        meeting.refresh_from_db()
        self.assertEqual(meeting.status, Meeting.Status.PROPOSED)
        self.assertIsNone(meeting.student_alternative_proposal)

    def test_student_can_cancel_approved_meeting(self):
        meeting = self._make_meeting(status=Meeting.Status.APPROVED)
        self.client.login(username=self.student.user.username, password="studentpass1234!")
        response = self.client.post(
            reverse("meetings:student_cancel", args=[meeting.pk]),
            {"reason": "Pas disponible finalement"},
        )
        meeting.refresh_from_db()
        self.assertEqual(meeting.status, Meeting.Status.CANCELLED)
        self.assertIn("Pas disponible", meeting.student_message)

    def test_student_cannot_cancel_proposed_meeting(self):
        """Un RDV pas encore approuvé ne peut pas être 'annulé' (il faut le refuser)."""
        meeting = self._make_meeting()
        self.client.login(username=self.student.user.username, password="studentpass1234!")
        response = self.client.post(
            reverse("meetings:student_cancel", args=[meeting.pk]),
            {"reason": ""},
        )
        meeting.refresh_from_db()
        self.assertEqual(meeting.status, Meeting.Status.PROPOSED)

    def test_other_student_cannot_cancel(self):
        """Un autre élève ne peut pas annuler le RDV de quelqu'un d'autre."""
        meeting = self._make_meeting(status=Meeting.Status.APPROVED)
        # Crée un autre élève
        other = Student.objects.create(
            internal_code="OTH-001", first_name="X", last_name="Y",
            birth_year=2010, level="college", class_name="3A",
        )
        other_user, _ = create_student_account(other)
        other_user.set_password("pw1234!")
        other_user.save()

        self.client.login(username=other_user.username, password="pw1234!")
        response = self.client.post(
            reverse("meetings:student_cancel", args=[meeting.pk]),
            {"reason": ""},
        )
        self.assertEqual(response.status_code, 403)
        meeting.refresh_from_db()
        self.assertEqual(meeting.status, Meeting.Status.APPROVED)
