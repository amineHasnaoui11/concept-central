#!/usr/bin/env python
"""Vérifie les séances manquées.

Usage : python scripts/check_missed_sessions.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "concept_central.settings")
django.setup()

from wellbeing.services import mark_missed_sessions  # noqa: E402

print("📅 Vérification des séances manquées...")
mark_missed_sessions()
print("✅ Terminé.")
