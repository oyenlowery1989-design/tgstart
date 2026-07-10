# Telegram Automation Scripts

A collection of Python scripts for automating various Telegram operations using Telethon.

## 📁 Project Structure

```
telegram-start/
├── 1_login/              # Authentication scripts
├── 2_verify/             # Login verification scripts
├── 3_chat_management/    # Chat listing and group user management
├── 4_scraping/           # Link scraping utilities
├── 5_monitoring/         # Group statistics and monitoring
├── 6_messaging/          # Message mirroring and reading
├── 7_utilities/          # User participation and message management
├── utils/                # Shared utility functions
├── docs/                 # Documentation files
├── tools/                # Session conversion tools
├── sessions/             # Telegram session files
├── tdata_exports/        # Exported Telegram data
├── 99_data/              # General data storage
├── .env                  # Environment variables (API credentials)
└── run.py                # Main entry point
```

## 🚀 Quick Start

1. **Setup Environment**

   ```bash
   # See docs/QUICK_START_WSL.md for WSL setup
   # See docs/WSL_SETUP_GUIDE.md for detailed WSL instructions
   ```

2. **Configure API Credentials**
   - Edit `.env` file with your Telegram API credentials
   - See `docs/ACTION_REQUIRED.md` for required actions

3. **Run Scripts**
   ```bash
   python run.py
   ```

## 📚 Script Categories

### 1. Login & Authentication (`1_login/`)

- **1_login.py** - Standard phone number login
- **1_login_by_qr.py** - QR code-based login

### 2. Verification (`2_verify/`)

- **2_verify_login.py** - Basic login verification
- **2_verify_login_advanced.py** - Advanced verification with detailed checks

### 3. Chat Management (`3_chat_management/`)

- **30_list_chats.py** - List all accessible chats/groups
- **31_list_group_users.py** - List users in specific groups (exports to CSV with member count)
- Data stored in `30_data/` and `31_data/`

### 4. Scraping (`4_scraping/`)

- **40_scrape_links.py** - Basic link scraping from chats
- **41_scrape_links_advanced.py** - Advanced scraping with filters
- Data stored in `41_data/`

### 5. Monitoring (`5_monitoring/`)

- **50_group_stats.py** - Analyze group statistics and activity

### 6. Messaging (`6_messaging/`)

- **64_claude_edition/** - Ghost Mirror, forensics edition (edit/delete tracking, stealth read)
- **65/** - Ghost Mirror v4.0, FastAPI dashboard + SQLite backend, runs as bot + dashboard pair
- See `6_messaging/README.md` for details

### 7. Utilities (`7_utilities/`)

- **70_purge_my_messages.py** - Delete your messages from chats
- **71_find_my_participation.py** - Find chats where you've participated

## 🛠️ Utilities

### Shared Utils (`utils/`)

- **tg_utils.py** - Telegram-specific helper functions
- **ui_utils.py** - User interface utilities

### Tools (`tools/`)

- **convert_session.py** - Convert between session formats
- **claude_session_to_tdata/** - Claude session converter
- **claude_linux_session_to_tdata_working/** - Linux-specific converter

## 📖 Documentation

See the `docs/` folder for detailed documentation:

- **ACTION_REQUIRED.md** - Required setup actions
- **CODE_OVERVIEW.md** - Code structure overview
- **GUIDELINES.md** - Development guidelines
- **QUICK_START_WSL.md** - Quick WSL setup guide
- **WSL_SETUP_GUIDE.md** - Detailed WSL instructions
- **TODO.md** - Planned features and improvements
- **support_bot_implementation_plan.md** - Support bot roadmap

## 🔒 Security

- Never commit `.env` file to version control
- Keep session files secure (in `sessions/` folder)
- Review `docs/GUIDELINES.md` for security best practices

## 📝 Generated Files

The following files are generated during script execution:

- `dialogs.csv` - Exported dialog list
- `links.csv` - Scraped links
- `session_converter.log` - Session conversion logs

## 🤝 Contributing

See `docs/GUIDELINES.md` for contribution guidelines and coding standards.
