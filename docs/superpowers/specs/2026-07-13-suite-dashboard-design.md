# Suite-wide Web Dashboard — Design

Date: 2026-07-13
Status: Approved for planning

## Goal

Replace the terminal `run.py` menu with a single web dashboard covering the entire
pipeline (login, session verify, chat/group listing, scraping, group stats, purge,
participation-finder) plus the existing Ghost Mirror dashboard, as one FastAPI app.

`run.py` is not deleted — it stays as a minimal fallback for pure-terminal use — but
the dashboard becomes the primary, documented way to run the suite.

## Architecture

- New app at repo root: `dashboard/app.py`, `dashboard/templates/`, `dashboard/static/`,
  `dashboard/services/` (one module per capability, holding the extracted async logic).
- Single consolidated venv at repo root. `6_messaging/65/requirements.txt`
  (fastapi, uvicorn, jinja2, aiofiles, loguru) merges into root `requirements.txt`
  alongside telethon/pandas/rich/etc. `6_messaging/65/venv/` is retired once the merge
  is verified working.
- `6_messaging/65/ghost_runner.py` (the Telethon event-listener bot) is **untouched**.
  It keeps running as a supervised subprocess, coordinated via the existing SQLite
  `config_bump` polling. The new dashboard app launches/monitors it the same way
  `run_dashboard_pair()` in today's `run.py` does.
- `6_messaging/65/dashboard.py`'s existing routes (chats, users, events, setup, config
  toggles) are ported into the new root app as a `ghost_mirror` route module — logic
  unchanged, relocated under the shared auth/template setup.
- Each of the other 8 pipeline scripts gets its core logic extracted into an
  importable async function under `dashboard/services/`, called directly by FastAPI
  routes. No more subprocess/Rich-console coupling for these — Rich stays only in
  `run.py`'s legacy path.

## Navigation / routes

| Tab | Routes | Backing script → extracted service |
|---|---|---|
| Sessions | `/sessions`, `/sessions/login` | `1_login.py`, `1_login_by_qr.py`, `2_verify_login_advanced.py` |
| Chats | `/chats` | `30_list_chats.py` |
| Group Users | `/groups/<id>/users` | `31_list_group_users.py` |
| Scraping | `/scrape` | `41_scrape_links_advanced.py` |
| Stats | `/stats` | `50_group_stats.py` |
| Ghost Mirror | `/ghost/*` | ported from `65/dashboard.py` + `ghost_runner.py` subprocess |
| Utilities | `/utilities/participation`, `/utilities/purge` | `71_find_my_participation.py`, `70_purge_my_messages.py` |

### Session model

A global session switcher in the page header sets the "active session" for the whole
UI (server-side state keyed by browser cookie), used by every tab except Ghost Mirror
(which manages its own account via its own `.env`/session file, unchanged). This
mirrors today's `DEFAULT_SESSION` env var behavior but made interactive.

### Login flow (web)

`/sessions/login` is a small stateful multi-step form:

1. Enter phone number.
2. Enter the code Telegram sends.
3. Enter 2FA password, only if the account has one enabled.

The server holds the in-progress `TelegramClient` keyed by a short-lived login-flow ID
(server-side dict, not the browser cookie) between steps, since Telethon's
`send_code_request`/`sign_in` must reuse the same client object across steps.

QR login is a separate mode on the same page: server generates the QR (reusing the
existing `qrcode` logic from `1_login.py`), renders it as an image, and polls
Telethon's `qr.wait()` in a background task. A websocket pushes
`waiting → scanned → done` states to the browser.

### Long-running operations

Scraping, group-user listing, group stats, and purge each: the route starts the
service function as a background task and opens a websocket for that request that
streams progress events (`{current, total, message}`) — the same shape the Rich
progress bars use today, re-emitted as JSON instead of console updates.

### Purge safety

Purge (`/utilities/purge`) requires the shared HTTP Basic auth (see below) **and** a
type-to-confirm step — the user must type the target chat's name before the delete
fires. It is irreversible; the confirm step is in addition to, not instead of, auth.

## Auth

Reuses the existing HTTP Basic gate from `65/dashboard.py` unchanged:
`DASHBOARD_USER`/`DASHBOARD_PASSWORD` env vars, fail-closed to loopback-only binding
if no password is set. Extended to cover every route in the new app, not just Ghost
Mirror's.

## Error handling

Service functions raise normal exceptions. Routes catch them and turn them into an
error banner / websocket `{"error": "..."}` event, mirroring today's
`ui_utils.print_error`. Telethon-specific errors (session revoked, flood wait) get
specific user-facing messages instead of a raw traceback.

## Testing / verification

No test framework exists in this repo (per `CLAUDE.md`) and this project does not
introduce one. Verification is:

- `python -m py_compile` on every new/changed file.
- A manual pass per feature before considering it done: start the dashboard, drive
  login (phone+code and QR), drive one scrape, drive one purge against a disposable
  test chat, confirm the Ghost Mirror tab still works end-to-end.

## Out of scope

- No new JS framework — server-rendered Jinja2 + minimal JS for websockets, matching
  the existing Ghost Mirror dashboard's style.
- No refactor of `ghost_runner.py`'s internals or its SQLite coordination model.
- No removal of `run.py`; it remains a minimal fallback.
- No auth model beyond HTTP Basic (no per-user accounts, no RBAC) — this is a
  solo-operator tool, not multi-tenant.
