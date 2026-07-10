import asyncio
import subprocess
import sys
import time
from loguru import logger

# Configuration
RESTART_DELAY = 2  # Seconds before restarting
MAX_RESTARTS = 5   # Max restarts in a short window (optional, simple loop here)

def main():
    logger.add("data/run.log", rotation="1 MB")
    logger.info("Starting Watchdog for GhostMirror...")

    while True:
        try:
            logger.info("Launching ghost_runner.py...")
            # Run the ghost runner as a subprocess
            process = subprocess.Popen([sys.executable, "ghost_runner.py"])
            
            # Wait for it to finish
            return_code = process.wait()
            
            if return_code == 0:
                logger.info("GhostRunner exited normally. Watchdog stopping.")
                break
            else:
                logger.warning(f"GhostRunner crashed with exit code {return_code}. Restarting in {RESTART_DELAY}s...")
                time.sleep(RESTART_DELAY)
                
        except KeyboardInterrupt:
            logger.info("Watchdog interrupted by user. Stopping.")
            if 'process' in locals() and process.poll() is None:
                process.terminate()
            break
        except Exception as e:
            logger.error(f"Watchdog exception: {e}")
            time.sleep(RESTART_DELAY)

if __name__ == "__main__":
    main()
