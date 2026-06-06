from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.decorators import role_required
from accounts.models import Role
from education.csv_import import import_weekly_csv
from education.forms import (
    AlertFilterForm,
    CSVUploadForm,
    InterventionForm,
    InterventionOutcomeForm,
    RiskThresholdForm,
    TeacherRequestForm,
    WeeklyEntryForm,
)
from education.models import Alert, Intervention, RiskThreshold, TeacherRequest, WeeklyEntry
from education.services import plan_intervention, process_weekly_entry, resolve_alert, validate_alert
from recommendations.models import InterventionRecommendation


@login_required
@role_required(Role.OPERATOR, Role.SUPERVISOR, Role.ADMIN)
def weekly_entry_create(request):
    if request.user.role != Role.OPERATOR:
        messages.error(request, "Seuls les enseignants peuvent saisir les données.")
        return redirect("dashboard")

    form = WeeklyEntryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        entry = form.save(commit=False)
        entry.recorded_by = request.user
        entry.save()
        process_weekly_entry(entry)
        messages.success(
            request,
            f"Saisie enregistrée. Score : {entry.risk_score}/100 ({entry.risk_level}).",
        )
        return redirect("students:detail", pk=entry.student_id)

    return render(request, "education/weekly_form.html", {"form": form})


@login_required
@role_required(Role.OPERATOR)
def csv_upload(request):
    form = CSVUploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        ok, msg, _ = import_weekly_csv(form.cleaned_data["file"], request.user)
        if ok:
            messages.success(request, msg)
        else:
            messages.error(request, msg)
        return redirect("education:csv_upload")
    return render(request, "education/csv_upload.html", {"form": form})


@login_required
@role_required(Role.SUPERVISOR, Role.ADMIN)
def alert_list(request):
    form = AlertFilterForm(request.GET or None)
    alerts = Alert.objects.select_related("student", "weekly_entry").order_by("-created_at")

    if form.is_valid():
        status = form.cleaned_data.get("status")
        level = form.cleaned_data.get("level")
        q = form.cleaned_data.get("q")
        if status:
            alerts = alerts.filter(status=status)
        if level:
            alerts = alerts.filter(level=level)
        if q:
            alerts = alerts.filter(
                Q(student__first_name__icontains=q)
                | Q(student__last_name__icontains=q)
                | Q(student__internal_code__icontains=q)
            )

    paginator = Paginator(alerts, 20)
    page = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "education/alert_list.html",
        {"alerts": page, "page": page, "form": form, "total": alerts.count()},
    )


@login_required
@role_required(Role.SUPERVISOR, Role.ADMIN)
def alert_detail(request, pk):
    alert = get_object_or_404(
        Alert.objects.select_related("student", "weekly_entry"), pk=pk
    )
    recommendation = InterventionRecommendation.objects.filter(alert=alert).first()
    intervention_form = InterventionForm(request.POST or None)

    is_counselor = request.user.role == Role.SUPERVISOR
    is_admin = request.user.role == Role.ADMIN

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "validate" and is_counselor:
            validate_alert(alert, request.user)
            messages.success(request, "Alerte validée.")
        elif action == "resolve" and is_admin:
            resolve_alert(alert, request.user)
            messages.success(request, "Alerte résolue.")
        elif action == "intervention" and is_counselor and intervention_form.is_valid():
            plan_intervention(
                alert,
                intervention_form.cleaned_data["intervention_type"],
                intervention_form.cleaned_data["planned_date"],
                intervention_form.cleaned_data["notes"],
                request.user,
            )
            messages.success(request, "Intervention planifiée.")
        elif action == "open_psych" and is_counselor and alert.suggests_psych_dossier:
            return redirect("wellbeing:create_dossier", student_id=alert.student_id)
        else:
            messages.error(request, "Action non autorisée.")

        return redirect("education:alert_detail", pk=pk)

    return render(
        request,
        "education/alert_detail.html",
        {
            "alert": alert,
            "intervention_form": intervention_form,
            "recommendation": recommendation,
            "interventions": alert.interventions.all(),
            "is_counselor": is_counselor,
            "is_admin": is_admin,
        },
    )


