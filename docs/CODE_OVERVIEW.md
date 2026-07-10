# Telegram Tools - Workflow

A comprehensive set of tools to manage your Telegram automation. Each step builds on the previous one.

### 1. Authentication (`1_login/`)

- **`1_login.py`**:
  - **Action:** Interactive login (Phone or QR).
  - **Output:** Saves session to `sessions/<username>.session`.
  - **Usage:** Run this **once** to create a new session.

- **`2_verify_login.py`**:
  - **Action:** Checks if your default session is active.
  - **Usage:** Quick check for connectivity.

- **`2_verify_login_advanced.py`**:
  - **Action:** Scans all sessions in `sessions/` and verifies them.
  - **Usage:** Managing multiple accounts.

### 2. Discovery (`3_chat_management/`)

- **`30_list_chats.py`**:
  - **Action:** Lists all your groups, channels, and DMs.
  - **Output:** `30_data/30_dialogs.csv`
  - **Usage:** Run this to find the **ID** of a group you want to target.

- **`31_list_group_users.py`**:
  - **Action:** Scrapes member list from a specific group.
  - **Output:** `31_data/31_users_<name>_<id>.csv`
  - **Usage:** Edit the script to set `TARGET_GROUP` ID.

### 3. Scraping (`4_scraping/`)

- **`40_scrape_links.py`**:
  - **Action:** Basic link extractor.
  - **Output:** `30_links.csv`

- **`41_scrape_links_advanced.py`**:
  - **Action:** Advanced tool to extract/filter links from chat history.
  - **Features:** Resumable (checkpoints), filters (regex/keywords), deduplication.
  - **Output:** `41_data/41_links_<name>.csv`

### 4. Monitoring & Messaging (`5_monitoring/`, `6_messaging/`)

- **`50_group_stats.py`**:
  - **Action:** Analyzes activity to find top influencers and peak hours.
  - **Output:** `50_data/stats_<name>.csv`

- **`64_claude_edition/`** (run via `run.py` choice 7):
  - **Action:** Ghost Mirror, forensics edition. Stealth read, edit/delete tracking, logs.
  - Has its own nested git repo — not tracked by the parent project's `.gitignore` rules.

- **`65/`** (run via `run.py` choice 8):
  - **Action:** Ghost Mirror v4.0. Runs bot (`run.py`) + FastAPI dashboard (`dashboard.py`) as a pair.
  - **Config:** SQLite (`data/ghost.db`), dashboard gated by `DASHBOARD_PASSWORD` (HTTP Basic Auth, fail-closed on non-loopback host).

### 5. Utilities (`7_utilities/`)

- **`70_purge_my_messages.py`**:
  - **Action:** Deletes your own message history from a group.

- **`71_find_my_participation.py`**:
  - **Action:** Finds all groups where you have sent messages.

### Data Directories

- `sessions/`: Stores your login session files. **Keep private.**
- `*_data/`: Subdirectories for script outputs (e.g. `30_data`, `41_data`).
- `99_data/`: General data storage.
