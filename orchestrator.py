"""
The Forge Orchestrator - Master Control Script
Coordinates account creation, cloud phone control, and rerolling

This script:
1. Creates accounts (or uses existing ones)
2. Controls cloud phone via scrcpy/ADB
3. Monitors for webhook results
4. Loops through accounts automatically

Setup:
    pip install requests
    # For ADB control: pkg install android-tools
"""

import os
import sys
import time
import json
import subprocess
import requests
from datetime import datetime

# ============================================================
# CONFIGURATION
# ============================================================

# Files
ACCOUNTS_FILE = "accounts.txt"
COMPLETED_FILE = "completed_accounts.txt"
RESULTS_FILE = "forge_results.txt"

# Cloud Phone Settings
CLOUD_PHONE_IP = "localhost"  # Change to your cloud phone IP
CLOUD_PHONE_PORT = "5555"     # ADB port
USE_SCRCPY = True             # Set to True if using scrcpy

# The Forge Game
THE_FORGE_PLACE_ID = "76558904092080"
ROBLOX_PACKAGE = "com.roblox.client"

# Timing (adjust based on your phone speed)
WAIT_APP_LAUNCH = 10      # Seconds to wait for Roblox to launch
WAIT_GAME_LOAD = 30       # Seconds to wait for game to load
WAIT_SCRIPT_RUN = 120     # Seconds to wait for script to complete
WAIT_BETWEEN_ACCOUNTS = 5 # Seconds between accounts

# Discord Webhook (for status updates)
STATUS_WEBHOOK = ""  # Optional: webhook for orchestrator status

# ============================================================
# HELPERS
# ============================================================

