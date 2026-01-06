"""
Full Auto Reroll - Termux Version
Automatically logs in, joins game, runs Delta script for each account

Requirements (in Debian):
    apt install android-tools-adb python3 python3-pip -y
    pip3 install requests --break-system-packages
"""

import os
import time
import requests
import subprocess
import json

# ============================================================
# CONFIGURATION
# ============================================================

ACCOUNTS_FILE = "accounts.txt"
WEBHOOK_URL = "https://discord.com/api/webhooks/1457625547801886875/Lm5iwIsEoIOaiEJ2FuHQdR9fHsehYCYZNOax_zrz9GgZSEv5299miWPqGlK-xvZsQb-m"

# The Forge game ID
GAME_PLACE_ID = "13477794066"  # The Forge place ID

# Time to wait for reroll (seconds) - adjust based on how long script takes
REROLL_TIME = 300  # 5 minutes per account

# Delta script URL
DELTA_SCRIPT_URL = "https://raw.githubusercontent.com/FamyXLyecdd/reroll/main/TheForge_Auto.lua"

# ============================================================
# WEBHOOK
# ============================================================

def send_webhook(message):
    """Send Discord notification"""
    proxies = [
        WEBHOOK_URL.replace("discord.com", "webhook.lewisakura.moe"),
        WEBHOOK_URL.replace("discord.com", "hooks.hyra.io"),
        WEBHOOK_URL,
    ]
    
    for url in proxies:
        try:
            resp = requests.post(url, json={"content": message}, timeout=10)
            if resp.status_code in [200, 204]:
                return True
        except:
            continue
    return False

# ============================================================
# ADB FUNCTIONS
# ============================================================

