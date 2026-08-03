# Ghost Mirror React (shadcn) Frontend — Design

**Goal:** Build the Ghost Mirror section (sub-project 8 of 9) as real React pages inside the shell, replacing its "Not migrated yet" placeholder. One nav item (`/ghost`), five internal sub-routes navigated via an in-page tab strip — largest remaining sub-project.

## Context

`dashboard/routes/ghost_mirror.py` (ported unchanged from `6_messaging/65/dashboard.py`) currently serves five classic Jinja2 pages, all reading/writing the same SQLite `ghost.db` via a shared `execute_query()` helper:

- `GET /ghost` (home) — 3 stat tiles, critical-failures table, a 10-row recent-events table that polls `GET /ghost/api/recent_events_v2?after_ts=...` every 3s to prepend new rows live
- `GET /ghost/chats?page=N` — paginated (20/page) table: Monitor toggle, 5 core toggles (Log New/Mirror New/Edits/Deletes/Joins), an expandable "Advanced" row with 6 more toggles (Admin/Restrict/Invites/Bots/Bio/Reactions); toggles hit `POST /ghost/api/toggle/{chat_id}/{key}?value=0|1` and `POST /ghost/api/chats/{chat_id}/monitor?value=0|1`
- `GET /ghost/setup?q=...` — chat→backup-destination mapping table (monitor checkbox + backup `<select>` + per-row Save button), hits `POST /ghost/api/chat_mapping` with `{chat_id, monitored, backup_chat_id}`
- `GET /ghost/events?page=N&type=...` — paginated (50/page) event log with a type filter
- `GET /ghost/users?page=N&q=...` — paginated (50/page) user directory with a search box

All three POST endpoints already require `Depends(require_csrf_header)` (added in the CSRF-protection work just prior to this sub-project) — no auth changes needed here.

None of these five pages have a JSON API today (unlike Stats/Bot-Reply-queue, which had orphaned JSON endpoints from an earlier migration attempt) — `home`/`chats_list`/`setup_page`/`events_list`/`users_list` all return `HTMLResponse` built from `execute_query()` dicts. New `GET /ghost/api/...` endpoints are needed for all five.

## Architecture

### Backend (new, additive only — no changes to existing routes/logic)

Add to `dashboard/routes/ghost_mirror.py`:
- `GET /ghost/api/home` → `{monitored_count, message_count, event_count, failures, recent_events, config_bump, schema_version}` (same shape `home()` already builds for the template)
- `GET /ghost/api/chats?page=N` → `{chats, page, total_pages, total_chats}` (same query as `chats_list()`)
- `GET /ghost/api/setup?q=...` → `{chats, destinations, query}` (same query as `setup_page()`)
- `GET /ghost/api/events?page=N&type=...` → `{events, page, total_pages, total_events, type_filter}` (same query as `events_list()`)
- `GET /ghost/api/users?page=N&q=...` → `{users, page, total_pages, total_users, query}` (same query as `users_list()`)

`GET /ghost/api/recent_events_v2` and the three POST endpoints are reused exactly as-is.

### Frontend

- Five new routes under `/app/ghost`: `/ghost`, `/ghost/chats`, `/ghost/setup`, `/ghost/events`, `/ghost/users`. `nav.ts`'s existing "Ghost Mirror" item (`/ghost`, Automation group) is added to `MIGRATED_URLS`.
- Shared `<GhostTabs active="..." />` component: a small tab strip (Home/Chats/Setup/Events/Users, `Link` to each sub-route) rendered at the top of all five pages — mirrors the classic `ghost/base.html` secondary navbar and the Sessions sub-route precedent.
- `lib/ghost-api.ts`: one page-scoped module per house convention, typed responses for all 5 GET endpoints plus the 3 POST actions (toggle config, toggle monitor, save chat mapping), each POST helper attaching `X-CSRF-Token` via the shared `lib/csrf.ts`.
- Pagination: page-number based, matching the backend exactly — `Prev`/`Next` buttons, page (and filter/search/type) state read from and written to the URL via `useSearchParams`, so back/forward and shareable links work like the classic pages' `?page=N` links did.
- Home page keeps the 3s live-polling event feed (`setInterval`, prepend new rows, same as classic) — this is the one page in the rebuild with a "live updates without user action" requirement, matching its use as an always-open ops view.
- Toggle switches: new shadcn `Switch` component (first use in this rebuild — `checkbox`/`label` were added in Scrape, sub-project 7; `Switch` better matches the classic UI's `toggle-switch` CSS class visually and semantically for a live on/off action vs. a form checkbox).
- Chats page's "Advanced" 6-toggle row: a collapsible row (local `useState<Set<chatId>>` of expanded rows), not a separate page/dialog — matches classic behavior (click gear icon to expand/collapse in place).
- Setup page's backup-destination picker: shadcn `Select` (already installed from Sessions/Stats sub-projects).

## Out of scope

- Any change to the three existing POST endpoints' logic, or to `execute_query`/`get_db_connection`.
- Bot Reply Setup (`/reply/setup`) — stays sub-project 9.
- Retiring the classic Jinja2 `/ghost/*` pages — stay reachable as fallback after this ships.
- WebSocket-based live updates for Chats/Events/Users (only Home polls; the others are static per-page-load like their classic counterparts).

## Testing

- `npm run build` (`tsc -b` type-check) and `npm run lint`.
- `python -m py_compile` on the touched route file.
- Live browser verification via Playwright MCP against a running `dashboard/app.py` for all 5 pages: toggle a chat config value and confirm it persists, save a chat mapping, paginate/filter events and users, confirm Home's live feed picks up a new event.
