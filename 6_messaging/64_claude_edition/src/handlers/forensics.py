import os
import asyncio
from telethon import types
from src.handlers.base import BaseHandler
from src.config.settings import DELETION_CHECK_INTERVAL, NOTIFY_DELETIONS
from src.core.logger import log_error, log_to_disk, get_now, console
from telethon.errors import FloodWaitError

class ForensicsHandler(BaseHandler):
    async def register(self):
        # Starts the background task
        asyncio.create_task(self.bg_ghost_check())

    async def bg_ghost_check(self):
        """Background deletion checker - optimized to 60s interval."""
        while True:
            await asyncio.sleep(DELETION_CHECK_INTERVAL)
            # Use list() to iterate over keys safely if map changes
            current_pairs = list(self.state.mirror_map.items())
            
            for peer_id, pair in current_pairs:
                if not pair.history_ids: continue
                batch = list(pair.history_ids)[-50:]
                try:
                    results = await self.client.get_messages(pair.source_entity, ids=batch)
                    
                    for i, m_obj in enumerate(results):
                        is_deleted = False
                        if m_obj is None: is_deleted = True
                        elif isinstance(m_obj, types.MessageEmpty): is_deleted = True
                        elif hasattr(m_obj, 'deleted') and m_obj.deleted: is_deleted = True
                        elif hasattr(m_obj, 'message') and m_obj.message is None: is_deleted = True
                        
                        if is_deleted:
                            orig_id = batch[i]
                            if orig_id in pair.msg_map:
                                mirrored_m, sender, old_text = pair.msg_map[orig_id]
                                
                                # Always log to disk
                                log_to_disk("delete", {
                                    "source_chat_id": pair.source_id,
                                    "source_chat_title": pair.source_title,
                                    "src_msg_id": orig_id,
                                    "dst_chat_id": pair.dest_id,
                                    "dst_msg_id": mirrored_m.id,
                                    "sender_name": sender,
                                    "cached_text": old_text
                                })
                                
                                # Only send notification if enabled
                                if NOTIFY_DELETIONS:
                                    alert = (
                                        f"❌ **DELETED MESSAGE**\n"
                                        f"👤 **From:** @{sender}\n"
                                        f"📝 **Content was:**\n"
                                        f"_{old_text or '[Media/No Text]'}_\n"
                                    )
                                    try:
                                        await self.client.send_message(pair.dest_entity, alert, reply_to=mirrored_m.id)
                                    except FloodWaitError as e:
                                        await self.handle_flood_wait(e, "deletion_alert")
                                    except Exception as e:
                                        try:
                                            await self.client.send_message(pair.dest_entity, alert)
                                        except Exception as e2:
                                            log_error("deletion_alert_fallback", str(e2))
                                    
                                    session_name = "Ghost"
                                    if hasattr(self.client.session, 'filename'):
                                        session_name = os.path.basename(self.client.session.filename).replace('.session', '')
                                    
                                    console.print(f"[bold cyan]{session_name}[/bold cyan][{get_now().strftime('%H:%M:%S')}] 🗑️ [red]Deleted in {pair.source_title}:[/red] @{sender}")
                                
                                pair.msg_map.pop(orig_id, None)
                except FloodWaitError as e:
                    await self.handle_flood_wait(e, "deletion_check")
                except Exception as e:
                    log_error("deletion_check", str(e))
