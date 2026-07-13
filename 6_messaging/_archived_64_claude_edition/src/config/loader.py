
"""
FILE: src/config/loader.py
PURPOSE: Handles loading and saving the JSON configuration file (mirrors.json).
"""
import os
import json

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(ROOT_DIR, "data")
CONFIG_FILE = os.path.join(DATA_DIR, "mirrors.json")

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return []
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return []

def save_config(pairs_data):
    """
    Saves ghost mirror pairs to mirrors.json with automatic deduplication.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Deduplicate: same source and same destination
    unique_pairs = []
    seen = set()
    for p in pairs_data:
        # Create a unique key for this pair
        key = (str(p.get('source_id')), str(p.get('dest_id')))
        if key not in seen:
            unique_pairs.append(p)
            seen.add(key)
    
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(unique_pairs, f, indent=2)
    except Exception as e:
        print(f"Error saving config: {e}")
