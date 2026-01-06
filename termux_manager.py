#!/usr/bin/env python3
"""
Termux Roblox Orchestrator
automates account cycling on Android using Termux + ADB
"""

import os
import sys
import time
import json
import subprocess
import requests
import asyncio
from datetime import datetime

# ============================================================
# CONSTANTS & CONFIG
# ============================================================

CONFIG_FILE = "termux_config.json"
ACCOUNTS_FILE = "accounts.txt"
COMPLETED_FILE = "completed_accounts.txt"
ROBLOX_PACKAGE = "com.roblox.client"
THE_FORGE_ID = "76558904092080" # The Forge Place ID

# Default Config Structure
DEFAULT_CONFIG = {
    "adb_command": "adb", # or "su -c input" if root
    "coordinates": {
        "login_btn_main": [0, 0],
        "username_input": [0, 0],
        "password_input": [0, 0],
        "login_submit": [0, 0]
    },
    "timings": {
        "app_launch": 10,
        "game_load": 25,
        "script_run": 100
    },
    "webhook": ""
}

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def log(msg, color="white"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}")

def run_cmd(cmd, shell=True):
    try:
        result = subprocess.run(cmd, shell=shell, capture_output=True, text=True, timeout=10)
        return result.stdout.strip()
    except Exception as e:
        return None

def adb_shell(cmd_str):
    """Run an ADB shell command"""
    # If we are local termux, we might need 'adb shell <cmd>' or just '<cmd>' if root
    # For now assuming non-root ADB usage
    full_cmd = f"adb shell {cmd_str}"
    return run_cmd(full_cmd)

def tap(x, y):
    adb_shell(f"input tap {x} {y}")

def input_text(text):
    # Escape spaces and special chars
    escaped = text.replace(" ", "%s").replace("'", "\\'")
    adb_shell(f"input text '{escaped}'")

def keyevent(key_code):
    adb_shell(f"input keyevent {key_code}")

# ============================================================
# SETUP WIZARD
# ============================================================

def setup_wizard():
    print("="*60)
    print("  TERMUX ORCHESTRATOR SETUP")
    print("="*60)
    
    config = DEFAULT_CONFIG.copy()
    
    # 1. ADB Check
    print("\n[STEP 1] ADB Connection")
    print("Please enable 'Wireless Debugging' in Developer Options.")
    print("Then in Termux run: adb connect localhost:<port>")
    input("Press Enter when you have connected ADB successfully...")
    
    devices = run_cmd("adb devices")
    if "device" not in (devices or ""):
        print("❌ No device found! Please troubleshoot ADB.")
        if input("Continue anyway? (y/n): ").lower() != 'y':
            sys.exit(1)
    else:
        print("✅ Device found!")

    # 2. Coordinates
    print("\n[STEP 2] Screen Calibration")
    print("We need X,Y coordinates for buttons. Enable 'Pointer Location' in Developer Options.")
    print("This will show X/Y stats at the top of your screen when you touch it.")
    print("\nOpen Roblox (logged out) and hover/tap these locations to get X,Y:")
    
    def get_coord(name):
        while True:
            val = input(f"Enter X,Y for {name} (e.g. 540,1600): ").strip()
            try:
                x, y = map(int, val.replace(",", " ").split())
                return [x, y]
            except:
                print("Invalid format. Try again.")

    config["coordinates"]["login_btn_main"] = get_coord("Main 'Login' Button")
    config["coordinates"]["username_input"] = get_coord("Username Field")
    config["coordinates"]["password_input"] = get_coord("Password Field")
    config["coordinates"]["login_submit"] = get_coord("Submit Login Button")

    # 3. Webhook
    print("\n[STEP 3] Notification")
    config["webhook"] = input("Enter Discord Webhook (optional): ").strip()

    # Save
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)
    
    print(f"\n✅ Setup Complete! Saved to {CONFIG_FILE}")
    return config

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return setup_wizard()
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

# ============================================================
# ACCOUNT MANAGER
# ============================================================

