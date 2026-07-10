# 🔄 Telethon Session to Telegram Desktop Converter

A robust Python script that converts Telethon `.session` files (SQLite) into Telegram Desktop's `tdata` format with built-in keep-alive functionality.

## ✨ Features

- ✅ **Converts** Telethon sessions to Telegram Desktop format
- 🔐 **Maps** to official Telegram Desktop API (App ID: 2040)
- 🔄 **Keep-Alive** mechanism to prevent session timeout
- 📊 **Monitors** active sessions and identifies suspicious logins
- 🪟 **Windows-friendly** with tgcrypto-pyrofork (no C++ compiler needed)
- 📝 **Detailed logging** of all operations
- 🛡️ **Session maturation** - wait 24h to gain admin rights

## 🎯 Use Case

Perfect for users who:
- Need to use their Telethon session in Telegram Desktop
- Want to terminate suspicious sessions (like that Moldova login!)
- Need their session to mature for 24h to gain admin privileges
- Want a reliable, automated keep-alive solution

## 📦 What's Included

```
📁 session-converter/
├── 📄 session_to_tdata_converter.py  # Main conversion script
├── 📄 diagnostic.py                   # Environment checker
├── 📄 run_converter.bat               # Windows launcher
├── 📄 requirements.txt                # Python dependencies
├── 📄 README.md                       # This file
└── 📄 WINDOWS_SETUP_GUIDE.md         # Detailed setup guide
```

## 🚀 Quick Start

### 1️⃣ Check Your Environment

```bash
python diagnostic.py
```

This will verify:
- ✅ Python version (3.8+)
- ✅ Required packages
- ✅ Session files
- ✅ Script integrity

### 2️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

**Windows users:** If installation fails, use:
```bash
pip install telethon opentele tgcrypto-pyrofork
```

### 3️⃣ Configure the Script

Edit `session_to_tdata_converter.py`:

```python
SESSION_NAME = "your_session"     # Without .session extension
API_ID = 12345678                 # Your API ID from my.telegram.org
API_HASH = "your_api_hash"        # Your API hash
```

### 4️⃣ Run the Converter

**Windows:**
```bash
run_converter.bat
```

**Linux/Mac:**
```bash
python session_to_tdata_converter.py
```

## 📋 Requirements

