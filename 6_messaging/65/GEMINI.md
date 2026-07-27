# GhostMirror Project Context

## Overview

GhostMirror is a sophisticated Telegram mirroring and auditing system. It uses a `telethon` based runner (`ghost_runner.py`) to listen for events. Its standalone `dashboard.py` has been retired — configuration and monitoring now happen through the root `dashboard/` app's `/ghost/*` routes (`dashboard/routes/ghost_mirror.py`), which reads the same `ghost.db` unchanged.

## Current State: Phase 5.2 (Completed)

- **Core Engine**: Fully functional with `ConfigManager` for hot-reloads and `AuditLogger` for reliable logging.
- **Database**: SQLite (`ghost.db`) with `WAL` mode and parameterized queries.
- **Setup Flow**:
  - `/setup` page for mapping source chats to backup destinations.
  - Interactive session selection on startup (`select_session`).
- **Dashboard**:
  - Real-time event feed via `/api/recent_events_v2` (ASC polling).
  - Granular toggles per chat.
  - User search index.
- **Resilience**:
  - `mirror_message` has fallback logic (Forward -> Retry -> Copy).
  - `refresh_config_cache` enforces `monitored=1` filtering.

## Key Files

- `ghost_runner.py`: Main bot logic.
- `run.py`: Watchdog that supervises `ghost_runner.py`, launched by `dashboard/ghost_process.py`.
- `data/`: Stores database and logs.
- `../../dashboard/routes/ghost_mirror.py` + `../../dashboard/templates/ghost/`: the live web UI (moved out of this directory).

## Next Steps: Phase 6 (Robustness)

1. **FloodWait Handling**: Implement exponential backoff for rate limits.
2. ~~**Graceful Shutdown**: Handle SIGTERM signals cleanly.~~ Done — `run.py`'s watchdog now forwards SIGTERM to `ghost_runner.py` instead of orphaning it.
3. **Error Logging**: JSONL error logs viewer in dashboard.
4. **Auto-Restart**: Wrap message loop in broad try/except.
5. **Database Pruning**: UI task to clean old events.

## Recent Critical Fixes (Phase 5.2 Patch)

- **Monitored Enforcement**: Runner now strictly filters `monitored` chats in config cache.
- **Event Ordering**: Polling API changed to ASC for reliable tailing.
- **Fallback Logic**: Improved copy fallback to handle media correctly.
