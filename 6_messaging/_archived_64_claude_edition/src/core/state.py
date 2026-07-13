
"""
FILE: src/core/state.py
PURPOSE: Database for managing runtime state (cached messages, active pairs).
IMPROVEMENTS: Handles automatic updates to mirrors.json if a group ID changes (migration).
"""
import os
import json
from collections import deque
from telethon import utils # telethon utils
from src.config.settings import MAX_HISTORY_SIZE
from src.config.loader import save_config
from src.core.storage import save_json_atomic, ensure_dir

class GhostPair:
    def __init__(self, source_id, dest_id, source_title, dest_title):
        self.source_id = source_id
        self.peer_id = None
        self.dest_id = dest_id
        self.source_title = source_title
        self.dest_title = dest_title
        self.source_entity = None
        self.dest_entity = None
        
        # Forensics tracking: {orig_id: (mirrored_msg_obj, sender_name, captured_text)}
        # We store mirrored_msg_id instead of object for easy serialization
        self.msg_map = {} 
        self.history_ids = deque(maxlen=MAX_HISTORY_SIZE)
        
        # Date Separator Tracking
        self.last_separator_date = None

    def add_to_history(self, orig_id, mirrored_msg, sender, text):
        """Adds message to history and saves to disk."""
        if len(self.history_ids) >= MAX_HISTORY_SIZE:
            oldest = self.history_ids[0] if self.history_ids else None
            if oldest and oldest in self.msg_map:
                self.msg_map.pop(oldest, None)
        
        self.history_ids.append(orig_id)
        # Store just the ID and basic metadata for persistence
        self.msg_map[orig_id] = {
            "id": mirrored_msg.id,
            "sender": sender,
            "text": text
        }
        self.save_history()

    def save_history(self):
        """Persists msg_map to data/history/ folder."""
        history_dir = os.path.join("data", "history")
        ensure_dir(history_dir)
        file_path = os.path.join(history_dir, f"{self.source_id}.json")
        save_json_atomic(file_path, {
            "msg_map": {str(k): v for k, v in self.msg_map.items()},
            "history_ids": list(self.history_ids),
            "last_separator_date": self.last_separator_date
        })

    def load_history(self):
        """Loads msg_map from data/history/ folder."""
        file_path = os.path.join("data", "history", f"{self.source_id}.json")
        if not os.path.exists(file_path):
            return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Convert string keys back to int
                self.msg_map = {int(k): v for k, v in data.get("msg_map", {}).items()}
                self.history_ids = deque(data.get("history_ids", []), maxlen=MAX_HISTORY_SIZE)
                self.last_separator_date = data.get("last_separator_date")
        except Exception:
            pass

# Global State Container
class StateManager:
    def __init__(self):
        self.mirror_map = {}
        self.source_peers = []
        self.pairs_data = [] # Keep a reference to the loaded data for updating

    def load_pairs(self, client, pairs_data, console=None):
        import asyncio
        self.pairs_data = pairs_data
        start_tasks = []
        
        async def load_pair(p):
            try:
                # Load Source Entity
                raw_source_id = p['source_id']
                source_entity = await client.get_entity(raw_source_id)
                resolved_id = utils.get_peer_id(source_entity)
                
                # Check for Migration
                if resolved_id != raw_source_id:
                    if console:
                        console.print(f"[yellow]⚠️ Migration Detected: {p['source_title']} ID changed {raw_source_id} -> {resolved_id}. Updating config...[/yellow]")
                    p['source_id'] = resolved_id
                    save_config(self.pairs_data)
                
                pair = GhostPair(p['source_id'], p['dest_id'], p['source_title'], p['dest_title'])
                
                # Load History from Disk
                pair.load_history()
                
                # Get Input Entities
                try:
                    pair.source_entity = await client.get_input_entity(source_entity)
                except:
                    pair.source_entity = await client.get_input_entity(p['source_id'])

                try:
                    dest_ent = await client.get_entity(p['dest_id'])
                    pair.dest_entity = await client.get_input_entity(dest_ent)
                except Exception as e:
                    try:
                        pair.dest_entity = await client.get_input_entity(p['dest_id'])
                    except:
                        raise Exception(f"Could not resolve destination entity {p['dest_id']}. Error: {e}")

                pair.peer_id = resolved_id 
                self.mirror_map[pair.peer_id] = pair
                self.source_peers.append(pair.source_entity)
                if console:
                    console.print(f"👻 [bold green]Active:[/bold green] {pair.source_title}")
            except Exception as e:
                if console:
                    console.print(f"[red]Failed to load pair {p.get('source_title', 'Unknown')}:[/red] {e}")

        for p in pairs_data:
            start_tasks.append(load_pair(p))
            
        return start_tasks

    def get_pair(self, chat_id):
        return self.mirror_map.get(chat_id)
