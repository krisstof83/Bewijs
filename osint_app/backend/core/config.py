from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
APP_DIR = BASE_DIR
DATA_DIR = APP_DIR / "data"
IMPORTS_DIR = APP_DIR / "imports"
STATE_FILE = DATA_DIR / "import_state.json"
EVIDENCE_FILE = DATA_DIR / "evidence.json"
DOSSIERS_FILE = DATA_DIR / "dossiers.json"
TIMELINE_FILE = DATA_DIR / "timeline.json"
OSINT_FILE = DATA_DIR / "osint_results.json"

IMPORT_FOLDERS = (
    IMPORTS_DIR / "pdf",
    IMPORTS_DIR / "gmail",
    IMPORTS_DIR / "drive",
)

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".json", ".html", ".eml", ".csv"}
DATE_REGEX = r"\b(20\d{2}-\d{2}-\d{2})\b"
