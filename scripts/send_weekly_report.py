#!/usr/bin/env python
"""Envoie manuellement le rapport hebdomadaire à la direction.

Usage : python scripts/send_weekly_report.py
"""
import os
import sys
from pathlib import Path

# Permet l'exécution depuis n'importe où
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "concept_central.settings")
django.setup()

from education.reports import generate_weekly_statistics, send_weekly_report  # noqa: E402

print("=" * 70)
print("📊 ENVOI DU RAPPORT HEBDOMADAIRE")
print("=" * 70)

stats = generate_weekly_statistics()
print(f"\n📅 Période : {stats['period_start']} → {stats['period_end']}")
print(f"   - Alertes : {stats['total_alerts']} (dont {stats['critical_alerts']} critiques)")
print(f"   - Résolues : {stats['resolved_alerts']}")
print(f"   - Interventions : {stats['planned_interventions']}")
print(f"   - Entrées à risque : {stats['high_risk_entries']}/{stats['weekly_entries']}")

print("\n📧 Envoi du rapport...")
if send_weekly_report():
    print("✅ Rapport envoyé avec succès")
    sys.exit(0)
else:
    print("❌ Échec de l'envoi (vérifier .env)")
    sys.exit(1)