def log(message):
    """Print with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")


def send_status(message):
    """Send status update to webhook"""
    if not STATUS_WEBHOOK:
        return
    
    try:
        requests.post(
            STATUS_WEBHOOK,
            json={"content": f"🤖 **Orchestrator**: {message}"},
            timeout=5
        )
    except:
        pass


def adb_command(cmd, capture=False):
    """Run ADB command"""
    full_cmd = f"adb -s {CLOUD_PHONE_IP}:{CLOUD_PHONE_PORT} {cmd}"
    log(f"ADB: {cmd}")
    
    try:
        if capture:
            result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=30)
            return result.stdout.strip()
        else:
            subprocess.run(full_cmd, shell=True, timeout=30)
            return True
    except subprocess.TimeoutExpired:
        log("ADB command timed out")
        return None
    except Exception as e:
        log(f"ADB error: {e}")
        return None


def adb_shell(cmd):
    """Run shell command on device"""
    return adb_command(f'shell "{cmd}"')


def adb_tap(x, y):
    """Tap screen at coordinates"""
    adb_shell(f"input tap {x} {y}")
    time.sleep(0.5)


def adb_input_text(text):
    """Type text on device"""
    # Escape special characters
    text = text.replace(" ", "%s").replace("&", "\\&")
    adb_shell(f"input text '{text}'")
    time.sleep(0.3)


def adb_keyevent(key):
    """Send key event"""
    adb_shell(f"input keyevent {key}")
    time.sleep(0.3)


# ============================================================
# CLOUD PHONE CONTROL
# ============================================================

def connect_phone():
    """Connect to cloud phone via ADB"""
    log("Connecting to cloud phone...")
    result = adb_command(f"connect {CLOUD_PHONE_IP}:{CLOUD_PHONE_PORT}", capture=True)
    
    if result and "connected" in result.lower():
        log("Connected to cloud phone!")
        return True
    else:
        log(f"Connection result: {result}")
        return False


def is_roblox_running():
    """Check if Roblox is running"""
    result = adb_command("shell dumpsys activity activities | grep mFocusedApp", capture=True)
    return ROBLOX_PACKAGE in (result or "")


def launch_roblox():
    """Launch Roblox app"""
    log("Launching Roblox...")
    adb_shell(f"am start -n {ROBLOX_PACKAGE}/.ActivitySplash")
    time.sleep(WAIT_APP_LAUNCH)


def close_roblox():
    """Close Roblox app"""
    log("Closing Roblox...")
    adb_shell(f"am force-stop {ROBLOX_PACKAGE}")
    time.sleep(2)


def join_the_forge():
    """Join The Forge game"""
    log("Joining The Forge...")
    
    # Method 1: Deep link (most reliable)
    deep_link = f"roblox://placeId={THE_FORGE_PLACE_ID}"
    adb_shell(f"am start -a android.intent.action.VIEW -d '{deep_link}'")
    
    time.sleep(WAIT_GAME_LOAD)
    log("Waiting for game to load...")


def login_roblox(username, password):
    """Login to Roblox with credentials"""
    log(f"Logging in as: {username}")
    
    # This is a basic implementation - coordinates may need adjustment
    # based on your device resolution
    
    # Tap login button (adjust coordinates for your device)
    # You may need to use scrcpy to find the exact coordinates
    
    # Wait for login screen
    time.sleep(3)
    
    # These are placeholder coordinates - you'll need to adjust
    # TAP_LOGIN_BUTTON = (540, 1800)
    # TAP_USERNAME_FIELD = (540, 600)
    # TAP_PASSWORD_FIELD = (540, 750)
    # TAP_SUBMIT_BUTTON = (540, 900)
    
    log("NOTE: Login automation requires device-specific coordinates")
    log("You may need to login manually the first time")
    
    return True


def inject_delta_script():
    """
    Inject script using Delta executor
    
    Delta needs to be:
    1. Already installed on the cloud phone
    2. Set to auto-inject (if supported)
    3. Have the script in its autoexec folder
    
    This function just ensures Delta is ready
    """
    log("Preparing Delta executor...")
    
    # Delta package name (may vary)
    DELTA_PACKAGE = "com.delta.executor"  # Placeholder - get actual package name
    
    # Launch Delta
    # adb_shell(f"am start -n {DELTA_PACKAGE}/.MainActivity")
    # time.sleep(3)
    
    log("Script should auto-execute from Delta's autoexec folder")
    log("Make sure TheForge_Auto.lua is in Delta's autoexec!")
    
    return True


# ============================================================
# ACCOUNT MANAGEMENT
# ============================================================

def load_accounts():
    """Load accounts from queue file - supports multiple formats"""
    if not os.path.exists(ACCOUNTS_FILE):
        return []
    
    accounts = []
    with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            try:
                # Format 1: main.py format "Username: xxx, Password: yyy, Email: zzz, ..."
                if line.startswith("Username:"):
                    parts = {}
                    for item in line.split(", "):
                        if ": " in item:
                            key, value = item.split(": ", 1)
                            parts[key] = value
                    
                    if "Username" in parts and "Password" in parts:
                        # Remove timestamp from password if present
                        password = parts["Password"].split(" (")[0]
                        accounts.append({
                            "username": parts["Username"],
                            "password": password,
                            "email": parts.get("Email", ""),
                            "emailPassword": parts.get("Email Password", "")
                        })
                
                # Format 2: termux_signup.py format "username:password | Email: xxx | Created: xxx"
                elif ":" in line:
                    # Split by | first to get parts
                    main_parts = line.split(" | ")
                    user_pass = main_parts[0].split(":")
                    
                    if len(user_pass) >= 2:
                        username = user_pass[0].strip()
                        password = user_pass[1].strip()
                        email = ""
                        
                        # Check for email in remaining parts
                        for part in main_parts[1:]:
                            if part.startswith("Email:"):
                                email = part.replace("Email:", "").strip()
                                break
                        
                        accounts.append({
                            "username": username,
                            "password": password,
                            "email": email,
                            "emailPassword": ""
                        })
                        
            except Exception as e:
                print(f"Error parsing line: {line[:50]}... - {e}")
                continue
    
    return accounts


def mark_completed(account, result="unknown"):
    """Mark account as completed"""
    with open(COMPLETED_FILE, "a", encoding="utf-8") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"Username: {account['username']}, Password: {account['password']}, Email: {account.get('email', 'N/A')} | Result: {result} | {timestamp}\n")


def remove_from_queue(account):
    """Remove account from queue"""
    if not os.path.exists(ACCOUNTS_FILE):
        return
    
    with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
        for line in lines:
            if f"Username: {account['username']}" not in line:
                f.write(line)


# ============================================================
# MAIN ORCHESTRATION LOOP
# ============================================================

def process_account(account):
    """Process a single account through The Forge"""
    username = account["username"]
    password = account["password"]
    
    log(f"{'='*50}")
    log(f"Processing: {username}")
    log(f"{'='*50}")
    
    try:
        # Close any existing Roblox instance
        close_roblox()
        time.sleep(2)
        
        # Launch Roblox
        launch_roblox()
        
        # Login (if needed)
        # login_roblox(username, password)
        
        # Join The Forge
        join_the_forge()
        
        # Wait for Delta to inject and script to run
        log(f"Waiting {WAIT_SCRIPT_RUN}s for script to complete...")
        log("Script will send webhook when done and kick player")
        
        # Wait for the script to finish
        # The Lua script will send a webhook and kick the player
        time.sleep(WAIT_SCRIPT_RUN)
        
        # Check if still in game (should be kicked if script ran)
        if not is_roblox_running():
            log("Player was kicked - script completed!")
            return "completed"
        else:
            log("Still in game - script may not have run")
            return "timeout"
        
    except Exception as e:
        log(f"Error processing account: {e}")
        return "error"


def main():
    """Main orchestration loop"""
    print("=" * 60)
    print("  THE FORGE ORCHESTRATOR")
    print("  Automated Account Processing")
    print("=" * 60)
    print()
    
    # Check for accounts
    accounts = load_accounts()
    if not accounts:
        print(f"No accounts found in {ACCOUNTS_FILE}")
        print("Run termux_signup.py first to create accounts!")
        return
    
    print(f"Found {len(accounts)} account(s) in queue")
    print()
    
    # Connect to cloud phone
    if not connect_phone():
        print("Failed to connect to cloud phone!")
        print(f"Make sure ADB is enabled and device is at {CLOUD_PHONE_IP}:{CLOUD_PHONE_PORT}")
        return
    
    send_status(f"Starting processing of {len(accounts)} accounts")
    
    # Process each account
    processed = 0
    for i, account in enumerate(accounts):
        log(f"\nAccount {i+1}/{len(accounts)}")
        
        result = process_account(account)
        
        # Mark as completed
        mark_completed(account, result)
        remove_from_queue(account)
        processed += 1
        
        # Wait between accounts
        if i < len(accounts) - 1:
            log(f"Waiting {WAIT_BETWEEN_ACCOUNTS}s before next account...")
            time.sleep(WAIT_BETWEEN_ACCOUNTS)
    
    send_status(f"Completed processing {processed} accounts")
    
    print()
    print("=" * 60)
    print(f"  COMPLETED: {processed}/{len(accounts)} accounts")
    print(f"  Results saved to: {COMPLETED_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
