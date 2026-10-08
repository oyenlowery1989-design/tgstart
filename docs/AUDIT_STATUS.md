# Audit Status

Updated 2026-08-28 after a read-only review and focused remediation pass.

## Scope

The project is a local-first Telethon suite for account/session management, chat and
member discovery, link scraping, group analytics, message participation/purge utilities,
Ghost Mirror archival/audit, and human-approved AI reply drafting.

## Completed in this pass

- Bot Reply approval callbacks are operator-only.
- Dashboard WebSockets reject foreign or missing origins before `accept()`.
- Ghost Mirror config no longer overwrites dashboard changes on restart.
- Dashboard-managed workers use a stale-safe atomic PID lease.
- Non-loopback access requires an HTTPS public origin; remote HTTP is rejected.
- Bot Reply settings are validated before persistence.
- Session verification is serialized with other session users.
- Abandoned phone/QR login flows expire and clean up after 10 minutes.
- Focused regression tests cover these invariants.

## Verification

The current focused suite passes (16 tests across the dashboard, Bot Reply, and Ghost
Mirror checks). Changed Python files compile, `pip check` passes, frontend lint/build pass,
and `git diff --check` passes. The frontend lint output contains only three existing
Fast Refresh warnings in generated UI primitives.

## Remaining priority order

1. Eliminate cross-process Telethon session contention in Bot Reply setup by using a
   runner-owned dialog cache/API.
2. Bound scrape/stats WebSocket inputs and Ghost audit queue growth; expose worker health.
3. Make link-export checkpoints configuration-aware and preserve prior results on resume.
4. Escape formula-like CSV cells and normalize CLI output paths.
5. Add Python constraints/lock data and CI; remove or update the vulnerable, unused
   frontend `shadcn` production dependency (`nanoid`/`hono` advisories).

Account syncing and AI-based filtering remain intentionally deferred until these
reliability and data-safety foundations are complete.
