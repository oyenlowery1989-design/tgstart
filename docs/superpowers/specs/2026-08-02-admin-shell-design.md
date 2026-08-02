# Admin Dashboard Shell — Design

**Goal:** Replace the incrementally-migrated React frontend (2 pages, hand-rolled Tailwind, no router) with the foundation of a full admin dashboard: a shadcn/ui + TypeScript shell with real client-side routing, ready for 8 pages to be built into it one cycle at a time.

## Context

This is the first of 9 planned sub-projects in the "real admin dashboard" rebuild:

1. **Shell** (this spec) — scaffolding, layout, routing, placeholders
2. Sessions — entry point, has the recently-added delete feature
3. Stats — rebuild of the existing working page
4. Bot Reply queue — rebuild of the existing working page
5. Chats
6. Groups
7. Scrape
8. Ghost Mirror
9. Bot Reply setup

Each numbered item after this one gets its own brainstorm → spec → plan → implementation cycle. This spec covers only item 1.

The current `frontend/` (Vite + plain JS + hand-rolled Tailwind, built across two prior migrations for Stats and the Bot Reply queue) is retired by this rebuild — see Architecture.

## Architecture

- Delete the existing `frontend/` directory entirely and re-scaffold via `npx shadcn@latest init` (Vite framework, TypeScript, Tailwind).
- Add `react-router-dom` and shadcn's official dashboard block (sidebar + topbar + breadcrumbs) as the base layout — `npx shadcn@latest add <dashboard-block-name>`, then adapt its nav data to this suite's pages.
- `dashboard/app.py`'s existing serving mechanism is unchanged: `StaticFiles` mounted at `/app/assets` plus a catch-all route returning `index.html` for any other `/app/*` path (built during the Stats migration). React Router owns client-side routing under that catch-all; no backend routing changes needed.
- No new Python dependencies. No new `/api/*` endpoints in this cycle — this is UI scaffolding only.

## Navigation

Sidebar keeps the existing three-group structure (Accounts / Data / Automation) with all 8 destination pages, restyled with shadcn's sidebar components instead of plain Tailwind:

- **Accounts** — Sessions
- **Data** — Chats, Groups, Scrape, Stats
- **Automation** — Ghost Mirror, Bot Reply (queue + setup)

Every page except this shell itself renders a placeholder `Card` ("Not migrated yet") with a button linking out to that page's existing Jinja2 equivalent, until its own build cycle replaces the placeholder with real content.

## Transition regression guard

Today, `dashboard/templates/base.html`'s old navbar sends its Stats and Bot Reply links to `/app/stats` / `/app/reply` whenever `frontend_available` is true, because those two pages currently have working React implementations (built in the two prior migrations, now being retired by this rebuild). Once this shell ships, those routes exist under the new router but only show placeholders until sub-projects 3 and 4 land — sending users from the old navbar into a placeholder would be a real regression for two pages that work today.

Fix, scoped to this cycle: hardcode `base.html`'s Stats and Bot Reply navbar links back to `/stats` and `/reply` (bypassing the `frontend_available` conditional for just those two entries), restoring the conditional once each page's rewrite cycle (sub-projects 3 and 4) ships real content at `/app/stats` / `/app/reply`. The new shell's own sidebar still links every page — including Stats/Bot Reply — to their placeholder-with-fallback-button, consistent with every other not-yet-built page; this guard is specifically about the *old* Jinja2 navbar's already-working links not regressing.

## Out of scope (this cycle)

- Any real page content beyond placeholders — that's sub-projects 2-9.
- Any new backend `/api/*` endpoints beyond what Stats/Bot Reply queue already have.
- Retiring the old Jinja2 pages — they stay reachable and are the fallback target for every placeholder.
- Auth/login UX changes (HTTP Basic stays as-is, unaffected by the frontend rebuild).

## Testing

- `npm run build` (now includes `tsc` type-checking, since the project is TypeScript) — the compile-check equivalent for this stack.
- `python -m py_compile` for any Python touched (expected to be minimal-to-none this cycle, since `dashboard/app.py`'s serving mechanism doesn't change — only `base.html`'s two navbar links).
