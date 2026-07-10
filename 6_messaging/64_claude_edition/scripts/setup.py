
"""
FILE: setup.py
PURPOSE: Automatic setup script for Ghost Mirror project.
Initializes directories, installs dependencies, and verifies .env.
"""
import os
import subprocess
import sys
import platform

def print_step(msg):
    print(f"\n[STEP] {msg}")

# Auto-detect project root
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT_DIR)

def create_linux_shortcut():
    """Creates a start.sh script for Linux/Mac users."""
    if platform.system() == "Windows":
        return
    
    script_content = "#!/bin/bash\npython3 run.py\n"
    try:
        with open("start.sh", "w") as f:
            f.write(script_content)
        # Make it executable
        os.chmod("start.sh", 0o755)
        print("  ✅ Created 'start.sh' shortcut for Linux.")
    except Exception as e:
        print(f"  ⚠️ Could not create start.sh: {e}")

def main():
    os_name = platform.system()
    python_cmd = "python" if os_name == "Windows" else "python3"
    
    print("========================================")
    print("👻 Ghost Mirror - Auto Setup Script")
    print(f"Detected OS: {os_name}")
    print("========================================\n")

    # 1. Create necessary directories
    print_step("Ensuring data directories exist...")
    dirs = ["data/logs", "data/backups", "sessions"]
    for d in dirs:
        if not os.path.exists(d):
            os.makedirs(d)
            print(f"  Created: {d}")
        else:
            print(f"  Exists: {d}")

    # 2. Install dependencies
    print_step("Installing dependencies...")
    try:
        # Check if we are in a venv
        is_venv = sys.prefix != sys.base_prefix
        if not is_venv and os_name != "Windows":
            print("  ⚠️ Recommendation: You are not in a virtual environment.")
            print("  Consider using: python3 -m venv venv && source venv/bin/activate")
            
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("  ✅ Dependencies installed successfully.")
    except Exception as e:
        print(f"  ❌ Failed to install dependencies: {e}")
        print("  Check if 'pip' is installed and your internet connection.")
        sys.exit(1)

    # 3. Handle .env file
    print_step("Verifying .env configuration...")
    if not os.path.exists(".env"):
        print("  ⚠️ .env file missing. Creating template...")
        with open(".env", "w") as f:
            f.write("# APP Credentials (Get from my.telegram.org)\n")
            f.write("MAIN_API_ID=YOUR_API_ID\n")
            f.write("MAIN_API_HASH=YOUR_API_HASH\n\n")
            f.write("# Optional Settings\n")
            f.write("# DEFAULT_SESSION=sessions/your_session_name\n")
        print("  ✅ Created .env template. PLEASE EDIT IT with your API credentials.")
    else:
        print("  ✅ .env file already exists.")

    # 4. Linux specific shortcut
    if os_name != "Windows":
        create_linux_shortcut()

    # 5. Final instructions
    print("\n" + "="*40)
    print("🎉 SETUP COMPLETE!")
    print("="*40)
    print("Next Steps:")
    print("1. Edit .env with your Telegram API ID/Hash.")
    print("2. Run your bot:")
    if os_name == "Windows":
        print(f"   {python_cmd} run.py")
    else:
        print(f"   ./start.sh  (or {python_cmd} run.py)")
        print("\nNote: For 24/7 on servers, use 'screen' or 'tmux':")
        print(f"   screen -S ghost {python_cmd} run.py")
    print("=" * 40)

if __name__ == "__main__":
    main()
