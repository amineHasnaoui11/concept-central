from datetime import date

from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import Role, User
from students.models import ParentConsent, Student


class StudentModelTests(TestCase):
    def test_creation(self):
        s = Student.objects.create(
            internal_code="T-001",
            first_name="Test",
            last_name="Élève",
            birth_year=2010,
            level=Student.Level.COLLEGE,
            class_name="3A",
        )
        self.assertEqual(s.age_approx, date.today().year - 2010)
        self.assertFalse(s.has_family_contact)

    def test_anonymized_profile_excludes_name(self):
        s = Student.objects.create(
            internal_code="T-002",
            first_name="John",
            last_name="Doe",
            birth_year=2010,
            level=Student.Level.COLLEGE,
            class_name="3A",
        )
        profile = s.anonymized_profile()
        self.assertNotIn("John", str(profile))
        self.assertNotIn("Doe", str(profile))
        self.assertEqual(profile["pseudonym"], "ELEVE-T-002")


class StudentFormValidationTests(TestCase):
    def test_birth_year_too_young(self):
        from students.forms import StudentForm
        form = StudentForm(data={
            "internal_code": "T-99",
            "first_name": "A", "last_name": "B",
            "birth_year": date.today().year - 5,  # 5 ans → trop jeune
            "level": "college", "class_name": "3A",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("birth_year", form.errors)

    def test_duplicate_code(self):
        Student.objects.create(
            internal_code="DUP-001", first_name="A", last_name="B",
            birth_year=2010, level="college", class_name="3A",
        )
        from students.forms import StudentForm
        form = StudentForm(data={
            "internal_code": "DUP-001",
            "first_name": "C", "last_name": "D",
            "birth_year": 2010, "level": "college", "class_name": "3A",
        })
        self.assertFalse(form.is_valid())


class ConsentTests(TestCase):
    def test_consent_creation(self):
        s = Student.objects.create(
            internal_code="T-C", first_name="A", last_name="B",
            birth_year=2010, level="college", class_name="3A",
        )
        c = ParentConsent.objects.create(
            student=s,
            consent_type=ParentConsent.ConsentType.PSYCH_FOLLOWUP,
            granted=True,
        )
        self.assertTrue(c.is_active)

    def test_consent_uniqueness(self):
        from django.db.utils import IntegrityError
        s = Student.objects.create(
            internal_code="T-C2", first_name="A", last_name="B",
            birth_year=2010, level="college", class_name="3A",
        )
        ParentConsent.objects.create(
            student=s,
            consent_type=ParentConsent.ConsentType.PSYCH_FOLLOWUP,
            granted=True,
        )
        with self.assertRaises(IntegrityError):
            ParentConsent.objects.create(
                student=s,
                consent_type=ParentConsent.ConsentType.PSYCH_FOLLOWUP,
                granted=False,
            )


class StudentListAccessTests(TestCase):
    def setUp(self):
        self.student = Student.objects.create(
            internal_code="LIST-001", first_name="A", last_name="B",
            birth_year=2010, level="college", class_name="3A",
        )
        self.teacher = User.objects.create_user(
            username="t", password="strongpass1234!", role=Role.OPERATOR
        )

    def test_search_by_name(self):
        self.client.login(username="t", password="strongpass1234!")
        response = self.client.get(reverse("students:list"), {"q": "LIST-001"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "LIST-001")

    def test_admin_can_export(self):
        admin = User.objects.create_user(
            username="adm", password="strongpass1234!", role=Role.ADMIN
        )
        self.client.login(username="adm", password="strongpass1234!")
        response = self.client.get(
            reverse("students:data_export", args=[self.student.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("application/json", response["Content-Type"])

    def test_teacher_cannot_export(self):
        self.client.login(username="t", password="strongpass1234!")
        response = self.client.get(
            reverse("students:data_export", args=[self.student.pk])
        )
        self.assertEqual(response.status_code, 403)
