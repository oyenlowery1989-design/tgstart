
import os
import sys
import base64
import threading
import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
import subprocess

"""
FILE: render_wrapper.py
PURPOSE: Cloud-native wrapper for Render deployment.
Handles session restoration, configuration persistence, and keep-alive server
WITHOUT modifying the core codebase.
"""

# --- Keep-Alive Server ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Ghost Mirror Cloud Wrapper is Alive")
    def log_message(self, format, *args): return

def run_keep_alive():
    port = int(os.getenv("PORT", 8080))
    print(f"[CLOUD] Starting keep-alive server on port {port}")
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# --- Cloud Logic ---
def restore_cloud_files():
    # Point to the actual project root (parent of 'scripts')
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 1. Restore Session
    b64_session = os.getenv("SESSION_BASE64")
    if b64_session:
        sess_dir = os.path.join(root_dir, "sessions")
        os.makedirs(sess_dir, exist_ok=True)
        # We'll save it as 'cloud_session.session'
        # Then we MUST tell the runner to use it via DEFAULT_SESSION
        target = os.path.join(sess_dir, "cloud_session.session")
        try:
            with open(target, "wb") as f:
                f.write(base64.b64decode(b64_session))
            print("[CLOUD] ✅ Session restored from environment.")
            # Important: DEFAULT_SESSION should be relative to where ghost_runner.py runs
            os.environ["DEFAULT_SESSION"] = "sessions/cloud_session"
        except Exception as e:
            print(f"[CLOUD] ❌ Failed to restore session: {e}")

    # 2. Restore Config (Mirrors)
    b64_mirrors = os.getenv("MIRRORS_BASE64")
    if b64_mirrors:
        data_dir = os.path.join(root_dir, "data")
        os.makedirs(data_dir, exist_ok=True)
        target = os.path.join(data_dir, "mirrors.json")
        try:
            with open(target, "wb") as f:
                f.write(base64.b64decode(b64_mirrors))
            print("[CLOUD] ✅ Mirrors configuration restored from environment.")
        except Exception as e:
            print(f"[CLOUD] ❌ Failed to restore mirrors: {e}")

def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    print("="*60)
    print("👻 Ghost Mirror - Render Cloud Wrapper")
    print("="*60)
    
    # Restore files from env vars
    restore_cloud_files()
    
    # Start keep-alive server in background
    threading.Thread(target=run_keep_alive, daemon=True).start()
    
    # Run the actual bot
    print("[CLOUD] Launching main bot engine...")
    try:
        # We run it as a subprocess to keep the environment clean
        # and ensure run.py/ghost_runner.py logic remains untouched
        runner_path = os.path.join(root_dir, "ghost_runner.py")
        subprocess.check_call([sys.executable, runner_path])
    except KeyboardInterrupt:
        print("\n[CLOUD] Shutdown requested.")
    except Exception as e:
        print(f"[CLOUD] ❌ Bot exited with error: {e}")

if __name__ == "__main__":
    main()
