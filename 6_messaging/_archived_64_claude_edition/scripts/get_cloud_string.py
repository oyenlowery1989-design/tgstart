
import base64
import os
import json

"""
FILE: get_cloud_string.py
PURPOSE: Generates Base64 strings for Render deployment.
Allows you to store your session and mirrors in environment variables.
"""

def get_b64(filepath):
    # Auto-detect project root
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root_dir)
    
    if not os.path.exists(filepath):
        return None
    with open(filepath, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def main():
    print("="*60)
    print("📋 RENDER CLOUD STRINGS GENERATOR")
    print("="*60)

    # 1. Session String
    sess_dir = "sessions"
    found_sessions = [f for f in os.listdir(sess_dir) if f.endswith(".session")] if os.path.exists(sess_dir) else []
    
    if found_sessions:
        # Prioritize americandreamer8 if it exists
        target = "americandreamer8.session" if "americandreamer8.session" in found_sessions else found_sessions[0]
        path = os.path.join(sess_dir, target)
        print(f"\n[SESSION] Found: {target}")
        print("-" * 20)
        print(get_b64(path))
        print("-" * 20)
        print("👆 Copy this into Render Env Var: SESSION_BASE64")
    else:
        print("\n[SESSION] ❌ No .session files found in sessions/ folder.")

    # 2. Mirrors String
    mirror_path = "data/mirrors.json"
    if os.path.exists(mirror_path):
        print("\n[MIRRORS] Found: data/mirrors.json")
        print("-" * 20)
        print(get_b64(mirror_path))
        print("-" * 20)
        print("👆 Copy this into Render Env Var: MIRRORS_BASE64")
    else:
        print("\n[MIRRORS] ❌ data/mirrors.json not found.")

    print("\n" + "="*60)

if __name__ == "__main__":
    main()
