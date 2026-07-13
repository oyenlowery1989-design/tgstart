#!/usr/bin/env python3
"""
run.py

Auto-restart wrapper for ghost_runner.py
Ensures 24/7 operation by automatically restarting on crashes.

Features:
- Automatic restart on crash
- Exponential backoff for rapid failures
- Crash logging
- Graceful shutdown on Ctrl+C
- Health monitoring

Usage:
    python run.py
"""

import subprocess
import sys
import time
import os
import json
from datetime import datetime
from pathlib import Path

# Configuration
SCRIPT_TO_RUN = "ghost_runner.py"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT_PATH = os.path.join(SCRIPT_DIR, SCRIPT_TO_RUN)
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
CRASH_LOG = os.path.join(DATA_DIR, "crash_log.jsonl")

# Restart policy
MIN_RESTART_DELAY = 5  # seconds
MAX_RESTART_DELAY = 300  # 5 minutes
BACKOFF_MULTIPLIER = 2
RAPID_CRASH_THRESHOLD = 60  # If crashes within 60s, it's a rapid crash

def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)

def log_crash(exit_code, runtime_seconds, restart_count):
    """Log crash details to disk."""
    ensure_dirs()
    
    entry = {
        "ts": datetime.now().isoformat(),
        "exit_code": exit_code,
        "runtime_seconds": runtime_seconds,
        "restart_count": restart_count
    }
    
    try:
        with open(CRASH_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        print(f"Failed to log crash: {e}")

def print_banner():
    print("=" * 60)
    print("👻 Ghost Mirror Auto-Restart Wrapper")
    print("=" * 60)
    print(f"Wrapper: run.py")
    print(f"Target:  {SCRIPT_TO_RUN}")
    print(f"Dir:     {SCRIPT_DIR}")
    print(f"Log:     {CRASH_LOG}")
    print("=" * 60)
    print("\nPress Ctrl+C to stop gracefully\n")

def main():
    ensure_dirs()
    print_banner()
    
    restart_count = 0
    current_delay = MIN_RESTART_DELAY
    
    while True:
        start_time = time.time()
        
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting {SCRIPT_TO_RUN}...")
        if restart_count > 0:
            print(f"  (Restart #{restart_count})")
        
        try:
            # Run the script
            # we use sys.executable to ensure we use the same python interpreter (venv friendly)
            process = subprocess.Popen(
                [sys.executable, SCRIPT_PATH],
                cwd=SCRIPT_DIR,
                stdout=sys.stdout,
                stderr=sys.stderr
            )
            
            # Wait for it to finish
            exit_code = process.wait()
            
            # If the bot was manually stopped (Exit Code 0), stop the wrapper too
            if exit_code == 0:
                print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ Bot stopped normally (Manual Quit).")
                print("Stopping wrapper. Goodbye! 👋")
                sys.exit(0)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Received Ctrl+C. Shutting down gracefully...")
            try:
                # If we get Ctrl+C, we want to kill the subprocess too
                process.terminate()
                process.wait(timeout=5)
            except:
                # Force kill if terminate fails
                if 'process' in locals():
                    process.kill()
            print("✅ Shutdown complete.")
            sys.exit(0)
            
        except Exception as e:
            print(f"❌ Unexpected error running script: {e}")
            exit_code = -1
        
        # Calculate runtime
        runtime = time.time() - start_time
        
        # Log the crash
        log_crash(exit_code, runtime, restart_count)
        
        # Determine if this was a rapid crash
        is_rapid_crash = runtime < RAPID_CRASH_THRESHOLD
        
        if is_rapid_crash:
            # Exponential backoff for rapid crashes to prevent log spam/CPU spin
            current_delay = min(current_delay * BACKOFF_MULTIPLIER, MAX_RESTART_DELAY)
            print(f"⚠️  Rapid crash detected (ran for {runtime:.1f}s)")
            print(f"⏳ Waiting {current_delay}s before restart (backoff)...")
        else:
            # Reset delay if it ran successfully for a while
            current_delay = MIN_RESTART_DELAY
            print(f"🔄 Process exited after {runtime:.1f}s (exit code: {exit_code})")
            print(f"⏳ Restarting in {current_delay}s...")
        
        time.sleep(current_delay)
        restart_count += 1
        print()

if __name__ == "__main__":
    main()
