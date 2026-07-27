import asyncio
import signal
import subprocess
import sys
import time
from loguru import logger

# Configuration
RESTART_DELAY = 2  # Seconds before restarting
MAX_RESTARTS = 5   # Max restarts in a short window (optional, simple loop here)

_current_process = None


def _forward_signal(signum, frame):
    logger.info(f"Watchdog received signal {signum}. Stopping.")
    if _current_process is not None and _current_process.poll() is None:
        _current_process.terminate()
        try:
            _current_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            _current_process.kill()
    sys.exit(0)


def main():
    global _current_process
    logger.add("data/run.log", rotation="1 MB")
    logger.info("Starting Watchdog for GhostMirror...")

    signal.signal(signal.SIGTERM, _forward_signal)

    while True:
        try:
            logger.info("Launching ghost_runner.py...")
            # Run the ghost runner as a subprocess
            _current_process = subprocess.Popen([sys.executable, "ghost_runner.py"], stdin=subprocess.DEVNULL)

            # Wait for it to finish
            return_code = _current_process.wait()

            if return_code == 0:
                logger.info("GhostRunner exited normally. Watchdog stopping.")
                break
            else:
                logger.warning(f"GhostRunner crashed with exit code {return_code}. Restarting in {RESTART_DELAY}s...")
                time.sleep(RESTART_DELAY)

        except KeyboardInterrupt:
            logger.info("Watchdog interrupted by user. Stopping.")
            if _current_process is not None and _current_process.poll() is None:
                _current_process.terminate()
            break
        except Exception as e:
            logger.error(f"Watchdog exception: {e}")
            time.sleep(RESTART_DELAY)

if __name__ == "__main__":
    main()
