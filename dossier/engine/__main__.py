"""
FORENSIC_DOSSIER_ENGINE — Module entry point
Maakt aanroep via `python -m dossier.engine` mogelijk.
"""
from .cli import hoofd
import sys

sys.exit(hoofd())
