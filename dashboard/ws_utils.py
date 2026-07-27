"""Shared accept/session-guard/error-handling lifecycle for dashboard websocket routes."""
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect

from dashboard.state import get_active_session


@asynccontextmanager
async def ws_session(websocket: WebSocket, require_session: bool = True):
    """Accept the websocket, optionally resolve the active session, and run the
    caller's body under the standard disconnect/error/close handling.

    Yields the active session name, or None if there isn't one — callers that
    require a session should `return` immediately when it's None (the "no
    active session" error has already been sent to the client).
    """
    await websocket.accept()
    session_name: Optional[str] = None
    if require_session:
        session_name = get_active_session(websocket)
        if not session_name:
            await websocket.send_json({"error": "No active session set."})
    try:
        yield session_name
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"error": str(e)})
    finally:
        await websocket.close()
