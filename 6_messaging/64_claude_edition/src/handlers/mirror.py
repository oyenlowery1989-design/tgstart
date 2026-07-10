import os
import traceback
from telethon import events, types
from src.handlers.base import BaseHandler
from src.config.settings import NOTIFY_NEW_MESSAGES, NOTIFY_EDITS
from src.core.logger import log_error, log_to_disk, get_now, console
from src.core.database import record_user_seen_sender, record_user_seen_mention
from src.utils.text_utils import extract_mentions, generate_diff_text
from telethon.errors import FloodWaitError

class MirrorHandler(BaseHandler):
    async def register(self):
        # We need to register on all source peers
        # But peers are loaded dynamically. Telethon accepts a list of entities (or inputs)
        # However, if we pass a mutable list, does it update? No, Telethon filters at setup.
        # BUT: client.on(events.NewMessage(chats=...)) checks chats every time if it's a callable or always triggers if chats=None 
        # and we filter inside. Let's filter inside to be dynamic.
        
        @self.client.on(events.NewMessage())
        async def new_message_handler(event):
            # Dynamic check
            chat_id = event.chat_id
            pair = self.state.get_pair(chat_id)
            if not pair: return 
            
            try:
                now_chi = get_now()
                today_str = now_chi.strftime("%Y-%m-%d")
                
                # Date Separator
                if pair.last_separator_date != today_str:
                    day_name = now_chi.strftime("%a")
                    sep_text = f"────────── {today_str} ({day_name}) ──────────"
                    
                    try:
                        await self.client.send_message(pair.dest_entity, sep_text)
                    except FloodWaitError as e:
                        await self.handle_flood_wait(e, "date_separator")
                    except Exception as e:
                        log_error("date_separator", str(e))
                    
                    pair.last_separator_date = today_str
                    log_to_disk("separator", {
                        "source_chat_id": pair.source_id,
                        "dst_chat_id": pair.dest_id,
                        "text": sep_text
                    })

                # Sender Info
                sender = await event.get_sender()
                if not sender:
                     sender_name = "Unknown"
                     sender_id = event.sender_id if hasattr(event, 'sender_id') else 0
                else:
                     sender_name = getattr(sender, 'username', None) or getattr(sender, 'first_name', 'User')
                     sender_id = getattr(sender, 'id', None)

                # User Capture
                record_user_seen_sender(pair.source_id, pair.source_title, sender, now_chi)
                
                mentions = extract_mentions(event.message)
                for m in mentions:
                    record_user_seen_mention(pair.source_id, pair.source_title, m, now_chi)

                # Reply Logic
                reply_to_dst_id = None
                reply_to_src_id = None
                reply_context_msg = None
                
                if event.message.reply_to:
                    parent_id = event.message.reply_to.reply_to_msg_id
                    reply_to_src_id = parent_id
                    
                    if parent_id in pair.msg_map:
                        reply_to_dst_id = pair.msg_map[parent_id][0].id
                    else:
                        reply_context_msg = f"↪️ **Replying to old/missing message**"

                # Mirror Logic with improved media handling
                mirrored = None
                try:
                    if reply_to_dst_id:
                         # forward_messages does not support reply_to, so we must forward without it
                         # or use send_message with reply.
                        mirrored = await self.client.forward_messages(pair.dest_entity, event.message)
                    else:
                        mirrored = await self.client.forward_messages(pair.dest_entity, event.message)
                except FloodWaitError as e:
                    await self.handle_flood_wait(e, "message_forward")
                    # Retry after flood wait
                    try:
                        mirrored = await self.client.forward_messages(pair.dest_entity, event.message)
                    except Exception as e2:
                        log_error("message_forward_retry", str(e2))
                except Exception as e:
                    log_error("message_forward", str(e))
                    try:
                        # Fallback to send_message
                        msg_text = event.message.message or "[Media]"
                        mirrored = await self.client.send_message(pair.dest_entity, f"👤 **@{sender_name}:**\n{msg_text}")
                    except Exception as e2:
                        log_error("message_send_fallback", str(e2))

                mirrored_msg = mirrored[0] if isinstance(mirrored, list) else mirrored
                
                if mirrored_msg:
                    if reply_context_msg:
                        try:
                            await self.client.send_message(pair.dest_entity, reply_context_msg, reply_to=mirrored_msg.id)
                        except Exception as e:
                            log_error("reply_context", str(e))

                    pair.add_to_history(event.message.id, mirrored_msg, sender_name, event.message.message)
                    
                    log_to_disk("new", {
                        "source_chat_id": pair.source_id,
                        "source_chat_title": pair.source_title,
                        "src_msg_id": event.message.id,
                        "dst_chat_id": pair.dest_id,
                        "dst_msg_id": mirrored_msg.id,
                        "sender_id": sender_id,
                        "sender_name": sender_name,
                        "text": event.message.message,
                        "reply_to_src_id": reply_to_src_id,
                        "reply_to_dst_id": reply_to_dst_id
                    })

                # Only show console output if enabled
                session_name = "Ghost"
                if hasattr(self.client.session, 'filename'):
                    session_name = os.path.basename(self.client.session.filename).replace('.session', '')

                if NOTIFY_NEW_MESSAGES:
                    console.print(f"[bold cyan]{session_name}[/bold cyan][{now_chi.strftime('%H:%M:%S')}] 👻 [green]✓[/green] captured in {pair.source_title}")

            except Exception as e:
                log_error("new_message_handler", str(e), traceback.format_exc())

        @self.client.on(events.MessageEdited())
        async def edit_handler(event):
            chat_id = event.chat_id
            pair = self.state.get_pair(chat_id)
            if not pair: return
            
            try:
                sender = await event.get_sender()
                if not sender:
                     sender_name = "Unknown"
                     sender_id = event.sender_id if hasattr(event, 'sender_id') else 0
                else:
                     sender_name = getattr(sender, 'username', None) or getattr(sender, 'first_name', 'User')
                     sender_id = getattr(sender, 'id', None)
                
                # Capture mentions in edits
                mentions = extract_mentions(event.message)
                now_chi = get_now()
                for m in mentions:
                    record_user_seen_mention(pair.source_id, pair.source_title, m, now_chi)

                orig_msg_data = pair.msg_map.get(event.message.id)
                reply_to_id = orig_msg_data[0].id if orig_msg_data else None
                old_text = orig_msg_data[2] if orig_msg_data else ""
                new_text = event.message.message or ""

                # Visual Edit Alert
                diff_text = generate_diff_text(old_text, new_text)
                
                if not diff_text:
                    return

                context_str = ""
                if not reply_to_id:
                    context_str = "\n_(Original message not found in cache)_"

                # Only send alert if enabled
                if NOTIFY_EDITS:
                    alert = (
                        f"✏️ **EDIT DETECTED** by @{sender_name}{context_str}\n"
                        f"📜 **WAS:** {old_text}\n"
                        f"🆕 **NOW:** {new_text}\n"
                        f"🔍 **DIFF:**\n{diff_text}"
                    )
                    
                    try:
                        await self.client.send_message(pair.dest_entity, alert, reply_to=reply_to_id)
                    except FloodWaitError as e:
                        await self.handle_flood_wait(e, "edit_alert")
                        try:
                            await self.client.send_message(pair.dest_entity, alert, reply_to=reply_to_id)
                        except Exception as e2:
                            log_error("edit_alert_retry", str(e2))
                    except Exception as e:
                        log_error("edit_alert", str(e))
                        try:
                            await self.client.send_message(pair.dest_entity, alert)
                        except Exception as e2:
                            log_error("edit_alert_fallback", str(e2))
                
                # Update cache
                if orig_msg_data:
                    pair.msg_map[event.message.id] = (orig_msg_data[0], sender_name, new_text)

                # Always log to disk
                log_to_disk("edit", {
                    "source_chat_id": pair.source_id,
                    "source_chat_title": pair.source_title,
                    "src_msg_id": event.message.id,
                    "dst_chat_id": pair.dest_id,
                    "sender_id": sender_id,
                    "sender_name": sender_name,
                    "old_text": old_text,
                    "new_text": new_text
                })

                session_name = "Ghost"
                if hasattr(self.client.session, 'filename'):
                    session_name = os.path.basename(self.client.session.filename).replace('.session', '')

                # Only show console output if enabled
                if NOTIFY_EDITS:
                    console.print(f"[bold cyan]{session_name}[/bold cyan][{now_chi.strftime('%H:%M:%S')}] ✏️ [yellow]⚠[/yellow] edit in {pair.source_title}")
            except Exception as e:
                log_error("edit_handler", str(e), traceback.format_exc())
