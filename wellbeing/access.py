from accounts.models import Role


def can_view_psych_dossier(user):
    return user.role in (Role.SUPERVISOR, Role.ADMIN)


def can_manage_psych_dossier(user):
    return user.role == Role.SUPERVISOR
