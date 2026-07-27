# Bot Reply — Design

**Date:** 2026-07-27
**Status:** Approved, ready for implementation planning

## Goal

Port the standalone `bot-reply` project into `telegram-start` as a supervised subsystem: a
Telethon userbot that drafts AI replies to incoming messages, gated behind a human approval
step, configured entirely through the existing web dashboard rather than by hand-editing
`.env` and restarting.

The concrete gap this closes: `bot-reply` configured which chats to skip via a
comma-separated `IGNORE_CHAT_IDS` list in `.env`, edited blind — the operator had to stop the
process and run a throwaway script to dump chat names and IDs just to find the right numbers.
`telegram-start` already lists dialogs with names and IDs, and already has the per-chat
boolean + dashboard toggle + hot-reload pattern in `ghost_mirror`. This design reuses that
pattern rather than rebuilding it.

## Non-goals

- Rewriting the Vertex Gemini drafting prompt. It works; it moves across intact.
- Auto-sending without approval, under any configuration. See Security.
- Multi-user or RBAC. Single-operator tool, same as the rest of the suite.
- Refactoring `ghost_runner.py` or `ghost.db`. Untouched.

## Architecture

New subsystem at `6_messaging/bot_reply/`, supervised by `dashboard/app.py`'s lifespan
exactly as `ghost_mirror` is:

```
6_messaging/bot_reply/
  runner.py          # one asyncio loop: userbot client + approval bot client
  db.py              # schema, migrations, config cache, config_bump polling
  providers/
    __init__.py      # get_provider(name) -> draft_reply callable
    vertex.py        # Vertex Gemini (ported from bot-reply)
    anthropic.py     # Anthropic SDK
  persona.txt        # global default voice, re-read fresh per draft
  data/bot_reply.db  # gitignored

dashboard/
  bot_reply_process.py     # supervisor, mirrors ghost_process.py
  routes/bot_reply.py      # /reply/*
  templates/reply/
    index.html             # pending queue + runner status
    setup.html             # per-chat config
```

### Process model

One process, two Telethon clients in a single asyncio loop:

- **Userbot client** — authenticates as the operator's own account using the session named in
  `settings.session_name`. Listens for incoming messages, drafts replies, and is the only
  thing that ever sends into a real chat.
- **Approval bot client** — authenticates with a bot token. DMs the operator each draft with
  Approve / Edit / Reject inline buttons, and edits its own messages after resolution.

Both live in one process so a draft is created and resolved by the same runtime. The
double-send guard is therefore a local check in the common case, not cross-process
coordination.

`dashboard/bot_reply_process.py` mirrors `dashboard/ghost_process.py`, but is written from the
start with `start_new_session=True` and process-group termination
(`os.killpg(os.getpgid(proc.pid), SIGTERM)`). This is deliberate: `65/run.py` originally
SIGTERM'd only the watchdog and orphaned the real bot, which meant a "stop" left a live client
running and the next "start" produced two bots writing the same tables. bot_reply inherits the
fixed pattern rather than repeating the bug. The runner is also launched with
`stdin=subprocess.DEVNULL` — the other half of that same incident, where a blocking `input()`
prompt with no tty hung the process forever.

## Data model

New SQLite database at `6_messaging/bot_reply/data/bot_reply.db`, separate from `ghost.db`.

Separation is required, not stylistic: `ghost_runner.py` owns `ghost.db`'s `PRAGMA
user_version` migration chain. Two independent processes migrating one file would collide, and
a schema bump in either could break the other.

There is deliberately **no `chats` table**. The setup page lists dialogs live via the
dashboard's existing `dashboard/services/chats_service.py::list_dialogs()`, so the chat list
cannot go stale and no dialog-sync code is duplicated.

```sql
CREATE TABLE chat_config (
    chat_id          INTEGER PRIMARY KEY,
    title            TEXT,      -- cached label, for rendering the queue when a dialog
                                -- lookup is unavailable
    enabled          BOOLEAN NOT NULL DEFAULT 0,
    trigger_mode     TEXT,      -- NULL = inherit global; 'always' | 'mentions' | 'off'
    persona_override TEXT,      -- NULL = use the global persona.txt
    updated_at       TEXT
);

