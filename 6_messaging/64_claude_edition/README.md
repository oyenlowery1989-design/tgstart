# 👻 Ghost Mirror v4 - Claude Edition

Enhanced production-ready Telegram message mirroring system with forensics, user tracking, and monitoring. This version is a fully refactored, modular, and self-contained edition designed for 24/7 reliability.

## 🚀 Deployment (Server/VPS)

This folder contains everything needed to run the bot. Follow these steps to deploy on a new server:

### 1. Installation

Run the automatic setup script. This will install dependencies, create folders, and prepare your `.env`.

- **Windows**: `python scripts/setup.py`
- **Linux/Mac**: `python3 scripts/setup.py`

> **Linux Tip**: It's highly recommended to use a virtual environment:
> `python3 -m venv venv && source venv/bin/activate && python3 scripts/setup.py`

### 2. Configuration

Edit the `.env` file and add your Telegram API credentials (get them from [my.telegram.org](https://my.telegram.org)):

```env
MAIN_API_ID=123456
MAIN_API_HASH=abcdef123456...
```

### 3. Start Mirroring

Run the auto-restart wrapper to ensure 24/7 operation:

- **Windows**: `python run.py`
- **Linux/Mac**: `./start.sh` (or `python3 run.py`)

> **Server Tip (24/7)**: On Linux servers, use `screen` or `tmux` to keep the bot running after you disconnect:
> `screen -S ghost python3 run.py`

---

## ☁️ Render Deployment (Free Tier)

Since Render's free tier is transient (files are deleted) and it sleeps after 15 minutes, use this special workflow:

### 1. Generate Cloud Strings

On your PC, run the generator script:

```bash
python scripts/get_cloud_string.py
```

This will print two long strings: **SESSION_BASE64** and **MIRRORS_BASE64**.

### 2. Configure Render

Create a **Web Service** on Render and add these **Environment Variables**:

- `SESSION_BASE64`: (Paste your session string)
- `MIRRORS_BASE64`: (Paste your mirrors string)
- `MAIN_API_ID`: (Your Telegram API ID)
- `MAIN_API_HASH`: (Your Telegram API Hash)
- `PORT`: `8080` (Render's default)

**Settings:**

- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python scripts/render_wrapper.py`

### 3. Keep-Alive

Because the free tier sleeps, use a free service like [Cron-job.org](https://cron-job.org/) to ping your Render URL (e.g., `https://your-app.onrender.com`) every 10 minutes. This will keep the bot awake and mirroring 24/7.

---

## 📁 Project Structure

- **`run.py`** - Auto-restart wrapper (Recommended entry point).
- **`ghost_runner.py`** - The main bot engine.
- **`scripts/setup.py`** - One-click setup script.
- **`src/`** - Core logic, handlers, and internal utilities.
- **`data/`** - Persistent data (configs, logs, users).
- **`sessions/`** - Telegram session files.

---

## 🆕 Key Features

### 1. **24/7 Reliability** ✅

- **Auto-Restart**: `run.py` monitors the bot and restarts it instantly if it crashes.
- **Exponential Backoff**: If a persistent error occurs (like no internet), the bot waits longer between restarts to avoid spamming.
- **Graceful Shutdown**: Pressing `Ctrl+C` will disconnect cleanly and save all state.

### 2. **Modular Architecture** ✅

- **Isolated Handlers**: Separate logic for messages, deletions, admin actions, and member changes.
- **Self-Contained**: No external dependencies or parent folder requirements.
- **Internal Utilities**: Custom UI and Telegram helpers included in `src/utils/`.

### 3. **Forensics & Intelligence** ✅

- **Edit Tracking**: Generates text diffs (WAS vs NOW) for edited messages.
- **Deletion Recovery**: Detects deleted messages and logs their content.
- **User Index**: Builds a searchable database of every user "seen" in your chats.
- **Bio Fetcher**: Runs in the background to slowly fetch full user profiles without hitting API limits.

### 4. **Smart Configuration** ✅

- **Migration Detection**: If a group ID changes (e.g. Group -> Supergroup), the bot detects it and updates `mirrors.json` automatically.
- **Metadata UI**: The management menu shows group types (CHANNEL/GROUP) and live member counts.
- **Deduplication**: Prevents duplicate mirror pairs from being saved.

---

## 📊 Monitoring & Logs

- **Message Logs**: `data/logs/*.jsonl`
- **Error Logs**: `data/logs/errors.jsonl`
- **Crash Logs**: `data/crash_log.jsonl`
- **User Database**: `data/users_index.json`

---

## 🔒 Security & Performance

- **Stealth**: Does not send read receipts or "typing" indicators.
- **Optimized**: uses `asyncio` for high performance with minimal memory footprint.
- **Safe**: All sensitive data is stored locally in `.env` and `.session` files.

---

## 💾 Maintenance & Backups

To protect your configuration, sessions, and logs, it's essential to perform regular backups.

### 🏠 Local Backup

We've included a dedicated backup script that creates a timestamped ZIP of your entire project, including `.env`, `sessions/`, and `data/`.

```bash
python scripts/backup.py
```

- **Location**: Backups are saved in `data/backups/`.
- **Exclusions**: It automatically skips large internal files like `.git`, `__pycache__`, and previous backups to keep the file size small.

### ☁️ Recommended Strategy

1. **Regularly run `python scripts/backup.py`** (especially before making major changes).
2. **Copy the ZIP files** to an external drive or cloud storage (Google Drive, Dropbox, etc.).
3. **Git**: Use `git` for code changes, but remember that `.env` and `sessions/` are ignored by Git for security.

---

**Made with ❤️ by Claude & Antigravity**
