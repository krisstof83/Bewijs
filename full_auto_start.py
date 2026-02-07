#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP_DIR = ROOT / "osint_app"
BACKEND_DIR = APP_DIR / "backend"
FRONTEND_DIR = APP_DIR / "frontend"
VENV_DIR = BACKEND_DIR / ".venv"

REQUIRED_DIRS = [
    ROOT / "dossiers" / "personen",
    ROOT / "dossiers" / "zaken",
    ROOT / "dossiers" / "bewijs" / "pdf",
    ROOT / "dossiers" / "bewijs" / "emails",
    ROOT / "dossiers" / "bewijs" / "screenshots",
    ROOT / "imports" / "pdf",
    ROOT / "imports" / "gmail",
    ROOT / "imports" / "drive",
]


def ensure_python() -> None:
    if sys.version_info < (3, 10):
        raise SystemExit("Python 3.10+ is vereist")


def ensure_venv() -> Path:
    if not VENV_DIR.exists():
        subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)
    return VENV_DIR / "bin" / "python"


def install_deps(pybin: Path) -> None:
    subprocess.run([str(pybin), "-m", "pip", "install", "--upgrade", "pip"], check=True)
    subprocess.run([str(pybin), "-m", "pip", "install", "-r", str(BACKEND_DIR / "requirements.txt")], check=True)


def ensure_dirs() -> None:
    for directory in REQUIRED_DIRS:
        directory.mkdir(parents=True, exist_ok=True)


def find_free_port(start: int) -> int:
    for port in range(start, start + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("Geen vrije poort gevonden")


def wait_http(url: str, timeout: float = 20.0) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status < 500:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def start_backend(pybin: Path, port: int) -> subprocess.Popen:
    return subprocess.Popen(
        [str(pybin), "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", str(port)],
        cwd=APP_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def start_frontend(port: int) -> subprocess.Popen:
    python_exec = shutil.which("python3") or shutil.which("python") or sys.executable
    return subprocess.Popen(
        [python_exec, "-m", "http.server", str(port)],
        cwd=FRONTEND_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def main() -> None:
    ensure_python()
    ensure_dirs()
    pybin = ensure_venv()
    install_deps(pybin)

    backend_port = find_free_port(8000)
    backend_proc = start_backend(pybin, backend_port)
    backend_ok = wait_http(f"http://127.0.0.1:{backend_port}/health")
    if not backend_ok:
        backend_proc.kill()
        raise SystemExit("Backend niet bereikbaar")

    frontend_port = find_free_port(4173)
    frontend_proc = start_frontend(frontend_port)
    frontend_ok = wait_http(f"http://127.0.0.1:{frontend_port}/")
    if not frontend_ok:
        frontend_proc.kill()
        raise SystemExit("Frontend niet bereikbaar")

    frontend_url = f"http://127.0.0.1:{frontend_port}/index.html?api=http://127.0.0.1:{backend_port}"
    try:
        webbrowser.open(frontend_url)
    except Exception:
        pass

    status = ROOT / "full_auto_status.txt"
    status.write_text(
        "\n".join(
            [
                f"backend_port={backend_port}",
                f"frontend_port={frontend_port}",
                f"frontend_url={frontend_url}",
                f"backend_pid={backend_proc.pid}",
                f"frontend_pid={frontend_proc.pid}",
            ]
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
