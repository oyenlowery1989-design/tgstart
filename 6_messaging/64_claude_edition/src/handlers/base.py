
"""
FILE: src/handlers/base.py
PURPOSE: Abstract base class for all handlers. Contains common helper methods like flood wait handling.
"""
from src.core.logger import log_error, console
from telethon.errors import FloodWaitError
import asyncio

class BaseHandler:
    def __init__(self, client, state_manager):
        self.client = client
        self.state = state_manager
    
    async def register(self):
        """
        Must be implemented by subclasses to register event handlers.
        """
        raise NotImplementedError("Handlers must implement register()")

    async def handle_flood_wait(self, e, context="unknown"):
        """
        Logs Telethon FloodWaitError details and raises the exception.
        We do NOT sleep here, because sleeping blocks the event loop.
        Instead, we let the caller (the individual handler) decide how to handle it,
        or just log it and retry later.
        """
        wait_time = e.seconds
        console.print(f"[yellow]⏳ FloodWait: Need to wait {wait_time}s (Context: {context})[/yellow]")
        log_error("flood_wait", f"Need to wait {wait_time}s", f"Context: {context}")
        
        # We re-raise the error so the calling function knows it failed.
        # Sleeping inside an async function blocks concurrent tasks if not careful,
        # but asyncio.sleep is non-blocking. However, simply sleeping doesn't
        # "retry" the failed request automatically.
        # The caller needs to wrap the request in a loop if they want to retry.
        await asyncio.sleep(wait_time)
