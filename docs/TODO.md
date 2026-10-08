# 📝 Telegram Tools TODO List

## Planned Features

- [ ] **Account Syncing**: Sync settings and configurations across different Telegram sessions.
- [ ] **Advanced Filtering**: Add complex regex and AI-based filtering to the mirror scripts.
- [ ] **Reliable resumable exports**: Persist scan configuration and prior results so resumed link exports cannot silently omit data.
- [ ] **Safe exports**: Escape formula-like CSV cells and move all CLI output paths under the repository root.
- [ ] **Worker-owned session access**: Replace dashboard Bot Reply setup's direct Telethon session access with a runner-owned dialog cache/API.
- [ ] **Bounded jobs and queues**: Cap scrape/stats WebSocket jobs and Ghost audit queues; expose worker health and backlog.
- [ ] **Reproducible releases**: Add Python constraints and CI for `pip check`, compilation, frontend lint, and build.

## In Progress / Discussion

- Master controller for cross-account automation (deferred until single-worker and session ownership are stable).

## Completed

- [x] **User Listing**: Added user count to CSV export filename in `31_list_group_users.py`.
- [x] **UX**: Display resolved entity name for default target in `pick_target`.
- [x] **Files**: standardized output naming convention.
- [x] **Bot Reply**: AI-drafted, human-approved auto-replies via `6_messaging/bot_reply/`, configured from the dashboard's `/reply` and `/reply/setup` pages.
- [x] **CSRF protection**: double-submit-cookie token (`dashboard/csrf.py`), checked via `X-CSRF-Token` header on JSON/fetch routes (Bot Reply, Ghost Mirror toggles) or a `csrf_token` form field on native-form routes (session switch/delete, phone/QR login). Cookie provisioned app-wide by a lightweight middleware in `dashboard/app.py`. Covers both the classic Jinja2 UI and the React `/app` SPA. Landed 2026-08-03.
- [x] **Approval authorization**: Bot Reply approval callbacks require `BOT_REPLY_OPERATOR_USER_ID`; unauthorized users cannot approve, reject, or edit drafts.
- [x] **WebSocket origin protection**: Dashboard WebSockets reject missing or foreign `Origin` headers before accepting the connection.
- [x] **Single worker lease**: Dashboard-managed Ghost and Bot Reply workers use an atomic PID lease so reloads/multiple dashboard processes do not launch duplicate Telegram clients.
- [x] **Durable Ghost configuration**: `mirrors.json` seeds missing chats only; dashboard-managed mappings and monitoring state survive runner restarts.
- [x] **Remote transport guard**: Non-loopback dashboard access requires an HTTPS public origin; remote cleartext requests are refused and CSRF cookies are secure.
- [x] **Bot Reply settings validation**: Session names, provider/mode values, model text, history depth, TTL, and group-size limits are validated before persistence.
- [x] **Login lifecycle safety**: Session verification uses the shared session lock; abandoned phone/QR flows expire after 10 minutes and clean up clients/temp files.
- [x] **Regression checks**: Focused stdlib tests cover these security and lifecycle invariants; Python compilation and frontend lint/build pass.

See [`docs/AUDIT_STATUS.md`](AUDIT_STATUS.md) for the audit baseline, verification commands, and remaining prioritized work.
