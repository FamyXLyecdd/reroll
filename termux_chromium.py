"""
Termux Account Creator - Chromium + Selenium Version
Works on Termux (Android) with proot-distro Debian + headless Chromium

Setup:
    # In Termux
    pkg install proot-distro
    proot-distro install debian
    proot-distro login debian
    
    # Inside Debian
    apt update && apt install chromium chromium-driver python3 python3-pip -y
    pip3 install selenium requests --break-system-packages
    python3 termux_chromium.py
"""

import os
import sys
import random
import asyncio
import time
import requests
import json
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_PASSWORD = "Qing762.chy"
HEADLESS = True  # Set to False if you want to see the browser (needs display)
NOPECHA_API_KEY = "wlc9fkgvfvmoymzg"  # Your NopeCHA API key

WEBHOOK_URL = "https://discord.com/api/webhooks/1457625547801886875/Lm5iwIsEoIOaiEJ2FuHQdR9fHsehYCYZNOax_zrz9GgZSEv5299miWPqGlK-xvZsQb-m"

# Webhook proxies (Discord blocks direct Roblox requests)
WEBHOOK_PROXIES = [
    lambda url: url.replace("discord.com", "webhook.lewisakura.moe"),
    lambda url: url.replace("discord.com", "hooks.hyra.io"),
    lambda url: url,  # Original as fallback
]

# ============================================================
# USERNAME GENERATOR
# ============================================================

class UsernameGenerator:
    """Generate random usernames"""
    CONSONANTS = "bcdfghjklmnpqrstvwxyz"
    VOWELS = "aeiou"
    
    def __init__(self, min_length=10, max_length=15):
        self.min_length = min_length
        self.max_length = max_length
    
    def generate(self):
        length = random.randint(self.min_length, self.max_length)
        username = ""
        is_consonant = random.choice([True, False])
        
        for _ in range(length - 2):  # Leave room for numbers
            if is_consonant:
                username += random.choice(self.CONSONANTS)
            else:
                username += random.choice(self.VOWELS)
            is_consonant = not is_consonant
        
        # Add random numbers
        username += str(random.randint(10, 99))
        
        # Capitalize first letter sometimes
        if random.choice([True, False]):
            username = username[0].upper() + username[1:]
        
        return username


# ============================================================
# EMAIL GENERATOR (Multiple services with fallback)
# ============================================================

