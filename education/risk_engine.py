from education.models import RiskThreshold, WeeklyEntry


class RiskLevel:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


def compute_risk_score(entry: WeeklyEntry, thresholds: RiskThreshold | None = None):
    """Moteur de règles : absences + baisse de notes + incident comportemental + note critique."""
    thresholds = thresholds or RiskThreshold.get_active()
    score = 0
    reasons = []

    if entry.absences > thresholds.max_absences:
        score += 35
        reasons.append(f"Absences élevées ({entry.absences} > {thresholds.max_absences})")
    elif entry.absences == thresholds.max_absences:
        score += 20
        reasons.append(f"Absences au seuil ({entry.absences})")

    if entry.control_grade is not None and entry.previous_grade is not None:
        prev = float(entry.previous_grade)
        curr = float(entry.control_grade)
        if prev > 0:
            drop_pct = ((prev - curr) / prev) * 100
            if drop_pct >= thresholds.grade_drop_percent:
                score += 40
                reasons.append(
                    f"Baisse des notes ~{drop_pct:.0f}% (seuil {thresholds.grade_drop_percent}%)"
                )
            elif drop_pct >= thresholds.grade_drop_percent * 0.5:
                score += 20
                reasons.append(f"Baisse modérée des notes (~{drop_pct:.0f}%)")

    if entry.control_grade is not None:
        from decimal import Decimal
        current_grade = Decimal(str(entry.control_grade))
        critical_threshold = Decimal(str(thresholds.critical_grade_threshold))
        if current_grade <= critical_threshold:
            score += 30
            reasons.append(f"Note critique ({entry.control_grade}/20)")

    if entry.behavioral_incident:
        score += 25
        reasons.append("Incident comportemental signalé")

    score = min(100, score)

    if score >= thresholds.critical_score:
        level = RiskLevel.CRITICAL
    elif score >= thresholds.high_risk_score:
        level = RiskLevel.HIGH
    elif score >= 25:
        level = RiskLevel.MEDIUM
    else:
        level = RiskLevel.LOW

    return score, level, reasons


def apply_risk_to_entry(entry: WeeklyEntry):
    score, level, reasons = compute_risk_score(entry)
    entry.risk_score = score
    entry.risk_level = level
    entry.save(update_fields=["risk_score", "risk_level"])
    return score, level, reasons
