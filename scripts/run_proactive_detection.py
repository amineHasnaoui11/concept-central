#!/usr/bin/env python
"""Lance la détection proactive des élèves à risque.

Usage : python scripts/run_proactive_detection.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "concept_central.settings")
django.setup()

from education.analytics import run_proactive_detection  # noqa: E402

print("🔍 Détection proactive des élèves à risque...")
at_risk = run_proactive_detection()

if at_risk:
    print(f"⚠️  {len(at_risk)} élève(s) détecté(s) :")
    for student, analysis in at_risk:
        print(f"   - {student.first_name} {student.last_name} (score {analysis['current_score']})")
        for ind in analysis["indicators"]:
            print(f"     • {ind}")
else:
    print("✅ Aucun élève à risque proactif détecté.")
