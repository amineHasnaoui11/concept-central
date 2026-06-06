"""Tests pour le moteur de risque et l'import CSV."""
import io
from datetime import date, timedelta
from decimal import Decimal

from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import Role, User
from education.csv_import import import_weekly_csv
from education.models import Alert, RiskThreshold, WeeklyEntry
from education.risk_engine import compute_risk_score
from students.models import Student


class RiskEngineTests(TestCase):
    def setUp(self):
        RiskThreshold.objects.create(
            name="test", max_absences=3, grade_drop_percent=30,
            critical_grade_threshold=Decimal("5"),
            critical_score=75, high_risk_score=50, is_active=True,
        )
        self.student = Student.objects.create(
            internal_code="R-001", first_name="A", last_name="B",
            birth_year=2010, level="college", class_name="3A",
        )

    def test_low_risk_no_signals(self):
        entry = WeeklyEntry.objects.create(
            student=self.student, week_start=date.today(),
            absences=1, control_grade=Decimal("14"),
            previous_grade=Decimal("14"), behavioral_incident=False,
        )
        score, level, reasons = compute_risk_score(entry)
        self.assertLess(score, 25)
        self.assertEqual(level, "low")

    def test_high_risk_combined_signals(self):
        entry = WeeklyEntry.objects.create(
            student=self.student, week_start=date.today(),
            absences=5, control_grade=Decimal("8"),
            previous_grade=Decimal("14"), behavioral_incident=True,
        )
        score, level, reasons = compute_risk_score(entry)
        self.assertGreaterEqual(score, 75)
        self.assertEqual(level, "critical")
        self.assertGreaterEqual(len(reasons), 2)

    def test_grade_drop_alone_triggers_alert(self):
        entry = WeeklyEntry.objects.create(
            student=self.student, week_start=date.today(),
            absences=0, control_grade=Decimal("9"),
            previous_grade=Decimal("14"), behavioral_incident=False,
        )
        score, level, _ = compute_risk_score(entry)
        # Baisse ~36% → contribue significativement
        self.assertGreaterEqual(score, 40)

    def test_critical_grade_threshold(self):
        entry = WeeklyEntry.objects.create(
            student=self.student, week_start=date.today(),
            absences=0, control_grade=Decimal("4"),
            previous_grade=Decimal("5"), behavioral_incident=False,
        )
        score, _, reasons = compute_risk_score(entry)
        # La note 4 < 5 doit déclencher au moins le bonus "Note critique"
        self.assertTrue(any("critique" in r.lower() for r in reasons))


class CSVImportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="op", password="pass1234!", role=Role.OPERATOR
        )
        self.student = Student.objects.create(
            internal_code="CSV-001", first_name="A", last_name="B",
            birth_year=2010, level="college", class_name="3A",
        )

    def test_valid_csv(self):
        csv_content = (
            "internal_code,week_start,absences,control_grade,previous_grade,behavioral_incident\n"
            "CSV-001,2024-01-15,2,12,14,false\n"
        )
        file = io.BytesIO(csv_content.encode("utf-8"))
        ok, msg, created = import_weekly_csv(file, self.user)
        self.assertTrue(ok, msg)
        self.assertEqual(len(created), 1)

    def test_invalid_csv_missing_columns(self):
        csv_content = "internal_code,week_start,absences\nCSV-001,2024-01-15,2\n"
        file = io.BytesIO(csv_content.encode("utf-8"))
        ok, msg, _ = import_weekly_csv(file, self.user)
        self.assertFalse(ok)
        self.assertIn("manquantes", msg)

    def test_csv_with_unknown_student(self):
        csv_content = (
            "internal_code,week_start,absences,control_grade,previous_grade,behavioral_incident\n"
            "UNKNOWN-999,2024-01-15,2,12,14,false\n"
        )
        file = io.BytesIO(csv_content.encode("utf-8"))
        ok, msg, _ = import_weekly_csv(file, self.user)
        self.assertFalse(ok)


class AlertAutoCreationTests(TestCase):
    def setUp(self):
        RiskThreshold.objects.create(is_active=True)
        self.student = Student.objects.create(
            internal_code="ALERT-001", first_name="A", last_name="B",
            birth_year=2010, level="college", class_name="3A",
        )
        self.teacher = User.objects.create_user(
            username="t", password="p1234567!", role=Role.OPERATOR
        )

    def test_alert_created_on_high_risk_entry(self):
        WeeklyEntry.objects.create(
            student=self.student, week_start=date.today(),
            absences=5, control_grade=Decimal("8"),
            previous_grade=Decimal("14"), behavioral_incident=True,
            recorded_by=self.teacher,
        )
        # Le signal post_save devrait avoir créé l'alerte
        self.assertTrue(Alert.objects.filter(student=self.student).exists())

    def test_no_alert_for_low_risk_entry(self):
        WeeklyEntry.objects.create(
            student=self.student, week_start=date.today(),
            absences=0, control_grade=Decimal("14"),
            previous_grade=Decimal("14"), behavioral_incident=False,
            recorded_by=self.teacher,
        )
        self.assertFalse(Alert.objects.filter(student=self.student).exists())


class AlertPermissionTests(TestCase):
    def setUp(self):
        RiskThreshold.objects.create(is_active=True)
        self.student = Student.objects.create(
            internal_code="PERM-001", first_name="A", last_name="B",
            birth_year=2010, level="college", class_name="3A",
        )
        self.teacher = User.objects.create_user(
            username="t", password="p1234567!", role=Role.OPERATOR
        )
        self.counselor = User.objects.create_user(
            username="c", password="p1234567!", role=Role.SUPERVISOR
        )
        self.entry = WeeklyEntry.objects.create(
            student=self.student, week_start=date.today(),
            absences=5, control_grade=Decimal("8"),
            previous_grade=Decimal("14"), behavioral_incident=True,
            recorded_by=self.teacher,
        )
        self.alert = Alert.objects.filter(student=self.student).first()

    def test_counselor_can_validate(self):
        if self.alert:
            self.client.login(username="c", password="p1234567!")
            response = self.client.post(
                reverse("education:alert_detail", args=[self.alert.pk]),
                {"action": "validate"},
            )
            self.alert.refresh_from_db()
            self.assertEqual(self.alert.status, Alert.Status.VALIDATED)

    def test_teacher_blocked_from_alert_detail(self):
        if self.alert:
            self.client.login(username="t", password="p1234567!")
            response = self.client.get(
                reverse("education:alert_detail", args=[self.alert.pk])
            )
            self.assertEqual(response.status_code, 403)
