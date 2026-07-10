# Database Schema

## chats
chat_id (PK), title, type, monitored, backup_chat_id, member_count

## config
chat_id (PK), toggle_mirror_new, toggle_edits, toggle_deletes, toggle_admin,
toggle_restrict, toggle_invites, toggle_bots, toggle_bio_worker, diff_mode

## users
user_id (PK), username, first_name, last_name, is_bot, bio, last_seen

## messages
chat_id, message_id (PK composite), user_id, text, media_meta, ts

## events
event_id (PK), ts, chat_id, event_type, actor_user_id,
target_user_id, message_id, summary_json

## invites
invite_hash (PK), chat_id, creator_user_id, created_ts

## joins
id (PK), chat_id, user_id, invite_hash, joined_ts
