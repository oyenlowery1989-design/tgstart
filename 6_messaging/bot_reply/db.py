"""SQLite persistence for bot_reply: per-chat config, the pending-reply queue, and
settings. Separate from 6_messaging/65/ghost.db on purpose — ghost_runner.py owns that
file's PRAGMA user_version migration chain, and two independent processes migrating one
file would collide."""
import datetime
import sqlite3
from pathlib import Path
from typing import List, Optional

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "data" / "bot_reply.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS chat_config (
    chat_id          INTEGER PRIMARY KEY,
    title            TEXT,
    enabled          BOOLEAN NOT NULL DEFAULT 0,
    trigger_mode     TEXT,
    persona_override TEXT,
    updated_at       TEXT
);

CREATE TABLE IF NOT EXISTS pending_replies (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id           INTEGER NOT NULL,
    chat_title        TEXT,
    source_message_id INTEGER NOT NULL,
    source_text       TEXT,
    source_sender     TEXT,
    draft_text        TEXT NOT NULL,
    status            TEXT NOT NULL DEFAULT 'pending',
    approval_msg_id   INTEGER,
    created_at        TEXT NOT NULL,
    resolved_at       TEXT,
    sent_message_id   INTEGER,
    error             TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_pending_source
    ON pending_replies(chat_id, source_message_id);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


def get_connection(db_path: str = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.execute("PRAGMA foreign_keys=ON;")
    init_schema(conn)
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    conn.commit()


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def get_setting(conn: sqlite3.Connection, key: str, default: Optional[str] = None) -> Optional[str]:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    conn.commit()
    bump_config(conn)


def bump_config(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO settings (key, value) VALUES ('config_bump', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (_now(),),
    )
    conn.commit()


def get_chat_config(conn: sqlite3.Connection, chat_id: int) -> Optional[dict]:
    row = conn.execute("SELECT * FROM chat_config WHERE chat_id = ?", (chat_id,)).fetchone()
    return dict(row) if row else None


def upsert_chat_config(conn: sqlite3.Connection, chat_id: int, title: str, **fields) -> None:
    allowed_fields = {"enabled", "trigger_mode", "persona_override"}
    invalid_fields = set(fields.keys()) - allowed_fields
    if invalid_fields:
        raise ValueError(f"unknown chat_config fields: {invalid_fields}")

    existing = get_chat_config(conn, chat_id)
    if existing is None:
        conn.execute(
            "INSERT INTO chat_config (chat_id, title, updated_at) VALUES (?, ?, ?)",
            (chat_id, title, _now()),
        )
    if fields:
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        conn.execute(
            f"UPDATE chat_config SET title = ?, updated_at = ?, {set_clause} WHERE chat_id = ?",
            (title, _now(), *fields.values(), chat_id),
        )
    else:
        conn.execute(
            "UPDATE chat_config SET title = ?, updated_at = ? WHERE chat_id = ?",
            (title, _now(), chat_id),
        )
    conn.commit()
    bump_config(conn)


def insert_pending_reply(conn: sqlite3.Connection, chat_id: int, chat_title: str,
                          source_message_id: int, source_text: str, source_sender: str,
                          draft_text: str) -> Optional[int]:
    try:
        cur = conn.execute(
            """INSERT INTO pending_replies
               (chat_id, chat_title, source_message_id, source_text, source_sender,
                draft_text, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)""",
            (chat_id, chat_title, source_message_id, source_text, source_sender,
             draft_text, _now()),
        )
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError as e:
        # Only treat UNIQUE constraint violation on idx_pending_source as a duplicate.
        if "UNIQUE constraint failed" in str(e) or "idx_pending_source" in str(e):
            return None
        raise


def set_approval_msg_id(conn: sqlite3.Connection, reply_id: int, approval_msg_id: int) -> None:
    conn.execute(
        "UPDATE pending_replies SET approval_msg_id = ? WHERE id = ?",
        (approval_msg_id, reply_id),
    )
    conn.commit()


def try_resolve_pending(conn: sqlite3.Connection, reply_id: int, new_status: str) -> bool:
    """The double-send guard: only the caller that actually flips 'pending' -> new_status
    may act on the result. Works identically whether the racer is the DM button, the
    dashboard button, or a retried event."""
    cur = conn.execute(
        "UPDATE pending_replies SET status = ?, resolved_at = ? WHERE id = ? AND status = 'pending'",
        (new_status, _now(), reply_id),
    )
    conn.commit()
    return cur.rowcount == 1


def try_claim_for_sending(conn: sqlite3.Connection, reply_id: int) -> bool:
    """Guards 'approved' -> 'sending', the same single-winner pattern as
    try_resolve_pending, but for the second race: the button-approve path and
    _approved_poll_loop can both observe an 'approved' row and both try to send it."""
    cur = conn.execute(
        "UPDATE pending_replies SET status = 'sending' WHERE id = ? AND status = 'approved'",
        (reply_id,),
    )
    conn.commit()
    return cur.rowcount == 1


def release_claim(conn: sqlite3.Connection, reply_id: int) -> None:
    """Releases a 'sending' claim back to 'approved' (e.g. after a FloodWaitError), so
    _approved_poll_loop naturally retries it on its next pass instead of the reply being
    discarded on the first transient send failure."""
    conn.execute(
        "UPDATE pending_replies SET status = 'approved' WHERE id = ? AND status = 'sending'",
        (reply_id,),
    )
    conn.commit()


def retry_failed(conn: sqlite3.Connection, reply_id: int) -> bool:
    """Manual operator retry from the dashboard: only a 'failed' row may be resurrected
    back to 'approved', the same single-winner UPDATE pattern as try_resolve_pending."""
    cur = conn.execute(
        "UPDATE pending_replies SET status = 'approved', resolved_at = ? WHERE id = ? AND status = 'failed'",
        (_now(), reply_id),
    )
    conn.commit()
    return cur.rowcount == 1


def get_pending_reply(conn: sqlite3.Connection, reply_id: int) -> Optional[dict]:
    row = conn.execute("SELECT * FROM pending_replies WHERE id = ?", (reply_id,)).fetchone()
    return dict(row) if row else None


def list_pending_replies(conn: sqlite3.Connection, status: Optional[str] = None) -> List[dict]:
    if status:
        rows = conn.execute(
            "SELECT * FROM pending_replies WHERE status = ? ORDER BY created_at DESC", (status,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM pending_replies ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def mark_sent(conn: sqlite3.Connection, reply_id: int, sent_message_id: int) -> None:
    conn.execute(
        "UPDATE pending_replies SET status = 'sent', sent_message_id = ? WHERE id = ?",
        (sent_message_id, reply_id),
    )
    conn.commit()


def mark_failed(conn: sqlite3.Connection, reply_id: int, error: str) -> None:
    conn.execute(
        "UPDATE pending_replies SET status = 'failed', error = ? WHERE id = ?",
        (error, reply_id),
    )
    conn.commit()


def expire_stale_pending(conn: sqlite3.Connection, ttl_hours: float) -> int:
    cutoff = (datetime.datetime.now(datetime.timezone.utc)
              - datetime.timedelta(hours=ttl_hours)).isoformat()
    cur = conn.execute(
        "UPDATE pending_replies SET status = 'expired' "
        "WHERE status IN ('pending', 'approved', 'sending') AND created_at < ?",
        (cutoff,),
    )
    conn.commit()
    return cur.rowcount


if __name__ == "__main__":
    # Smoke check: the double-send invariant must hold — exactly one of two concurrent
    # resolve attempts on the same row may win.
    conn = get_connection(":memory:")
    reply_id = insert_pending_reply(conn, chat_id=1, chat_title="Test", source_message_id=100,
                                     source_text="hi", source_sender="alice", draft_text="hello!")
    assert reply_id is not None
    duplicate = insert_pending_reply(conn, chat_id=1, chat_title="Test", source_message_id=100,
                                      source_text="hi", source_sender="alice", draft_text="hello again")
    assert duplicate is None, "duplicate (chat_id, source_message_id) must be rejected"

    first = try_resolve_pending(conn, reply_id, "approved")
    second = try_resolve_pending(conn, reply_id, "approved")
    assert first is True, "first resolve attempt must win"
    assert second is False, "second resolve attempt on an already-resolved row must lose"

    row = get_pending_reply(conn, reply_id)
    assert row["status"] == "approved"

    claim_first = try_claim_for_sending(conn, reply_id)
    claim_second = try_claim_for_sending(conn, reply_id)
    assert claim_first is True, "first sending-claim attempt must win"
    assert claim_second is False, "second sending-claim attempt on an already-claimed row must lose"

    # A row orphaned in 'sending' (crash between try_claim_for_sending and mark_sent/
    # mark_failed) must still age out via expire_stale_pending, not be lost forever.
    stale_cutoff = (datetime.datetime.now(datetime.timezone.utc)
                    - datetime.timedelta(hours=1)).isoformat()
    conn.execute("UPDATE pending_replies SET created_at = ? WHERE id = ?",
                 (stale_cutoff, reply_id))
    conn.commit()
    expired_count = expire_stale_pending(conn, ttl_hours=0.5)
    assert expired_count == 1, "stale 'sending' row must be expired"
    row = get_pending_reply(conn, reply_id)
    assert row["status"] == "expired", "stale 'sending' row must transition to 'expired'"

    set_setting(conn, "provider", "vertex")
    assert get_setting(conn, "provider") == "vertex"
    assert get_setting(conn, "config_bump") is not None, "set_setting must bump config_bump"

    upsert_chat_config(conn, chat_id=42, title="Some Group", enabled=1, trigger_mode="mentions")
    cfg = get_chat_config(conn, 42)
    assert cfg["enabled"] == 1 and cfg["trigger_mode"] == "mentions"

    # release_claim: a FloodWait mid-send must return the row to 'approved', not lose it.
    reply_id2 = insert_pending_reply(conn, chat_id=2, chat_title="Test2", source_message_id=200,
                                      source_text="hi2", source_sender="bob", draft_text="hello2")
    assert try_resolve_pending(conn, reply_id2, "approved") is True
    assert try_claim_for_sending(conn, reply_id2) is True
    release_claim(conn, reply_id2)
    assert get_pending_reply(conn, reply_id2)["status"] == "approved", \
        "release_claim must return a 'sending' row to 'approved'"
    assert try_claim_for_sending(conn, reply_id2) is True, "row must be re-claimable after release"

    # retry_failed: only a 'failed' row may be resurrected to 'approved'.
    mark_failed(conn, reply_id2, "boom")
    assert get_pending_reply(conn, reply_id2)["status"] == "failed"
    retry_first = retry_failed(conn, reply_id2)
    retry_second = retry_failed(conn, reply_id2)
    assert retry_first is True, "first retry of a failed row must win"
    assert retry_second is False, "retrying an already-approved row must lose (not failed anymore)"
    assert get_pending_reply(conn, reply_id2)["status"] == "approved"

    reply_id3 = insert_pending_reply(conn, chat_id=3, chat_title="Test3", source_message_id=300,
                                      source_text="hi3", source_sender="carol", draft_text="hello3")
    assert retry_failed(conn, reply_id3) is False, "retry_failed must refuse a non-failed row (still pending)"

    print("db.py smoke check OK")
