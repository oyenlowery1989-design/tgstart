# Messaging Scripts Overview

This folder contains the Ghost Mirror implementations for mirroring, monitoring, and archiving Telegram messages. Launch both via the root `run.py` menu (choices 7 and 8).

## Active Implementations

### `64_claude_edition/` (run.py choice 7)

**Ghost Mirror - Claude Edition (Forensics)**

- **Purpose**: Stealth mirroring with forensics-grade edit/delete tracking.
- **Key Features**:
  - Stealth mode: no read receipts on the source chat.
  - Edits show `FROM: [old]` -> `TO: [new]`.
  - Deletes recover and repost the original message text.
  - Daily logs and a deduplicated user roster.
- **Note**: Has its own nested git repo (`.git`), separate from the parent project.
- **Run**: `python run.py` from inside `6_messaging/64_claude_edition/`.

### `65/` (run.py choice 8)

**Ghost Mirror v4.0**

- **Purpose**: Long-running mirror system with a web dashboard for configuration and monitoring.
- **Key Features**:
  - Granular per-chat toggles (logging, mirroring, edits, deletions, invites).
  - Persistent cache for accurate edit diffs / delete recovery across restarts.
  - SQLite backend (`data/ghost.db`).
  - FastAPI dashboard at `http://127.0.0.1:8000`, HTTP Basic Auth via `DASHBOARD_PASSWORD` (fail-closed if bound to a non-loopback host without one).
- **Run**: needs two processes — `run.py` (bot) and `dashboard.py` (UI). `run.py` choice 8 starts both (bot in background, dashboard in foreground).
- See `65/README.md` for full setup/runbook.

## Archived (superseded)

`_archived/` holds retired implementations kept for reference, not tracked by git and not runnable from the menu:

- `2ghost_mirror_dev_2026-Feb-12_09-40AM/` - dev snapshot, superseded by `64_claude_edition/` and `65/`.
- `63_ghost_mirror_1/` - superseded by `64_claude_edition/`.