def run_adb(cmd):
    """Run ADB command"""
    try:
        result = subprocess.run(
            f"adb {cmd}",
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.stdout.strip()
    except Exception as e:
        print(f"ADB error: {e}")
        return ""

def tap(x, y):
    """Tap screen at coordinates"""
    run_adb(f"shell input tap {x} {y}")
    time.sleep(0.5)

def swipe(x1, y1, x2, y2, duration=500):
    """Swipe on screen"""
    run_adb(f"shell input swipe {x1} {y1} {x2} {y2} {duration}")
    time.sleep(0.5)

def type_text(text):
    """Type text"""
    # Escape special characters
    escaped = text.replace(" ", "%s").replace("'", "\\'").replace('"', '\\"')
    run_adb(f'shell input text "{escaped}"')
    time.sleep(0.3)

def press_key(key):
    """Press key (BACK=4, HOME=3, ENTER=66)"""
    run_adb(f"shell input keyevent {key}")
    time.sleep(0.3)

def launch_app(package):
    """Launch app by package name"""
    run_adb(f"shell monkey -p {package} -c android.intent.category.LAUNCHER 1")
    time.sleep(2)

def force_stop(package):
    """Force stop app"""
    run_adb(f"shell am force-stop {package}")
    time.sleep(1)

def clear_app(package):
    """Clear app data"""
    run_adb(f"shell pm clear {package}")
    time.sleep(1)

def launch_roblox_game(place_id):
    """Launch Roblox with specific game"""
    run_adb(f'shell am start -a android.intent.action.VIEW -d "roblox://placeId={place_id}"')
    time.sleep(5)

# ============================================================
# ROBLOX LOGIN
# ============================================================

def login_roblox_web(username, password):
    """Login to Roblox and get auth cookie"""
    session = requests.Session()
    
    # Get CSRF token
    try:
        csrf_resp = session.post("https://auth.roblox.com/v2/login", timeout=10)
        csrf_token = csrf_resp.headers.get("x-csrf-token", "")
    except:
        csrf_token = ""
    
    # Login
    headers = {
        "Content-Type": "application/json",
        "X-CSRF-TOKEN": csrf_token,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    payload = {
        "ctype": "Username",
        "cvalue": username,
        "password": password
    }
    
    try:
        resp = session.post(
            "https://auth.roblox.com/v2/login",
            json=payload,
            headers=headers,
            timeout=30
        )
        
        # Get .ROBLOSECURITY cookie
        roblosecurity = session.cookies.get(".ROBLOSECURITY")
        
        if roblosecurity:
            print(f"  Login success: {username}")
            return roblosecurity
        else:
            print(f"  Login failed: {resp.text[:100]}")
            return None
    except Exception as e:
        print(f"  Login error: {e}")
        return None

def inject_cookie_to_roblox(cookie):
    """Inject .ROBLOSECURITY cookie into Roblox app"""
    # Roblox stores auth in shared_prefs
    prefs_path = "/data/data/com.roblox.client/shared_prefs/RobloxSharedPrefs.xml"
    
    # Create the prefs content
    prefs_content = f'''<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<map>
    <string name=".ROBLOSECURITY">{cookie}</string>
</map>'''
    
    # Write to file via ADB
    run_adb(f'shell "echo \\'{prefs_content}\\' > {prefs_path}"')
    run_adb(f'shell chmod 660 {prefs_path}')
    
    print("  Cookie injected")

# ============================================================
# DELTA EXECUTOR
# ============================================================

def run_delta_script():
    """Open Delta and execute script"""
    # Delta package name (may vary)
    delta_packages = [
        "com.delta.executor",
        "com.deltaexec.app",
        "delta.executor"
    ]
    
    for pkg in delta_packages:
        launch_app(pkg)
        time.sleep(3)
    
    # Wait for Delta to open
    time.sleep(5)
    
    # The user needs to have the script saved in Delta
    # Or we can try to inject via clipboard
    
    print("  Delta should be open - script needs to be pre-loaded")
    print("  Waiting for reroll to complete...")

# ============================================================
# LOAD ACCOUNTS
# ============================================================

def load_accounts(filename):
    """Load accounts from file"""
    accounts = []
    
    try:
        with open(filename, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                # Parse "Username: X, Password: Y" format
                if "Username:" in line:
                    parts = line.split(",")
                    username = parts[0].split(":")[1].strip()
                    password = parts[1].split(":")[1].strip()
                # Parse "username:password" format
                elif ":" in line:
                    parts = line.split(":")
                    username = parts[0].strip()
                    password = parts[1].strip()
                else:
                    continue
                
                accounts.append({"username": username, "password": password})
    except Exception as e:
        print(f"Error loading accounts: {e}")
    
    return accounts

# ============================================================
# MAIN AUTOMATION
# ============================================================

def process_account(account, index, total):
    """Process one account"""
    username = account["username"]
    password = account["password"]
    
    print(f"\n{'='*50}")
    print(f"Account {index}/{total}: {username}")
    print(f"{'='*50}")
    
    # Step 1: Login via web to get cookie
    print("Step 1: Logging in...")
    cookie = login_roblox_web(username, password)
    
    if not cookie:
        print("  FAILED - Could not login")
        return False
    
    # Step 2: Force stop Roblox
    print("Step 2: Resetting Roblox app...")
    force_stop("com.roblox.client")
    
    # Step 3: Inject cookie (optional - may not work on all devices)
    # print("Step 3: Injecting cookie...")
    # inject_cookie_to_roblox(cookie)
    
    # Step 3: Launch Roblox and join game
    print("Step 3: Launching The Forge...")
    launch_roblox_game(GAME_PLACE_ID)
    
    # Wait for game to load
    print("Step 4: Waiting for game to load...")
    time.sleep(30)
    
    # Step 5: Run Delta script
    print("Step 5: Running Delta script...")
    run_delta_script()
    
    # Step 6: Wait for reroll to complete
    print(f"Step 6: Waiting {REROLL_TIME}s for reroll...")
    time.sleep(REROLL_TIME)
    
    # Step 7: Done with this account
    print(f"Done with {username}")
    send_webhook(f"✅ Processed account: **{username}**")
    
    return True

def main():
    print("="*50)
    print("  THE FORGE AUTO REROLLER")
    print("  Full Automation via Termux")
    print("="*50)
    
    # Check ADB
    print("\nChecking ADB connection...")
    devices = run_adb("devices")
    print(devices)
    
    if "device" not in devices:
        print("\n⚠️  No ADB device found!")
        print("Try: adb connect localhost:5555")
        print("Or enable ADB in cloud phone settings")
        return
    
    # Load accounts
    print(f"\nLoading accounts from {ACCOUNTS_FILE}...")
    accounts = load_accounts(ACCOUNTS_FILE)
    print(f"Found {len(accounts)} accounts")
    
    if not accounts:
        print("No accounts found!")
        return
    
    # Send start notification
    send_webhook(f"🚀 Starting reroll for **{len(accounts)}** accounts")
    
    # Process each account
    success = 0
    failed = 0
    
    for i, account in enumerate(accounts, 1):
        try:
            if process_account(account, i, len(accounts)):
                success += 1
            else:
                failed += 1
        except Exception as e:
            print(f"Error processing account: {e}")
            failed += 1
        
        # Small delay between accounts
        if i < len(accounts):
            print("\nWaiting 10s before next account...")
            time.sleep(10)
    
    # Final summary
    print("\n" + "="*50)
    print(f"COMPLETE: {success} success, {failed} failed")
    print("="*50)
    
    send_webhook(f"🏁 Reroll complete!\n✅ Success: {success}\n❌ Failed: {failed}")

if __name__ == "__main__":
    main()
