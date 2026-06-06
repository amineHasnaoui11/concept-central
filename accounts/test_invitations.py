"""Tests pour le système d'invitation et le signup élève."""
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.invitations import StudentInvitation
from accounts.models import Role, User
from accounts.signup_services import (
    claim_invitation,
    generate_student_invitation,
    revoke_invitation,
)
from students.models import Student


class InvitationGenerationTests(TestCase):
    def setUp(self):
        self.counselor = User.objects.create_user(
            username="psy", password="pass1234!", role=Role.SUPERVISOR
        )
        self.student = Student.objects.create(
            internal_code="INV-T-001", first_name="A", last_name="B",
            birth_year=2010, level="college", class_name="3A",
            parent_email="parent@example.tn",
        )

    def test_generate_invitation(self):
        inv = generate_student_invitation(self.student, self.counselor)
        self.assertTrue(inv.code.startswith("INV-"))
        self.assertTrue(inv.is_valid)
        self.assertEqual(inv.student, self.student)

    def test_cannot_generate_if_student_has_account(self):
        # Crée un compte directement
        user = User.objects.create_user(username="existing", password="x", role=Role.STUDENT)
        self.student.user = user
        self.student.save()
        with self.assertRaises(ValueError):
            generate_student_invitation(self.student, self.counselor)

    def test_new_invitation_invalidates_old(self):
        old = generate_student_invitation(self.student, self.counselor)
        new = generate_student_invitation(self.student, self.counselor)
        old.refresh_from_db()
        self.assertFalse(old.is_valid)  # expiré
        self.assertTrue(new.is_valid)

    def test_counselor_view_requires_login(self):
        response = self.client.get(
            reverse("accounts:invitation_generate", args=[self.student.pk])
        )
        self.assertEqual(response.status_code, 302)  # redirect to login

    def test_counselor_can_generate_via_view(self):
        self.client.login(username="psy", password="pass1234!")
        response = self.client.post(
            reverse("accounts:invitation_generate", args=[self.student.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(StudentInvitation.objects.filter(student=self.student).exists())

    def test_revoke_invitation(self):
        inv = generate_student_invitation(self.student, self.counselor)
        revoke_invitation(inv)
        inv.refresh_from_db()
        self.assertFalse(inv.is_valid)


class InvitationClaimTests(TestCase):
    def setUp(self):
        self.counselor = User.objects.create_user(
            username="psy", password="pass1234!", role=Role.SUPERVISOR
        )
        self.student = Student.objects.create(
            internal_code="CLM-T-001", first_name="A", last_name="B",
            birth_year=2010, level="college", class_name="3A",
            parent_email="recovery@example.tn",
        )
        self.invitation = generate_student_invitation(self.student, self.counselor)

    def test_successful_claim(self):
        user, student = claim_invitation(
            invitation_code=self.invitation.code,
            internal_code=self.student.internal_code,
            username="myusername",
            password="StrongP@ssword123!",
        )
        self.assertEqual(user.username, "myusername")
        self.assertEqual(user.role, Role.STUDENT)
        # user.email = parent_email pour password reset
        self.assertEqual(user.email, "recovery@example.tn")

        student.refresh_from_db()
        self.assertEqual(student.user, user)

        # invitation marquée comme utilisée
        self.invitation.refresh_from_db()
        self.assertTrue(self.invitation.is_used)

    def test_wrong_invitation_code(self):
        with self.assertRaisesMessage(ValueError, "introuvable"):
            claim_invitation(
                invitation_code="INV-WRONG-WRONG-WRONG",
                internal_code=self.student.internal_code,
                username="x", password="x",
            )

    def test_wrong_internal_code(self):
        with self.assertRaisesMessage(ValueError, "code interne"):
            claim_invitation(
                invitation_code=self.invitation.code,
                internal_code="WRONG-CODE",
                username="x", password="StrongP@ssword123!",
            )

    def test_expired_invitation(self):
        self.invitation.expires_at = timezone.now() - timedelta(days=1)
        self.invitation.save()
        with self.assertRaisesMessage(ValueError, "expiré"):
            claim_invitation(
                invitation_code=self.invitation.code,
                internal_code=self.student.internal_code,
                username="x", password="StrongP@ssword123!",
            )

    def test_used_invitation_cannot_be_reused(self):
        claim_invitation(
            invitation_code=self.invitation.code,
            internal_code=self.student.internal_code,
            username="user1", password="StrongP@ssword123!",
        )
        with self.assertRaisesMessage(ValueError, "déjà été utilisé"):
            claim_invitation(
                invitation_code=self.invitation.code,
                internal_code=self.student.internal_code,
                username="user2", password="StrongP@ssword123!",
            )

    def test_username_already_taken(self):
        User.objects.create_user(username="taken", password="x", role=Role.OPERATOR)
        with self.assertRaisesMessage(ValueError, "déjà pris"):
            claim_invitation(
                invitation_code=self.invitation.code,
                internal_code=self.student.internal_code,
                username="taken", password="StrongP@ssword123!",
            )


class SignupViewTests(TestCase):
    def setUp(self):
        self.counselor = User.objects.create_user(
            username="psy", password="pass1234!", role=Role.SUPERVISOR
        )
        self.student = Student.objects.create(
            internal_code="SV-001", first_name="A", last_name="B",
            birth_year=2010, level="college", class_name="3A",
            parent_email="p@example.tn",
        )
        self.invitation = generate_student_invitation(self.student, self.counselor)

    def test_signup_page_accessible(self):
        response = self.client.get(reverse("student_signup"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "invitation_code")
        self.assertContains(response, "INV-XXXX")

    def test_successful_signup_logs_in(self):
        response = self.client.post(
            reverse("student_signup"),
            {
                "invitation_code": self.invitation.code,
                "internal_code": self.student.internal_code,
                "username": "newstudent",
                "password1": "StrongP@ssword123!",
                "password2": "StrongP@ssword123!",
            },
        )
        # Redirige vers dashboard étudiant
        self.assertEqual(response.status_code, 302)
        # L'élève est créé et connecté
        user = User.objects.get(username="newstudent")
        self.assertEqual(user.role, Role.STUDENT)

    def test_password_mismatch(self):
        response = self.client.post(
            reverse("student_signup"),
            {
                "invitation_code": self.invitation.code,
                "internal_code": self.student.internal_code,
                "username": "newstudent",
                "password1": "StrongP@ssword123!",
                "password2": "DifferentPass!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ne correspondent pas")

    def test_url_prefilled_code(self):
        response = self.client.get(
            reverse("student_signup") + f"?code={self.invitation.code}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.invitation.code)


class StudentPasswordResetTests(TestCase):
    """Vérifie que le password reset fonctionne pour les élèves via parent_email."""

    def test_reset_sends_email_to_parent_email(self):
        from django.core import mail

        counselor = User.objects.create_user(
            username="psy", password="pass1234!", role=Role.SUPERVISOR
        )
        student = Student.objects.create(
            internal_code="PR-001", first_name="A", last_name="B",
            birth_year=2010, level="college", class_name="3A",
            parent_email="parent@example.tn",
        )
        invitation = generate_student_invitation(student, counselor)
        claim_invitation(
            invitation_code=invitation.code,
            internal_code=student.internal_code,
            username="elve1", password="StrongP@ssword123!",
        )

        # Demande de reset
        response = self.client.post(
            reverse("password_reset"),
            {"email": "parent@example.tn"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("parent@example.tn", mail.outbox[0].to)
