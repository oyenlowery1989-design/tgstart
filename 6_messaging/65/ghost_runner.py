import os
import sys
import json
import asyncio
import datetime
import sqlite3
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from telethon import TelegramClient, events, functions, types as tl_types, utils as tl_utils
from telethon.errors import FloodWaitError
from dotenv import load_dotenv
from loguru import logger
import aiofiles
import uuid
import re
import difflib
from collections import deque

try:
    from telethon.tl.types import UpdateChatInviteImporter
except ImportError:
    UpdateChatInviteImporter = None
    logger.warning("UpdateChatInviteImporter not available in this Telethon version; invite-join attribution disabled.")

ANONYMOUS_ADMIN_ID = 1087968824  # Telegram's "GroupAnonymousBot" account id

# --- Configuration ---
load_dotenv()
if not os.getenv("API_ID"):
    load_dotenv(".env.local")

API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
SESSION_NAME = os.getenv("SESSION_NAME", "ghost_session")
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
MAX_BIO_QUEUE_SIZE = int(os.getenv("BIO_QUEUE_SIZE", 500))
BIO_WORKER_DELAY = float(os.getenv("BIO_WORKER_DELAY", 2.0))

# Setup Logging
LOG_DIR = DATA_DIR / "logs"
ERROR_DIR = DATA_DIR / "errors"
MEDIA_DIR = DATA_DIR / "media"
DB_PATH = DATA_DIR / "ghost.db"

DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)
ERROR_DIR.mkdir(exist_ok=True)
MEDIA_DIR.mkdir(exist_ok=True)

logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add(ERROR_DIR / "{time:YYYY-MM-DD}.log", level="ERROR", rotation="00:00")
# Note: JSONL Logging is handled by AuditLogger

# --- Database Manager (SQLite) ---
class DatabaseManager:
    SCHEMA_VERSION = 4  # Phase 4: reaction mirroring + dest-message tracking
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = None
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path, check_same_thread=False, timeout=5.0)

    def _init_db(self):
        self.conn = self._connect()
        self.conn.row_factory = sqlite3.Row
        # Hardening
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")
        self.conn.execute("PRAGMA busy_timeout=5000;")
        self._migrate()
    
    def _apply_schema_v2(self, cur):
        # Migration to add toggle_log_new
        try:
            cur.execute("ALTER TABLE config ADD COLUMN toggle_log_new BOOLEAN DEFAULT 1")
            logger.info("Added toggle_log_new column to config table.")
        except sqlite3.OperationalError:
            pass

    def _apply_schema_v3(self, cur):
        # Migration to add toggle_joins and config_meta
        try:
            cur.execute("ALTER TABLE config ADD COLUMN toggle_joins BOOLEAN DEFAULT 1")
            logger.info("Added toggle_joins column to config table.")
        except sqlite3.OperationalError:
            pass
            
        cur.execute("""
            CREATE TABLE IF NOT EXISTS config_meta (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        # Initialize bump timestamp if missing
        cur.execute("INSERT OR IGNORE INTO config_meta (key, value) VALUES ('config_bump', '0')")

    def _apply_schema_v4(self, cur):
        # Migration to add toggle_reactions and dest_message_id (mirrored-message tracking,
        # needed to reply-thread reaction mirrors onto the correct destination message)
        try:
            cur.execute("ALTER TABLE config ADD COLUMN toggle_reactions BOOLEAN DEFAULT 1")
            logger.info("Added toggle_reactions column to config table.")
        except sqlite3.OperationalError:
            pass
        try:
            cur.execute("ALTER TABLE messages ADD COLUMN dest_message_id INTEGER")
            logger.info("Added dest_message_id column to messages table.")
        except sqlite3.OperationalError:
            pass

    def _migrate(self):
        cur = self.conn.cursor()
        
        try:
            cur.execute("PRAGMA user_version")
            current_ver = cur.fetchone()[0]
        except:
            current_ver = 0
            
        logger.info(f"Database version: {current_ver}. Target: {self.SCHEMA_VERSION}")
        
        if current_ver < 1:
            logger.info("Applying Migration v1 (Initial Schema)")
            self._apply_schema_v1(cur)
            current_ver = 1
            
        if current_ver < 2:
            logger.info("Applying Migration v2 (Toggle Log New)")
            self._apply_schema_v2(cur)
            current_ver = 2
            
        if current_ver < 3:
            logger.info("Applying Migration v3 (Toggle Joins & Config Meta)")
            self._apply_schema_v3(cur)
            current_ver = 3

        if current_ver < 4:
            logger.info("Applying Migration v4 (Reactions & Dest Message Tracking)")
            self._apply_schema_v4(cur)
            cur.execute(f"PRAGMA user_version = {self.SCHEMA_VERSION}")
            self.conn.commit()
            
    def _apply_schema_v1(self, cur):
        # Chats Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                chat_id INTEGER PRIMARY KEY,
                title TEXT,
                type TEXT,
                monitored BOOLEAN DEFAULT 0,
                backup_chat_id INTEGER,
                member_count INTEGER
            )
        """)
        
        # Config Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS config (
                chat_id INTEGER PRIMARY KEY,
                toggle_mirror_new BOOLEAN DEFAULT 1,
                toggle_edits BOOLEAN DEFAULT 1,
                toggle_deletes BOOLEAN DEFAULT 1,
                toggle_admin BOOLEAN DEFAULT 1,
                toggle_restrict BOOLEAN DEFAULT 1,
                toggle_invites BOOLEAN DEFAULT 1,
                toggle_bots BOOLEAN DEFAULT 1,
                toggle_bio_worker BOOLEAN DEFAULT 0,
                diff_mode TEXT DEFAULT 'word',
                FOREIGN KEY(chat_id) REFERENCES chats(chat_id)
            )
        """)
        
        # Users Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                is_bot BOOLEAN,
                bio TEXT,
                last_seen TEXT
            )
        """)
        
        # Messages Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                chat_id INTEGER,
                message_id INTEGER,
                user_id INTEGER,
                text TEXT,
                media_meta TEXT,
                ts TEXT,
                PRIMARY KEY (chat_id, message_id)
            )
        """)
        
        # Events Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                ts TEXT,
                chat_id INTEGER,
                event_type TEXT,
                actor_user_id INTEGER,
                target_user_id INTEGER,
                message_id INTEGER,
                summary_json TEXT
            )
        """)
        
        # Invites Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS invites (
                invite_hash TEXT PRIMARY KEY,
                chat_id INTEGER,
                creator_user_id INTEGER,
                created_ts TEXT
            )
        """)
        
        # Joins Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS joins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                user_id INTEGER,
                invite_hash TEXT,
                joined_ts TEXT
            )
        """)

    def execute(self, query: str, params: tuple = ()):
        try:
            cur = self.conn.cursor()
            cur.execute(query, params)
            self.conn.commit()
            return cur
        except sqlite3.Error as e:
            logger.error(f"DB Error: {e} | Query: {query}")
            raise

    def close(self):
        if self.conn:
            self.conn.close()

