from django.core.management.base import BaseCommand

from wellbeing.services import mark_missed_sessions


class Command(BaseCommand):
    help = "Marque les séances manquées et déclenche rappel/référencement."

    def handle(self, *args, **options):
        mark_missed_sessions()
        self.stdout.write(self.style.SUCCESS("Séances manquées traitées."))
