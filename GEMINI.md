# Gemini Work Log

## 2026-02-11: User Listing Script Enhancements

### 3_chat_management/31_list_group_users.py

- **Feature**: Added user count to the output CSV filename (e.g., `..._61.csv`) for easier tracking.
- **Refactor**: Replaced date-based suffix with user count as requested.

### utils/tg_utils.py

- **UX Improvement**: Updated `pick_target` to automatically resolve and display the name of the default target entity (Group/Channel User) alongside its ID in the interactive menu.

### Documentation

- Updated `README.md` and `docs/TODO.md` to reflect these changes.