# --- Config Manager ---
class ConfigManager:
    def __init__(self, db: DatabaseManager, mirrors_path: str = "mirrors.json"):
        self.db = db
        self.mirrors_path = mirrors_path
        self.config_cache: Dict[int, Dict[str, Any]] = {}

    def load_initial_config(self):
        """
        1. Load mirrors.json
        2. Upsert chats into DB
        3. Insert default config if missing
        4. Load final config from DB (overrides)
        """
        if not os.path.exists(self.mirrors_path):
            logger.warning(f"{self.mirrors_path} not found. Skipping initial seed.")
            return

        try:
            with open(self.mirrors_path, "r", encoding="utf-8") as f:
                mirrors = json.load(f)
                
            for m in mirrors:
                chat_id = m.get("chat_id")
                if not chat_id: continue
                
                # 1. Update Chats Table
                self.db.execute("""
                    INSERT INTO chats (chat_id, title, backup_chat_id, monitored)
                    VALUES (?, ?, ?, 1)
                    ON CONFLICT(chat_id) DO UPDATE SET
                    title=excluded.title,
                    backup_chat_id=excluded.backup_chat_id,
                    monitored=1
                """, (chat_id, m.get("title", "Unknown"), m.get("backup_chat_id")))
                
                # 2. Insert Default Config if not exists
                defaults = m.get("defaults", {})
                self.db.execute("""
                    INSERT OR IGNORE INTO config (
                        chat_id, toggle_mirror_new, toggle_log_new, toggle_edits, toggle_deletes, toggle_joins
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    chat_id, 
                    defaults.get("mirror_new", 1), 
                    defaults.get("log_new", 1), 
                    defaults.get("edits", 1), 
                    defaults.get("deletes", 1),
                    defaults.get("joins", 1) # toggle_joins default
                ))
                
            logger.info(f"Loaded {len(mirrors)} mirrors from JSON.")
            self.refresh_config_cache()
            
        except Exception as e:
            logger.error(f"Failed to load mirrors.json: {e}")

    def refresh_config_cache(self):
        query = """
            SELECT c.*, ch.backup_chat_id 
            FROM config c 
            JOIN chats ch ON c.chat_id = ch.chat_id
            WHERE ch.monitored = 1
        """
        cur = self.db.execute(query)
        rows = cur.fetchall()
        self.config_cache = {row["chat_id"]: dict(row) for row in rows}
        logger.info(f"Refreshed config cache. {len(self.config_cache)} active configs.")

    def get_config(self, chat_id: int) -> Dict[str, Any]:
        return self.config_cache.get(chat_id, {})

    def is_monitored(self, chat_id: int) -> bool:
        return chat_id in self.config_cache

    def get_last_bump(self) -> str:
        cur = self.db.execute("SELECT value FROM config_meta WHERE key='config_bump'")
        row = cur.fetchone()
        return row[0] if row else "0"

# --- Audit Logger ---
class AuditLogger:
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.queue = asyncio.Queue()
        self.writer_task = None
        
    async def start(self):
        self.writer_task = asyncio.create_task(self._writer_loop())
        
    async def log_event(self, event_data: Dict[str, Any]):
        await self.queue.put(event_data)
        
    async def _writer_loop(self):
        while True:
            event = await self.queue.get()
            try:
                await self._write_to_disk(event)
                await self._write_to_db(event)
            except Exception as e:
                logger.error(f"Failed to write event: {e}")
            finally:
                self.queue.task_done()
                
    async def _write_to_disk(self, event: Dict[str, Any]):
        today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
        filepath = LOG_DIR / f"{today}.jsonl"
        
        async with aiofiles.open(filepath, mode="a", encoding="utf-8") as f:
            await f.write(json.dumps(event, default=str) + "\n")
            
    async def _write_to_db(self, event: Dict[str, Any]):
        # Basic insert, full implementation would parse specific fields
        # Here we just insert into 'events' table
        try:
             self.db.execute("""
                INSERT INTO events (event_id, ts, chat_id, event_type, summary_json)
                VALUES (?, ?, ?, ?, ?)
            """, (
                event.get("event_id"),
                event.get("ts_utc"),
                event.get("chat_id"),
                event.get("event_type"),
                json.dumps(event, default=str)
            ))
        except Exception as e:
            logger.error(f"DB Write Error: {e}")

    async def stop(self):
        if self.writer_task:
            await self.queue.join()
            self.writer_task.cancel()

# --- Ghost Runner ---
class GhostRunner:
    def __init__(self, session_name: str = None):
        self.db = DatabaseManager(DB_PATH)
        self.config_mgr = ConfigManager(self.db)
        self.audit = AuditLogger(self.db)
        
        if not API_ID or not API_HASH:
            logger.error("API_ID and API_HASH not found in env.")
            sys.exit(1)
            
        # Session Selection Logic
        final_session = session_name or SESSION_NAME
        
        # Check if it's a path or just a name
        # If passed from select_session, it might be "sessions/name" (without ext)
        # We assume the caller handles the pathing relative to CWD if needed, 
        # or we treat it as relative to DATA_DIR if simple name.
        
        # If it comes from our new selector, it is a relative path string like "sessions\myuser"
        session_path = final_session
        if not os.path.isabs(session_path) and not session_path.startswith("sessions"):
             # Default fallback logic: stick it in DATA_DIR if not explicit
             session_path = str(DATA_DIR / final_session)
             
        logger.info(f"Using session: {session_path}")
        self.client = TelegramClient(session_path, API_ID, API_HASH)
        
        # Message Index for Diffs/Recovery: {chat_id: {msg_id: {"text": "...", "media": {...}}}}
        self.message_cache = {}
        self.max_cache_per_chat = 1000

        # Dedup state for reaction mirroring: {(msg_id, user_id): last_seen_emoji}
        self.reaction_state = {}

        # User-intelligence: throttled background bio-fetch queue (populates users.bio)
        self._bio_queue = asyncio.Queue()
        self._bio_processed = set()

        # Dedup state for invite-join notifications: {(chat_id, user_id): last_claimed_ts}.
        # A join-via-link fires both a ChatAction event and a separate raw
        # UpdateChatInviteImporter update - without this, both handlers would notify.
        self._invite_join_claims = {}

    def _claim_invite_join(self, chat_id, user_id) -> bool:
        """First caller within the dedup window wins and should proceed; later callers
        for the same (chat_id, user_id) within the window are duplicates and should skip."""
        now = datetime.datetime.now(datetime.timezone.utc).timestamp()
        key = (chat_id, user_id)
        last = self._invite_join_claims.get(key)
        self._invite_join_claims[key] = now
        if len(self._invite_join_claims) > 500:
            for k in list(self._invite_join_claims.keys())[:250]:
                self._invite_join_claims.pop(k, None)
        return last is None or (now - last) >= 10

    def _record_user_seen(self, user_id, username=None, first_name=None, last_name=None, is_bot=None):
        """Upsert basic sighting info into the users table. Fields we don't have yet
        (None) leave the existing stored value untouched via COALESCE."""
        if not user_id:
            return
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        try:
            self.db.execute("""
                INSERT INTO users (user_id, username, first_name, last_name, is_bot, last_seen)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username=COALESCE(excluded.username, users.username),
                    first_name=COALESCE(excluded.first_name, users.first_name),
                    last_name=COALESCE(excluded.last_name, users.last_name),
                    is_bot=COALESCE(excluded.is_bot, users.is_bot),
                    last_seen=excluded.last_seen
            """, (user_id, username, first_name, last_name, is_bot, now))
        except Exception as e:
            logger.warning(f"Failed to record user {user_id}: {e}")
            return

        if is_bot or user_id in self._bio_processed:
            return
        # Bio fetching is opt-in (toggle_bio_worker); only queue if some monitored chat wants it.
        if any(cfg.get("toggle_bio_worker") for cfg in self.config_mgr.config_cache.values()):
            if self._bio_queue.qsize() < MAX_BIO_QUEUE_SIZE:
                self._bio_queue.put_nowait(user_id)

    def _get_display_name(self, user_id) -> str:
        if not user_id:
            return "Unknown"
        try:
            cur = self.db.execute("SELECT username, first_name, last_name FROM users WHERE user_id=?", (user_id,))
            row = cur.fetchone()
        except Exception:
            row = None
        if not row:
            return f"user {user_id}"
        name = " ".join(filter(None, [row["first_name"], row["last_name"]])).strip()
        username = row["username"]
        if name and username:
            return f"{name} (@{username})"
        if name:
            return name
        if username:
            return f"@{username}"
        return f"user {user_id}"

    async def _maybe_record_sender(self, event):
        """Best-effort: record the sender of a NewMessage/MessageEdited event without an
        extra API round-trip (Telethon events already carry/cache the sender)."""
        try:
            sender = await event.get_sender()
            if sender:
                self._record_user_seen(
                    sender.id,
                    getattr(sender, "username", None),
                    getattr(sender, "first_name", None),
                    getattr(sender, "last_name", None),
                    bool(getattr(sender, "bot", False))
                )
        except Exception:
            pass

    async def _bio_worker(self):
        """Background worker: fetches full user profiles (bio) for queued user ids,
        throttled to avoid hammering Telegram's API."""
        while True:
            try:
                user_id = await self._bio_queue.get()
                try:
                    if not any(cfg.get("toggle_bio_worker") for cfg in self.config_mgr.config_cache.values()):
                        continue  # feature currently off everywhere; drop rather than stall the queue
                    full = await self.client(functions.users.GetFullUserRequest(user_id))
                    about = getattr(full.full_user, "about", None)
                    self.db.execute("UPDATE users SET bio=? WHERE user_id=?", (about, user_id))
                    self._bio_processed.add(user_id)
                except FloodWaitError as e:
                    wait_s = getattr(e, "seconds", 60)
                    logger.warning(f"Bio fetch FloodWait: sleeping {wait_s}s")
                    await asyncio.sleep(wait_s)
                    self._bio_queue.put_nowait(user_id)
                except Exception as e:
                    logger.warning(f"Bio fetch failed for {user_id}: {e}")
                finally:
                    self._bio_queue.task_done()
                await asyncio.sleep(BIO_WORKER_DELAY)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Bio worker error: {e}")
                await asyncio.sleep(1)

    def _hydrate_cache_from_db(self):
        """Load recent messages from SQLite to hydrate cache on startup."""
        logger.info("Hydrating message cache from SQLite...")
        try:
            # Load last 1000 messages per chat
            # This is a bit expensive so we might limit total or just load per chat on demand?
            # Phase 3 limitation: simple bulk load of recent
            cur = self.db.execute("""
                SELECT chat_id, message_id, text, media_meta, dest_message_id
                FROM messages
                ORDER BY ts DESC
                LIMIT 5000
            """)
            rows = cur.fetchall()
            for r in rows:
                c_id = r["chat_id"]
                if c_id not in self.message_cache:
                    self.message_cache[c_id] = {}

                # We need to recreate media object? No, we just need meta for recovery log
                # But for 'media' arg in _cache_message we passed object.
                # Here we just store the dict form directly
                self.message_cache[c_id][r["message_id"]] = {
                    "text": r["text"] or "",
                    "media_meta": json.loads(r["media_meta"]) if r["media_meta"] else {},
                    "dest_message_id": r["dest_message_id"] if "dest_message_id" in r.keys() else None
                }
            logger.info(f"Hydrated cache with {len(rows)} messages.")
        except Exception as e:
            logger.error(f"Failed to hydrate cache: {e}")

    def _cache_message(self, chat_id: int, message_id: int, text: str, media: Any):
        # 1. Update In-Memory (preserve dest_message_id set later by mirror_message)
        if chat_id not in self.message_cache:
            self.message_cache[chat_id] = {}

        existing = self.message_cache[chat_id].get(message_id, {})
        mm = self._get_media_meta(media)
        self.message_cache[chat_id][message_id] = {
            "text": text or "",
            "media_meta": mm,
            "dest_message_id": existing.get("dest_message_id")
        }
        if len(self.message_cache[chat_id]) > self.max_cache_per_chat:
             k = next(iter(self.message_cache[chat_id]))
             del self.message_cache[chat_id][k]

        # 2. Persist to SQLite (Durable Cache). ON CONFLICT UPDATE (not INSERT OR REPLACE) so
        # an edit's re-cache doesn't wipe dest_message_id recorded after the original mirror.
        try:
            self.db.execute("""
                INSERT INTO messages (chat_id, message_id, user_id, text, media_meta, ts)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(chat_id, message_id) DO UPDATE SET
                    text=excluded.text,
                    media_meta=excluded.media_meta,
                    ts=excluded.ts
            """, (
                chat_id,
                message_id,
                None, # We don't have user_id easily in this sig, would need to update sig or pass it.
                      # But for 'cache' purposes we mostly need text/media.
                      # Ideally we pass user_id too.
                text,
                json.dumps(mm),
                datetime.datetime.now(datetime.timezone.utc).isoformat()
            ))
        except Exception as e:
            logger.warning(f"Failed to persist message {message_id} to DB: {e}")

    def _get_message_from_cache_or_db(self, chat_id: int, message_id: int) -> Optional[Dict[str, Any]]:
        # 1. Try Memory
        if chat_id in self.message_cache:
            if message_id in self.message_cache[chat_id]:
                return self.message_cache[chat_id][message_id]
        
        # 2. Try DB (Cache Miss Fallback)
        try:
            cur = self.db.execute("SELECT text, media_meta FROM messages WHERE chat_id=? AND message_id=?", (chat_id, message_id))
            row = cur.fetchone()
            if row:
                # Hydrate back to memory optionally, or just return
                mm = json.loads(row["media_meta"]) if row["media_meta"] else {}
                return {"text": row["text"] or "", "media_meta": mm}
        except Exception as e:
            logger.warning(f"DB lookup failed for message {message_id}: {e}")
            
        return None

    def _record_mirror_result(self, chat_id: int, source_msg_id: int, dest_msg_id: int):
        """Remember where a source message landed in the backup chat, so later events
        (reactions, replies) referencing the source message can be threaded onto it."""
        if chat_id in self.message_cache and source_msg_id in self.message_cache[chat_id]:
            self.message_cache[chat_id][source_msg_id]["dest_message_id"] = dest_msg_id
        try:
            self.db.execute(
                "UPDATE messages SET dest_message_id=? WHERE chat_id=? AND message_id=?",
                (dest_msg_id, chat_id, source_msg_id)
            )
        except Exception as e:
            logger.warning(f"Failed to record dest_message_id for {source_msg_id}: {e}")

    def _get_dest_message_id(self, chat_id: int, source_msg_id: int) -> Optional[int]:
        cached = self.message_cache.get(chat_id, {}).get(source_msg_id)
        if cached and cached.get("dest_message_id"):
            return cached["dest_message_id"]
        try:
            cur = self.db.execute(
                "SELECT dest_message_id FROM messages WHERE chat_id=? AND message_id=?",
                (chat_id, source_msg_id)
            )
            row = cur.fetchone()
            if row and row["dest_message_id"]:
                return row["dest_message_id"]
        except Exception as e:
            logger.warning(f"Failed to look up dest_message_id for {source_msg_id}: {e}")
        return None

    def _get_media_meta(self, media):
        if not media: return {}
        return {
           "type": type(media).__name__,
           "id": getattr(media, "id", None)
        }

    def _get_diff(self, old_text, new_text, mode="word"):
        if not old_text or not new_text:
            return None
            
        if mode == "word":
            a = old_text.split()
            b = new_text.split()
            # unify expected format usually
            diff = difflib.unified_diff(a, b, lineterm="")
            return "\n".join(diff)
        else:
            # char mode
            diff = difflib.ndiff(old_text, new_text)
            return "".join(diff)

    async def start(self):
        logger.info("Initializing GhostRunner...")
        
        # 1. Init Data & Config
        self.config_mgr.load_initial_config()
        self._hydrate_cache_from_db() # Load cache
        await self.audit.start()
        
        # Start Config Refresh Task
        asyncio.create_task(self._config_refresh_loop())
        asyncio.create_task(self._bio_worker())

        # 2. Connect to Telegram
        logger.info("Connecting to Telegram...")
        await self.client.start()
        
        me = await self.client.get_me()
        logger.info(f"Connected as: {me.first_name} (@{me.username}) ID: {me.id}")
        
        # 2.5. Sync Dialogs (Populate DB)
        # We do this after connect so we have access to dialogs
        await self._sync_dialogs()
        
        # 3. Register Handlers
        self._register_handlers()
        
        # 4. Health Check / Status
        logger.info("GhostRunner is HEALTHY. Waiting for events (Phase 2)...")
        
        # 5. Keep running
        try:
            await self.client.run_until_disconnected()
        finally:
            await self.audit.stop()
            self.db.close()
            logger.info("GhostRunner stopped.")

    async def _sync_dialogs(self):
        """Fetch all dialogs and upsert into chats table."""
        logger.info("Syncing dialogs...")
        try:
            count = 0
            async for dialog in self.client.iter_dialogs(limit=None):
                entity = dialog.entity
                
                # Determine type
                c_type = "unknown"
                if hasattr(entity, "broadcast") and entity.broadcast:
                    c_type = "channel"
                elif hasattr(entity, "megagroup") and entity.megagroup:
                    c_type = "supergroup"
                elif hasattr(entity, "participants_count"): # Basic group
                    c_type = "group"
                elif hasattr(entity, "first_name"): # User/Bot
                    c_type = "user"
                    if getattr(entity, "bot", False):
                        c_type = "bot"
                
                # Title
                title = dialog.name or "Deleted Account"
                
                # Member count (approx)
                participants_count = getattr(entity, "participants_count", 0)
                
                self.db.execute("""
                    INSERT INTO chats (chat_id, title, type, member_count)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(chat_id) DO UPDATE SET
                    title=excluded.title,
                    type=excluded.type,
                    member_count=excluded.member_count
                """, (entity.id, title, c_type, participants_count))
                count += 1
                
            logger.info(f"Synced {count} dialogs to DB.")
        except Exception as e:
            logger.error(f"Dialog sync failed: {e}")

    def _register_handlers(self):
        """Register all Telethon event handlers."""
        # New Messages
        self.client.add_event_handler(
            self._handle_new_message, 
            events.NewMessage(incoming=True)
        )
        
        # Message Edits
        self.client.add_event_handler(
            self._handle_message_edit,
            events.MessageEdited(incoming=True)
        )
        
        # Message Deletes
        self.client.add_event_handler(
            self._handle_message_delete,
            events.MessageDeleted()
        )
        
        # Chat Actions (Joins/Adds/etc)
        self.client.add_event_handler(
            self._handle_chat_action,
            events.ChatAction()
        )

        # Reactions (no dedicated high-level Telethon event; comes through Raw updates)
        self.client.add_event_handler(
            self._handle_raw_update,
            events.Raw()
        )
        logger.info("Event handlers registered.")

    async def _handle_new_message(self, event):
        await self._maybe_record_sender(event)
        await self.process_event(event, "message_new")

    async def _handle_message_edit(self, event):
        await self._maybe_record_sender(event)
        await self.process_event(event, "message_edit")
            
    async def _handle_message_delete(self, event):
        # Deletes are special, they might be bulk
        await self.process_event(event, "message_delete")

    async def _handle_chat_action(self, event):
        # Map chat actions to internal event types (existing plain join/leave audit logging,
        # gated by toggle_joins - unchanged).
        if event.user_joined or event.user_added:
            await self.process_event(event, "user_join")
        elif event.user_left or event.user_kicked:
            await self.process_event(event, "user_leave")

        # Bot detection and invite-link create/revoke/join-by-link attribution,
        # gated by toggle_bots / toggle_invites (previously unwired schema columns).
        await self._handle_member_event_extras(event)

    async def _handle_member_event_extras(self, event):
        try:
            chat_id = getattr(event, "chat_id", None)
            if chat_id is None:
                return
            if not self.config_mgr.is_monitored(chat_id):
                return
            config = self.config_mgr.get_config(chat_id)

            user_id = getattr(event, "user_id", None)
            is_bot = False
            if user_id:
                try:
                    user = await self.client.get_entity(user_id)
                    is_bot = bool(getattr(user, "bot", False))
                    self._record_user_seen(
                        user_id, getattr(user, "username", None),
                        getattr(user, "first_name", None), getattr(user, "last_name", None), is_bot
                    )
                except Exception:
                    pass

            admin_id = None
            action_message = getattr(event, "action_message", None)
            if action_message:
                admin_id = getattr(action_message, "sender_id", None)

            user_label = self._get_display_name(user_id)
            action_text = None
            action_type = None
            gate_toggle = None

            if event.user_joined or event.user_added:
                if is_bot:
                    action_text = f"🤖 Bot {'added' if event.user_added else 'joined'}: {user_label}"
                    if admin_id and event.user_added:
                        action_text += f" (by {self._get_display_name(admin_id)})"
                    action_type = "bot_join"
                    gate_toggle = "toggle_bots"
                elif action_message and isinstance(getattr(action_message, "action", None), tl_types.MessageActionChatJoinedByLink):
                    # UpdateChatInviteImporter fires separately for the same join; only one
                    # of the two handlers should notify.
                    if self._claim_invite_join(chat_id, user_id):
                        inviter_id = action_message.action.inviter_id
                        inviter_label = "Anonymous Admin" if inviter_id == ANONYMOUS_ADMIN_ID else self._get_display_name(inviter_id)
                        action_text = f"🔗 User joined via link: {user_label} (by {inviter_label})"
                        action_type = "invite_join"
                        gate_toggle = "toggle_invites"
            elif event.user_left and is_bot:
                action_text = f"🤖 Bot left: {user_label}"
                action_type = "bot_leave"
                gate_toggle = "toggle_bots"
            elif event.user_kicked and is_bot:
                action_text = f"🤖 Bot removed: {user_label}"
                if admin_id:
                    action_text += f" (by {self._get_display_name(admin_id)})"
                action_type = "bot_kick"
                gate_toggle = "toggle_bots"

            # Invite link lifecycle events ride on the same ChatAction event shape
            if getattr(event, "created_invite", None):
                invite = event.created_invite
                action_text = "🔗 Invite link created"
                if getattr(invite, "usage_limit", None):
                    action_text += f" (limit: {invite.usage_limit} uses)"
                action_type = "invite_created"
                gate_toggle = "toggle_invites"
            elif getattr(event, "revoked_invite", None):
                action_text = "🔗 Invite link revoked"
                action_type = "invite_revoked"
                gate_toggle = "toggle_invites"

            if not action_text or not gate_toggle:
                return
            if not config.get(gate_toggle, True):
                return

            await self.audit.log_event({
                "event_id": str(uuid.uuid4()),
                "ts_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "chat_id": chat_id,
                "event_type": action_type,
                "actor_user_id": admin_id,
                "target_user_id": user_id,
                "summary": action_text
            })

            backup_id = config.get("backup_chat_id")
            if backup_id:
                try:
                    await self.client.send_message(backup_id, action_text)
                except Exception as e:
                    logger.warning(f"Failed to mirror member event for user {user_id}: {e}")
        except Exception as e:
            logger.error(f"Member event extras handler error: {e}")

    async def _handle_invite_join(self, event):
        """Attributes a join to the specific invite link/creator used, via the raw
        UpdateChatInviteImporter update (distinct from the plain ChatAction join event)."""
        try:
            chat_id = None
            peer = getattr(event, "peer", None)
            if peer is not None:
                chat_id = tl_utils.get_peer_id(peer)
            if chat_id is None:
                return

            if not self.config_mgr.is_monitored(chat_id):
                return
            config = self.config_mgr.get_config(chat_id)
            if not config.get("toggle_invites", True):
                return

            user_id = getattr(event, "user_id", None)
            if not user_id:
                return

            # The ChatAction-embedded link detection fires separately for the same join;
            # only one of the two handlers should notify.
            if not self._claim_invite_join(chat_id, user_id):
                return

            admin_id = None
            invite = getattr(event, "invite", None)
            if invite is not None:
                admin_id = getattr(invite, "admin_id", None)

            action_text = f"🔗 User joined via invite: {self._get_display_name(user_id)}"
            if admin_id:
                action_text += f" (link by {self._get_display_name(admin_id)})"

            await self.audit.log_event({
                "event_id": str(uuid.uuid4()),
                "ts_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "chat_id": chat_id,
                "event_type": "invite_join",
                "actor_user_id": admin_id,
                "target_user_id": user_id,
                "summary": action_text
            })

            backup_id = config.get("backup_chat_id")
            if backup_id:
                try:
                    await self.client.send_message(backup_id, action_text)
                except Exception as e:
                    logger.warning(f"Failed to mirror invite join for user {user_id}: {e}")
        except Exception as e:
            logger.error(f"Invite join handler error: {e}")

    async def _handle_raw_update(self, event):
        # Cheap filter first: events.Raw() fires for every update Telegram sends.
        if isinstance(event, (tl_types.UpdateMessageReactions, tl_types.UpdateBotMessageReaction)):
            await self._handle_reaction_update(event)
        elif isinstance(event, (tl_types.UpdateChannelParticipant, tl_types.UpdateChatParticipant)):
            await self._handle_participant_update(event)
        elif UpdateChatInviteImporter is not None and isinstance(event, UpdateChatInviteImporter):
            await self._handle_invite_join(event)

    async def _handle_reaction_update(self, event):
        try:
            chat_id = None
            if hasattr(event, "peer") and event.peer is not None:
                chat_id = tl_utils.get_peer_id(event.peer)
            elif hasattr(event, "peer_id") and event.peer_id is not None:
                chat_id = tl_utils.get_peer_id(event.peer_id)
            if chat_id is None:
                return

            if not self.config_mgr.is_monitored(chat_id):
                return
            config = self.config_mgr.get_config(chat_id)
            if not config.get("toggle_reactions", True):
                return

            msg_id = getattr(event, "msg_id", None)
            if not msg_id:
                return

            # Collect (user_id, emoji) pairs from whichever update shape fired
            reactions_to_process = []
            if isinstance(event, tl_types.UpdateMessageReactions):
                recent = getattr(event.reactions, "recent_reactions", []) or []
                for r in recent:
                    uid = tl_utils.get_peer_id(r.peer_id)
                    emoji = str(getattr(r.reaction, "emoticon", "❤️"))
                    reactions_to_process.append((uid, emoji))
            elif isinstance(event, tl_types.UpdateBotMessageReaction):
                uid = tl_utils.get_peer_id(event.actor_id)
                emoji = str(getattr(event.reaction, "emoticon", "❤️"))
                reactions_to_process.append((uid, emoji))

            if not reactions_to_process:
                return

            # Dedup per (msg_id, user_id): only act when the reaction actually changed
            emoji_groups: Dict[str, List[int]] = {}
            for uid, emoji in reactions_to_process:
                state_key = (msg_id, uid)
                if self.reaction_state.get(state_key) == emoji:
                    continue
                self.reaction_state[state_key] = emoji
                if len(self.reaction_state) > 1000:
                    for k in list(self.reaction_state.keys())[:500]:
                        self.reaction_state.pop(k, None)
                emoji_groups.setdefault(emoji, []).append(uid)
                self._record_user_seen(uid)  # cheap: no extra API call, just marks them seen

            if not emoji_groups:
                return

            backup_id = config.get("backup_chat_id")
            dest_msg_id = self._get_dest_message_id(chat_id, msg_id)

            for emoji, uids in emoji_groups.items():
                authors_str = ", ".join(self._get_display_name(u) for u in uids)

                await self.audit.log_event({
                    "event_id": str(uuid.uuid4()),
                    "ts_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "chat_id": chat_id,
                    "event_type": "reaction",
                    "actor_user_id": uids[0],
                    "message_id": msg_id,
                    "reaction": emoji,
                    "authors": uids
                })

                if backup_id and dest_msg_id:
                    try:
                        await self.client.send_message(
                            backup_id,
                            f"{emoji} Reaction (by {authors_str})",
                            reply_to=dest_msg_id
                        )
                    except Exception as e:
                        logger.warning(f"Failed to mirror reaction for msg {msg_id}: {e}")
        except Exception as e:
            logger.error(f"Reaction handler error: {e}")

    @staticmethod
    def _is_admin_participant(p):
        return isinstance(p, (tl_types.ChannelParticipantAdmin, tl_types.ChatParticipantAdmin))

    @staticmethod
    def _is_banned_participant(p):
        return isinstance(p, tl_types.ChannelParticipantBanned)

    async def _handle_participant_update(self, event):
        """Mirrors promote/demote/ban/restrict/unrestrict actions. Gated by the existing
        toggle_admin (promote/demote) and toggle_restrict (ban/restrict/unrestrict) columns,
        which previously existed in the schema/dashboard with no handler behind them."""
        try:
            chat_id = None
            if isinstance(event, tl_types.UpdateChannelParticipant):
                chat_id = event.channel_id
            elif isinstance(event, tl_types.UpdateChatParticipant):
                chat_id = event.chat_id
            if chat_id is None:
                return

            if not self.config_mgr.is_monitored(chat_id):
                return
            config = self.config_mgr.get_config(chat_id)

            user_id = getattr(event, "user_id", None)
            actor_id = getattr(event, "actor_id", None)
            if not user_id:
                return

            old_participant = getattr(event, "prev_participant", None)
            new_participant = getattr(event, "new_participant", None)

            user_label = self._get_display_name(user_id)
            actor_label = self._get_display_name(actor_id) if actor_id else None

            action_text = None
            action_type = None
            gate_toggle = None

            if self._is_admin_participant(new_participant) and (not old_participant or not self._is_admin_participant(old_participant)):
                action_text = f"👑 Promoted to admin: {user_label}" + (f" (by {actor_label})" if actor_label else "")
                action_type = "promote"
                gate_toggle = "toggle_admin"
            elif self._is_admin_participant(old_participant) and (not new_participant or not self._is_admin_participant(new_participant)):
                action_text = f"👤 Demoted from admin: {user_label}" + (f" (by {actor_label})" if actor_label else "")
                action_type = "demote"
                gate_toggle = "toggle_admin"
            elif self._is_banned_participant(new_participant):
                rights = getattr(new_participant, "banned_rights", None)
                if rights and rights.view_messages:
                    action_text = f"🚫 Banned: {user_label}" + (f" (by {actor_label})" if actor_label else "")
                    action_type = "ban"
                    gate_toggle = "toggle_restrict"
                elif rights:
                    restrictions = []
                    if rights.send_messages: restrictions.append("send messages")
                    if rights.send_media: restrictions.append("send media")
                    if rights.send_stickers: restrictions.append("send stickers")
                    if rights.send_polls: restrictions.append("send polls")
                    if restrictions:
                        action_text = f"⚠️ Restricted: {user_label} (cannot {', '.join(restrictions)})" + (f" (by {actor_label})" if actor_label else "")
                        action_type = "restrict"
                        gate_toggle = "toggle_restrict"
            elif self._is_banned_participant(old_participant) and new_participant and not self._is_banned_participant(new_participant):
                action_text = f"✅ Unrestricted: {user_label}" + (f" (by {actor_label})" if actor_label else "")
                action_type = "unrestrict"
                gate_toggle = "toggle_restrict"

            if not action_text or not gate_toggle:
                return
            if not config.get(gate_toggle, True):
                return

            await self.audit.log_event({
                "event_id": str(uuid.uuid4()),
                "ts_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "chat_id": chat_id,
                "event_type": action_type,
                "actor_user_id": actor_id,
                "target_user_id": user_id,
                "summary": action_text
            })

            backup_id = config.get("backup_chat_id")
            if backup_id:
                try:
                    await self.client.send_message(backup_id, action_text)
                except Exception as e:
                    logger.warning(f"Failed to mirror participant change for user {user_id}: {e}")
        except Exception as e:
            logger.error(f"Participant handler error: {e}")

    async def process_event(self, telethon_event, event_type: str):
        """
        Central processor: Intake -> Normalize -> Toggle check -> Action -> Log
        """
        try:
            # 0. Context & Scope Check
            # deletions don't have .chat usually in the event object same way, check docs
            # For simplicity in Phase 2, we try to grab chat_id safely
            chat_id = getattr(telethon_event, "chat_id", None)
            
            # If deleted event, it might be in func of the event
            if not chat_id and hasattr(telethon_event, "chats"):
                # For bulk deletes, we might process differently, but let's grab the first one for now
                if telethon_event.chats:
                    chat_id = telethon_event.chats[0]
            
            if not chat_id:
                return # Can't process without context
                
            # 1. Toggle Check (Fast Fail - Gate 0)
            if not self.config_mgr.is_monitored(chat_id):
                return
                
            config = self.config_mgr.get_config(chat_id)

            # 2. Granular Gates per Event Type
            should_log = False
            should_action = False
            
            if event_type == "message_new":
                # Gate: toggle_log_new AND toggle_mirror_new
                should_log = config.get("toggle_log_new", True)
                should_action = config.get("toggle_mirror_new", True)
                
            elif event_type == "message_edit":
                should_log = config.get("toggle_edits", True)
                
            elif event_type == "message_delete":
                should_log = config.get("toggle_deletes", True)
                
            elif event_type in ["user_join", "user_leave"]:
                # Gate with toggle_joins
                should_log = config.get("toggle_joins", True)

            # Fast output if nothing to do
            if not should_log and not should_action:
                return

            # 3. Normalize Event
            # If we need to log OR act, we need the event object.
            normalized_event = await self._normalize_event(telethon_event, event_type, chat_id)
            if not normalized_event:
                return

            # 4. Action Execution (Mirroring)
            if event_type == "message_new" and should_action:
                asyncio.create_task(self.mirror_message(telethon_event, config))
            
            # 5. Logging Execution
            if should_log:
                await self.audit.log_event(normalized_event)
            
        except Exception as e:
            logger.error(f"Error processing {event_type}: {e}")

    async def _config_refresh_loop(self):
        """Periodically refresh config if bump timestamp changes."""
        last_known_bump = "0"
        while True:
            await asyncio.sleep(2) # Poll every 2s
            try:
                current_bump = self.config_mgr.get_last_bump()
                if current_bump != last_known_bump:
                    logger.info(f"Config bump detected ({last_known_bump} -> {current_bump}). Refreshing...")
                    self.config_mgr.refresh_config_cache()
                    last_known_bump = current_bump
            except Exception as e:
                logger.error(f"Config refresh failed: {e}")

    async def _normalize_event(self, event, event_type: str, chat_id: int) -> Optional[Dict[str, Any]]:
        """
        Convert Telethon event to Canonical JSON Schema
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        
        base_event = {
            "event_id": str(uuid.uuid4()),
            "ts_utc": now.isoformat(),
            "chat_id": chat_id,
            "event_type": event_type,
            "actor_user_id": None,
            "target_user_id": None,
            "message_id": None,
            "text": None,
            "media_meta": {}
        }
        
        # Populate specific fields
        if event_type == "message_new":
            msg = event.message
            base_event["message_id"] = msg.id
            base_event["actor_user_id"] = msg.sender_id
            base_event["text"] = msg.text
            base_event["media_meta"] = self._get_media_meta(msg.media)
            
            # Cache for future edits/deletes
            self._cache_message(chat_id, msg.id, msg.text, msg.media)

        elif event_type == "message_edit":
            msg = event.message
            base_event["message_id"] = msg.id
            base_event["actor_user_id"] = msg.sender_id
            base_event["text_after"] = msg.text
            base_event["media_meta"] = self._get_media_meta(msg.media)
            
            # Retrieve cached version OR DB Fallback
            cached = self._get_message_from_cache_or_db(chat_id, msg.id)
            if cached:
                base_event["text_before"] = cached["text"]
                # Compute Diff
                conf = self.config_mgr.get_config(chat_id)
                diff_mode = conf.get("diff_mode", "word")
                base_event["diff"] = self._get_diff(cached["text"], msg.text, diff_mode)
            else:
                 base_event["text_before"] = None
                 base_event["diff"] = None
                 
            # Update cache
            self._cache_message(chat_id, msg.id, msg.text, msg.media)

        elif event_type == "message_delete":
             # deleted_ids is a list
             base_event["message_ids"] = event.deleted_ids
             base_event["message_id"] = event.deleted_ids[0] if event.deleted_ids else None
             
             # Attempt recovery on first ID
             if event.deleted_ids:
                msg_id = event.deleted_ids[0]
                cached = self._get_message_from_cache_or_db(chat_id, msg_id)
                if cached:
                    base_event["text_before"] = cached["text"] # Recovered text
                    base_event["media_meta"] = cached["media_meta"]

        elif event_type in ["user_join", "user_leave"]:
            base_event["actor_user_id"] = event.user_id
            if event.user_added or event.user_kicked:
                 base_event["actor_user_id"] = event.action_message.sender_id
                 base_event["target_user_id"] = event.user_id
        
        return base_event

    async def mirror_message(self, event, config: Dict[str, Any]):
        """
        Mirroring Strategy:
        0. If this message replies to one we've already mirrored, COPY it threaded onto the
           mirrored parent (Telegram's forward_messages can't carry reply_to, so a reply must
           be copied, not forwarded - this is the only way to preserve the thread visually).
           If the parent isn't in our map (evicted/never mirrored), fall through to (1) and
           post a "replying to old/missing message" note alongside it instead.
        1. Default behavior: FORWARD message to backup_chat
        2. If forward fails: Retry once after short delay.
        3. If retry fails: Fallback to COPY (send_message with file=media).
        """
        backup_id = config.get("backup_chat_id")
        if not backup_id:
            logger.warning(f"Skipping mirroring for {event.chat_id}: monitored=True but backup_chat_id is missing.")
            return

        reply_to_dst_id = None
        reply_context_note = None
        if event.message.reply_to:
            reply_to_src_id = event.message.reply_to.reply_to_msg_id
            if reply_to_src_id:
                reply_to_dst_id = self._get_dest_message_id(event.chat_id, reply_to_src_id)
                if not reply_to_dst_id:
                    reply_context_note = "↪️ Replying to an old/missing message"

        if reply_to_dst_id:
            try:
                if event.message.media:
                    sent = await self.client.send_file(
                        backup_id,
                        event.message.media,
                        caption=event.message.text,
                        reply_to=reply_to_dst_id
                    )
                else:
                    sent = await self.client.send_message(
                        backup_id,
                        event.message.text or "",
                        reply_to=reply_to_dst_id
                    )
                self._record_mirror_result(event.chat_id, event.id, self._extract_sent_id(sent))
                return
            except Exception as e:
                logger.warning(f"Threaded reply copy failed for {event.id}: {e}. Falling back to forward.")
                # Falls through to the standard forward/retry/copy path below.

        try:
            # 1. Try Forward
            sent = await self.client.forward_messages(backup_id, event.message)
            self._record_mirror_result(event.chat_id, event.id, self._extract_sent_id(sent))
        except Exception as e:
            logger.warning(f"Forward failed for {event.id}: {e}. Retrying...")
            # 2. Retry
            await asyncio.sleep(1)
            try:
                sent = await self.client.forward_messages(backup_id, event.message)
                self._record_mirror_result(event.chat_id, event.id, self._extract_sent_id(sent))
            except Exception as e2:
                logger.warning(f"Retry forward failed for {event.id}: {e2}. Fallback to COPY.")

                # 3. Fallback to Copy
                try:
                    # 3. Fallback to Copy
                    if event.message.media:
                        # Send file explicitly with caption
                        sent = await self.client.send_file(
                            backup_id,
                            event.message.media,
                            caption=event.message.text,
                            reply_to=None
                        )
                    else:
                        # Just text
                        sent = await self.client.send_message(
                            backup_id,
                            event.message.text,
                            reply_to=None
                        )
                    self._record_mirror_result(event.chat_id, event.id, self._extract_sent_id(sent))

                    # 4. Log Fallback
                    await self.audit.log_event({
                        "event_type": "mirror_fallback_copy",
                        "ts_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        "chat_id": event.chat_id,
                        "message_id": event.id,
                        "message_id": event.id,
                        "error": str(e2)
                    })
                except Exception as e3:
                    logger.error(f"Copy fallback failed for {event.id}: {e3}")
                    # Log critical failure
                    await self.audit.log_event({
                        "event_type": "mirror_failed_total",
                        "ts_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        "chat_id": event.chat_id,
                        "message_id": event.id,
                        "error": str(e3)
                    })

        if reply_context_note:
            dest_id = self._get_dest_message_id(event.chat_id, event.id)
            if dest_id:
                try:
                    await self.client.send_message(backup_id, reply_context_note, reply_to=dest_id)
                except Exception as e:
                    logger.warning(f"Failed to post reply-context note for {event.id}: {e}")

    @staticmethod
    def _extract_sent_id(sent) -> Optional[int]:
        """forward_messages can return a single Message or a list; send_file/send_message
        always return a single Message. Normalize to the destination message id."""
        if sent is None:
            return None
        if isinstance(sent, list):
            return sent[0].id if sent else None
        return getattr(sent, "id", None)
        


def select_session():
    """Interactive session selector"""
    # 1. Look for 'sessions' folder
    sessions_dir = Path("sessions")
    if not sessions_dir.exists():
        # Fallback to checking root or data dir? 
        # User specifically said "folder session", so likely "sessions"
        return None

    files = list(sessions_dir.glob("*.session"))
    if not files:
        return None

    print("\nAvailable Sessions:")
    for idx, f in enumerate(files):
        print(f"{idx + 1}. {f.stem}")
    
    print(f"{len(files) + 1}. Use Default (.env)")
    
    while True:
        try:
            choice = input(f"\nSelect Session (1-{len(files) + 1}): ")
            if not choice.strip(): continue
            val = int(choice)
            
            if val == len(files) + 1:
                return None # Use default
                
            if 1 <= val <= len(files):
                # Return path without extension, relative to CWD
                # Telethon adds .session
                selected = files[val-1]
                # We return "sessions/filename" (stripped)
                return str(selected.with_suffix(''))
                
        except ValueError:
            pass
        print("Invalid selection.")

async def main():
    # Try selection
    selected_session = None
    try:
        # Only run interactive if in terminal (stdin isatty check is good usually, but direct assume for now)
        selected_session = select_session()
    except Exception as e:
        logger.warning(f"Session selection skipped: {e}")

    runner = GhostRunner(session_name=selected_session)
    await runner.start()

if __name__ == "__main__":
    asyncio.run(main())
