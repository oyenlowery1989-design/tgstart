# Event Schema

All events follow a normalized structure:

{
  "event_id": "uuid",
  "ts_utc": "ISO8601",
  "chat_id": 123,
  "chat_title": "Example",
  "event_type": "message_new",
  "actor_user_id": 111,
  "target_user_id": null,
  "message_id": 555,
  "text_before": null,
  "text_after": "Hello",
  "diff": null,
  "media_meta": {},
  "invite_hash": null,
  "restriction": null
}

Event types include:
- message_new
- message_edit
- message_delete
- user_join
- user_leave
- admin_promote
- admin_demote
- user_ban
- user_unban
- user_restrict
- invite_create
- bot_added
- bot_removed
