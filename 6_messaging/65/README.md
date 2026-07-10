# GhostMirror (v4.0)

GhostMirror is a Telegram mirroring bot system designed for robust, long-running message duplication across chats and channels.

## Features

- **Granular Toggles**: Control logging, mirroring, edits, deletions, and invites per chat.
- **Persistent Cache**: Recovers message history after restarts for accurate edit diffs and delete recovery.
- **Dashboard**: Real-time web UI for configuration and monitoring.
- **Setup Flow**: Guided interface to map source chats to backup destinations.
- **SQLite Backend**: Single file database for easy portability.

## Installation

1. Create a virtual environment:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate # Linux/Mac
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Configure Environment:
   - Create `.env.local` based on `.env.example`.
   - Add your `API_ID` and `API_HASH`.
   - Optional: set `DASHBOARD_PASSWORD` (and `DASHBOARD_USER`, default `admin`) to require
     HTTP Basic auth on the dashboard. Required if `DASHBOARD_HOST` is ever set to anything
     other than `127.0.0.1`/`localhost` — the dashboard refuses to start otherwise.

## Runbook

### 1. Starting the System

You need to run two processes (in separate terminals):

**Terminal 1: Ghost Runner** (The Bot)

```bash
python ghost_runner.py
```

_This process connects to Telegram, syncs your dialogs, and mirrors messages._

**Terminal 2: Dashboard** (The UI)

```bash
python dashboard.py
```

_Access at: http://127.0.0.1:8000_

### 2. Configuration & Setup

1. Open the Dashboard.
2. Go to the **Setup** tab.
3. You will see a list of all chats your account is a member of.
4. Toggle "Monitor" for the chats you want to mirror.
5. Select a "Backup Destination" (Channel/Group) for each monitored chat.
6. Click **Save**. The Runner will pick up changes within 2 seconds.

### 3. Common Issues

- **FloodWaitError**: If you see this in logs, stop the runner and wait the specified seconds. Mirroring too fast triggers Telegram limits.
- **Database Locked**: Ensure both scripts are running from the same directory. Restart both if stuck.
- **Permission Denied**: Check file permissions on `data/ghost.db`.

## License

MIT
