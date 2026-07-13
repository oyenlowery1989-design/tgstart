"""Launches/monitors the Ghost Mirror bot subprocess, mirroring run.py's run_dashboard_pair()."""
import subprocess
import sys
from pathlib import Path

GHOST_DIR = Path(__file__).resolve().parent.parent / "6_messaging" / "65"


def start_ghost_bot() -> subprocess.Popen:
    return subprocess.Popen([sys.executable, "run.py"], cwd=str(GHOST_DIR))


def stop_ghost_bot(proc: subprocess.Popen) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
