"""Détection proactive des risques et analyse de tendances"""
from datetime import datetime, timedelta

from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

from education.models import Alert, WeeklyEntry
from education.notifications import get_counselor_emails
from students.models import Student


def analyze_student_trend(student, weeks=4):
    entries = WeeklyEntry.objects.filter(student=student).order_by("-week_start")[:weeks]
    if len(entries) < 2:
        return {"trend": "insufficient_data", "risk_level": "unknown", "indicators": []}

    indicators = []
    risk_scores = [e.risk_score for e in entries]

    if len(risk_scores) >= 3:
        recent_avg = sum(risk_scores[:2]) / 2
        older_avg = sum(risk_scores[2:]) / len(risk_scores[2:])
        if recent_avg > older_avg + 15:
            trend = "declining"
            indicators.append(f"Score en hausse (+{recent_avg - older_avg:.0f} points)")
        elif recent_avg < older_avg - 15:
            trend = "improving"
        else:
            trend = "stable"
    else:
        trend = "stable"

    absences = [e.absences for e in entries]
    if len(absences) >= 2 and absences[0] > absences[1] + 2:
        indicators.append(f"Absences en hausse ({absences[0]})")

    grades = [(e.control_grade, e.previous_grade) for e in entries
              if e.control_grade and e.previous_grade]
    if len(grades) >= 2:
        recent = float(grades[0][0])
        older = float(grades[1][0])
        if recent < older - 3:
            indicators.append(f"Baisse notable ({recent:.1f} vs {older:.1f})")

    incidents = [e.behavioral_incident for e in entries]
    if sum(incidents) >= 2:
        indicators.append(f"Incidents répétés ({sum(incidents)}/{len(incidents)})")

    current_score = risk_scores[0]
    if current_score >= 70 or (current_score >= 50 and trend == "declining"):
        risk_level = "high"
    elif current_score >= 40 or (current_score >= 30 and trend == "declining"):
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "trend": trend, "risk_level": risk_level,
        "indicators": indicators, "current_score": current_score,
        "score_evolution": risk_scores,
    }


def detect_at_risk_students():
    at_risk = []
    students = Student.objects.filter(weekly_entries__isnull=False).distinct()

    for student in students:
        analysis = analyze_student_trend(student, weeks=4)
        if (analysis["trend"] == "declining"
                and 35 <= analysis["current_score"] < 50):
            recent_alerts = Alert.objects.filter(
                student=student,
                created_at__gte=datetime.now() - timedelta(days=14),
            )
            if not recent_alerts.exists():
                at_risk.append((student, analysis))
    return at_risk


def send_proactive_alert_notification(at_risk_students):
    if not at_risk_students:
        return False
    counselor_emails = get_counselor_emails()
    if not counselor_emails:
        return False

    subject = f"🔍 Détection Proactive : {len(at_risk_students)} élève(s) à surveiller"
    context = {"at_risk_students": at_risk_students, "site_url": settings.SITE_URL}
    html_message = render_to_string("emails/proactive_alert.html", context)

    try:
        email = EmailMessage(
            subject=subject,
            body=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=counselor_emails,
        )
        email.content_subtype = "html"
        email.send(fail_silently=False)
        return True
    except Exception:
        return False


def run_proactive_detection():
    at_risk = detect_at_risk_students()
    if at_risk:
        send_proactive_alert_notification(at_risk)
    return at_risk
