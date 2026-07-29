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

- **`dashboard/`** (run via `run.py` choice 8, or `python dashboard/app.py` directly):
  - **Action:** Full-suite web dashboard — login, sessions, chats, group users, scraping,
    stats, Ghost Mirror, and utilities (participation/purge), all behind one HTTP Basic
    auth gate.
  - Manages `6_messaging/65/ghost_runner.py` (Ghost Mirror bot) as a supervised subprocess
    internally; its routes read the same `6_messaging/65/data/ghost.db` SQLite backend.
  - **Config:** dashboard gated by `DASHBOARD_PASSWORD` (HTTP Basic Auth, fail-closed on
    non-loopback host).
  - The older `6_messaging/64_claude_edition/` (CLI-only forensics edition) and
    `6_messaging/65/dashboard.py` (its standalone dashboard pair) have both been retired;
    see git history, not this file, for their design.

### Bot Reply (`6_messaging/bot_reply/`)

AI-drafted, human-approved auto-replies, configured via the dashboard's Bot Reply tab
(`/reply`, `/reply/setup`) rather than `.env` — the only required `.env` keys are
credentials, which must never be committed:

- `BOT_REPLY_APPROVAL_BOT_TOKEN` — the approval bot's token (from @BotFather)
- `BOT_REPLY_OPERATOR_USER_ID` — your own Telegram user id, so the approval bot knows who to DM
- `GOOGLE_APPLICATION_CREDENTIALS`, `GCP_PROJECT_ID`, `GCP_LOCATION` — required if using the `vertex` provider
- `ANTHROPIC_API_KEY` — required if using the `anthropic` provider

Everything else (which chats reply, trigger mode, provider/model choice, persona
overrides) is configured live from `/reply/setup` and hot-reloads within ~2s via the
same `config_bump` polling pattern Ghost Mirror uses — no restart needed.

### 5. Utilities (`7_utilities/`)

- **`70_purge_my_messages.py`**:
  - **Action:** Deletes your own message history from a group.

- **`71_find_my_participation.py`**:
  - **Action:** Finds all groups where you have sent messages.

### Data Directories

- `sessions/`: Stores your login session files. **Keep private.**
- `*_data/`: Subdirectories for script outputs (e.g. `30_data`, `41_data`).
- `99_data/`: General data storage.