def load_accounts():
    if not os.path.exists(ACCOUNTS_FILE):
        print(f"❌ {ACCOUNTS_FILE} not found!")
        return []
    
    accounts = []
    with open(ACCOUNTS_FILE, "r") as f:
        for line in f:
            if "Username:" in line and "Password:" in line:
                # Parse "Username: x, Password: y"
                try:
                    parts = {}
                    # Remove brackets like (Created at...) if present to clean up
                    clean_line = line.split("(")[0]
                    items = clean_line.split(",")
                    for item in items:
                        if ":" in item:
                            k, v = item.split(":", 1)
                            parts[k.strip()] = v.strip()
                    
                    if "Username" in parts and "Password" in parts:
                        accounts.append({
                            "username": parts["Username"], 
                            "password": parts["Password"]
                        })
                except Exception as e:
                    print(f"Error parsing line: {line[:20]}... {e}")
            elif ":" in line and "|" in line:
                 # Support "user:pass | email" format too just in case
                parts = line.strip().split("|")[0].split(":")
                if len(parts) >= 2:
                    accounts.append({"username": parts[0].strip(), "password": parts[1].strip()})
    return accounts

# ============================================================
# MAIN LOOP
# ============================================================

def get_current_activity():
    """Get the current running activity name"""
    res = adb_shell("dumpsys activity activities | grep mResumedActivity")
    if not res:
        res = adb_shell("dumpsys activity activities | grep mFocusedApp")
    return res or ""

def main():
    config = load_config()
    accounts = load_accounts()
    
    if not accounts:
        print("No accounts to process.")
        return

    print(f"Loaded {len(accounts)} accounts.")
    coords = config["coordinates"]
    timings = config["timings"]

    for i, acc in enumerate(accounts):
        username = acc["username"]
        password = acc["password"]
        
        print(f"\n[{i+1}/{len(accounts)}] Processing: {username}")
        
        try:
            # 1. Reset App
            log("Clearing App Data...")
            adb_shell(f"pm clear {ROBLOX_PACKAGE}")
            time.sleep(2)
            
            # 2. Launch App
            log("Launching Roblox...")
            adb_shell(f"monkey -p {ROBLOX_PACKAGE} -c android.intent.category.LAUNCHER 1")
            
            log(f"Waiting {timings['app_launch']}s for launch...")
            time.sleep(timings["app_launch"])
            
            # 3. Login Flow
            log("Performing Login...")
            
            # Click Main Login
            x, y = coords["login_btn_main"]
            tap(x, y)
            time.sleep(3) # Wait for animation
            
            # Username
            x, y = coords["username_input"]
            tap(x, y)
            time.sleep(1)
            input_text(username)
            keyevent(66) # ENTER
            time.sleep(1)
            
            # Password
            x, y = coords["password_input"]
            tap(x, y)
            time.sleep(1)
            input_text(password)
            keyevent(66) # ENTER
            time.sleep(1)
            
            # Submit
            x, y = coords["login_submit"]
            tap(x, y)
            
            log(f"Waiting {timings['game_load']}s for Home Screen...")
            time.sleep(timings["game_load"])
            
            # SMART CHECK: Check if still on Login Screen?
            # We can't easily detect "Login Screen" by name as it varies, 
            # but we can check if we are NOT in Home (if we can identify Home).
            # For now, let's just proceed. If login failed, the Deep Link ensures we try to join.
            # However, if we are stuck on a Captcha or 2FA, the game launch might fail or require auth.
            
            activity = get_current_activity()
            if "LoginActivity" in activity or "SignUp" in activity:
                log("⚠️ WARNING: It seems we are still on the Login Screen!", "red")
                log("Skipping this account due to failed login...", "red")
                continue
            
            # 4. Launch Game
            log(f"Launching The Forge ({THE_FORGE_ID})...")
            cmd = f"am start -a android.intent.action.VIEW -d \"roblox://placeId={THE_FORGE_ID}\""
            adb_shell(cmd)
            
            # 5. Wait for Script
            wait_time = timings["script_run"]
            log(f"Waiting {wait_time}s for Auto-Script to run...")
            time.sleep(wait_time)
            
            # 6. Mark Complete
            with open(COMPLETED_FILE, "a") as f:
                f.write(f"{username}:{password} | {datetime.now()}\n")
                
            log(f"Finished {username}")
        
        except KeyboardInterrupt:
            print("\nStopping...")
            break
        except Exception as e:
            log(f"❌ ERROR processing {username}: {e}", "red")
            
        finally:
            # Cleanup
            adb_shell(f"am force-stop {ROBLOX_PACKAGE}")
            time.sleep(2)

if __name__ == "__main__":
    main()
