import csv
import io
import json
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.decorators import ROLE_ADMIN, role_required
from audit.models import AuditLog, log_event
from education.models import Alert, WeeklyEntry
from students.forms import ParentConsentForm, StudentForm, StudentSearchForm
from students.models import ParentConsent, Student
from wellbeing.access import can_view_psych_dossier
from wellbeing.models import PsychDossier


@login_required
def student_list(request):
    form = StudentSearchForm(request.GET or None)
    qs = Student.objects.all()

    if form.is_valid():
        q = form.cleaned_data.get("q")
        level = form.cleaned_data.get("level")
        class_name = form.cleaned_data.get("class_name")

        if q:
            qs = qs.filter(
                Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(internal_code__icontains=q)
            )
        if level:
            qs = qs.filter(level=level)
        if class_name:
            qs = qs.filter(class_name__icontains=class_name)

    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "students/list.html",
        {"students": page, "page": page, "form": form, "total": qs.count()},
    )


@login_required
def student_detail(request, pk):
    student = get_object_or_404(Student, pk=pk)
    entries = WeeklyEntry.objects.filter(student=student).order_by("-week_start")[:8]
    alerts = Alert.objects.filter(student=student).order_by("-created_at")[:5]
    dossier = PsychDossier.objects.filter(student=student).first()
    show_psych = dossier and can_view_psych_dossier(request.user)
    consents = student.consents.all()
    return render(
        request,
        "students/detail.html",
        {
            "student": student,
            "entries": entries,
            "alerts": alerts,
            "dossier": dossier if show_psych else None,
            "psych_blocked": bool(dossier and not show_psych),
            "hidden_dossier_id": dossier.pk if dossier and not show_psych else None,
            "consents": consents,
        },
    )


@role_required(*ROLE_ADMIN)
def student_create(request):
    if request.method == "POST":
        form = StudentForm(request.POST)
        if form.is_valid():
            student = form.save()
            messages.success(
                request,
                f"L'élève {student.first_name} {student.last_name} a été créé.",
            )
            return redirect("students:detail", pk=student.pk)
    else:
        form = StudentForm()
    return render(request, "students/create.html", {"form": form, "title": "Créer un élève"})


@role_required(*ROLE_ADMIN)
def student_edit(request, pk):
    student = get_object_or_404(Student, pk=pk)
    if request.method == "POST":
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            updated = form.save()
            messages.success(request, f"{updated} mis à jour.")
            return redirect("students:detail", pk=updated.pk)
    else:
        form = StudentForm(instance=student)
    return render(
        request,
        "students/edit.html",
        {"form": form, "student": student, "title": "Modifier un élève"},
    )


@role_required(*ROLE_ADMIN)
def student_delete(request, pk):
    student = get_object_or_404(Student, pk=pk)
    if request.method == "POST":
        name = f"{student.first_name} {student.last_name}"
        student.delete()
        messages.success(request, f"L'élève {name} a été supprimé.")
        return redirect("students:list")
    return render(
        request,
        "students/delete.html",
        {"student": student, "title": "Supprimer un élève"},
    )