CREATE TABLE pending_replies (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id           INTEGER NOT NULL,
    chat_title        TEXT,
    source_message_id INTEGER NOT NULL,
    source_text       TEXT,
    source_sender     TEXT,
    draft_text        TEXT NOT NULL,
    status            TEXT NOT NULL DEFAULT 'pending',
                      -- pending | approved | rejected | sent | failed | expired
    approval_msg_id   INTEGER,   -- id of the approval bot's DM, so it can be edited
                                 -- after resolution
    created_at        TEXT NOT NULL,
    resolved_at       TEXT,
    sent_message_id   INTEGER,
    error             TEXT
);

CREATE UNIQUE INDEX idx_pending_source
    ON pending_replies(chat_id, source_message_id);

CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT);
-- keys: session_name, provider, model, trigger_mode (global default),
--       small_group_max_size, draft_ttl_hours, config_bump
```

Nullable `trigger_mode` and `persona_override` are what make "per-chat with global defaults"
work without pre-populating a row for every dialog the operator belongs to.

### Idempotency and the double-send guard

`UNIQUE INDEX (chat_id, source_message_id)` makes draft creation idempotent. If the runner
restarts mid-draft, or Telethon redelivers an event, the insert fails rather than queueing a
second draft for the same incoming message.

Resolution uses one conditional UPDATE:

```sql
UPDATE pending_replies
   SET status = 'approved', resolved_at = ?
 WHERE id = ? AND status = 'pending'
