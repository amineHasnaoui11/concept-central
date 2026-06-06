"""Services pour le système d'invitation et le signup élève."""
from django.db import transaction

from accounts.invitations import StudentInvitation
from accounts.models import Role, User
from students.models import Student


def generate_student_invitation(student: Student, created_by: User) -> StudentInvitation:
    """Génère un nouveau code d'invitation pour un élève.

    Invalide automatiquement les invitations précédentes non utilisées
    (sécurité : un seul code valide à la fois).
    """
    if student.user:
        raise ValueError(
            f"L'élève {student} possède déjà un compte ({student.user.username})."
        )

    # Invalider les invitations précédentes non utilisées
    from django.utils import timezone
    StudentInvitation.objects.filter(
        student=student, used_at__isnull=True
    ).update(expires_at=timezone.now())

    invitation = StudentInvitation.objects.create(
        student=student,
        created_by=created_by,
    )
    return invitation


def suggest_username(student: Student) -> str:
    """Suggère un username basé sur le code interne."""
    safe = student.internal_code.replace("-", "_").replace(" ", "_").lower()
    return f"eleve_{safe}"


@transaction.atomic
def claim_invitation(
    invitation_code: str,
    internal_code: str,
    username: str,
    password: str,
) -> tuple[User, Student]:
    """Crée un compte élève à partir d'une invitation valide.

    Vérifie :
    - L'invitation existe et est valide (non utilisée, non expirée)
    - Le code interne correspond bien à l'élève de l'invitation
    - Le username est disponible

    Retourne (User créé, Student lié).
    """
    try:
        invitation = StudentInvitation.objects.select_for_update().get(code=invitation_code)
    except StudentInvitation.DoesNotExist:
        raise ValueError("Code d'invitation introuvable.")

    if not invitation.is_valid:
        if invitation.is_used:
            raise ValueError("Ce code d'invitation a déjà été utilisé.")
        raise ValueError("Ce code d'invitation a expiré. Demandez-en un nouveau.")

    if invitation.student.internal_code.lower() != internal_code.strip().lower():
        raise ValueError(
            "Le code interne ne correspond pas à cette invitation."
        )

    if invitation.student.user is not None:
        raise ValueError("Un compte existe déjà pour cet élève.")

    username_clean = username.strip()
    if User.objects.filter(username__iexact=username_clean).exists():
        raise ValueError(
            f"Le nom d'utilisateur « {username_clean} » est déjà pris. "
            "Essayez-en un autre."
        )

    student = invitation.student

    # user.email = parent_email → permet password reset via parent
    user = User.objects.create_user(
        username=username_clean,
        password=password,
        first_name=student.first_name,
        last_name=student.last_name,
        email=student.parent_email or "",
        role=Role.STUDENT,
    )

    student.user = user
    student.save(update_fields=["user"])

    invitation.mark_used(user)

    return user, student


def revoke_invitation(invitation: StudentInvitation):
    """Force l'expiration d'une invitation (admin)."""
    from django.utils import timezone
    invitation.expires_at = timezone.now()
    invitation.save(update_fields=["expires_at"])