class TempEmail:
    """Generate temporary emails using multiple services"""
    
    def __init__(self):
        self.address = None
        self.password = None
        self.token = None
        self.account_id = None
        self.service = None
    
    def try_mailtm(self, password):
        """Try Mail.tm service"""
        try:
            resp = requests.get("https://api.mail.tm/domains", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                domains = [d["domain"] for d in data.get("hydra:member", [])]
                if domains:
                    domain = random.choice(domains)
                    gen = UsernameGenerator(8, 12)
                    username = gen.generate().lower()
                    address = f"{username}@{domain}"
                    
                    create_resp = requests.post(
                        "https://api.mail.tm/accounts",
                        json={"address": address, "password": password},
                        timeout=10
                    )
                    
                    if create_resp.status_code == 201:
                        self.address = address
                        self.password = password
                        self.service = "mail.tm"
                        return True
        except:
            pass
        return False
    
    def try_guerrilla(self, password):
        """Try Guerrilla Mail service"""
        try:
            resp = requests.get(
                "https://api.guerrillamail.com/ajax.php?f=get_email_address",
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                if "email_addr" in data:
                    self.address = data["email_addr"]
                    self.password = password
                    self.token = data.get("sid_token")
                    self.service = "guerrilla"
                    return True
        except:
            pass
        return False
    
    def try_tempmail_io(self, password):
        """Try temp-mail.io service"""
        try:
            # Generate random email with common temp domains
            domains = ["mailto.plus", "fexpost.com", "fexbox.org", "fexbox.ru"]
            domain = random.choice(domains)
            gen = UsernameGenerator(8, 12)
            username = gen.generate().lower()
            self.address = f"{username}@{domain}"
            self.password = password
            self.service = "tempmail_fake"
            return True
        except:
            pass
        return False
    
    def create(self, password=DEFAULT_PASSWORD):
        """Create a new temporary email with fallback"""
        print("Trying email services...")
        
        # Try multiple services
        if self.try_mailtm(password):
            print(f"  Mail.tm: {self.address}")
            return True
        
        print("  Mail.tm failed, trying Guerrilla...")
        if self.try_guerrilla(password):
            print(f"  Guerrilla: {self.address}")
            return True
        
        print("  Guerrilla failed, using fake email...")
        if self.try_tempmail_io(password):
            print(f"  Generated: {self.address}")
            return True
        
        return False
        
        return False
    
    def get_messages(self):
        """Get inbox messages"""
        if not self.token:
            return []
        
        try:
            resp = requests.get(
                f"{self.BASE_URL}/messages",
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=10
            )
            if resp.status_code == 200:
                return resp.json().get("hydra:member", [])
        except Exception as e:
            print(f"Error fetching messages: {e}")
        
        return []
    
    def get_message_content(self, message_id):
        """Get full message content"""
        if not self.token:
            return None
        
        try:
            resp = requests.get(
                f"{self.BASE_URL}/messages/{message_id}",
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=10
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            print(f"Error fetching message: {e}")
        
        return None


# ============================================================
# ROBLOX ACCOUNT CREATOR (CHROMIUM VERSION)
# ============================================================

class RobloxCreator:
    """Create Roblox accounts using Selenium + Chromium"""
    
    def __init__(self, headless=True):
        self.headless = headless
        self.driver = None
    
    def setup_driver(self):
        """Initialize Chromium WebDriver"""
        options = Options()
        
        # Required for proot/container environment
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-extensions")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--lang=en-US")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # NopeCHA extension (if available)
        nopecha_path = os.path.join(os.path.dirname(__file__), "NopeCHA")
        if os.path.exists(nopecha_path) and NOPECHA_API_KEY:
            options.add_argument(f"--load-extension={nopecha_path}")
            print(f"NopeCHA extension loaded from {nopecha_path}")
        
        # Try to find chromedriver
        chromedriver_paths = [
            "/usr/bin/chromedriver",
            "/usr/lib/chromium/chromedriver",
            "/usr/lib/chromium-browser/chromedriver",
            "chromedriver"
        ]
        
        chromedriver_path = None
        for path in chromedriver_paths:
            if os.path.exists(path):
                chromedriver_path = path
                break
        
        try:
            if chromedriver_path:
                service = Service(chromedriver_path)
                self.driver = webdriver.Chrome(service=service, options=options)
            else:
                self.driver = webdriver.Chrome(options=options)
            
            self.driver.set_window_size(1920, 1080)
            print("Chromium WebDriver initialized successfully!")
            return True
        except Exception as e:
            print(f"Error setting up Chromium: {e}")
            return False
    
    def validate_username(self, username):
        """Check if username is available"""
        try:
            url = f"https://auth.roblox.com/v2/usernames/validate?request.username={username}&request.birthday=04%2F15%2F02&request.context=Signup"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("code") == 0
        except Exception as e:
            print(f"Error validating username: {e}")
        return False
    
    def generate_valid_username(self, prefix=None):
        """Generate a valid, available username"""
        gen = UsernameGenerator(10, 15)
        
        for _ in range(50):  # Max attempts
            if prefix:
                username = f"{prefix}_{random.randint(0, 9999)}"
            else:
                username = gen.generate()
            
            if self.validate_username(username):
                return username
        
        # Fallback
        return gen.generate()
    
    def solve_captcha_nopecha(self):
        """Solve FunCaptcha using NopeCHA API"""
        if not NOPECHA_API_KEY:
            print("No NopeCHA API key - cannot solve CAPTCHA")
            return False
        
        try:
            # Find FunCaptcha public key from page
            page_source = self.driver.page_source
            
            # Look for Arkose/FunCaptcha
            import re
            pk_match = re.search(r'public[_-]?key["\s:=]+["\']?([A-F0-9-]{36})', page_source, re.IGNORECASE)
            
            if not pk_match:
                # Try to find in network or iframe
                iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                for iframe in iframes:
                    src = iframe.get_attribute("src") or ""
                    if "arkoselabs" in src or "funcaptcha" in src:
                        pk_match = re.search(r'pk=([A-F0-9-]{36})', src, re.IGNORECASE)
                        if pk_match:
                            break
            
            if not pk_match:
                print("Could not find FunCaptcha public key")
                return False
            
            public_key = pk_match.group(1)
            print(f"Found FunCaptcha key: {public_key[:8]}...")
            
            # Request solve from NopeCHA
            print("Requesting CAPTCHA solution from NopeCHA...")
            resp = requests.post(
                "https://api.nopecha.com/",
                json={
                    "key": NOPECHA_API_KEY,
                    "type": "funcaptcha",
                    "sitekey": public_key,
                    "url": self.driver.current_url
                },
                timeout=30
            )
            
            if resp.status_code != 200:
                print(f"NopeCHA API error: {resp.status_code}")
                return False
            
            data = resp.json()
            
            if "error" in data:
                print(f"NopeCHA error: {data.get('error')}")
                return False
            
            # Poll for solution
            request_id = data.get("data")
            if not request_id:
                print("No request ID from NopeCHA")
                return False
            
            print("Waiting for CAPTCHA solution...")
            for _ in range(60):  # Max 2 minutes
                time.sleep(2)
                
                poll_resp = requests.post(
                    "https://api.nopecha.com/",
                    json={
                        "key": NOPECHA_API_KEY,
                        "id": request_id
                    },
                    timeout=30
                )
                
                poll_data = poll_resp.json()
                
                if "error" in poll_data:
                    if poll_data.get("error") == 1:  # Still processing
                        continue
                    print(f"NopeCHA poll error: {poll_data}")
                    return False
                
                if "data" in poll_data:
                    token = poll_data["data"]
                    print("CAPTCHA solved! Injecting token...")
                    
                    # Inject the token
                    self.driver.execute_script(f'''
                        var callback = window.ArkoseEnforcement && window.ArkoseEnforcement.callback;
                        if (callback) callback("{token}");
                        
                        // Try other methods
                        var inputs = document.querySelectorAll('input[name*="captcha"], input[name*="token"], input[name*="fc-token"]');
                        inputs.forEach(function(input) {{ input.value = "{token}"; }});
                        
                        // Dispatch events
                        document.dispatchEvent(new CustomEvent('FunCaptchaCallback', {{detail: {{token: "{token}"}}}}));
                    ''')
                    
                    return True
            
            print("CAPTCHA solve timeout")
            return False
            
        except Exception as e:
            print(f"Error solving CAPTCHA: {e}")
            return False
    
    def create_account(self, password=DEFAULT_PASSWORD, email_obj=None):
        """Create a Roblox account"""
        if not self.driver:
            if not self.setup_driver():
                return None
        
        username = self.generate_valid_username()
        print(f"Creating account: {username}")
        
        try:
            # Setup NopeCHA API (no extension needed)
            print("Using NopeCHA API for CAPTCHA solving")
            
            # Navigate to signup page
            self.driver.get("https://www.roblox.com/CreateAccount")
            wait = WebDriverWait(self.driver, 30)
            
            # Accept cookies if present
            try:
                cookie_btn = wait.until(EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, ".cookie-btn, .btn-primary-md.btn-min-width")
                ))
                cookie_btn.click()
                time.sleep(1)
            except:
                pass
            
            # Fill birthday
            print("Filling birthday...")
            month_dropdown = wait.until(EC.presence_of_element_located((By.ID, "MonthDropdown")))
            Select(month_dropdown).select_by_value("Jan")
            
            day_dropdown = self.driver.find_element(By.ID, "DayDropdown")
            Select(day_dropdown).select_by_value("15")
            
            year_dropdown = self.driver.find_element(By.ID, "YearDropdown")
            current_year = datetime.now().year - 19
            Select(year_dropdown).select_by_value(str(current_year))
            
            # Fill username
            print("Filling username...")
            username_input = self.driver.find_element(By.ID, "signup-username")
            username_input.clear()
            username_input.send_keys(username)
            
            # Fill password
            print("Filling password...")
            password_input = self.driver.find_element(By.ID, "signup-password")
            password_input.clear()
            password_input.send_keys(password)
            
            time.sleep(2)
            
            # Click signup button
            print("Clicking signup...")
            signup_btn = self.driver.find_element(By.ID, "signup-button")
            signup_btn.click()
            
            print("Signup submitted, waiting for CAPTCHA/redirect...")
            
            # Wait a moment for captcha to load
            time.sleep(5)
            
            # Check if CAPTCHA appeared and try to solve it
            if "captcha" in self.driver.page_source.lower() or "arkose" in self.driver.page_source.lower():
                print("CAPTCHA detected - attempting to solve with NopeCHA API...")
                if self.solve_captcha_nopecha():
                    print("CAPTCHA solution submitted!")
                    time.sleep(5)  # Wait for form to process
                else:
                    print("CAPTCHA solving failed")
            
            # Wait for either home page (success) or timeout
            try:
                wait_long = WebDriverWait(self.driver, 60)  # 1 minute
                wait_long.until(lambda d: "home" in d.current_url.lower())
            except TimeoutException:
                print("Timeout - checking if captcha is still present...")
                if "captcha" in self.driver.page_source.lower() or "arkose" in self.driver.page_source.lower():
                    print("CAPTCHA still present - NopeCHA may have failed")
                    return None
            
            # Check if we made it to home
            if "home" in self.driver.current_url.lower():
                print(f"SUCCESS! Account created: {username}")
                
                # Get cookies
                cookies = self.driver.get_cookies()
                roblosecurity = None
                for cookie in cookies:
                    if cookie["name"] == ".ROBLOSECURITY":
                        roblosecurity = cookie["value"]
                        break
                
                # Add email if provided
                if email_obj and email_obj.address:
                    self.add_email(email_obj.address)
                
                return {
                    "username": username,
                    "password": password,
                    "email": email_obj.address if email_obj else None,
                    "email_password": email_obj.password if email_obj else None,
                    "roblosecurity": roblosecurity,
                    "cookies": cookies
                }
            else:
                print("Account creation may have failed")
                return None
                
        except Exception as e:
            print(f"Error during signup: {e}")
            return None
    
    def add_email(self, email):
        """Add email to account"""
        try:
            self.driver.get("https://www.roblox.com/my/account#!/info")
            wait = WebDriverWait(self.driver, 10)
            
            time.sleep(3)
            
            # Find and click "Add Email"
            add_email_btn = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//*[contains(text(), 'Add Email')]")
            ))
            add_email_btn.click()
            
            time.sleep(2)
            
            # Find email input and fill
            email_input = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[type='email'], input[name*='email'], input[placeholder*='email']")
            ))
            email_input.send_keys(email)
            
            time.sleep(1)
            
            # Submit
            submit_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Add Email')]")
            submit_btn.click()
            
            print(f"Email added: {email}")
            return True
        except Exception as e:
            print(f"Error adding email: {e}")
            return False
    
    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()
            self.driver = None


