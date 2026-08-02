# Stats React (shadcn) Frontend — Design

**Goal:** Build the Stats page (sub-project 3 of 9 in the admin dashboard rebuild) as a real React page inside the shell, replacing its "Not migrated yet" placeholder — pure frontend work, no backend changes.

## Context

An earlier, now-superseded migration (before the shell rebuild) already built `dashboard/routes/stats.py`'s JSON API: `GET /api/stats/session` (returns `{active_session, all_sessions}`) and `WS /api/stats/ws` (accepts `{group_id, limit}`, streams `{current, total, message}` progress, finishes with `{done: true, top_users, peak_hours, total_scanned, unique_senders, busiest_hour}`). The shell rebuild (sub-project 1) deleted the old plain-JS frontend that consumed these endpoints, but never touched the backend — both endpoints are live and unchanged today, just currently unused.

## Architecture

- No backend changes. Reuse `GET /api/stats/session` and `WS /api/stats/ws` exactly as-is.
- One new frontend route: `/app/stats` (already exists as a nav item in `nav.ts` — same pattern as Sessions, filtered out of the generic `NotMigratedPage` mapping and given an explicit route).
- Single page, no sub-routes (unlike Sessions) — no `findActiveNavItem` changes needed beyond what Sessions already added.
- UI: form (group ID + limit inputs, Scan button) → WS-driven progress bar → on completion, 3 shadcn `Card` tiles (Total scanned / Unique senders / Busiest hour) + 2 Recharts bar charts (Top Users, Peak Hours) side by side.
- New dependency: `recharts` (not currently installed in the TS scaffold — was present in the old JS frontend, needs re-adding).
- Error handling: the established `resp.ok`-check pattern for the session-info fetch; WS errors surface inline, same as Sessions' QR page pattern (state machine, error Alert, no crash).

## Out of scope

- Any other page's migration.
- Any change to `stats_service.py`'s scan logic, `group_stats()`, or the WS message shapes.
- Retiring the old Jinja2 `/stats` page — stays reachable as the placeholder fallback until this ships, and after.

## Testing

- `npm run build` (`tsc -b` type-check).
- Manual smoke test: curl `/app/stats` for 200, then a live browser check (real WS scan against a real group + session if available in the environment, same reduced-scope fallback as prior sub-projects if not).
