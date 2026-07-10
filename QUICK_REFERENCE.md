# Quick Reference Guide

## 🎯 Common Tasks

### First Time Setup

```powershell
# Windows
.\setup.ps1

# Linux/WSL
bash setup.sh
```

### Daily Usage

```powershell
# Activate environment
.\venv\Scripts\Activate.ps1  # Windows
source venv/bin/activate      # Linux/WSL

# Run main script
python run.py
```

## 📂 Where to Find Things

| What you need       | Where to look        |
| ------------------- | -------------------- |
| Login to Telegram   | `1_login/`           |
| Verify login status | `2_verify/`          |
| List chats/groups   | `3_chat_management/` |
| Scrape links        | `4_scraping/`        |
| Group statistics    | `5_monitoring/`      |
| Mirror messages     | `6_messaging/`       |
| Manage messages     | `7_utilities/`       |
| Helper functions    | `utils/`             |
| Documentation       | `docs/`              |
| Session converters  | `tools/`             |

## 🔧 Script Quick Reference

### Authentication

```bash
# Login with phone
python 1_login/1_login.py

# Login with QR code
python 1_login/1_login_by_qr.py

# Verify login
python 2_verify/2_verify_login.py
```

### Chat Management

```bash
# List all chats
python 3_chat_management/30_list_chats.py

# List group users
python 3_chat_management/31_list_group_users.py
```

### Scraping

```bash
# Basic link scraping
python 4_scraping/40_scrape_links.py

# Advanced scraping
python 4_scraping/41_scrape_links_advanced.py
```

### Monitoring

```bash
# Group statistics
python 5_monitoring/50_group_stats.py
```

### Messaging

```bash
# Ghost Mirror - Claude Edition (forensics)
python run.py  # choice 7 -> 6_messaging/64_claude_edition/run.py

# Ghost Mirror - Dashboard v4.0 (bot + web UI)
python run.py  # choice 8 -> 6_messaging/65/ (run.py + dashboard.py)
```

### Utilities

```bash
# Delete your messages
python 7_utilities/70_purge_my_messages.py

# Find your participation
python 7_utilities/71_find_my_participation.py
```

## 🔑 Environment Variables

Edit `.env` file:

```env
API_ID=your_api_id_here
API_HASH=your_api_hash_here
PHONE=+1234567890
```

Get credentials from: https://my.telegram.org/apps

## 📊 Output Files

| File             | Description       | Location                     |
| ---------------- | ----------------- | ---------------------------- |
| `dialogs.csv`    | Chat list export  | Root                         |
| `links.csv`      | Scraped links     | Root                         |
| `30_dialogs.csv` | Chat details      | `3_chat_management/30_data/` |
| `31_users_*.csv` | Group users       | `3_chat_management/31_data/` |
| `41_links.csv`   | Advanced scraping | `4_scraping/41_data/`        |
| `*.json`         | Config files      | `6_messaging/*/`             |

## 🆘 Troubleshooting

### Import Errors

```bash
# Reinstall dependencies
pip install -r requirements.txt
```

### Session Issues

```bash
# Delete old session and login again
rm sessions/*.session
python 1_login/1_login.py
```

### Permission Errors (WSL)

```bash
# Make scripts executable
chmod +x setup.sh
chmod +x wsl_setup.sh
```

## 📚 Documentation Files

- `README.md` - Main project documentation
- `ORGANIZATION.md` - Structure and improvements
- `docs/ACTION_REQUIRED.md` - Required setup actions
- `docs/QUICK_START_WSL.md` - WSL quick start
- `docs/WSL_SETUP_GUIDE.md` - Detailed WSL guide
- `docs/GUIDELINES.md` - Development guidelines
- `docs/CODE_OVERVIEW.md` - Code structure
- `docs/TODO.md` - Future improvements

## 🚀 Pro Tips

1. **Always activate venv** before running scripts
2. **Keep .env secure** - never commit to git
3. **Backup sessions** regularly
4. **Check docs/** for detailed guides
5. **Use QR login** for faster authentication
6. **Review output** in respective `*_data/` folders

## 🔗 Useful Links

- Telegram API: https://my.telegram.org/apps
- Telethon Docs: https://docs.telethon.dev/
- Python Docs: https://docs.python.org/3/
