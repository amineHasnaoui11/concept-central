from functools import wraps

from django.shortcuts import redirect


PARENT_SESSION_KEY = "family_parent_email"


def parent_login(request, email: str):
    request.session[PARENT_SESSION_KEY] = email.lower()
    request.session.set_expiry(60 * 60 * 2)


def parent_logout(request):
    request.session.pop(PARENT_SESSION_KEY, None)


def current_parent_email(request):
    return request.session.get(PARENT_SESSION_KEY)


def parent_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not current_parent_email(request):
            return redirect("family:request_access")
        return view_func(request, *args, **kwargs)
    return _wrapped
