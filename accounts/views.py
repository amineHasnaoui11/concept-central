from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache

from accounts.decorators import ROLE_SUPERVISOR_OR_ADMIN, role_required
from accounts.forms import LoginForm, StudentSignupForm
from accounts.invitations import StudentInvitation
from accounts.models import Role
from accounts.signup_services import (
    claim_invitation,
    generate_student_invitation,
    revoke_invitation,
    suggest_username,
)
from audit.models import AuditLog, log_event
from students.models import Student


@never_cache
def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = LoginForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect("dashboard")
    return render(request, "accounts/login.html", {"form": form})


@login_required
def logout_view(request):
    logout(request)
    return redirect("accounts:login")


# ============================================================
# CÔTÉ CONSEILLER / ADMIN : générer / révoquer une invitation
# ============================================================
@login_required
@role_required(*ROLE_SUPERVISOR_OR_ADMIN)
def invitation_generate(request, student_id):
    """Génère un code d'invitation pour qu'un élève crée son compte."""
    student = get_object_or_404(Student, pk=student_id)

    if student.user:
        messages.info(
            request,
            f"L'élève a déjà un compte ({student.user.username}). "
            "Plus d'invitation nécessaire.",
        )
        return redirect("students:detail", pk=student.pk)

    if request.method == "POST":
        try:
            invitation = generate_student_invitation(student, request.user)
            log_event(
                AuditLog.EventType.DOSSIER_OPENED,
                f"Invitation élève générée pour {student.internal_code}",
                user=request.user,
                student=student,
                event="invitation_generated",
                code_prefix=invitation.code[:8],
            )
            return render(
                request,
                "accounts/invitation_created.html",
                {
                    "student": student,
                    "invitation": invitation,
                    "signup_url": request.build_absolute_uri("/inscription/"),
                },
            )
        except ValueError as e:
            messages.error(request, str(e))
            return redirect("students:detail", pk=student.pk)

    return render(
        request,
        "accounts/invitation_confirm.html",
        {"student": student},
    )


@login_required
@role_required(*ROLE_SUPERVISOR_OR_ADMIN)
def invitation_revoke(request, pk):
    """Révoque une invitation non utilisée."""
    invitation = get_object_or_404(StudentInvitation, pk=pk)
    if invitation.is_used:
        messages.error(request, "Cette invitation a déjà été utilisée — impossible à révoquer.")
    else:
        revoke_invitation(invitation)
        messages.success(request, f"Invitation {invitation.code[:12]}... révoquée.")
    return redirect("students:detail", pk=invitation.student.pk)


# ============================================================
# CÔTÉ ÉLÈVE : inscription publique
# ============================================================
@never_cache
def student_signup(request):
    """Inscription publique d'un élève à partir d'un code d'invitation."""
    if request.user.is_authenticated:
        return redirect("dashboard")

    # Pré-remplissage si le code est dans l'URL : /inscription/?code=INV-XXX
    initial = {}
    if request.method == "GET" and "code" in request.GET:
        initial["invitation_code"] = request.GET["code"]

    form = StudentSignupForm(request.POST or None, initial=initial)

    if request.method == "POST" and form.is_valid():
        try:
            user, student = claim_invitation(
                invitation_code=form.cleaned_data["invitation_code"],
                internal_code=form.cleaned_data["internal_code"],
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password1"],
            )
            log_event(
                AuditLog.EventType.DOSSIER_OPENED,
                f"Compte élève créé via invitation : {user.username}",
                student=student,
                event="student_signup_completed",
            )
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            messages.success(
                request,
                f"Bienvenue {student.first_name} ! Votre compte est créé.",
            )
            return redirect("meetings:student_dashboard")
        except ValueError as e:
            form.add_error(None, str(e))

    return render(request, "accounts/student_signup.html", {"form": form})
