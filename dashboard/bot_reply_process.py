"""Launches/monitors the bot_reply subprocess directly — no separate watchdog process.

6_messaging/65/'s original two-process design (a watchdog Popen'ing the real bot) let a
dashboard "stop" SIGTERM the watchdog only, orphaning the real bot with no signal handler
to forward the shutdown — the next "start" then spawned a second live bot writing the same
tables. One subprocess plus an asyncio monitor task inside this process avoids that
failure class entirely: there is only one thing to signal, and this module is the one
signaling it.
"""
import asyncio
import os
import signal
import subprocess
import sys
from pathlib import Path

BOT_REPLY_DIR = Path(__file__).resolve().parent.parent / "6_messaging" / "bot_reply"
RESTART_DELAY = 2


class BotReplyHandle:
    def __init__(self, proc: subprocess.Popen, monitor_task):
        self.proc = proc
        self.monitor_task = monitor_task
        self.stopping = False


def _spawn() -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "runner.py"],
        cwd=str(BOT_REPLY_DIR),
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )


async def _monitor(handle: BotReplyHandle) -> None:
    while True:
        await asyncio.sleep(RESTART_DELAY)
        if handle.stopping:
            return
        if handle.proc.poll() is not None:
            handle.proc = _spawn()


def start_bot_reply() -> BotReplyHandle:
    handle = BotReplyHandle(_spawn(), None)
    handle.monitor_task = asyncio.create_task(_monitor(handle))
    return handle


async def stop_bot_reply(handle: BotReplyHandle) -> None:
    handle.stopping = True
    handle.monitor_task.cancel()
    try:
        os.killpg(os.getpgid(handle.proc.pid), signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        await asyncio.to_thread(handle.proc.wait, timeout=10)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(handle.proc.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
        await asyncio.to_thread(handle.proc.wait)


if __name__ == "__main__":
    assert callable(start_bot_reply) and callable(stop_bot_reply)
    print("bot_reply_process.py smoke check OK")
