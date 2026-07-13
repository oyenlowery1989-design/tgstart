"""Active-session cookie state and sessions/ directory helpers."""
import os
from pathlib import Path
from typing import List, Optional
from fastapi import Request

ROOT_DIR = Path(__file__).resolve().parent.parent
SESSIONS_DIR = ROOT_DIR / "sessions"
ACTIVE_SESSION_COOKIE = "active_session"


def list_sessions() -> List[str]:
    """Returns sorted session names (no .session extension), skipping temp files."""
    if not SESSIONS_DIR.exists():
        return []
    names = []
    for f in sorted(SESSIONS_DIR.glob("*.session")):
        name = f.stem
        if not name.startswith("temp_login_"):
            names.append(name)
    return sorted(names)


def session_path(session_name: str) -> str:
    """Absolute path (no extension) Telethon expects for TelegramClient(session_path)."""
    return str(SESSIONS_DIR / session_name)


def get_active_session(request: Request) -> Optional[str]:
    """Reads the active_session cookie; falls back to the first available session."""
    sessions = list_sessions()
    cookie_name = request.cookies.get(ACTIVE_SESSION_COOKIE)
    if cookie_name and cookie_name in sessions:
        return cookie_name
    return sessions[0] if sessions else None


if __name__ == "__main__":
    assert callable(list_sessions) and callable(session_path) and callable(get_active_session)
    print("state.py smoke check OK:", list_sessions())
