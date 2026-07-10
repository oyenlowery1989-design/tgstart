
"""
FILE: src/handlers/reaction.py -> src/handlers/handle_reactions.py
PURPOSE: Mirrors message reactions (likes, emoticons) to the destination channel.
"""
import traceback
import os
from telethon import events, types, utils
from src.handlers.base import BaseHandler
from src.config.settings import NOTIFY_REACTIONS, MIRROR_REACTIONS_AS_TEXT, MAX_BIO_QUEUE_SIZE
from src.core.logger import log_error, log_to_disk, get_now, console
from src.core.user_intelligence import update_user_index, bio_fetch_queue, processed_bios, get_user_info_string

import time

class ReactionHandler(BaseHandler):
    def __init__(self, client, state_manager):
        super().__init__(client, state_manager)
        # Track last known reaction for (message_id, user_id) to avoid duplicates
        self.reaction_state = {} 

    async def register(self):
        @self.client.on(events.Raw())
        async def reaction_handler(event):
            try:
                # Broadened match to ensure we don't miss updates in any group type
                if not isinstance(event, (types.UpdateMessageReactions, types.UpdateBotMessageReaction, types.UpdateEditMessage, types.UpdateNewMessage)):
                    return

                # Determine Chat ID (Try multiple sources for robustness)
                chat_id = None
                if hasattr(event, 'chat_id'):
                    chat_id = event.chat_id
                elif hasattr(event, 'peer'):
                    chat_id = utils.get_peer_id(event.peer)
                elif hasattr(event, 'peer_id'):
                    chat_id = utils.get_peer_id(event.peer_id)
                elif hasattr(event, 'message') and hasattr(event.message, 'peer_id'):
                    chat_id = utils.get_peer_id(event.message.peer_id)
                
                if chat_id is None: return

                # Retrieve pair
                pair = self.state.get_pair(chat_id)
                if not pair: return

                # Determine msg_id
                msg_id = getattr(event, 'msg_id', None)
                if not msg_id and hasattr(event, 'message'):
                    msg_id = event.message.id
                
                if not msg_id: return

                # List of (uid, emoji) to notify
                reactions_to_process = [] 

                # 1. Standard Collection
                if isinstance(event, types.UpdateMessageReactions):
                    recent = getattr(event.reactions, 'recent_reactions', []) or []
                    for r in recent:
                        uid = str(utils.get_peer_id(r.peer_id))
                        emoji = str(getattr(r.reaction, 'emoticon', '❤️'))
                        reactions_to_process.append((uid, emoji))
                    
                    # Fallback for Basic Groups: If no recent reactors but count > 0
                    if not recent and hasattr(event.reactions, 'results'):
                        for res in event.reactions.results:
                            emoji = str(getattr(res.reaction, 'emoticon', '❤️'))
                            # We don't know who, so we use a placeholder or skip
                            # For now, we only notify if we know WHO did it to avoid "Someone reacted" spam
                            pass

                # 2. Targeted update (Reacting to bot/self)
                elif isinstance(event, types.UpdateBotMessageReaction):
                    uid = str(utils.get_peer_id(event.actor_id))
                    emoji = str(getattr(event.reaction, 'emoticon', '❤️'))
                    reactions_to_process.append((uid, emoji))
                
                # 3. Message Edits/New Messages containing reactions
                elif hasattr(event, 'message') and hasattr(event.message, 'reactions') and event.message.reactions:
                    recent = getattr(event.message.reactions, 'recent_reactions', []) or []
                    for r in recent:
                        uid = str(utils.get_peer_id(r.peer_id))
                        emoji = str(getattr(r.reaction, 'emoticon', '❤️'))
                        reactions_to_process.append((uid, emoji))

                if not reactions_to_process: return

                # Grouping for clean output
                emoji_groups = {} 

                for uid, emoji in reactions_to_process:
                    state_key = (msg_id, uid)
                    if self.reaction_state.get(state_key) == emoji:
                        continue
                    
                    self.reaction_state[state_key] = emoji
                    
                    # Cache cleanup
                    if len(self.reaction_state) > 1000:
                        keys = list(self.reaction_state.keys())
                        for k in keys[:500]: self.reaction_state.pop(k)

                    # Update User Index
                    update_user_index(uid, None, None, seen_in=str(chat_id)) 
                    if uid not in processed_bios and bio_fetch_queue.qsize() < MAX_BIO_QUEUE_SIZE:
                        bio_fetch_queue.put_nowait(uid)
                    
                    user_info_str = get_user_info_string(uid)
                    if emoji not in emoji_groups:
                        emoji_groups[emoji] = []
                    emoji_groups[emoji].append(user_info_str)

                    # LOG TO DISK
                    log_to_disk("reaction", {
                        "source_chat_id": pair.source_id,
                        "msg_id": msg_id,
                        "user_id": uid,
                        "reaction": emoji
                    })

                # NOTIFICATIONS
                for emoji, authors in emoji_groups.items():
                    authors_str = ", ".join(authors)
                    session_name = os.path.basename(self.client.session.filename or "Ghost").replace('.session', '')

                    if NOTIFY_REACTIONS:
                        console.print(f"[bold cyan]{session_name}[/bold cyan][{get_now().strftime('%H:%M:%S')}] {emoji} [magenta]Reaction in {pair.source_title}[/magenta] (by {authors_str})")
                    
                    if MIRROR_REACTIONS_AS_TEXT:
                        try:
                            reply_to_id = None
                            if msg_id in pair.msg_map:
                                entry = pair.msg_map[msg_id]
                                reply_to_id = entry.get('id') if isinstance(entry, dict) else entry[0].id
                            
                            if reply_to_id:
                                txt = f"{emoji} **Reaction** (by {authors_str})"
                                await self.client.send_message(pair.dest_entity, txt, reply_to=reply_to_id)
                        except Exception as e:
                            log_error("reaction_mirror_fail", f"Failed to mirror in {pair.source_title}: {e}")

            except Exception as e:
                log_error("reaction_handler", str(e), traceback.format_exc())
