
"""
FILE: src/core/prefetcher.py
PURPOSE: Background task to pre-fetch and index users in monitored groups.
"""
import asyncio
import traceback
from telethon import functions, types
from src.core.logger import log_error, console
from src.core.user_intelligence import record_user_seen_sender, get_now

async def prefetch_users(client, state_manager):
    """
    Identifies all participants in mirror sources and indexes them.
    Runs silently in the background.
    """
    try:
        source_entities = state_manager.source_peers
        if not source_entities:
            return

        console.print(f"[dim]🔍 User pre-fetching started for {len(source_entities)} groups...[/dim]")
        
        total_indexed = 0
        for entity in source_entities:
            try:
                # Iterate participants with conservative yielding to prevent DC errors
                async for user in client.iter_participants(entity):
                    if not user or user.bot:
                        continue
                    
                    record_user_seen_sender(0, "Background Prefetch", user, get_now())
                    total_indexed += 1
                    
                    if total_indexed % 20 == 0:
                        await asyncio.sleep(0.5) # Increased sleep for DC stability
                        
            except Exception as e:
                # Catch DC Errors silently to prevent task crash during network instability
                if "DC" in str(e):
                    console.print(f"[dim]⚠️ Telegram DC Communication issue. Continuing...[/dim]")
                    await asyncio.sleep(2) # Backoff
                else:
                    log_error("prefetch_group_fail", f"Could not pre-fetch group: {e}")
        
        console.print(f"[dim]✅ User pre-fetching complete. Indexed {total_indexed} participants.[/dim]")

    except Exception as e:
        log_error("prefetch_users_global_fail", str(e), traceback.format_exc())

async def start_prefetch_task(client, state_manager):
    """Utility to start the prefetcher as a background task."""
    asyncio.create_task(prefetch_users(client, state_manager))