- Python 3.8+
- Telethon session file (`.session`)
- Telegram API credentials ([get them here](https://my.telegram.org/apps))
- Active internet connection

## 🔧 Installation Options

### Option 1: Standard Installation (Recommended)

```bash
pip install telethon opentele tgcrypto-pyrofork
```

### Option 2: Without TGCrypto (if compilation fails)

```bash
pip install telethon opentele
```

The script works without `tgcrypto`, just with slower encryption.

### Option 3: Alternative Converter

```bash
pip install telethon tgconvertor
```

The script will automatically detect and use `tgconvertor` if `opentele` is unavailable.

## 🎛️ Configuration Options

| Setting | Description | Default |
|---------|-------------|---------|
| `SESSION_NAME` | Your .session filename (without extension) | Required |
| `API_ID` | Telegram API ID | Required |
| `API_HASH` | Telegram API hash | Required |
| `OUTPUT_DIR` | Where to save tdata folder | `./output_tdata` |
| `KEEP_ALIVE_ENABLED` | Enable/disable keep-alive loop | `True` |
| `KEEP_ALIVE_INTERVAL` | Seconds between pings | `300` (5 min) |
| `TARGET_WAIT_TIME_HOURS` | How long to keep alive | `24` hours |

## 📊 What the Script Does

### Phase 1: Conversion
1. Validates your session file
2. Connects to Telegram with your session
3. Converts to Telegram Desktop's tdata format
4. Maps to official Desktop API (ID: 2040)
5. Saves to `output_tdata` folder

### Phase 2: Monitoring
1. Lists all active sessions
2. Highlights suspicious logins
3. Shows device info, location, IP

### Phase 3: Keep-Alive (Optional)
1. Sends ping every 5 minutes
2. Prevents session timeout
3. Tracks elapsed and remaining time
4. Logs all activity
5. Helps session mature to gain admin rights

## 🕒 Why Keep-Alive for 24 Hours?

Telegram implements security measures where **new sessions cannot immediately**:
- ❌ Terminate other active sessions
- ❌ Access full account management
- ❌ Change certain security settings

After ~24 hours, your session gains **administrative privileges** to:
- ✅ Terminate suspicious sessions (like that Moldova one!)
- ✅ Full account control
- ✅ Enhanced security options

The keep-alive loop ensures your session:
- Stays active during the waiting period
- Doesn't time out
- Matures to gain these privileges

## 📁 Using the Generated tdata

### Telegram Desktop Portable:

1. Close Telegram Desktop
2. Go to your Telegram Portable folder
3. Backup original `tdata` (optional)
4. Rename `output_tdata` → `tdata`
5. Launch Telegram Desktop

### Regular Telegram Desktop:

**Windows:**
```
C:\Users\YourName\AppData\Roaming\Telegram Desktop\tdata
```

**Mac:**
```
~/Library/Application Support/Telegram Desktop/tdata
```

**Linux:**
```
~/.local/share/TelegramDesktop/tdata
```

## 🛡️ Security Features

- ✅ Highlights suspicious sessions
- ✅ Monitors login locations
- ✅ Tracks device information
- ✅ Identifies non-official apps
- ✅ Enables session termination after 24h
- ✅ Complete activity logging

## 📝 Logging

All operations are logged to `session_converter.log`:

```
2024-02-09 10:30:15 - INFO - Session authorized
2024-02-09 10:30:20 - INFO - Logged in as: John Doe (@johndoe)
2024-02-09 10:30:25 - INFO - Converting to tdata format...
2024-02-09 10:30:45 - INFO - ✓ tdata saved to: ./output_tdata
2024-02-09 10:30:50 - INFO - KEEP-ALIVE MODE ACTIVATED
2024-02-09 10:30:50 - INFO - Session will be kept alive until: 2024-02-10 10:30:50
2024-02-09 10:35:50 - INFO - [Ping #1] Session active | Elapsed: 0:05:00 | Remaining: 23:55:00
```

## ⚠️ Troubleshooting

### "Session file not found"
- Ensure `SESSION_NAME` matches your file (without `.session`)
- Put the `.session` file in the same folder as the script

### "Module not found" errors
Run the diagnostic tool:
```bash
python diagnostic.py
```

### "Session is not authorized"
- Your session might be expired
- Try logging in again with Telethon

### Windows compilation errors
Use the precompiled version:
```bash
pip install tgcrypto-pyrofork
```

### Keep-alive stops unexpectedly
- Check `session_converter.log`
- Verify internet connection
- The script will auto-reconnect

## 🔍 Monitoring Active Sessions

Example output:

```
ACTIVE SESSIONS: 3
========================================================================

[Session 1]
  Device: PC
  Platform: Windows 10
  App: Telegram Desktop 4.12
  Location: United States, New York
  IP: 1.2.3.4
  Current: YES
  Official: YES

[Session 2]
  Device: Android
  Platform: Android 13
  App: Telegram 10.5
  Location: Moldova, Chișinău  ⚠ SUSPICIOUS SESSION FROM MOLDOVA DETECTED!
  IP: 5.6.7.8
  Current: NO
  Official: YES
```

## 🎯 Next Steps After Conversion

1. ✅ **Verify login** - Open Telegram Desktop with new tdata
2. ⏳ **Wait 24 hours** - Let your session mature
3. 🔍 **Check sessions** - Settings → Privacy & Security → Active Sessions
4. ❌ **Terminate Moldova session** - After 24h, you can remove it
5. 🔐 **Enable 2FA** - Add two-factor authentication for extra security

## 💡 Pro Tips

1. **Run overnight**: Start the script before bed, wake up with admin rights
2. **Monitor the log**: Check `session_converter.log` for any issues
3. **Backup tdata**: Always backup original tdata before replacing
4. **Use 2FA**: Enable two-factor authentication after securing your account
5. **Check regularly**: Review active sessions weekly

## ⚡ Advanced Usage

### Custom ping interval (every 3 minutes)
```python
KEEP_ALIVE_INTERVAL = 180
```

### Extended keep-alive (48 hours)
```python
TARGET_WAIT_TIME_HOURS = 48
```

### Disable keep-alive (just convert)
```python
KEEP_ALIVE_ENABLED = False
```

### Stop keep-alive early
Press `Ctrl+C` - conversion will be saved, keep-alive will stop

## 🤝 Support

Having issues? Try these steps:

1. Run `python diagnostic.py` to check your setup
2. Review `session_converter.log` for error details
3. Check `WINDOWS_SETUP_GUIDE.md` for detailed instructions
4. Ensure API credentials are correct
5. Verify session file is not corrupted

## ⚖️ Legal & Ethics

- ✅ Use only on **your own** Telegram accounts
- ✅ Respect Telegram's Terms of Service
- ✅ Secure your API credentials
- ❌ Don't share session files
- ❌ Don't use for unauthorized access

## 🔒 Privacy

- Your credentials **never leave your computer**
- All operations are **local**
- No data sent to third parties
- Only communicates with **official Telegram servers**

## 📜 License

This script is provided as-is for educational and personal use. Always comply with Telegram's Terms of Service.

## 🙏 Credits

Built with:
- [Telethon](https://github.com/LonamiWebs/Telethon) - Telegram client library
- [OpenTele](https://github.com/thedemons/opentele) - Telegram Desktop converter
- [TGCrypto](https://github.com/pyrogram/tgcrypto) - Fast encryption

---

**Made with ❤️ for secure Telegram session management**

*Last updated: February 2026*
