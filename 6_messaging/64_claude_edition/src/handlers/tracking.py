import os
import traceback
from telethon import events, types
try:
    from telethon.tl.types import UpdateChatInviteImporter
except ImportError:
    UpdateChatInviteImporter = None
    print("⚠️ UpdateChatInviteImporter not found. Invite link tracking will be disabled.")

from src.handlers.base import BaseHandler
from src.config.settings import (
    NOTIFY_JOINS, NOTIFY_LEAVES, NOTIFY_KICKS, NOTIFY_ADDS,
    NOTIFY_INVITE_LINKS, NOTIFY_BOT_EVENTS
)
from src.core.logger import log_error, log_to_disk, get_now, console
from src.core.database import record_user_seen_sender
from telethon.errors import FloodWaitError

class TrackingHandler(BaseHandler):
    async def register(self):
        @self.client.on(events.ChatAction())
        async def action_handler(event):
            # Dynamic filter
            pair = self.state.get_pair(event.chat_id)
            if not pair: return 

            try:
                # ChatAction events don't have get_sender(), use event.user instead
                user = None
                if event.user_id:
                    try:
                        user = await self.client.get_entity(event.user_id)
                    except:
                        pass
                
                # Get the admin who performed the action (if applicable)
                admin = None
                admin_name = None
                if event.action_message:
                    try:
                        admin_id = getattr(event.action_message, 'sender_id', None)
                        if admin_id:
                            admin = await self.client.get_entity(admin_id)
                            admin_name = getattr(admin, 'username', None) or getattr(admin, 'first_name', 'Admin')
                    except:
                        pass
                
                # Fallback to event properties
                sender_name = getattr(user, 'username', None) or getattr(user, 'first_name', 'User') if user else 'User'
                uid = event.user_id if event.user_id else None
                now_chi = get_now()
                
                if uid and user:
                    record_user_seen_sender(pair.source_id, pair.source_title, user, now_chi)

                action_text = None
                console_emoji = None
                notify_enabled = False  # Track if notification should be sent
                
                # --- User Movement Events ---
                if event.user_joined or event.user_added:
                    # Check if this is a bot
                    is_bot = user and getattr(user, 'bot', False)
                    
                    if is_bot:
                        # Bot added/joined
                        if event.user_added:
                            action_text = f"🤖 **Bot Added:** @{sender_name}"
                            if admin_name:
                                action_text += f" (by @{admin_name})"
                        else:
                            action_text = f"🤖 **Bot Joined:** @{sender_name}"
                        console_emoji = "🤖"
                        notify_enabled = NOTIFY_BOT_EVENTS
                    else:
                        # Regular user
                        if admin_name and event.user_added:
                            action_text = f"🚪 **User Added:** @{sender_name} (by @{admin_name})"
                            console_emoji = "➕"
                            notify_enabled = NOTIFY_ADDS
                        else:
                            # Check if joined by link
                            inviter_name = None
                            if event.action_message and isinstance(event.action_message.action, types.MessageActionChatJoinedByLink):
                                inviter_id = event.action_message.action.inviter_id
                                if inviter_id == 1087968824: # GroupAnonymousBot
                                    inviter_name = "Anonymous Admin"
                                else:
                                    try:
                                        u = await self.client.get_entity(inviter_id)
                                        inviter_name = getattr(u, 'username', None) or getattr(u, 'first_name', 'Unknown')
                                        if inviter_name == "GroupAnonymousBot": inviter_name = "Anonymous Admin"
                                    except:
                                        inviter_name = f"User{inviter_id}"
                            
                            if inviter_name:
                                action_text = f"🔗 **User Joined via Link:** @{sender_name} (by @{inviter_name})"
                                console_emoji = "🔗"
                                notify_enabled = NOTIFY_INVITE_LINKS
                            else:
                                action_text = f"🚪 **User Joined:** @{sender_name}"
                                console_emoji = "🚪"
                                notify_enabled = NOTIFY_JOINS
                    
                    log_to_disk("join" if not is_bot else "bot_join", {
                        "source_chat_id": pair.source_id, 
                        "user_id": uid, 
                        "username": sender_name, 
                        "added_by": admin_name,
                        "is_bot": is_bot
                    })
                
                elif event.user_left:
                    # Check if this is a bot
                    is_bot = user and getattr(user, 'bot', False)
                    
                    if is_bot:
                        action_text = f"🤖 **Bot Left:** @{sender_name}"
                        console_emoji = "🤖"
                        notify_enabled = NOTIFY_BOT_EVENTS
                    else:
                        action_text = f"🚪 **User Left:** @{sender_name}"
                        console_emoji = "🚶"
                        notify_enabled = NOTIFY_LEAVES
                    
                    log_to_disk("leave" if not is_bot else "bot_leave", {
                        "source_chat_id": pair.source_id, 
                        "user_id": uid, 
                        "username": sender_name,
                        "is_bot": is_bot
                    })
                
                elif event.user_kicked:
                    # Check if this is a bot
                    is_bot = user and getattr(user, 'bot', False)
                    
                    if is_bot:
                        action_text = f"🤖 **Bot Removed:** @{sender_name}"
                        if admin_name:
                            action_text += f" (by @{admin_name})"
                        console_emoji = "🤖"
                        notify_enabled = NOTIFY_BOT_EVENTS
                    else:
                        if admin_name:
                            action_text = f"🚪 **User Kicked:** @{sender_name} (by @{admin_name})"
                        else:
                            action_text = f"🚪 **User Kicked:** @{sender_name}"
                        console_emoji = "🚫"
                        notify_enabled = NOTIFY_KICKS
                    
                    log_to_disk("kick" if not is_bot else "bot_kick", {
                        "source_chat_id": pair.source_id, 
                        "user_id": uid, 
                        "username": sender_name, 
                        "kicked_by": admin_name,
                        "is_bot": is_bot
                    })
                
                # --- Invite Link Events ---
                if hasattr(event, 'created_invite') and event.created_invite:
                    invite = event.created_invite
                    action_text = f"🔗 **Invite Link Created**"
                    if hasattr(invite, 'usage_limit') and invite.usage_limit:
                        action_text += f" (limit: {invite.usage_limit} uses)"
                    if hasattr(invite, 'expire_date') and invite.expire_date:
                        action_text += f" (expires: {invite.expire_date})"
                    console_emoji = "🔗"
                    notify_enabled = NOTIFY_INVITE_LINKS
                    log_to_disk("invite_created", {
                        "source_chat_id": pair.source_id,
                        "usage_limit": getattr(invite, 'usage_limit', None),
                        "expire_date": str(getattr(invite, 'expire_date', None))
                    })
                
                if hasattr(event, 'revoked_invite') and event.revoked_invite:
                    action_text = f"🔗 **Invite Link Revoked**"
                    console_emoji = "🔗"
                    notify_enabled = NOTIFY_INVITE_LINKS
                    log_to_disk("invite_revoked", {"source_chat_id": pair.source_id})

                # Send notification if enabled
                if action_text and notify_enabled:
                    session_name = "Ghost"
                    if hasattr(self.client.session, 'filename'):
                        session_name = os.path.basename(self.client.session.filename).replace('.session', '')

                    # Console output
                    if console_emoji:
                        console.print(f"[bold cyan]{session_name}[/bold cyan][{now_chi.strftime('%H:%M:%S')}] {console_emoji} [yellow]{action_text.replace('**', '')}[/yellow]")
                    
                    # Send to backup chat
                    try:
                        await self.client.send_message(pair.dest_entity, action_text)
                    except FloodWaitError as e:
                        await self.handle_flood_wait(e, "chat_action")
                    except Exception as e:
                        log_error("chat_action_send", str(e))

            except Exception as e:
                log_error("chat_action_handler", str(e), traceback.format_exc())

        if UpdateChatInviteImporter:
            async def invite_join_handler(event):
                try:
                    # Get chat ID
                    chat_id = event.peer.channel_id if hasattr(event.peer, 'channel_id') else (event.peer.chat_id if hasattr(event.peer, 'chat_id') else None)
                    if not chat_id:
                        return
                    
                    pair = self.state.get_pair(chat_id)
                    if not pair:
                        return
                    
                    # Get user who joined
                    user_id = event.user_id
                    try:
                        user = await self.client.get_entity(user_id)
                        user_name = getattr(user, 'username', None) or getattr(user, 'first_name', 'User')
                    except:
                        user_name = f"User{user_id}"
                    
                    # Get invite link info
                    invite_link = "unknown"
                    created_by = None
                    
                    if hasattr(event, 'invite') and event.invite:
                        invite = event.invite
                        if hasattr(invite, 'link'):
                            invite_link = invite.link
                        
                        # Try to get who created the link
                        if hasattr(invite, 'admin_id'):
                            try:
                                admin = await self.client.get_entity(invite.admin_id)
                                created_by = getattr(admin, 'username', None) or getattr(admin, 'first_name', 'Admin')
                            except:
                                created_by = f"Admin{invite.admin_id}"
                    
                    now_chi = get_now()
                    
                    # Build alert
                    action_text = f"🔗 **User Joined via Invite:** @{user_name}"
                    if created_by:
                        action_text += f" (link by @{created_by})"
                    
                    # Only notify if enabled
                    if NOTIFY_INVITE_LINKS:
                        session_name = "Ghost"
                        if hasattr(self.client.session, 'filename'):
                            session_name = os.path.basename(self.client.session.filename).replace('.session', '')

                        console.print(f"[bold cyan]{session_name}[/bold cyan][{now_chi.strftime('%H:%M:%S')}] 🔗 [cyan]{action_text.replace('**', '')}[/cyan]")
                        
                        try:
                            await self.client.send_message(pair.dest_entity, action_text)
                        except FloodWaitError as e:
                            await self.handle_flood_wait(e, "invite_join")
                        except Exception as e:
                            log_error("invite_join_send", str(e))
                    
                    # Always log
                    log_to_disk("invite_join", {
                        "source_chat_id": pair.source_id,
                        "user_id": user_id,
                        "username": user_name,
                        "invite_link": invite_link,
                        "created_by": created_by
                    })
                    
                except Exception as e:
                    log_error("invite_join_handler", str(e), traceback.format_exc())

            self.client.add_event_handler(invite_join_handler, events.Raw(types=[UpdateChatInviteImporter]))