# ============================================================
# BULK IMPORT (admin)
# ============================================================
@role_required(*ROLE_ADMIN)
def student_bulk_import(request):
    """Import en masse d'élèves via CSV."""
    if request.method == "POST" and request.FILES.get("file"):
        file = request.FILES["file"]
        try:
            content = file.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            messages.error(request, "Encodage non supporté. Utilisez UTF-8.")
            return redirect("students:bulk_import")

        first_line = content.split("\n")[0] if content else ""
        delimiter = ";" if ";" in first_line and "," not in first_line else ","
        reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)

        required = {"internal_code", "first_name", "last_name", "birth_year", "level", "class_name"}
        headers = {h.strip().lower() for h in (reader.fieldnames or []) if h}
        missing = required - headers
        if missing:
            messages.error(
                request,
                f"Colonnes manquantes : {', '.join(sorted(missing))}",
            )
            return redirect("students:bulk_import")

        created, updated, errors = 0, 0, []
        for i, row in enumerate(reader, start=2):
            row = {k.strip().lower(): v for k, v in row.items() if k}
            try:
                code = row["internal_code"].strip()
                obj, was_created = Student.objects.update_or_create(
                    internal_code=code,
                    defaults={
                        "first_name": row.get("first_name", "").strip(),
                        "last_name": row.get("last_name", "").strip(),
                        "birth_year": int(row["birth_year"]),
                        "level": row.get("level", "college").strip(),
                        "class_name": row.get("class_name", "").strip(),
                        "parent_full_name": row.get("parent_full_name", "").strip(),
                        "parent_phone": row.get("parent_phone", "").strip(),
                        "parent_email": row.get("parent_email", "").strip(),
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
            except (KeyError, ValueError) as e:
                errors.append(f"Ligne {i} : {e}")

        if errors:
            messages.warning(
                request,
                f"{created} créé(s), {updated} mis à jour, {len(errors)} erreur(s).",
            )
        else:
            messages.success(
                request,
                f"Import réussi : {created} créé(s), {updated} mis à jour.",
            )
        return redirect("students:list")

    return render(request, "students/bulk_import.html")


# ============================================================
# RGPD-style data export (admin)
# ============================================================
@role_required(*ROLE_ADMIN)
def student_data_export(request, pk):
    """Exporte toutes les données d'un élève (droit d'accès RGPD)."""
    student = get_object_or_404(Student, pk=pk)

    data = {
        "exported_at": timezone.now().isoformat(),
        "student": {
            "internal_code": student.internal_code,
            "first_name": student.first_name,
            "last_name": student.last_name,
            "birth_year": student.birth_year,
            "level": student.level,
            "class_name": student.class_name,
            "parent_full_name": student.parent_full_name,
            "parent_phone": student.parent_phone,
            "parent_email": student.parent_email,
            "parent_preferred_language": student.parent_preferred_language,
            "created_at": student.created_at.isoformat(),
        },
        "weekly_entries": [
            {
                "week_start": e.week_start.isoformat(),
                "absences": e.absences,
                "control_grade": str(e.control_grade) if e.control_grade else None,
                "previous_grade": str(e.previous_grade) if e.previous_grade else None,
                "behavioral_incident": e.behavioral_incident,
                "observation": e.observation,
                "risk_score": e.risk_score,
                "risk_level": e.risk_level,
            }
            for e in student.weekly_entries.all()
        ],
        "alerts": [
            {
                "level": a.level,
                "risk_score": a.risk_score,
                "summary": a.summary,
                "status": a.status,
                "created_at": a.created_at.isoformat(),
                "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
            }
            for a in student.alerts.all()
        ],
        "consents": [
            {
                "type": c.consent_type,
                "granted": c.granted,
                "granted_at": c.granted_at.isoformat() if c.granted_at else None,
                "revoked_at": c.revoked_at.isoformat() if c.revoked_at else None,
                "granted_by": c.granted_by,
            }
            for c in student.consents.all()
        ],
    }

    # Dossier psychologique : uniquement le métadonnée, pas les notes cliniques
    if hasattr(student, "psych_dossier"):
        d = student.psych_dossier
        data["psych_dossier"] = {
            "status": d.status,
            "created_at": d.created_at.isoformat(),
            "summary": d.summary,
            "sessions_count": d.sessions.count(),
        }

    log_event(
        AuditLog.EventType.ACCESS_DENIED,  # repurposed for traceability
        f"Export RGPD demandé pour {student.internal_code}",
        user=request.user,
        student=student,
        event="rgpd_data_export",
    )

    response = HttpResponse(
        json.dumps(data, indent=2, ensure_ascii=False),
        content_type="application/json; charset=utf-8",
    )
    response["Content-Disposition"] = (
        f'attachment; filename="export_{student.internal_code}_'
        f'{timezone.now().strftime("%Y%m%d")}.json"'
    )
    return response


# ============================================================
# CONSENT MANAGEMENT
# ============================================================
@role_required(*ROLE_ADMIN)
def student_consents(request, pk):
    student = get_object_or_404(Student, pk=pk)
    if request.method == "POST":
        form = ParentConsentForm(request.POST)
        if form.is_valid():
            consent_type = form.cleaned_data["consent_type"]
            obj, _ = ParentConsent.objects.update_or_create(
                student=student,
                consent_type=consent_type,
                defaults={
                    "granted": form.cleaned_data["granted"],
                    "granted_by": form.cleaned_data["granted_by"],
                    "notes": form.cleaned_data["notes"],
                    "granted_at": timezone.now() if form.cleaned_data["granted"] else None,
                    "revoked_at": None if form.cleaned_data["granted"] else timezone.now(),
                    "recorded_by": request.user,
                },
            )
            messages.success(request, "Consentement enregistré.")
            return redirect("students:consents", pk=pk)
    else:
        form = ParentConsentForm()

    return render(
        request,
        "students/consents.html",
        {"student": student, "consents": student.consents.all(), "form": form},
    )