```

The caller that observes `rowcount == 1` won and proceeds to send; a caller observing `0` lost
and does nothing. This is correct regardless of which surface raced — DM button, dashboard
button, or a retry — and needs no locking.

## Data flow

### Drafting

1. Userbot receives a message in chat X.
2. `should_reply()` decides whether to act (see Trigger evaluation).
3. Prompt is assembled: persona (`chat_config.persona_override` if set, else `persona.txt`
   re-read fresh from disk), plus recent history from chat X.
4. The configured provider is called.
5. A `pending_replies` row is inserted with status `pending`.
6. The approval bot DMs the operator the draft with Approve / Edit / Reject inline buttons,
   recording its own message id in `approval_msg_id`.

Persona is re-read from disk on every draft, so editing `persona.txt` takes effect on the next
message with no restart — matching current `bot-reply` behavior.

### Resolving via Telegram DM

Button callback fires in-process → conditional UPDATE to `approved` → on winning, the userbot
sends into chat X → status becomes `sent` and `sent_message_id` is recorded → the approval bot
edits its own DM to show the outcome, so stale buttons cannot be pressed again.

**Edit** prompts the operator for replacement text, then follows the same path with the
substituted body. **Reject** transitions to `rejected` and sends nothing.

### Resolving via dashboard

The dashboard performs the same conditional UPDATE to `approved` and stops — it holds no
Telegram client. The runner's poll loop picks up `approved`-but-unsent rows every 2s and sends
them.

Dashboard approval therefore lands within roughly 2s, which is acceptable for a reply. The DM
path skips the poll entirely and sends immediately, since it is already inside the runner's
process.

### Config hot-reload

The dashboard writes `chat_config` / `settings`, then bumps `settings.config_bump` with a
fresh timestamp. The runner polls that key every 2s and refreshes its in-memory cache on
change. This is the `ghost_mirror` mechanism, unchanged.

`session_name` is the one exception: changing which account replies cannot hot-reload, so
writing it triggers a supervisor restart of the runner.

## Trigger evaluation

Deliberately a pure function with no Telethon objects in its signature, so it is testable
without a network or a client:

```python
should_reply(chat_cfg, globals_, msg_meta) -> bool
```

1. `chat_cfg.enabled` must be 1, else stop.
2. Never reply to the operator's own messages, or to messages from bots.
3. Resolve mode: `chat_cfg.trigger_mode` if set, else `settings.trigger_mode`.
4. `off` → stop. `mentions` → require an @mention of the operator or a reply to one of their
   messages. `always` → proceed, **unless** the group has more members than
   `small_group_max_size`, which downgrades it to mentions-only.

Step 4's size clause preserves `bot-reply`'s `SMALL_GROUP_MAX_SIZE` semantics — freely chatty
in small groups, mention-only in large ones — now overridable per chat.

### Allowlist, not denylist — a deliberate behavior change

`bot-reply` used `IGNORE_CHAT_IDS`, a **denylist**: reply everywhere except the listed chats.
`chat_config.enabled` is an **allowlist**: silent everywhere until a chat is explicitly
enabled.

Rationale: a denylist-defaulted auto-replier begins sending AI-authored messages as the
operator in every newly joined group before they notice. That failure is public and
unrecoverable. The allowlist's failure mode is that the operator ticks a checkbox.

This is the only place the port intentionally changes behavior rather than preserving it. It
was raised explicitly during design and approved.

## Provider layer

`providers/get_provider(name)` returns a callable selected by `settings.provider`
(`vertex` | `anthropic`). Each provider module exposes:

```python
async def draft_reply(system_prompt: str, history: list[dict], incoming: str) -> str
```

`vertex.py` is the ported Gemini implementation with its existing GCP credentials and model
name. `anthropic.py` is the equivalent against the Anthropic SDK. Provider and model name are
stored in `settings` and selectable from the dashboard; credentials stay in `.env`.

## Error handling

| Failure | Behavior |
|---|---|
| Provider call fails | Row stored as `failed` with the error text, surfaced in the dashboard queue with a Retry button. No DM sent. |
| Telegram send fails (e.g. FloodWait) | Row stays `approved`; retried with backoff. After N attempts → `failed`. Never silently dropped. |
| Draft goes stale | Older than `draft_ttl_hours` (default 6) → `expired`, never sent. A reply to a six-hour-old message is worse than no reply. |
| Runner crashes | Supervisor restarts it. In-flight `approved` rows are picked up by the poll loop on boot, so nothing approved is lost. |
| Provider credentials missing or invalid | Runner logs and refuses to begin drafting rather than going silently quiet; surfaced as a status banner on the dashboard page. |

## Testing

This repo has no test framework, linter config, or CI — `python -m py_compile` is the only
available check, and the established convention is a `__main__` smoke check per module. Two of
those are substantive:

- **`db.py`** — against an in-memory database: apply the schema, insert a pending row, run the
  conditional UPDATE twice, assert `rowcount` is 1 then 0. This asserts the double-send
  invariant, the one property that must not regress.
- **`should_reply()`** — table-driven assertions across the mode / group-size / mention matrix.
  Pure function, no network, no Telegram.

Provider modules get a signature check only; smoke tests make no live API calls.

## Security

Three properties are not negotiable and must not be simplified away during implementation:

1. **Only an `approved` transition may send.** There is no auto-send path and no "trusted
   chat" bypass. The approval gate is the entire safety mechanism of this subsystem — the
   userbot sends as the operator's real account, under their own name.
2. **Credentials stay in `.env`,** never committed: the approval bot token, GCP service
   account, and Anthropic API key. Per existing project convention, fallback defaults in code
   must be `0` / `""` and never real values.
3. **Enabling a chat sends its content to a third-party LLM.** Message text leaves the machine
   as prompt context. This should be stated plainly in the dashboard UI next to the enable
   toggle, not buried in documentation.

The `/reply/*` routes sit behind the dashboard's existing HTTP Basic auth gate, inherited
automatically from the app-level dependency in `dashboard/app.py`.

## Open items for the implementation plan

- Exact retry/backoff counts for FloodWait handling.
- Whether the pending-queue page polls or uses a websocket. The suite has an established
  websocket pattern (`dashboard/ws_utils.py`), but the queue is low-volume enough that polling
  may be sufficient; decide during implementation.
- Approval DM formatting: how much source context to include alongside the draft.
- Prompt history depth — how many prior messages from the chat to include as context. Starts
  as a `settings` key (`history_depth`) so it is tunable without a code change; the initial
  default should match whatever `bot-reply` currently uses.
