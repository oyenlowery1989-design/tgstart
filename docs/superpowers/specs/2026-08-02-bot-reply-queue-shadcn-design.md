# Bot Reply Queue React (shadcn) Frontend — Design

**Goal:** Build the Bot Reply queue page (sub-project 4 of 9) as a real React page inside the shell, replacing its "Not migrated yet" placeholder — pure frontend, no backend changes.

## Context

An earlier, now-superseded migration (before the shell rebuild) already built `dashboard/routes/bot_reply.py`'s JSON API: `GET /reply/api/queue` (returns `{configured, pending, approved, recent}`, each a list of reply rows) and `POST /reply/api/pending/{id}/approve|reject|retry`. The shell rebuild deleted the old plain-JS frontend that consumed these, but never touched the backend — all four endpoints are live and unchanged today.

Checked the old page's git history per the process note from sub-project 3's final review: one real fix was applied to it before deletion (`fdfe600` — guard `fetchQueue` against non-OK responses, clear stale error on success). That pattern is already the established convention in this rebuild (used in Sessions' and Stats' API modules) — no gap to carry forward here.

## Architecture

- No backend changes. Reuse `GET /reply/api/queue` and the three `POST /reply/api/pending/{id}/*` endpoints exactly as-is.
- One new frontend route: `/app/reply` (already exists as a nav item — "Bot Reply", Automation group — filtered out of the generic placeholder mapping like Sessions/Stats).
- Single page, no sub-routes. "Bot Reply Setup" (`/reply/setup`) stays its own future sub-project (9 of 9), untouched here.
- UI: shadcn `Table` split into three sections — Pending (Approve/Reject buttons), Approved (read-only), Recent (status `Badge`, Retry button on `failed` rows, error text shown for failures).
- Polling: `setInterval` every 10s (matches the old page's behavior), plus an immediate refetch after any action — same pattern as the old page, applying the `resp.ok`-check + error-clearing convention from the start.
- New dependency: none — `Table`, `Badge`, `Button`, `Alert` are all already installed from sub-project 2.

## Out of scope

- Any other page's migration, including Bot Reply Setup (`/reply/setup`).
- Any change to `bot_reply.py`'s route logic or the runner (`6_messaging/bot_reply/`).
- Retiring the old Jinja2 `/reply` page — stays reachable as fallback until this ships, and after.

## Testing

- `npm run build` (`tsc -b` type-check).
- Manual smoke test: curl `/app/reply` for 200, then a live browser check (same reduced-scope fallback as prior sub-projects if no live pending drafts exist in the environment).
