# Architecture

> `dashboard.py` in this directory is retired — its routes were ported into the root
> `dashboard/` app (`dashboard/routes/ghost_mirror.py`, prefixed `/ghost`), which is the
> live web UI. `run.py` here still launches `ghost_runner.py` as a supervised subprocess,
> now invoked by `dashboard/ghost_process.py` instead of standalone.

## Components
- ghost_runner.py: Telegram listener + event processor
- run.py: Auto-restart watchdog for ghost_runner.py, launched by dashboard/ghost_process.py
- data/: Persistent storage (ghost.db, logs)

## Data Flow
Telegram → Event Handler → JSONL Audit → SQLite Index → Dashboard

## Concurrency
- asyncio event loop
- Telethon async handlers
- Background bio worker
- FloodWait protection with backoff
