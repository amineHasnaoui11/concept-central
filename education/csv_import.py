import csv
import io
from datetime import datetime
from decimal import Decimal

from audit.models import AuditLog, log_event
from education.models import WeeklyEntry
from education.services import process_weekly_entry
from students.models import Student

REQUIRED_COLUMNS = {
    "internal_code",
    "week_start",
    "absences",
    "control_grade",
    "previous_grade",
    "behavioral_incident",
}


def parse_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "oui", "yes", "o")


def import_weekly_csv(file_obj, user):
    """Import CSV hebdomadaire avec validation stricte."""
    try:
        content = file_obj.read()
        if isinstance(content, bytes):
            content = content.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        msg = "Encodage invalide. Utilisez UTF-8."
        log_event(AuditLog.EventType.CSV_IMPORT_FAILED, msg, user=user, error=str(e))
        return False, msg, []

    first_line = content.split("\n")[0] if content else ""
    delimiter = ";" if ";" in first_line and "," not in first_line else ","
    reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)

    if not reader.fieldnames:
        msg = "Fichier CSV vide ou sans en-têtes."
        log_event(AuditLog.EventType.CSV_IMPORT_FAILED, msg, user=user)
        return False, msg, []

    headers = {h.strip().lower() for h in reader.fieldnames if h and h.strip()}
    missing = REQUIRED_COLUMNS - headers
    if missing:
        msg = (
            f"Colonnes manquantes : {', '.join(sorted(missing))}. "
            f"Requises : {', '.join(sorted(REQUIRED_COLUMNS))}."
        )
        log_event(
            AuditLog.EventType.CSV_IMPORT_FAILED,
            msg,
            user=user,
            found_columns=list(headers),
            missing_columns=list(missing),
        )
        return False, msg, []

    created = []
    errors = []

    def _dec(val):
        if val is None or str(val).strip() == "":
            return None
        return Decimal(str(val).strip().replace(",", "."))

    for row_num, row in enumerate(reader, start=2):
        row = {k.strip().lower(): v for k, v in row.items() if k}
        code = row.get("internal_code", "").strip()
        if not code:
            errors.append(f"Ligne {row_num} : internal_code vide.")
            continue

        try:
            student = Student.objects.get(internal_code=code)
        except Student.DoesNotExist:
            errors.append(f"Ligne {row_num} : élève '{code}' introuvable.")
            continue

        try:
            week_start_str = row["week_start"].strip()
            week_start = None
            for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
                try:
                    week_start = datetime.strptime(week_start_str, fmt).date()
                    break
                except ValueError:
                    continue
            if week_start is None:
                raise ValueError("format non reconnu")
        except (ValueError, KeyError):
            errors.append(
                f"Ligne {row_num} : week_start invalide (DD/MM/YYYY ou YYYY-MM-DD)."
            )
            continue

        try:
            entry, _ = WeeklyEntry.objects.update_or_create(
                student=student,
                week_start=week_start,
                defaults={
                    "absences": int(row.get("absences") or 0),
                    "control_grade": _dec(row.get("control_grade")),
                    "previous_grade": _dec(row.get("previous_grade")),
                    "behavioral_incident": parse_bool(row.get("behavioral_incident", "false")),
                    "observation": row.get("observation", ""),
                    "recorded_by": user,
                },
            )
            process_weekly_entry(entry)
            created.append(entry)
        except Exception as e:
            errors.append(f"Ligne {row_num} : {e}")

    if errors and not created:
        msg = "Import échoué : " + " | ".join(errors[:5])
        log_event(AuditLog.EventType.CSV_IMPORT_FAILED, msg, user=user, errors=errors)
        return False, msg, []

    if errors:
        msg = (
            f"{len(created)} ligne(s) importée(s). "
            f"Avertissements : " + " | ".join(errors[:3])
        )
    else:
        msg = f"{len(created)} saisie(s) importée(s) avec succès."

    return True, msg, created
