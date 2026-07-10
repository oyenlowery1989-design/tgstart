# Architecture

## Components
- ghost_runner.py: Telegram listener + event processor
- dashboard.py: FastAPI web UI
- run.py: Auto-restart watchdog
- data/: Persistent storage

## Data Flow
Telegram → Event Handler → JSONL Audit → SQLite Index → Dashboard

## Concurrency
- asyncio event loop
- Telethon async handlers
- Background bio worker
- FloodWait protection with backoff