# ============================================================
# WEBHOOK NOTIFICATION
# ============================================================

def send_webhook(message, webhook_url=WEBHOOK_URL):
    """Send Discord webhook notification"""
    if not webhook_url:
        return False
    
    data = {
        "content": message,
        "username": "Roblox Creator Bot"
    }
    
    for proxy_fn in WEBHOOK_PROXIES:
        try:
            url = proxy_fn(webhook_url)
            resp = requests.post(
                url,
                json=data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            if resp.status_code in [200, 204]:
                return True
        except:
            continue
    
    return False


# ============================================================
# ACCOUNT SAVING
# ============================================================

def save_account(account, filename="accounts.txt"):
    """Save account to file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Main format (compatible with orchestrator.py)
    line = f"Username: {account['username']}, Password: {account['password']}"
    if account.get('email'):
        line += f", Email: {account['email']}"
    if account.get('email_password'):
        line += f", Email Password: {account['email_password']}"
    line += f" (Created at {timestamp})\n"
    
    with open(filename, "a", encoding="utf-8") as f:
        f.write(line)
    
    # Also save cookies for RAM
    if account.get('roblosecurity'):
        with open("ram_cookies.txt", "a", encoding="utf-8") as f:
            f.write(f"{account['roblosecurity']}\n")
    
    print(f"Account saved: {account['username']}")


# ============================================================
# MAIN
# ============================================================

async def main():
    print("=" * 50)
    print("  Roblox Account Creator")
    print("  Chromium + Selenium + NopeCHA")
    print("  For Termux (proot-distro Debian)")
    print("=" * 50)
    print()
    
    if NOPECHA_API_KEY:
        print(f"NopeCHA API Key: {NOPECHA_API_KEY[:4]}...{NOPECHA_API_KEY[-4:]}")
    else:
        print("WARNING: No NopeCHA API key - you'll need to solve CAPTCHAs manually")
    print()
    
    # Configuration
    password = input(f"Password (default: {DEFAULT_PASSWORD}): ").strip() or DEFAULT_PASSWORD
    count = input("Number of accounts to create (default: 1): ").strip()
    count = int(count) if count.isdigit() else 1
    
    use_email = input("Use email verification? [y/n] (default: y): ").strip().lower()
    use_email = use_email != "n"
    
    print()
    print(f"Creating {count} account(s)...")
    print()
    
    creator = RobloxCreator(headless=HEADLESS)
    created_accounts = []
    
    for i in range(count):
        print(f"\n{'='*40}")
        print(f"Account {i + 1}/{count}")
        print(f"{'='*40}")
        
        # Generate email if needed
        email = None
        if use_email:
            email = TempEmail()
            if email.create(password):
                print(f"Email created: {email.address}")
            else:
                print("Failed to create email, continuing without...")
                email = None
        
        # Create account
        account = creator.create_account(password=password, email_obj=email)
        
        if account:
            save_account(account)
            created_accounts.append(account)
            
            # Send webhook notification
            if WEBHOOK_URL:
                msg = f"**New Account Created**\n```\nUsername: {account['username']}\nPassword: {password}\n```"
                send_webhook(msg)
        else:
            print(f"Failed to create account {i + 1}")
        
        # Wait between accounts
        if i < count - 1:
            print("Waiting 10 seconds before next account...")
            await asyncio.sleep(10)
    
    creator.close()
    
    print()
    print("=" * 50)
    print(f"Created {len(created_accounts)}/{count} accounts")
    print("Accounts saved to: accounts.txt")
    print("RAM cookies saved to: ram_cookies.txt")
    print("=" * 50)
    
    # Print summary
    if created_accounts:
        print("\nCredentials:")
        for acc in created_accounts:
            print(f"  {acc['username']} : {acc['password']}")


if __name__ == "__main__":
    asyncio.run(main())
