"""
Archive automatiquement les dossiers dont la date de rétention est dépassée.
À exécuter périodiquement (ex: mensuel).

Usage : python manage.py archive_expired_dossiers
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from audit.models import AuditLog, log_event
from wellbeing.models import PsychDossier, add_timeline_event


class Command(BaseCommand):
    help = "Archive les dossiers dont la date de rétention est dépassée (conformité RGPD)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Affiche seulement les dossiers à archiver, sans modifier.",
        )

    def handle(self, *args, **options):
        today = timezone.now().date()
        qs = PsychDossier.objects.filter(
            retention_until__lt=today,
        ).exclude(status=PsychDossier.Status.ARCHIVED)

        count = qs.count()
        self.stdout.write(f"Dossiers à archiver : {count}")

        if options["dry_run"]:
            for d in qs:
                self.stdout.write(
                    f"  - {d.student.internal_code} (rétention jusqu'au {d.retention_until})"
                )
            return

        for dossier in qs:
            dossier.status = PsychDossier.Status.ARCHIVED
            dossier.save(update_fields=["status"])
            add_timeline_event(
                dossier, None,
                "Archivage automatique",
                f"Période de rétention ({dossier.retention_until}) dépassée.",
            )
            log_event(
                AuditLog.EventType.DOSSIER_OPENED,  # repurposed
                f"Dossier {dossier.pk} archivé (rétention dépassée)",
                student=dossier.student,
                event="dossier_archived",
            )

        self.stdout.write(self.style.SUCCESS(f"{count} dossier(s) archivé(s)."))
