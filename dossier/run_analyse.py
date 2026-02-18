#!/usr/bin/env python3
"""
FORENSIC_DOSSIER_ENGINE — Standalone run-script
Voer dit script uit vanuit de workspace-root om de volledige analyse te starten.

Gebruik:
    python dossier/run_analyse.py
    python dossier/run_analyse.py --dossier ./dossier --verbose
"""
from __future__ import annotations

import sys
from pathlib import Path

# Voeg workspace-root toe aan Python-pad
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from dossier.engine.cli import hoofd

if __name__ == "__main__":
    sys.exit(hoofd())
