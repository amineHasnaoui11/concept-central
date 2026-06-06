from django.core.management.base import BaseCommand

from accounts.models import User


class Command(BaseCommand):
    help = "Réinitialise les mots de passe des comptes démo à demo1234."

    def handle(self, *args, **options):
        for username in ("enseignant", "conseiller", "direction"):
            u = User.objects.filter(username=username).first()
            if not u:
                self.stdout.write(self.style.ERROR(f"Compte manquant : {username}"))
                continue
            u.is_active = True
            u.set_password("demo1234")
            u.save()
            self.stdout.write(self.style.SUCCESS(f"OK : {username} / demo1234"))
        self.stdout.write("Reconnectez-vous sur http://127.0.0.1:8000/")
