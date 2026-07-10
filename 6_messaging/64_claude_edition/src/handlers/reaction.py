import traceback
import os
from telethon import events, types
from src.handlers.base import BaseHandler
from src.config.settings import NOTIFY_REACTIONS, MAX_BIO_QUEUE_SIZE
from src.core.logger import log_error, log_to_disk, get_now, console
from src.core.database import update_user_index, bio_fetch_queue, processed_bios

class ReactionHandler(BaseHandler):
    async def register(self):
        @self.client.on(events.Raw(types=[types.UpdateMessageReactions, types.UpdateBotMessageReaction]))
        async def reaction_handler(event):
            try:
                # Determine chat ID
                chat_id = None
                if isinstance(event.peer, types.PeerChannel): chat_id = event.peer.channel_id
                elif isinstance(event.peer, types.PeerChat): chat_id = event.peer.chat_id
                
                # Retrieve pair
                pair = self.state.get_pair(chat_id)
                if not pair: return

                # Fix: event.reactions is a MessageReactions object, not a list
                if hasattr(event, 'reactions') and event.reactions:
                    reactions_list = getattr(event.reactions, 'results', [])
                    for r in reactions_list:
                        # Try to get user_id from recent_reactions if available
                        user_id_obj = None
                        if hasattr(r, 'recent_reactions'):
                             for recent in r.recent_reactions:
                                 user_id_obj = getattr(recent, 'peer_id', None)
                                 break
                        
                        uid = None
                        if user_id_obj and hasattr(user_id_obj, 'user_id'):
                            uid = str(user_id_obj.user_id)
                        
                        reaction_emoji = getattr(r, 'reaction', '❤️')
                        # Handle EmoticonReaction vs CustomReaction
                        if hasattr(reaction_emoji, 'emoticon'):
                            reaction_emoji = reaction_emoji.emoticon
                        elif hasattr(reaction_emoji, 'document_id'):
                            reaction_emoji = "[Custom]"
                        
                        if uid:
                            update_user_index(uid, None, None) 
                            if uid not in processed_bios and bio_fetch_queue.qsize() < MAX_BIO_QUEUE_SIZE:
                                bio_fetch_queue.put_nowait(uid)
                        
                        # LOGGING & NOTIFICATION
                        log_to_disk("reaction", {
                            "source_chat_id": pair.source_id,
                            "msg_id": event.msg_id,
                            "user_id": uid,
                            "reaction": str(reaction_emoji)
                        })
                        
                        if NOTIFY_REACTIONS:
                            # Console
                            # Access session name safely
                            session_name = "Ghost"
                            if hasattr(self.client.session, 'filename'):
                                session_name = os.path.basename(self.client.session.filename).replace('.session', '')
                            
                            console.print(f"[bold cyan]{session_name}[/bold cyan][{get_now().strftime('%H:%M:%S')}] {reaction_emoji} [magenta]Reaction in {pair.source_title}[/magenta]")
                            
                            # Send to Backup - ISOLATED TRY/EXCEPT
                            try:
                                # Find mirrored message to reply to
                                reply_to_id = None
                                if event.msg_id in pair.msg_map:
                                    reply_to_id = pair.msg_map[event.msg_id][0].id
                                
                                txt = f"{reaction_emoji} **Reaction**"
                                if uid: txt += f" (by User {uid})"
                                
                                if reply_to_id:
                                    await self.client.send_message(pair.dest_entity, txt, reply_to=reply_to_id)
                                else:
                                    await self.client.send_message(pair.dest_entity, f"{txt} (on msg {event.msg_id})")
                            except Exception as e:
                                # This catches the "Reaction" specific fail the user mentioned
                                # "The specified message ID is invalid or you can't do that operation..."
                                log_error("reaction_notify_fail", f"Failed to mirror reaction: {e}")
                                # DO NOT PROPAGATE - Keep the bot alive

            except Exception as e:
                log_error("reaction_handler", str(e), traceback.format_exc())
