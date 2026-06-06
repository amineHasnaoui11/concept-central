"""Services pour les comptes élèves (rétro-compatibilité).

NOTE: Le flow recommandé est maintenant l'invitation publique
(accounts.signup_services.claim_invitation).
La fonction `create_student_account` est gardée pour le seed_demo et les tests
mais NE devrait PAS être utilisée en production (le conseiller verrait le
mot de passe).
"""
import secrets
import string

from django.db import transaction

from accounts.models import Role, User
from students.models import Student


def generate_username(student: Student) -> str:
    safe = student.internal_code.replace("-", "_").replace(" ", "_").lower()
    return f"eleve_{safe}"


def generate_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


@transaction.atomic
def create_student_account(student: Student) -> tuple[User, str]:
    """Crée un compte User lié à un Student. Mode démo / tests uniquement."""
    if student.user:
        raise ValueError(f"L'élève {student} a déjà un compte ({student.user.username}).")

    username = generate_username(student)
    base = username
    suffix = 1
    while User.objects.filter(username=username).exists():
        suffix += 1
        username = f"{base}_{suffix}"

    password = generate_password()
    user = User.objects.create_user(
        username=username,
        password=password,
        first_name=student.first_name,
        last_name=student.last_name,
        email=student.parent_email or "",
        role=Role.STUDENT,
    )
    student.user = user
    student.save(update_fields=["user"])

    return user, password


def disable_student_account(student: Student) -> bool:
    if not student.user:
        return False
    student.user.is_active = False
    student.user.save(update_fields=["is_active"])
    return True
