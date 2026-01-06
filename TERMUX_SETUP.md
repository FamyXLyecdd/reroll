# The Forge Automation - Termux Edition

Automated Roblox account creation and race rerolling for The Forge game.

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    TERMUX (Your Phone)                     │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  1. termux_signup.py      Creates Roblox accounts          │
│         │                 using Firefox + Selenium         │
│         ▼                                                  │
│  2. login_queue.txt       Stores username:password         │
│         │                                                  │
│         ▼                                                  │
│  3. orchestrator.py       Controls cloud phone via ADB     │
│         │                                                  │
│         ▼                                                  │
│  ┌──────────────────────────────────────────────────────┐ │
│  │            CLOUD PHONE (ugphone/vsphone)             │ │
│  │  - Roblox App                                        │ │
│  │  - Delta Executor (auto-inject)                      │ │
│  │  - TheForge_Auto.lua (in Delta's autoexec)           │ │
│  └──────────────────────────────────────────────────────┘ │
│         │                                                  │
│         ▼                                                  │
│  4. Discord Webhook       Receives mythic/legendary finds  │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

## 📱 Termux Setup

### 1. Install Required Packages

```bash
# Update Termux
pkg update && pkg upgrade

# Install x11-repo for Firefox
pkg install x11-repo

# Install Firefox and geckodriver
pkg install firefox
pkg install geckodriver

# Install Python
pkg install python

# Install pip packages
pip install selenium requests

# For cloud phone control (optional)
pkg install android-tools
```

### 2. Clone/Copy Files

Copy these files to your Termux home directory:
- `termux_signup.py` - Account creator
- `orchestrator.py` - Cloud phone controller
- `TheForge_Auto.lua` - Game script

### 3. Configure

Edit `termux_signup.py`:
```python
DEFAULT_PASSWORD = "YourPassword123"
WEBHOOK_URL = "https://discord.com/api/webhooks/..."
```

Edit `orchestrator.py`:
```python
CLOUD_PHONE_IP = "your_cloud_phone_ip"
CLOUD_PHONE_PORT = "5555"
```

## 📱 Cloud Phone Setup (ugphone/vsphone)

### 1. Install Apps
- Roblox (from Play Store)
- Delta Executor

### 2. Configure Delta
1. Put `TheForge_Auto.lua` in Delta's `autoexec` folder
2. Enable auto-inject if available

### 3. Enable ADB (if using orchestrator)
1. Enable Developer Options on the cloud phone
2. Enable USB/Wireless Debugging
3. Note the IP address for ADB connection

## 🚀 Usage

### Option A: Manual Flow (Recommended for Testing)

1. **Create accounts:**
   ```bash
   python termux_signup.py
   ```

2. **Login to cloud phone manually**

3. **Join The Forge game**

4. **Delta auto-injects and runs script**

5. **Check Discord for results!**

### Option B: Fully Automated

1. **Run orchestrator:**
   ```bash
   python orchestrator.py
   ```

2. **It will automatically:**
   - Read accounts from `login_queue.txt`
   - Control cloud phone via ADB
   - Launch Roblox and join game
   - Wait for script to complete
   - Move to next account

## 📁 Files

| File | Purpose |
|------|---------|
| `termux_signup.py` | Creates Roblox accounts |
| `orchestrator.py` | Controls cloud phone automation |
| `TheForge_Auto.lua` | In-game reroll script |
| `login_queue.txt` | Accounts waiting to be processed |
| `completed_accounts.txt` | Processed accounts with results |
| `accounts_termux.txt` | All created accounts |

## ⚙️ TheForge_Auto.lua Features

- ✅ Auto redeems codes
- ✅ Auto rerolls for races
- ✅ Stops immediately on **Mythic** (Archangel, Demon, Angel)
- ✅ Tracks **Legendary** (Felynx, Golem, Dragonborn, Minotaur)
- ✅ Sends Discord webhook with account details
- ✅ Saves accounts to files
- ✅ Kicks player when done

## 🔧 Troubleshooting

### Firefox won't start in Termux
```bash
# Make sure you have x11-repo
pkg install x11-repo
pkg reinstall firefox geckodriver
```

### Selenium errors
```bash
pip install --upgrade selenium
```

### ADB can't connect
```bash
# Check if adb is working
adb devices

# Connect manually
adb connect IP:PORT
```

### Delta not injecting
1. Make sure script is in autoexec folder
2. Try manual injection first
3. Check Delta is up to date

## ⚠️ Notes

- NopeCHA has 200 free solves/day - for heavy use, get paid plan
- Adjust timing values in `orchestrator.py` for your phone speed
- Test with 1-2 accounts first before running bulk

## 📞 Support

For issues, check:
1. Termux wiki: https://wiki.termux.com
2. Selenium docs: https://selenium-python.readthedocs.io
