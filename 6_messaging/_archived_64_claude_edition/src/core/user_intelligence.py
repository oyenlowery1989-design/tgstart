
"""
FILE: src/core/user_intelligence.py
PURPOSE: Handles User Index, Bio Fetching, and Sighting tracking.
"""
import os
import json
import asyncio
import traceback
from telethon import functions
from telethon.errors import FloodWaitError

from src.core.logger import log_error, get_now, DATA_DIR
from src.core.storage import ensure_dir, save_json_atomic
from src.config.settings import MAX_BIO_QUEUE_SIZE, BIO_WORKER_DELAY

# Paths
USERS_DIR = os.path.join(DATA_DIR, "users")
USERS_SEEN_FILE = os.path.join(USERS_DIR, "users_seen.jsonl")
USERS_INDEX_FILE = os.path.join(USERS_DIR, "users_index.json")

# In-Memory Cache
users_index_cache = {}
processed_bios = set()
bio_fetch_queue = asyncio.Queue()

def load_users_index():
    global users_index_cache
    ensure_dir(USERS_DIR)
    if os.path.exists(USERS_INDEX_FILE):
        try:
            with open(USERS_INDEX_FILE, 'r', encoding='utf-8') as f:
                users_index_cache = json.load(f)
        except Exception as e:
            log_error("users_index_load", str(e), traceback.format_exc())
            users_index_cache = {}
    else:
        users_index_cache = {}
    
    # Populate processed bios set
    for k, v in users_index_cache.items():
        if v.get("bio_fetched"):
            processed_bios.add(k)

def update_user_index(key, username, display_name, phone=None, lang_code=None, bio=None, verified=None, scam=None, fake=None, seen_in=None):
    """
    Updates the global index if info is new/changed.
    """
    changed = False
    
    if key not in users_index_cache:
        users_index_cache[key] = {
            "username": username,
            "display_name": display_name,
            "added_at": get_now().isoformat(),
            "seen_in": []
        }
        changed = True
    
    curr = users_index_cache[key]
    
    def update_field(field, value):
        nonlocal changed
        if value is not None and curr.get(field) != value:
            curr[field] = value
            changed = True

    update_field("username", username)
    update_field("display_name", display_name)
    update_field("phone", phone)
    update_field("lang_code", lang_code)
    update_field("bio", bio)
    update_field("verified", verified)
    update_field("scam", scam)
    update_field("fake", fake)

    if seen_in:
        current_chats = set(curr.get("seen_in", []))
        if seen_in not in current_chats:
            current_chats.add(seen_in)
            curr["seen_in"] = list(current_chats)
            changed = True

    if bio is not None:
        curr["bio_fetched"] = True
        processed_bios.add(key)
        changed = True

    if changed:
        save_json_atomic(USERS_INDEX_FILE, users_index_cache)

async def bio_worker(client):
    """
    Background worker that fetches full user profiles.
    """
    from src.core.logger import console 
    while True:
        try:
            user_id_str = await bio_fetch_queue.get()
            
            if user_id_str in processed_bios:
                bio_fetch_queue.task_done()
                continue
                
            try:
                from telethon import utils # Hidden import to avoid circulars if any
                uid = int(user_id_str) if user_id_str.isdigit() else user_id_str
                full_user_result = await client(functions.users.GetFullUserRequest(uid))
                
                user_obj = full_user_result.users[0] if full_user_result.users else None
                about = getattr(full_user_result.full_user, 'about', None)
                
                if user_obj:
                    username = getattr(user_obj, 'username', None)
                    first = getattr(user_obj, 'first_name', '') or ''
                    last = getattr(user_obj, 'last_name', '') or ''
                    display = (f"{first} {last}").strip() or username or "Unknown"
                    phone = getattr(user_obj, 'phone', None)
                    verified = getattr(user_obj, 'verified', False)
                    scam = getattr(user_obj, 'scam', False)
                    fake = getattr(user_obj, 'fake', False)
                    lang = getattr(user_obj, 'lang_code', None)

                    update_user_index(user_id_str, username, display, phone=phone, lang_code=lang, bio=about, verified=verified, scam=scam, fake=fake)
                else:
                    update_user_index(user_id_str, None, None, bio=about)
                
            except FloodWaitError as e:
                wait_time = e.seconds if hasattr(e, 'seconds') else 60
                console.print(f"[yellow]⏳ Bio FloodWait: Sleeping {wait_time}s[/yellow]")
                await asyncio.sleep(wait_time)
                bio_fetch_queue.put_nowait(user_id_str)
            except Exception as e:
                log_error("bio_fetch", f"Failed for {user_id_str}: {e}")
            
            bio_fetch_queue.task_done()
            await asyncio.sleep(BIO_WORKER_DELAY)
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            log_error("bio_worker", str(e), traceback.format_exc())
            await asyncio.sleep(1)

def record_user_seen_sender(chat_id, chat_title, sender, ts_dt):
    uid = str(getattr(sender, 'id', None))
    if not uid or uid == 'None': return

    is_new = True
    if uid in users_index_cache:
        if str(chat_id) in users_index_cache[uid].get("seen_in", []):
            is_new = False
    
    username = getattr(sender, 'username', None)
    first = getattr(sender, 'first_name', '') or ''
    last = getattr(sender, 'last_name', '') or ''
    display = (f"{first} {last}").strip() or username or "Unknown"

    update_user_index(uid, username, display, 
                    phone=getattr(sender, 'phone', None), 
                    lang_code=getattr(sender, 'lang_code', None), 
                    verified=getattr(sender, 'verified', False), 
                    scam=getattr(sender, 'scam', False), 
                    fake=getattr(sender, 'fake', False), 
                    seen_in=str(chat_id))

    if is_new:
        entry = {
            "type": "sender", "ts": ts_dt.isoformat(),
            "source_chat_id": chat_id, "source_chat_title": chat_title,
            "user_id": uid, "username": username, "display_name": display, "phone": getattr(sender, 'phone', None)
        }
        try:
            with open(USERS_SEEN_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            log_error("user_seen_log", str(e))
    
    if uid not in processed_bios and bio_fetch_queue.qsize() < MAX_BIO_QUEUE_SIZE:
        bio_fetch_queue.put_nowait(uid)

def record_user_seen_mention(chat_id, chat_title, username_raw, ts_dt):
    clean_user = username_raw.lstrip('@')
    key = f"@{clean_user}"
    
    is_new = True
    if key in users_index_cache:
        if str(chat_id) in users_index_cache[key].get("seen_in", []):
            is_new = False
            
    update_user_index(key, clean_user, None, seen_in=str(chat_id))

    if is_new:
        entry = {
            "type": "mention", "ts": ts_dt.isoformat(),
            "source_chat_id": chat_id, "source_chat_title": chat_title,
            "username": clean_user, "raw": username_raw
        }
        try:
            with open(USERS_SEEN_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            log_error("mention_log", str(e))

def get_user_info_string(uid_str):
    if uid_str not in users_index_cache:
        return f"User {uid_str}"
    u = users_index_cache[uid_str]
    name, uname = u.get("display_name"), u.get("username")
    if name and uname: return f"{name} (@{uname})"
    if name: return f"{name} (ID: {uid_str})"
    if uname: return f"@{uname} (ID: {uid_str})"
    return f"User {uid_str}"
