# 📝 Telegram Tools TODO List

## Planned Features

- [ ] **Account Syncing**: Sync settings and configurations across different Telegram sessions.
- [ ] **Advanced Filtering**: Add complex regex and AI-based filtering to the mirror scripts.
- [ ] **CSRF protection**: every mutating POST route (`/sessions/active`, `/sessions/{name}/delete`, Ghost Mirror toggles, Bot Reply approve/reject/settings) relies on HTTP Basic auth only — browsers replay cached Basic-auth credentials on cross-origin form POSTs, so a malicious page could trigger these while the dashboard tab is authenticated. Flagged 2026-08-02 during session-delete security review; deferred since this is a local-only, password-gated tool and fixing it properly needs an app-wide CSRF token, not a per-route patch.

## In Progress / Discussion

- Master controller for cross-account automation.

## Completed

- [x] **User Listing**: Added user count to CSV export filename in `31_list_group_users.py`.
- [x] **UX**: Display resolved entity name for default target in `pick_target`.
- [x] **Files**: standardized output naming convention.
- [x] **Bot Reply**: AI-drafted, human-approved auto-replies via `6_messaging/bot_reply/`, configured from the dashboard's `/reply` and `/reply/setup` pages.
