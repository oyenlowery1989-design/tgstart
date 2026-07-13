
"""
FILE: src/core/storage.py
PURPOSE: Low-level file system and JSON storage utilities.
"""
import os
import json
import traceback
from src.core.logger import log_error

def ensure_dir(path):
    """Ensures a directory exists."""
    os.makedirs(path, exist_ok=True)

def save_json_atomic(file_path, data, indent=2):
    """
    Writes data to a temporary file and then renames it to target.
    This prevents file corruption during crashes.
    """
    temp_file = file_path + ".tmp"
    try:
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        os.replace(temp_file, file_path)
        return True
    except Exception as e:
        log_error("storage_save_atomic", f"Failed to save {file_path}: {e}", traceback.format_exc())
        if os.path.exists(temp_file):
            os.remove(temp_file)
        return False
