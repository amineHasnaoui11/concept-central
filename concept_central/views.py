from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.shortcuts import render
from django.utils import timezone

from accounts.models import Role
from education.models import Alert, Intervention, WeeklyEntry
from students.models import Student
from wellbeing.models import PsychDossier


@login_required
def dashboard(request):
    user = request.user
    ctx = {"role": user.role}

    # Élève → redirection vers son dashboard dédié
    if user.role == Role.STUDENT:
        from django.shortcuts import redirect
        return redirect("meetings:student_dashboard")

    if user.role == Role.OPERATOR:
        ctx["recent_entries"] = (
            WeeklyEntry.objects.filter(recorded_by=user)
            .select_related("student")[:10]
        )

        entries_for_chart = WeeklyEntry.objects.filter(
            recorded_by=user
        ).order_by("-week_start")[:8]

        ctx["weeks_labels"] = [
            e.week_start.strftime("%d/%m") for e in reversed(entries_for_chart)
        ]
        ctx["avg_grades"] = [
            float(e.control_grade) if e.control_grade else 0
            for e in reversed(entries_for_chart)
        ]

        absences_data = (
            WeeklyEntry.objects.filter(recorded_by=user)
            .values("student__first_name", "student__last_name")
            .annotate(total_absences=Count("absences"))
            .order_by("-total_absences")[:10]
        )

        ctx["students_absences"] = [
            f"{d['student__first_name']} {d['student__last_name']}" for d in absences_data
        ]
        ctx["absences_counts"] = [d["total_absences"] for d in absences_data]

        ctx["recent_alerts_count"] = Alert.objects.filter(
            weekly_entry__recorded_by=user
        ).count()

        return render(request, "dashboard/operator.html", ctx)

    if user.role == Role.SUPERVISOR:
        ctx["pending_alerts"] = (
            Alert.objects.filter(status=Alert.Status.PENDING)
            .select_related("student")[:15]
        )
        ctx["open_dossiers"] = PsychDossier.objects.filter(
            status=PsychDossier.Status.OPEN
        ).count()

        alerts_by_level = Alert.objects.values("level").annotate(count=Count("id"))
        ctx["alert_levels"] = [a["level"] for a in alerts_by_level]
        ctx["alert_counts"] = [a["count"] for a in alerts_by_level]

        twelve_weeks_ago = timezone.now().date() - timedelta(weeks=12)
        alerts_timeline = (
            Alert.objects.filter(created_at__gte=twelve_weeks_ago)
            .extra(select={"week": 'strftime("%%Y-%%W", created_at)'})
            .values("week")
            .annotate(count=Count("id"))
            .order_by("week")
        )

        ctx["alert_weeks"] = [a["week"] for a in alerts_timeline]
        ctx["alert_weekly_counts"] = [a["count"] for a in alerts_timeline]

        total_interventions = Intervention.objects.count()
        resolved_interventions = Intervention.objects.filter(
            alert__status=Alert.Status.RESOLVED
        ).count()
        ctx["interventions_planned"] = total_interventions
        ctx["interventions_resolved"] = resolved_interventions

        return render(request, "dashboard/supervisor.html", ctx)

    if user.role == Role.ADMIN:
        ctx["alert_stats"] = Alert.objects.values("status").annotate(total=Count("id"))
        ctx["student_count"] = Student.objects.count()
        ctx["total_alerts"] = Alert.objects.count()
        ctx["total_entries"] = WeeklyEntry.objects.count()
        ctx["open_dossiers"] = PsychDossier.objects.filter(
            status=PsychDossier.Status.OPEN
        ).count()

        alerts_by_class = (
            Alert.objects.values("student__class_name")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )
        ctx["classes"] = [a["student__class_name"] for a in alerts_by_class]
        ctx["class_alert_counts"] = [a["count"] for a in alerts_by_class]

        eight_weeks_ago = timezone.now().date() - timedelta(weeks=8)
        entries_timeline = (
            WeeklyEntry.objects.filter(week_start__gte=eight_weeks_ago)
            .values("week_start")
            .annotate(avg_risk=Avg("risk_score"), count=Count("id"))
            .order_by("week_start")
        )

        ctx["trend_weeks"] = [
            e["week_start"].strftime("%d/%m") for e in entries_timeline
        ]
        ctx["trend_avg_risk"] = [
            float(e["avg_risk"]) if e["avg_risk"] else 0 for e in entries_timeline
        ]

        return render(request, "dashboard/admin.html", ctx)

    return render(request, "dashboard/generic.html", ctx)
