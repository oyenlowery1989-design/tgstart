# Telethon to Telegram Desktop Converter - Windows Setup Guide

## 📋 Prerequisites

1. **Python 3.8 or higher** installed
   - Download from: https://www.python.org/downloads/
   - During installation, CHECK "Add Python to PATH"

2. **Telegram API Credentials**
   - Visit: https://my.telegram.org/apps
   - Log in with your phone number
   - Create a new application to get:
     - `api_id` (number)
     - `api_hash` (string)

3. **Your Telethon Session File**
   - Should be a `.session` file (SQLite database)
   - Place it in the same folder as the converter script

## 🔧 Installation Steps

### Step 1: Install Required Libraries

Open Command Prompt or PowerShell in the script directory and run:

```bash
# Recommended: Install with tgcrypto-pyrofork (precompiled for Windows)
pip install telethon opentele tgcrypto-pyrofork

# Alternative if above fails:
pip install telethon opentele --no-deps
pip install pyaes rsa pyasn1
```

### Step 2: Handle Common Windows Errors

#### Error: "Microsoft Visual C++ 14.0 or greater is required"

This happens when trying to install `tgcrypto`. Solutions:

**Solution A (Easiest):** Use the precompiled version
```bash
pip uninstall tgcrypto  # Remove problematic version
pip install tgcrypto-pyrofork  # Install Windows-compatible version
```

**Solution B:** Use pure Python (slower but works)
```bash
# Just skip tgcrypto entirely - the script will work without it
pip install telethon opentele
```

**Solution C:** Install build tools (if you want native tgcrypto)
```bash
# Download and install Visual Studio Build Tools
# https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022
# Then install tgcrypto normally
```

#### Error: "No module named 'opentele'"

```bash
pip install opentele
```

If that fails, try the alternative converter:
```bash
pip install tgconvertor
```

## 📝 Configuration

### Step 1: Edit the Script

Open `session_to_tdata_converter.py` and modify these lines:

```python
# Your Telethon session details
SESSION_NAME = "my_account"  # If your file is "my_account.session"
API_ID = 12345678            # Your numeric API ID
API_HASH = "abcdef123456789" # Your API hash string

# Output directory for tdata
OUTPUT_DIR = "./output_tdata"  # Where to save the tdata folder

# Keep-alive settings
KEEP_ALIVE_ENABLED = True           # Set to False to skip keep-alive
KEEP_ALIVE_INTERVAL = 300           # Ping every 5 minutes
TARGET_WAIT_TIME_HOURS = 24         # Wait for 24 hours
```

### Step 2: Verify Your Session File

Make sure your session file is named correctly:
- If SESSION_NAME = "my_account", the file should be "my_account.session"
- Place it in the same folder as the converter script

## 🚀 Usage

### Method 1: Run Directly

```bash
python session_to_tdata_converter.py
```

### Method 2: Use the Batch File (Windows)

Double-click `run_converter.bat`

## 📊 What the Script Does

1. **Validates** your session file and dependencies
2. **Converts** your Telethon session to Telegram Desktop's tdata format
3. **Maps** the session to Telegram Desktop's official API (ID: 2040)
4. **Monitors** active sessions and identifies suspicious ones
5. **Keeps alive** your session for 24 hours to gain administrative power
6. **Logs** everything to `session_converter.log`

## ⏰ Keep-Alive Feature

### Why 24 Hours?

Telegram has security measures where new sessions must wait ~24 hours before they can:
- Terminate other active sessions
- Access full account management features

### What the Keep-Alive Does

- Sends a ping to Telegram every 5 minutes
- Prevents your session from timing out
- Shows elapsed and remaining time
- Lists active sessions every hour
- Highlights suspicious sessions (like the Moldova one)

### To Stop Keep-Alive Early

Press `Ctrl+C` - the script will save your tdata and exit gracefully

## 📁 Using the Generated tdata

### For Telegram Desktop Portable:

1. Download Telegram Desktop Portable
2. Close Telegram Desktop if running
3. Navigate to the portable folder
4. Backup the original `tdata` folder (optional)
5. Replace it with your `output_tdata` folder (rename to `tdata`)
6. Launch Telegram Desktop - you'll be logged in!

### For Regular Telegram Desktop:

Windows tdata location:
```
C:\Users\YourUsername\AppData\Roaming\Telegram Desktop\tdata
```

1. Close Telegram Desktop
2. Backup the original tdata folder
3. Replace with your generated tdata
4. Launch Telegram Desktop

## 🔍 Monitoring Sessions

The script will show all your active sessions:

```
ACTIVE SESSIONS: 3
================================

[Session 1]
  Device: PC
  Platform: Windows 10
  App: Telegram Desktop 4.x
  Location: United States, California
  IP: 1.2.3.4
  Current: YES
  Official: YES

[Session 2]
  Device: Android
  Platform: Android 12
  App: Telegram 10.x
  Location: Moldova, Chișinău  ⚠ SUSPICIOUS
  IP: 5.6.7.8
  Current: NO
  Official: YES
```

## 🛡️ Security Notes

### About the Moldova Session

- The script will **highlight** suspicious sessions
- After 24 hours, you can terminate it via Telegram Desktop
- Or use the official app: Settings → Privacy → Active Sessions

### Session Lifetime

- Your converted session will be a **logged-in session**
- It will appear as "Telegram Desktop" in your active sessions
- You can revoke it anytime from Settings → Privacy → Active Sessions

## 🐛 Troubleshooting

### "Session file not found"

- Check that `SESSION_NAME` matches your file (without .session extension)
- Ensure the .session file is in the same directory as the script

### "Session is not authorized"

- Your session file might be expired or corrupted
- Try logging in again with Telethon to refresh it

### "Conversion failed"

Check the log file `session_converter.log` for details. Common issues:
- Missing dependencies
- Corrupted session file
- Network connectivity issues

### Script hangs during conversion

- This is normal for first connection (can take 30-60 seconds)
- Check your internet connection
- Review the log file for specific errors

### Keep-alive stops unexpectedly

- Network disconnection
- Telegram server issues
- The script will attempt to reconnect automatically
- Check `session_converter.log` for error details

## 📞 Getting Help

If you encounter issues:

1. Check `session_converter.log` for error messages
2. Verify all configuration values are correct
3. Ensure your API credentials are valid
4. Try running with `KEEP_ALIVE_ENABLED = False` first

## ⚙️ Advanced Options

### Change Ping Frequency

```python
KEEP_ALIVE_INTERVAL = 180  # Ping every 3 minutes instead of 5
```

### Extend Keep-Alive Duration

```python
TARGET_WAIT_TIME_HOURS = 48  # Run for 48 hours instead of 24
```

### Disable Keep-Alive

```python
KEEP_ALIVE_ENABLED = False  # Just convert and exit
```

## 📜 Log Files

All activity is logged to `session_converter.log`:
- Timestamps for all operations
- Session information
- Ping statistics
- Error messages (if any)

## 🎯 Next Steps After Conversion

1. **Verify the login** - Open Telegram Desktop with the new tdata
2. **Check active sessions** - Look for your old sessions
3. **Wait 24 hours** - Let your new session mature
4. **Terminate suspicious sessions** - Use Settings → Privacy → Active Sessions
5. **Enable 2FA** - Add extra security to your account

## ⚠️ Important Warnings

- Keep your API credentials private
- Don't share your .session files
- Always backup your original tdata before replacing
- The Moldova session won't disappear immediately - you need admin rights to terminate it

## 🔐 Privacy & Security

- Your credentials never leave your computer
- All operations are done locally
- No data is sent to third parties
- The script only communicates with official Telegram servers
