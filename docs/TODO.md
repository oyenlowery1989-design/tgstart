# 📝 Telegram Tools TODO List

## Planned Features

- [ ] **Account Syncing**: Sync settings and configurations across different Telegram sessions.
- [ ] **Advanced Filtering**: Add complex regex and AI-based filtering to the mirror scripts.

## In Progress / Discussion

- Master controller for cross-account automation.

## Completed

- [x] **User Listing**: Added user count to CSV export filename in `31_list_group_users.py`.
- [x] **UX**: Display resolved entity name for default target in `pick_target`.
- [x] **Files**: standardized output naming convention.
- [x] **Bot Reply**: AI-drafted, human-approved auto-replies via `6_messaging/bot_reply/`, configured from the dashboard's `/reply` and `/reply/setup` pages.
- [x] **CSRF protection**: double-submit-cookie token (`dashboard/csrf.py`), checked via `X-CSRF-Token` header on JSON/fetch routes (Bot Reply, Ghost Mirror toggles) or a `csrf_token` form field on native-form routes (session switch/delete, phone/QR login). Cookie provisioned app-wide by a lightweight middleware in `dashboard/app.py`. Covers both the classic Jinja2 UI and the React `/app` SPA. Landed 2026-08-03.
