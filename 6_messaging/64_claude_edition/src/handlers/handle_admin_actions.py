"""
FILE: src/handlers/handle_admin_actions.py
PURPOSE: Mirrors Admin actions like Bans, Kicks, Restrictions, Promotions, and Demotions.
"""
import os
import traceback
from telethon import events, types
from src.handlers.base import BaseHandler
from src.config.settings import (
    NOTIFY_BANS, NOTIFY_RESTRICTIONS, NOTIFY_UNRESTRICTIONS,
    NOTIFY_PROMOTIONS, NOTIFY_DEMOTIONS
)
from src.core.logger import log_error, log_to_disk, get_now, console
from telethon.errors import FloodWaitError

class AdminActionHandler(BaseHandler):
    async def register(self):
        @self.client.on(events.Raw(types=[types.UpdateChannelParticipant, types.UpdateChatParticipant]))
        async def participant_handler(event):
            try:
                # Determine which chat this is for
                chat_id = None
                if isinstance(event, types.UpdateChannelParticipant):
                    chat_id = event.channel_id
                elif isinstance(event, types.UpdateChatParticipant):
                    chat_id = event.chat_id
                
                # Check if this is one of our monitored chats
                pair = self.state.get_pair(chat_id)
                if not pair:
                    return
                
                # Get user and admin info
                user_id = event.user_id if hasattr(event, 'user_id') else None
                actor_id = event.actor_id if hasattr(event, 'actor_id') else None
                
                if not user_id:
                    return
                
                # Fetch user and admin entities
                try:
                    user = await self.client.get_entity(user_id)
                    user_name = getattr(user, 'username', None) or getattr(user, 'first_name', 'User')
                except:
                    user_name = f"User{user_id}"
                
                admin_name = None
                if actor_id:
                    try:
                        admin = await self.client.get_entity(actor_id)
                        admin_name = getattr(admin, 'username', None) or getattr(admin, 'first_name', 'Admin')
                    except:
                        admin_name = f"Admin{actor_id}"
                
                # Analyze the permission change
                old_participant = event.prev_participant if hasattr(event, 'prev_participant') else None
                new_participant = event.new_participant if hasattr(event, 'new_participant') else None
                
                action_text = None
                action_type = None
                console_emoji = None
                now_chi = get_now()
                notify_enabled = False
                
                # Helper for determining admin status
                def is_admin(p):
                    return isinstance(p, (types.ChannelParticipantAdmin, types.ChatParticipantAdmin))
                
                def is_banned(p):
                    return isinstance(p, types.ChannelParticipantBanned)
                
                # Check for admin promotion
                if is_admin(new_participant):
                    # User was promoted to admin
                    if not old_participant or not is_admin(old_participant):
                        action_text = f"👑 **User Promoted to Admin:** @{user_name}"
                        if admin_name:
                            action_text += f" (by @{admin_name})"
                        action_type = "promote"
                        console_emoji = "👑"
                        notify_enabled = NOTIFY_PROMOTIONS
                
                # Check for admin demotion
                elif is_admin(old_participant):
                    if not new_participant or not is_admin(new_participant):
                        action_text = f"👤 **Admin Demoted:** @{user_name}"
                        if admin_name:
                            action_text += f" (by @{admin_name})"
                        action_type = "demote"
                        console_emoji = "👤"
                        notify_enabled = NOTIFY_DEMOTIONS
                
                # Check for ban
                elif is_banned(new_participant):
                    if hasattr(new_participant, 'banned_rights') and new_participant.banned_rights:
                        if new_participant.banned_rights.view_messages:
                            # Full ban
                            action_text = f"🚫 **User Banned:** @{user_name}"
                            if admin_name:
                                action_text += f" (by @{admin_name})"
                            action_type = "ban"
                            console_emoji = "🚫"
                            notify_enabled = NOTIFY_BANS
                        else:
                            # Restricted (muted or limited permissions)
                            restrictions = []
                            if new_participant.banned_rights.send_messages:
                                restrictions.append("send messages")
                            if new_participant.banned_rights.send_media:
                                restrictions.append("send media")
                            if new_participant.banned_rights.send_stickers:
                                restrictions.append("send stickers")
                            if new_participant.banned_rights.send_polls:
                                restrictions.append("send polls")
                            
                            if restrictions:
                                restriction_str = ", ".join(restrictions)
                                action_text = f"⚠️ **User Restricted:** @{user_name} (cannot {restriction_str})"
                                if admin_name:
                                    action_text += f" (by @{admin_name})"
                                action_type = "restrict"
                                console_emoji = "⚠️"
                                notify_enabled = NOTIFY_RESTRICTIONS
                
                # Check for unban/unrestrict
                elif is_banned(old_participant) and new_participant and not is_banned(new_participant):
                    action_text = f"✅ **User Unrestricted:** @{user_name}"
                    if admin_name:
                        action_text += f" (by @{admin_name})"
                    action_type = "unrestrict"
                    console_emoji = "✅"
                    notify_enabled = NOTIFY_UNRESTRICTIONS
                
                # Send alert and log (only if notification is enabled)
                if action_text and notify_enabled:
                    session_name = "Ghost"
                    if hasattr(self.client.session, 'filename'):
                        session_name = os.path.basename(self.client.session.filename).replace('.session', '')

                    # Console output
                    if console_emoji:
                        console.print(f"[bold cyan]{session_name}[/bold cyan][{now_chi.strftime('%H:%M:%S')}] {console_emoji} [magenta]{action_text.replace('**', '')}[/magenta]")
                    
                    # Send to backup chat
                    try:
                        await self.client.send_message(pair.dest_entity, action_text)
                    except FloodWaitError as e:
                        await self.handle_flood_wait(e, "participant_change")
                    except Exception as e:
                        log_error("participant_change_send", str(e))
                
                # Always log to disk regardless of notification setting
                if action_text:
                    log_to_disk(action_type, {
                        "source_chat_id": pair.source_id,
                        "source_chat_title": pair.source_title,
                        "user_id": user_id,
                        "username": user_name,
                        "actor_id": actor_id,
                        "actor_name": admin_name,
                        "old_participant": str(type(old_participant).__name__) if old_participant else None,
                        "new_participant": str(type(new_participant).__name__) if new_participant else None
                    })
            
            except Exception as e:
                log_error("participant_handler", str(e), traceback.format_exc())
