# Telegram Support Bot Implementation Plan

## Goal

A professional Support Ticket Bot (`@SupportBot`) using SQLite.
This implementation is broken down into **3 Phases** to ensure stability and incremental progress.

## Phase 1: Core Support Foundation

**Objective**: Build a working ticket system where users can chat with admins.

- **Interactive Start Menu**: Buttons for [Prices], [Hours], [Contact Support].
- **Ticket Workflow**:
  - User clicks "Contact Support" -> Bot creates Forum Topic in Admin Group.
  - Admin replies in topic -> Bot copies message to User.
  - User replies -> Bot forwards to Topic.
- **Rich User Profiling**: Pin user details (ID, Name, Photo) in the topic.
- **Basic Commands**: `/close`, `/ban`, `/unban`, `/id`, `/note`.
- **Database**: `users` table, `config` table.

## Phase 2: Engagement & Loyalty (Rewards)

**Objective**: Adding gamification to keep users engaged.

- **Referral System**: `t.me/Bot?start=123` logic.
- **Points System**:
  - `users` table updated with `balance` and `referrer_id`.
  - `referrals` table added.
  - Commands: `/balance`, `/addpoints`.
- **Post-Resolution Feedback**:
  - `/close` triggers "Rate us 1-5 stars".
  - 5-star ratings award points to the user.
- **Snippet System**: `/snippet` and `/use` for faster replies.

## Phase 3: Investor Verification (Sales)

**Objective**: Turning support users into verified investors.

- **Stellar Verification**:
  - [Check My Investment] button added to menu.
  - User inputs "G..." address.
  - Bot checks Horizon API for specific Asset holdings.
- **Upsell Logic**:
  - **Holder**: "Verified! Buy more for a bonus."
  - **Non-Holder**: "Buy TKN now!"
- **Targeted Broadcasts**: `/broadcast_investors` (Only to verified holders).
- **Database**: Add `stellar_address` and `asset_balance` fields.

## Technical Stack

- **Library**: `python-telegram-bot` (v20+ Async).
- **Database**: `SQLite` (Single file `80_data/support_bot.db`).
- **External API**: Stellar Horizon (Public) for Phase 3.
