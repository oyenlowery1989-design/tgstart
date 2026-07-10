
# ============================================================
# USER CONFIGURABLE SETTINGS
# ============================================================

# Performance Tuning
DELETION_CHECK_INTERVAL = 60  # Seconds between deletion checks (default: 60)
MAX_HISTORY_SIZE = 5000       # Max messages to track per pair (default: 5000)
BIO_WORKER_DELAY = 3          # Seconds between bio fetches (default: 3)
MAX_BIO_QUEUE_SIZE = 1000     # Max users in bio fetch queue (default: 1000)

# Timezone Configuration
TIMEZONE_STR = "America/Chicago"  # Timezone for logging (default: America/Chicago)

# Log Rotation
MAX_LOG_AGE_DAYS = 30  # Days before archiving logs (default: 30)

# ============================================================
# EVENT NOTIFICATION TOGGLES
# ============================================================
# Control which events trigger notifications in terminal and backup chat
# Set to False to disable notifications (events are still logged to disk)

# --- Message Events ---
NOTIFY_NEW_MESSAGES = True    # When someone sends a new message
NOTIFY_EDITS = True           # When someone edits their message
NOTIFY_DELETIONS = True       # When someone deletes their message

# --- User Movement Events ---
NOTIFY_JOINS = True           # When a user joins the group voluntarily
NOTIFY_LEAVES = True          # When a user leaves the group voluntarily
NOTIFY_KICKS = True           # When an admin kicks/removes a user
NOTIFY_ADDS = True            # When an admin adds a user to the group

# --- Permission & Restriction Events ---
NOTIFY_BANS = True            # When an admin bans a user completely
NOTIFY_RESTRICTIONS = True    # When an admin restricts a user (mute, limit permissions)
NOTIFY_UNRESTRICTIONS = True  # When an admin removes restrictions from a user
NOTIFY_PROMOTIONS = True      # When an admin promotes a user to admin
NOTIFY_DEMOTIONS = True       # When an admin demotes an admin to regular user

# --- Group Settings Events ---
NOTIFY_INVITE_LINKS = True        # When invite links are created, revoked, or edited
NOTIFY_BOT_EVENTS = True          # When bots are added or removed from the group

# --- Other Events ---
NOTIFY_REACTIONS = True       # When someone reacts to a message (👍, ❤️, etc.)
MIRROR_REACTIONS_AS_TEXT = True # Whether to send a text notification for reactions in the mirror
