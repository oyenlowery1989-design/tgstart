import os
import zipfile
import datetime
import sys

# Auto-detect project root
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT_DIR)

import subprocess

def get_git_branch():
    try:
        branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).decode().strip()
        if branch in ['main', 'master']:
            return 'main'
        if branch == 'dev':
            return 'dev'
        return 'other'
    except:
        return 'other'

def create_backup():
    """
    Creates a timestamped ZIP backup of the Ghost Mirror project.
    Now organizes backups into subfolders by branch: main, dev, or other.
    """
    # Configuration
    timestamp = datetime.datetime.now().strftime("%Y-%b-%d_%I-%M%p")
    branch_folder = get_git_branch()
    backup_root = "data/backups"
    branch_dir = os.path.join(backup_root, branch_folder)
    
    zip_filename = f"ghost_mirror_{branch_folder}_{timestamp}.zip"
    zip_path = os.path.join(branch_dir, zip_filename)
    
    # Ensure backup directories exist
    if not os.path.exists(branch_dir):
        os.makedirs(branch_dir)
        print(f"Created branch backup directory: {branch_dir}")

    # Exclude patterns
    exclude_dirs = {
        '__pycache__', 
        '.git', 
        'venv', 
        '.venv', 
        'env',
        'backups', # Don't backup the backups!
        '.agent',
        '.gemini'
    }
    
    print(f"📦 Starting backup to: {zip_path}")
    print("----------------------------------------")
    
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk('.'):
                # Filter out excluded directories
                dirs[:] = [d for d in dirs if d not in exclude_dirs]
                
                for file in files:
                    file_path = os.path.join(root, file)
                    
                    # Skip the zip file itself if it's being created in the root (unlikely)
                    if file == zip_filename:
                        continue
                        
                    # Calculate archive path (relative to root)
                    arc_name = os.path.relpath(file_path, '.')
                    
                    # Add to zip
                    zipf.write(file_path, arc_name)
                    # print(f"  + Added: {arc_name}")
        
        size_mb = os.path.getsize(zip_path) / (1024 * 1024)
        print("----------------------------------------")
        print(f"✅ Backup successful!")
        print(f"📁 File: {zip_path}")
        print(f"⚖️  Size: {size_mb:.2f} MB")
        print("\nTIP: Since this is a local backup, it's a good idea to copy this ")
        print("zip file to an external drive or cloud storage occasionally.")

    except Exception as e:
        print(f"❌ Backup failed: {e}")

if __name__ == "__main__":
    create_backup()