@login_required
@role_required(Role.SUPERVISOR)
def intervention_outcome(request, pk):
    """Évaluer l'efficacité d'une intervention (item 10)."""
    intervention = get_object_or_404(Intervention, pk=pk)

    if request.method == "POST":
        form = InterventionOutcomeForm(request.POST, instance=intervention)
        if form.is_valid():
            obj = form.save(commit=False)
            if obj.completed and not obj.completed_at:
                obj.completed_at = timezone.now()
            obj.save()
            messages.success(request, "Évaluation enregistrée.")
            return redirect("education:alert_detail", pk=intervention.alert_id)
    else:
        form = InterventionOutcomeForm(instance=intervention)

    return render(
        request,
        "education/intervention_outcome.html",
        {"form": form, "intervention": intervention},
    )


@login_required
@role_required(Role.ADMIN)
def risk_config(request):
    threshold = RiskThreshold.get_active()
    form = RiskThresholdForm(request.POST or None, instance=threshold)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Seuils mis à jour.")
        return redirect("education:risk_config")
    return render(request, "education/risk_config.html", {"form": form})


@login_required
@role_required(Role.ADMIN)
def export_report(request):
    import csv as csv_module

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="rapport_alertes.csv"'
    writer = csv_module.writer(response)
    writer.writerow([
        "id", "eleve_code", "niveau", "score", "statut", "cree_le", "resolu_le",
    ])
    for a in Alert.objects.select_related("student").order_by("-created_at"):
        writer.writerow([
            a.pk,
            a.student.internal_code,
            a.level,
            a.risk_score,
            a.status,
            a.created_at.isoformat(),
            a.resolved_at.isoformat() if a.resolved_at else "",
        ])
    return response


# === TEACHER REQUESTS ===
@login_required
@role_required(Role.OPERATOR)
def teacher_request_create(request):
    form = TeacherRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        tr = form.save(commit=False)
        tr.teacher = request.user
        tr.save()
        messages.success(request, f"Demande envoyée au conseiller pour {tr.student}.")
        return redirect("education:teacher_request_list")
    return render(request, "education/teacher_request_create.html", {"form": form})


@login_required
@role_required(Role.OPERATOR)
def teacher_request_list(request):
    requests_qs = TeacherRequest.objects.filter(teacher=request.user).select_related(
        "student", "assigned_to"
    )
    paginator = Paginator(requests_qs, 20)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "education/teacher_request_list.html", {"requests": page, "page": page})


@login_required
@role_required(Role.SUPERVISOR, Role.ADMIN)
def counselor_request_list(request):
    qs = TeacherRequest.objects.select_related("student", "teacher", "assigned_to")
    return render(
        request,
        "education/counselor_request_list.html",
        {
            "pending": qs.filter(status=TeacherRequest.Status.PENDING),
            "in_progress": qs.filter(status=TeacherRequest.Status.IN_PROGRESS),
            "resolved": qs.filter(status=TeacherRequest.Status.RESOLVED),
        },
    )


@login_required
def teacher_request_detail(request, pk):
    tr = get_object_or_404(
        TeacherRequest.objects.select_related("student", "teacher", "assigned_to"),
        pk=pk,
    )
    is_teacher = request.user == tr.teacher
    is_counselor = request.user.role in [Role.SUPERVISOR, Role.ADMIN]

    if not (is_teacher or is_counselor):
        messages.error(request, "Accès non autorisé.")
        return redirect("dashboard")

    if request.method == "POST" and is_counselor:
        action = request.POST.get("action")
        if action == "take":
            tr.assigned_to = request.user
            tr.status = TeacherRequest.Status.IN_PROGRESS
            tr.save()
            messages.success(request, "Demande prise en charge.")
        elif action == "respond":
            tr.response = request.POST.get("response", "").strip()
            tr.save()
            messages.success(request, "Réponse enregistrée.")
        elif action == "resolve":
            tr.status = TeacherRequest.Status.RESOLVED
            tr.resolved_at = timezone.now()
            tr.save()
            messages.success(request, "Demande résolue.")
        return redirect("education:teacher_request_detail", pk=pk)

    return render(
        request,
        "education/teacher_request_detail.html",
        {"request_obj": tr, "is_teacher": is_teacher, "is_counselor": is_counselor},
    )
