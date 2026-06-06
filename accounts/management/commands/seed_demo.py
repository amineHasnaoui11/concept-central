from datetime import date, timedelta

from django.core.management.base import BaseCommand

from accounts.models import Role, User
from education.models import RiskThreshold, WeeklyEntry
from education.services import process_weekly_entry
from students.models import Student


class Command(BaseCommand):
    help = "Crée utilisateurs démo, élèves et une saisie à risque."

    def handle(self, *args, **options):
        RiskThreshold.get_active()

        users = [
            ("enseignant", Role.OPERATOR, "Enseignant", "enseignant@ecole.tn"),
            ("conseiller", Role.SUPERVISOR, "Conseiller", "conseiller@ecole.tn"),
            ("direction", Role.ADMIN, "Direction", "direction@ecole.tn"),
        ]
        for username, role, first, email in users:
            u, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "role": role,
                    "first_name": first,
                    "email": email,
                    "is_active": True,
                },
            )
            u.role = role
            u.email = email
            u.is_active = True
            u.set_password("demo1234")
            u.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f"{'Créé' if created else 'Réinitialisé'} : {username} / demo1234"
                )
            )

        students_data = [
            ("TN-2024-001", "Youssef", "Ben Ali", 2011, "3A", Student.Level.COLLEGE, "parent1@famille.tn"),
            ("TN-2024-002", "Salma", "Trabelsi", 2010, "2B", Student.Level.COLLEGE, "parent2@famille.tn"),
            ("TN-2024-003", "Omar", "Mansour", 2008, "1S", Student.Level.LYCEE, "parent3@famille.tn"),
        ]
        for code, fn, ln, by, cls, lvl, p_email in students_data:
            Student.objects.update_or_create(
                internal_code=code,
                defaults={
                    "first_name": fn,
                    "last_name": ln,
                    "birth_year": by,
                    "class_name": cls,
                    "level": lvl,
                    "parent_email": p_email,
                    "parent_full_name": f"Parent de {fn}",
                    "parent_phone": "+216 00 000 000",
                },
            )

        teacher = User.objects.get(username="enseignant")
        s1 = Student.objects.get(internal_code="TN-2024-001")
        week = date.today() - timedelta(days=date.today().weekday())

        entry, _ = WeeklyEntry.objects.update_or_create(
            student=s1,
            week_start=week,
            defaults={
                "absences": 4,
                "control_grade": "8.50",
                "previous_grade": "14.00",
                "behavioral_incident": True,
                "observation": "Isolement, baisse brutale des résultats.",
                "recorded_by": teacher,
            },
        )
        _, alert = process_weekly_entry(entry)
        if alert:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Alerte démo créée (score {alert.risk_score}, "
                    f"pont psych: {alert.suggests_psych_dossier})"
                )
            )

        # === Compte élève + RDV démo ===
        from wellbeing.models import PsychDossier
        from meetings.models import Meeting
        from meetings.services import create_student_account
        from django.utils import timezone
        from datetime import timedelta as _td

        counselor = User.objects.get(username="conseiller")
        dossier, _ = PsychDossier.objects.get_or_create(
            student=s1,
            defaults={"opened_by": counselor, "summary": "Suivi démo"},
        )

        if not s1.user:
            try:
                user, pwd = create_student_account(s1)
                # En démo on force un mot de passe simple
                user.set_password("eleve1234")
                user.save()
                self.stdout.write(self.style.SUCCESS(
                    f"Compte élève : {user.username} / eleve1234"
                ))
            except ValueError:
                pass
        else:
            # Réinitialise le mot de passe pour la démo
            s1.user.set_password("eleve1234")
            s1.user.save()
            self.stdout.write(self.style.SUCCESS(
                f"Compte élève réinitialisé : {s1.user.username} / eleve1234"
            ))
            s1.refresh_from_db()

        # Crée un RDV joignable immédiatement pour la démo (dans 3 minutes)
        if s1.user and not Meeting.objects.filter(student=s1).exists():
            meeting = Meeting.objects.create(
                dossier=dossier, student=s1, counselor=counselor,
                scheduled_at=timezone.now() + _td(minutes=3),
                topic="RDV de démonstration",
                counselor_notes="RDV automatique créé par seed_demo",
            )
            meeting.approve(message="OK (auto)")
            self.stdout.write(self.style.SUCCESS(
                f"RDV démo créé (joignable immédiatement)"
            ))

        self.stdout.write(self.style.SUCCESS("Données de démonstration prêtes."))
