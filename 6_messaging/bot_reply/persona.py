"""Loads the AI persona used to draft replies. Re-reads the global file fresh on every
call — no restart needed to change tone. A per-chat override (from chat_config) takes
priority when set."""
from pathlib import Path
from typing import Optional

DEFAULT_PERSONA_PATH = Path(__file__).resolve().parent / "persona.txt"


def load_persona(persona_override: Optional[str], persona_path: Path = DEFAULT_PERSONA_PATH) -> str:
    if persona_override:
        return persona_override
    try:
        return persona_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return ""


if __name__ == "__main__":
    assert load_persona("custom persona text") == "custom persona text"
    assert isinstance(load_persona(None), str)  # falls back to file (or "" if missing)
    print("persona.py smoke check OK")
