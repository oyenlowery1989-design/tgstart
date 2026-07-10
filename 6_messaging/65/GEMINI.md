# GhostMirror Project Context

## Overview

GhostMirror is a sophisticated Telegram mirroring and auditing system. It uses a `telethon` based runner (`ghost_runner.py`) to listen for events and a `fastapi` dashboard (`dashboard.py`) for configuration and monitoring.

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
- `dashboard.py`: Web UI and API.
- `templates/`: Jinja2 templates (`index.html`, `chats.html`, `setup.html`).
- `data/`: Stores database and logs.

## Next Steps: Phase 6 (Robustness)

1. **FloodWait Handling**: Implement exponential backoff for rate limits.
2. **Graceful Shutdown**: Handle SIGTERM signals cleanly.
3. **Error Logging**: JSONL error logs viewer in dashboard.
4. **Auto-Restart**: Wrap message loop in broad try/except.
5. **Database Pruning**: UI task to clean old events.

## Recent Critical Fixes (Phase 5.2 Patch)

- **Monitored Enforcement**: Runner now strictly filters `monitored` chats in config cache.
- **Event Ordering**: Polling API changed to ASC for reliable tailing.
- **Fallback Logic**: Improved copy fallback to handle media correctly.
