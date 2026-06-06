from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from accounts.models import Role


def role_required(*roles):
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if request.user.role not in roles:
                raise PermissionDenied(
                    f"Rôle '{request.user.get_role_display()}' non autorisé."
                )
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


ROLE_OPERATOR = (Role.OPERATOR,)
ROLE_SUPERVISOR = (Role.SUPERVISOR,)
ROLE_ADMIN = (Role.ADMIN,)
ROLE_STUDENT = (Role.STUDENT,)
ROLE_SUPERVISOR_OR_ADMIN = (Role.SUPERVISOR, Role.ADMIN,)
ROLE_ALL_STAFF = (Role.OPERATOR, Role.SUPERVISOR, Role.ADMIN,)
