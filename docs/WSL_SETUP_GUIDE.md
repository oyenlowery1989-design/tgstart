# WSL Setup Guide for Telegram Session Converter

## ✅ Why WSL?

Your code works perfectly on Linux but has `tgcrypto` compilation issues on Windows. WSL (Windows Subsystem for Linux) gives you a native Linux environment inside Windows without dual-booting or VMs.

## 🚀 Installation Steps

### Step 1: Install WSL (Currently Running)

```powershell
wsl --install
```

- This installs Ubuntu by default
- **You'll need to restart your computer after installation completes**

### Step 2: After Restart - Initial Setup

1. Open "Ubuntu" from the Start Menu
2. Create a username and password when prompted
3. Wait for initial setup to complete

### Step 3: Update Ubuntu

```bash
sudo apt update
sudo apt upgrade -y
```

### Step 4: Install Python and Dependencies

```bash
# Install Python and pip
sudo apt install python3-pip python3-venv -y

# Install the required packages (tgcrypto will compile perfectly!)
pip3 install telethon opentele tgcrypto
```

## 📁 Accessing Your Windows Files from WSL

Your Windows drives are automatically mounted in WSL:

- `C:\` → `/mnt/c/`
- `E:\` → `/mnt/e/`

So your project at `E:\vibecode\telegram-start` is accessible at:

```bash
/mnt/e/vibecode/telegram-start
```

## 🔄 Working with Your Project in WSL

### Option A: Work Directly from Windows Location

```bash
# Navigate to your project
cd /mnt/e/vibecode/telegram-start

# Run your Python scripts
python3 convert_session.py
```

### Option B: Copy to WSL Home (Faster Performance)

```bash
# Copy project to WSL home directory
cp -r /mnt/e/vibecode/telegram-start ~/telegram-start
cd ~/telegram-start

# Run your scripts
python3 convert_session.py

# Copy results back to Windows when done
cp -r tdata_exports /mnt/e/vibecode/telegram-start/
```

## 🛠️ Quick Commands Reference

### Navigate to your project:

```bash
cd /mnt/e/vibecode/telegram-start
```

### Create a Python virtual environment (recommended):

```bash
python3 -m venv venv
source venv/bin/activate
pip install telethon opentele tgcrypto
```

### Run your scripts:

```bash
python3 convert_session.py
```

### Check installed packages:

```bash
pip3 list | grep -E "telethon|opentele|tgcrypto"
```

### Exit WSL:

```bash
exit
```

## 💡 Tips

1. **File Editing**: You can edit files in WSL using:
   - Windows editors (VS Code, Notepad++) - just open files from `\\wsl$\Ubuntu\home\yourusername\`
   - Linux editors: `nano`, `vim`, or install VS Code in WSL: `code .`

2. **Performance**: Files in WSL's native filesystem (`~/`) are faster than accessing Windows files (`/mnt/e/`)

3. **Keep PC On**: For 24-hour keep-alive operations, your PC must stay on (don't sleep/hibernate)

4. **WSL Commands from Windows**:
   ```powershell
   # Run a command in WSL from PowerShell
   wsl python3 /mnt/e/vibecode/telegram-start/convert_session.py
   ```

## 🔧 Troubleshooting

### If WSL doesn't start:

```powershell
# Check WSL status
wsl --status

# List installed distributions
wsl --list --verbose

# Set Ubuntu as default
wsl --set-default Ubuntu
```

### If tgcrypto still fails:

```bash
# Install build essentials
sudo apt install build-essential python3-dev -y

# Then reinstall
pip3 install --upgrade --force-reinstall tgcrypto
```

## 🎯 Next Steps After WSL Installation

1. **Restart your computer** (required after first WSL install)
2. Open "Ubuntu" from Start Menu
3. Set up username/password
4. Run the commands in Step 3 and 4 above
5. Navigate to your project and run your scripts!

## 📚 Additional Resources

- [WSL Documentation](https://docs.microsoft.com/en-us/windows/wsl/)
- [WSL Best Practices](https://docs.microsoft.com/en-us/windows/wsl/setup/environment)
- [Accessing Linux files from Windows](https://docs.microsoft.com/en-us/windows/wsl/filesystems)
