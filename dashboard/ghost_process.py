"""Launches the Ghost Mirror worker only after a session is selected."""
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

GHOST_DIR = Path(__file__).resolve().parent.parent / "6_messaging" / "65"
_process: Optional[subprocess.Popen] = None
_session_name: Optional[str] = None


def start_ghost_bot(session_path: Path, session_name: str) -> subprocess.Popen:
    """Start or replace Ghost Mirror with a selected root session."""
    global _process, _session_name
    if _process is not None and _process.poll() is None:
        stop_ghost_bot(_process)
    env = os.environ.copy()
    env["SESSION_NAME"] = str(session_path)
    _process = subprocess.Popen([sys.executable, "run.py"], cwd=str(GHOST_DIR), env=env)
    _session_name = session_name
    return _process


def status() -> dict:
    running = _process is not None and _process.poll() is None
    return {"running": running, "session_name": _session_name if running else None}


def stop_ghost_bot(proc: Optional[subprocess.Popen] = None) -> None:
    global _process, _session_name
    proc = proc or _process
    if proc is None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
    if proc is _process:
        _process = None
        _session_name = None
