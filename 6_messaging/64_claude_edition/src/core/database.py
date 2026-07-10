
"""
FILE: src/core/database.py
PURPOSE: Compatibility bridge while transitioning to specialized modules.
"""
from src.core.user_intelligence import (
    load_users_index, 
    update_user_index, 
    bio_worker, 
    record_user_seen_sender, 
    record_user_seen_mention, 
    get_user_display_name, 
    get_user_info_string,
    users_index_cache,
    processed_bios,
    bio_fetch_queue
)
# Note: For new scripts, import directly from src.core.user_intelligence
