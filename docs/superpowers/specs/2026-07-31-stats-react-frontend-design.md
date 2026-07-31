# Stats React Frontend — Design

**Goal:** Replace the terminal-only mental model of "working with this project" by giving
the dashboard a modern, non-server-rendered frontend, starting with a single page (Stats)
as a validated MVP slice before porting the rest.

## Context

`dashboard/app.py` already serves a full web UI (FastAPI + Jinja2 + vanilla JS) covering
Sessions, Chats, Groups, Scrape, Stats, Ghost Mirror, and Bot Reply — so "not in terminal"
is already true today. This project is specifically about upgrading that UI's look and
interaction model to a modern SPA stack (React + Vite + Tailwind), not building a UI where
none existed.

## Architecture

- New `frontend/` directory: a Vite + React + Tailwind SPA.
- `npm run build` in `frontend/` outputs static files (`frontend/dist/`).
- `dashboard/app.py` serves those static files at `/` and mounts a new `/api/*` router
  namespace for JSON endpoints, alongside the existing Jinja2 HTML routes (which keep
  serving unmigrated pages during the transition).
- One process, one port — `python dashboard/app.py` continues to be the single command
  that runs everything. No separate frontend dev server process required to use the app
  (Vite's dev server remains available for `frontend/`-only development, but is not part
  of the running-the-app contract).
- All existing Telethon/session/service logic (`dashboard/services/*.py`,
  `dashboard/state.py`, `dashboard/tg_client.py`) is reused unchanged. New `/api/*` routes
  are thin wrappers that call the same service functions the Jinja2 routes call today.

## Rollout scope (this spec)

MVP slice: **Stats page only**, rebuilt in the new stack. All other pages
(Sessions, Chats, Groups, Scrape, Ghost Mirror, Bot Reply) stay on the existing Jinja2
templates, reachable exactly as they are today, until a later slice ports each one.

## Navigation (applies once more pages migrate)

Left sidebar, grouped by purpose, dark/dense theme:

- **Accounts** — Sessions
- **Data** — Chats, Groups, Scrape, Stats
- **Automation** — Ghost Mirror, Bot Reply

For this slice, the sidebar renders all seven entries; entries not yet migrated to
`frontend/` link out to their existing Jinja2 page (full page navigation, not a SPA route)
so the whole app stays reachable throughout the migration.

## Stats page (this slice)

Layout: form (group picker + scan-limit input + Scan button) at top, three summary tiles
below it (total scanned / unique senders / most-active hour), then Top Users and Peak
Hours charts side-by-side beneath the tiles.

- Charts: [Recharts](https://recharts.org/).
- Scan progress: ported from the existing `dashboard/routes/stats.py` `/stats/ws`
  WebSocket handler to `/api/stats/ws`, same message shape
  (`{"current", "total", "message"}`, then a final `{"done": true, "top_users",
  "peak_hours", ...}`). This is a one-shot progress mechanism for a single scan
  operation — distinct from the config-hot-reload polling pattern used by Ghost Mirror /
  Bot Reply, and is not being changed to polling.
- Backend: new `dashboard/routes/api/stats.py` (or an `/api` prefix added to the existing
  `dashboard/routes/stats.py` router) calls `dashboard.services.stats_service.group_stats`
  exactly as today's handler does.

## Auth

`/api/*` routes sit behind the same HTTP Basic gate as the rest of the dashboard
(`DASHBOARD_USER`/`DASHBOARD_PASSWORD`). No new auth code, no session cookies, no change
to the fail-closed loopback-only behavior when the password is unset.

## Error handling

`/api/*` routes return FastAPI's default `HTTPException` JSON shape
(`{"detail": "..."}`). The frontend renders that string on failure (e.g. scan target not
found, session not connected) — no new error-response format introduced.

## Testing

Matches the repo's existing no-test-framework convention:

- New Python route code: `python -m py_compile` (as documented in the root `CLAUDE.md`).
- New frontend code: `npm run build` must succeed with no errors — the equivalent of a
  compile check for a stack with no test runner configured.

## Out of scope (future slices)

- Porting Sessions, Chats, Groups, Scrape, Ghost Mirror, Bot Reply to `frontend/`.
- Any change to the config-hot-reload polling pattern used elsewhere in the dashboard.
- Login/session UX changes (HTTP Basic stays as-is).
