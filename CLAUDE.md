# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Telethon-based Telegram automation suite: a numbered pipeline of standalone CLI scripts (login, verification, chat/group listing, scraping, monitoring, messaging) launched from one interactive menu (`run.py`), plus two separate "Ghost Mirror" message-mirroring subsystems under `6_messaging/`.

## Commands

Root-level scripts share one venv and `requirements.txt`:

```bash
python -m venv venv
venv/bin/pip install -r requirements.txt   # or venv\Scripts\pip on Windows
python run.py                              # interactive menu, choice 0 to exit
```

`6_messaging/64_claude_edition/` and `6_messaging/65/` each have their **own** `requirements.txt` and are meant to run in their own venv (installed separately, not from the root `requirements.txt`). Root `run.py` choices 7/8 launch them as subprocesses:

- Choice 7 → `6_messaging/64_claude_edition/run.py` (a supervisor loop around `ghost_runner.py`)
- Choice 8 → starts `6_messaging/65/run.py` (bot) in the background, then `6_messaging/65/dashboard.py` (FastAPI UI, `http://127.0.0.1:8000`) in the foreground

There is no test suite, linter config, or CI in this repo — don't assume `pytest`/`ruff`/etc. exist. `python -m py_compile <file>` is the only verification available for a quick syntax check.

## Architecture

### Numbered pipeline convention

Each top-level `N_name/` directory is a self-contained stage; scripts inside are prefixed with their stage number (e.g. `31_list_group_users.py` lives in `3_chat_management/`). `run.py` is a thin dispatcher — each menu choice just `subprocess.run`s a script by path, no shared in-process state between stages. When a stage got a "basic" version and later an "advanced" one (`2_verify_login.py` → `2_verify_login_advanced.py`, `40_scrape_links.py` → `41_scrape_links_advanced.py`), only the advanced script is wired into the menu; the superseded one is typically left in place unwired rather than deleted.

Script outputs go to a dedicated `NN_data/` folder next to the script (e.g. `31_data/`), gitignored except for a `.gitkeep`.

### Shared `utils/` package

- `utils/ui_utils.py`: the only sanctioned way to touch `rich` — new scripts should import from here (`console`, `print_header`, `print_error`, `print_success`, `create_table`, `get_progress`), not import `rich` directly.
- `utils/tg_utils.py`: `pick_target`/`pick_group` (interactive entity pickers), `slugify`.

### Env var convention

Scripts prefer `MAIN_API_ID`/`MAIN_API_HASH`, falling back to `API_ID`/`API_HASH` if unset. `DEFAULT_SESSION` (or `SESSION_NAME` in the messaging subsystems) points at the active `.session` file, typically under `sessions/`. Never hardcode real `API_ID`/`API_HASH` values as fallback defaults in code — this has happened before and required a git-history rewrite to fix; fallback defaults must be `0`/`""`.

Privacy/safety-sensitive behavior is opt-in via env flags, off by default: `EXPORT_PHONE_NUMBERS` and `AGGRESSIVE_SCRAPE` in `3_chat_management/31_list_group_users.py`.

### `6_messaging/`: two independent Ghost Mirror implementations

Both mirror messages between a source chat and a backup chat, but with different architectures — they are **not** interchangeable versions, both are intentionally kept:

- **`64_claude_edition/`**: CLI-only, modular `src/{config,core,handlers,utils}/` layout, one handler class per event type, JSON/JSONL file-based persistence (`data/mirrors.json`, `data/history/*.json`, `data/users/*.json`). No web UI.
- **`65/`**: FastAPI dashboard (`dashboard.py`) + monolithic `ghost_runner.py` (Telethon client, SQLite `DatabaseManager`/`ConfigManager`/`AuditLogger`, all event handling in one file) + SQLite backend (`data/ghost.db`) with schema migrations gated by `PRAGMA user_version`. Per-chat config toggles (`toggle_mirror_new`, `toggle_edits`, `toggle_admin`, `toggle_reactions`, etc.) live in the `config` table and hot-reload into the running bot within ~2s via a polled `config_bump` timestamp — no restart needed to change a chat's settings from the dashboard.

`65`'s dashboard is gated by HTTP Basic auth (`DASHBOARD_USER`/`DASHBOARD_PASSWORD`); if unset, it only binds loopback — it refuses to start bound to a non-loopback host without a password set (fail-closed by design, see the startup check in `dashboard.py`).

`65/ghost_runner.py`'s `messages` table tracks `dest_message_id` (where a source message landed in the backup chat) — this is what lets reactions and replies thread onto the correct mirrored message. When editing `_cache_message`, always update via `ON CONFLICT DO UPDATE` on specific columns, never `INSERT OR REPLACE`, or an edit will silently wipe the recorded `dest_message_id`.

### Adding a new script

Per project convention (previously documented in `docs/GUIDELINES.md`): wrap `asyncio.run()` in try/except for `KeyboardInterrupt`/`EOFError`, save session files under `sessions/`, save data as `.csv` in a dedicated `NN_data/` folder, and add the new script to the menu table in `run.py` so it's reachable.
