# Sessions React Frontend — Design

**Goal:** Build the Sessions page (sub-project 2 of 9 in the admin dashboard rebuild) as a real React page inside the shell built in sub-project 1, replacing its "Not migrated yet" placeholder — full feature parity: session list/status/switch/delete, phone login, and QR login.

## Context

The shell (sub-project 1, merged) established: TypeScript + shadcn/ui (base-ui variant — `render={<Element/>}`, not `asChild`), react-router-dom (`basename: "/app"`), a shared `NotMigratedPage` placeholder, and a nav data file (`frontend/src/lib/nav.ts`) as the single source of truth for the sidebar. This is the first sub-project to build a real page.

The existing Sessions backend (`dashboard/routes/sessions.py`, `dashboard/services/sessions_service.py`) already covers: session listing with live status checks, an active-session cookie switcher, delete (added this session, path-traversal-safe), phone login (phone → code → optional 2FA, all three steps already return JSON), and QR login (websocket-driven: QR image → waiting → optional 2FA → done/error).

## Architecture

- One new backend endpoint: `GET /sessions/api/list`, returning `{results, active_session, all_sessions}` — the exact data `sessions_page` already assembles for its Jinja2 template, refactored into a shared helper both routes call (same pattern as the Bot Reply queue's `_queue_data()`).
- No other backend changes. `POST /active`, `POST /{name}/delete`, `POST /login/phone`, `POST /login/code`, `POST /login/2fa`, and `WS /login/qr/ws` are all called directly from React unchanged — the first two already work fine via `fetch` (redirects resolve transparently, body isn't needed), the rest already return/exchange JSON.
- Three new frontend routes, added directly to the router in `main.tsx` (not derived from `nav.ts`, since these are sub-pages reached via in-page navigation, not sidebar entries):
  - `/app/sessions` — table + switcher + delete + links to both login flows
  - `/app/sessions/login` — phone login wizard
  - `/app/sessions/login/qr` — QR login (reuses the existing WS message shape)
- `frontend/src/components/layout.tsx`'s breadcrumb/active-nav logic switches from exact `pathname === item.url` to a `startsWith` match, so both login sub-routes still correctly highlight "Sessions" in the sidebar — this is the first page with sub-routes, and the shell's final review flagged this exact gap as something to fix "when sub-project 2 adds one."
- Error handling in every new `fetch` call follows the corrected pattern from the Bot Reply queue's final-review fix (check `r.ok` before parsing JSON, clear stale error state on a successful refetch) — applied from the start this time, not discovered as a fix-round finding.

## Out of scope

- Any change to `sessions_service.py`'s actual login/check/delete logic — reused as-is.
- Any other page's migration (Stats, Bot Reply queue, Chats, Groups, Scrape, Ghost Mirror, Bot Reply setup) — separate sub-projects.
- Retiring the old Jinja2 `/sessions`, `/sessions/login`, `/sessions/login/qr` pages — they stay reachable (the shell's `NotMigratedPage` pattern elsewhere still needs them as fallbacks until every page is migrated).

## Testing

- `npm run build` (`tsc -b` type-check included), `python -m py_compile` for the new backend endpoint.
- Manual smoke test: curl checks for all 3 new routes returning the SPA shell, PLUS a live browser render check (per the shell's final review — curl alone can't prove React actually mounted and the QR/phone flows work).
