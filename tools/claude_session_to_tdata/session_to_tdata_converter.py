#!/usr/bin/env python3
"""
Telethon Session to Telegram Desktop tdata Converter
=====================================================
Converts a .session file (SQLite) to Telegram Desktop's tdata format.
Includes a keep-alive mechanism to maintain session activity.

REQUIREMENTS INSTALLATION (Windows):
------------------------------------
# Option 1: Use tgcrypto-pyrofork (precompiled for Windows)
pip install telethon opentele tgcrypto-pyrofork

# Option 2: If above fails, use without tgcrypto (slower but works)
pip install telethon opentele

# Alternative converter library (if opentele has issues):
pip install tgconvertor

USAGE:
------
1. Edit the configuration variables below
2. Run: python session_to_tdata_converter.py
3. The script will convert your session and keep it alive
"""

import os
import sys
import time
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('session_converter.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION - EDIT THESE VALUES
# ============================================================================

# Your Telethon session details
from dotenv import load_dotenv
load_dotenv()

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SESSION_NAME = os.getenv("DEFAULT_SESSION", os.path.join(ROOT_DIR, "sessions", "americandreamer8"))

# If it's a relative path, make it absolute relative to ROOT_DIR
if not os.path.isabs(SESSION_NAME):
    SESSION_NAME = os.path.join(ROOT_DIR, SESSION_NAME)

API_ID = int(os.getenv("MAIN_API_ID", os.getenv("API_ID", 12345)))
API_HASH = os.getenv("MAIN_API_HASH", os.getenv("API_HASH", "your_api_hash_here"))

# Output directory for tdata
OUTPUT_DIR = "./output_tdata"

# Keep-alive settings
KEEP_ALIVE_ENABLED = True
KEEP_ALIVE_INTERVAL = 300  # Send keep-alive every 5 minutes (300 seconds)
TARGET_WAIT_TIME_HOURS = 24  # Wait for 24 hours to gain session termination power

# ============================================================================
# DEPENDENCY CHECK
# ============================================================================

def check_dependencies():
    """Check if required libraries are installed."""
    missing_libs = []
    
    try:
        import telethon
        logger.info(f"✓ Telethon version: {telethon.__version__}")
    except ImportError:
        missing_libs.append("telethon")
    
    # Try to import conversion library
    converter_lib = None
    try:
        import opentele
        converter_lib = "opentele"
        logger.info(f"✓ OpenTele installed")
    except ImportError:
        try:
            import tgconvertor
            converter_lib = "tgconvertor"
            logger.info(f"✓ TGConvertor installed")
        except ImportError:
            missing_libs.append("opentele or tgconvertor")
    
    # Check for tgcrypto (optional but recommended)
    try:
        import tgcrypto
        logger.info(f"✓ TGCrypto installed (fast encryption)")
    except ImportError:
        logger.warning("⚠ TGCrypto not installed - encryption will be slower")
        logger.warning("  For Windows: pip install tgcrypto-pyrofork")
    
    if missing_libs:
        logger.error(f"✗ Missing required libraries: {', '.join(missing_libs)}")
        logger.error("Install with: pip install " + " ".join(missing_libs))
        return False, None
    
    return True, converter_lib

# ============================================================================
# SESSION CONVERSION USING OPENTELE
# ============================================================================

async def convert_with_opentele(session_file, api_id, api_hash, output_dir):
    """Convert session using OpenTele library."""
    from opentele.td import TDesktop
    from opentele.tl import TelegramClient
    from opentele.api import API, UseCurrentSession
    
    logger.info("Starting conversion with OpenTele...")
    
    try:
        # Create client from session file
        client = TelegramClient(session_file, api_id, api_hash)
        
        # Connect and get authorization
        await client.connect()
        
        if not await client.is_user_authorized():
            logger.error("Session is not authorized!")
            return None
        
        logger.info("Session is authorized. Getting user info...")
        me = await client.get_me()
        logger.info(f"Logged in as: {me.first_name} (@{me.username})")
        
        # Convert to Telegram Desktop format
        # Use Telegram Desktop's official API credentials (App ID: 2040)
        logger.info("Converting to tdata format...")
        tdesk = await client.ToTDesktop(
            flag=UseCurrentSession,
            api=API.TelegramDesktop  # Uses official Desktop API (2040)
        )
        
        # Save tdata
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        tdesk.SaveTData(str(output_path))
        logger.info(f"✓ tdata saved to: {output_path.absolute()}")
        
        return client  # Return client for keep-alive
        
    except Exception as e:
        logger.error(f"Conversion failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

# ============================================================================
# SESSION CONVERSION USING TGCONVERTOR (FALLBACK)
# ============================================================================

async def convert_with_tgconvertor(session_file, api_id, api_hash, output_dir):
    """Convert session using TGConvertor library (fallback option)."""
    from tgconvertor.manager import SessionManager
    
    logger.info("Starting conversion with TGConvertor...")
    
    try:
        manager = SessionManager()
        
        # Convert session
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        result = await manager.telethon_to_tdata(
            session_file=session_file,
            api_id=api_id,
            api_hash=api_hash,
            output_folder=str(output_path)
        )
        
        if result:
            logger.info(f"✓ tdata saved to: {output_path.absolute()}")
            
            # Reconnect to return active client for keep-alive
            from telethon import TelegramClient
            client = TelegramClient(session_file, api_id, api_hash)
            await client.connect()
            return client
        else:
            logger.error("Conversion failed")
            return None
            
    except Exception as e:
        logger.error(f"Conversion failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

# ============================================================================
# KEEP-ALIVE MECHANISM
# ============================================================================

async def keep_alive_loop(client, duration_hours=24, interval_seconds=300):
    """
    Keeps the session alive by periodically pinging Telegram servers.
    
    This prevents the session from timing out and helps it mature to gain
    administrative privileges (like terminating other sessions after 24h).
    
    Args:
        client: Active Telethon client
        duration_hours: How long to keep alive (default: 24 hours)
        interval_seconds: Time between pings (default: 5 minutes)
    """
    from telethon.tl.functions.updates import GetStateRequest
    
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=duration_hours)
    ping_count = 0
    
    logger.info("=" * 70)
    logger.info("KEEP-ALIVE MODE ACTIVATED")
    logger.info(f"Session will be kept alive until: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Ping interval: {interval_seconds} seconds ({interval_seconds/60:.1f} minutes)")
    logger.info("=" * 70)
    
    try:
        while datetime.now() < end_time:
            try:
                # Ping Telegram servers to keep session active
                await client(GetStateRequest())
                ping_count += 1
                
                elapsed = datetime.now() - start_time
                remaining = end_time - datetime.now()
                
                logger.info(f"[Ping #{ping_count}] Session active | "
                          f"Elapsed: {str(elapsed).split('.')[0]} | "
                          f"Remaining: {str(remaining).split('.')[0]}")
                
                # Check for active sessions every hour
                if ping_count % (3600 // interval_seconds) == 0:
                    await list_active_sessions(client)
                
                # Wait before next ping
                await asyncio.sleep(interval_seconds)
                
            except Exception as e:
                logger.error(f"Ping failed: {e}")
                # Try to reconnect
                if not client.is_connected():
                    logger.warning("Client disconnected. Reconnecting...")
                    await client.connect()
                await asyncio.sleep(10)  # Short delay before retry
        
        logger.info("=" * 70)
        logger.info(f"✓ Keep-alive completed! Total pings: {ping_count}")
        logger.info("Your session should now have administrative privileges.")
        logger.info("You can now terminate suspicious sessions.")
        logger.info("=" * 70)
        
    except KeyboardInterrupt:
        logger.info("\n⚠ Keep-alive interrupted by user")
    except Exception as e:
        logger.error(f"Keep-alive loop error: {e}")
        import traceback
        logger.error(traceback.format_exc())

# ============================================================================
# SESSION MONITORING
# ============================================================================

async def list_active_sessions(client):
    """List all active sessions on the account."""
    from telethon.tl.functions.account import GetAuthorizationsRequest
    
    try:
        auths = await client(GetAuthorizationsRequest())
        logger.info("\n" + "=" * 70)
        logger.info(f"ACTIVE SESSIONS: {len(auths.authorizations)}")
        logger.info("=" * 70)
        
        for i, auth in enumerate(auths.authorizations, 1):
            logger.info(f"\n[Session {i}]")
            logger.info(f"  Device: {auth.device_model}")
            logger.info(f"  Platform: {auth.platform} {auth.system_version}")
            logger.info(f"  App: {auth.app_name} {auth.app_version}")
            logger.info(f"  Location: {auth.country}, {auth.region}")
            logger.info(f"  IP: {auth.ip}")
            logger.info(f"  Current: {'YES' if auth.current else 'NO'}")
            logger.info(f"  Official: {'YES' if auth.official_app else 'NO'}")
            
            # Highlight suspicious sessions
            if "moldova" in auth.country.lower() and not auth.current:
                logger.warning(f"  ⚠ SUSPICIOUS SESSION FROM MOLDOVA DETECTED!")
        
        logger.info("=" * 70 + "\n")
        
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")

# ============================================================================
# MAIN FUNCTION
# ============================================================================

async def main():
    """Main execution function."""
    logger.info("=" * 70)
    logger.info("TELETHON SESSION TO TELEGRAM DESKTOP CONVERTER")
    logger.info("=" * 70)
    
    # Check dependencies
    deps_ok, converter_lib = check_dependencies()
    if not deps_ok:
        logger.error("Please install required dependencies first!")
        return
    
    # Validate session file
    session_file_path = f"{SESSION_NAME}.session"
    if not os.path.exists(session_file_path):
        logger.error(f"Session file not found: {session_file_path}")
        logger.error(f"Current directory: {os.getcwd()}")
        logger.error("Please ensure the session file exists and SESSION_NAME is correct.")
        return
    
    logger.info(f"✓ Session file found: {session_file_path}")
    logger.info(f"Using converter: {converter_lib}")
    
    # Convert session
    client = None
    if converter_lib == "opentele":
        client = await convert_with_opentele(SESSION_NAME, API_ID, API_HASH, OUTPUT_DIR)
    else:
        client = await convert_with_tgconvertor(SESSION_NAME, API_ID, API_HASH, OUTPUT_DIR)
    
    if not client:
        logger.error("Conversion failed. Exiting.")
        return
    
    logger.info("\n✓ Conversion successful!")
    logger.info(f"Your tdata folder is ready at: {Path(OUTPUT_DIR).absolute()}")
    logger.info("\nTo use with Telegram Desktop:")
    logger.info("1. Close Telegram Desktop if running")
    logger.info("2. Navigate to Telegram Desktop Portable folder")
    logger.info("3. Replace the 'tdata' folder with your generated folder")
    logger.info("4. Start Telegram Desktop\n")
    
    # List current sessions
    await list_active_sessions(client)
    
    # Keep-alive loop
    if KEEP_ALIVE_ENABLED:
        logger.info("Starting keep-alive mode to mature your session...")
        logger.info("This will help you gain the ability to terminate other sessions.\n")
        
        try:
            await keep_alive_loop(
                client, 
                duration_hours=TARGET_WAIT_TIME_HOURS,
                interval_seconds=KEEP_ALIVE_INTERVAL
            )
        except KeyboardInterrupt:
            logger.info("\nKeep-alive stopped by user.")
        
        # Final session check
        logger.info("\nFinal session status:")
        await list_active_sessions(client)
    
    # Cleanup
    await client.disconnect()
    logger.info("\n✓ Script completed successfully!")

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    # Run the async main function
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n\nScript interrupted by user. Goodbye!")
    except Exception as e:
        logger.error(f"\nFatal error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
