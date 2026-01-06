"""
Termux Account Creator - Firefox + Selenium Version
Works on Termux (Android) with headless Firefox

Setup in Termux:
    pkg update && pkg install x11-repo
    pkg install firefox geckodriver python
    pip install selenium requests
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
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_PASSWORD = "Qing762.chy"
HEADLESS = True  # Set to False if you want to see the browser
NOPECHA_API_KEY = ""  # Your NopeCHA API key (optional)

WEBHOOK_URL = ""  # Discord webhook for notifications (optional)

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
# EMAIL GENERATOR (Mail.tm API)
# ============================================================

class TempEmail:
    """Generate temporary emails using Mail.tm"""
    
    BASE_URL = "https://api.mail.tm"
    
    def __init__(self):
        self.address = None
        self.password = None
        self.token = None
        self.account_id = None
    
    def get_domains(self):
        """Get available email domains"""
        try:
            resp = requests.get(f"{self.BASE_URL}/domains", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                domains = [d["domain"] for d in data.get("hydra:member", [])]
                return domains
        except Exception as e:
            print(f"Error getting domains: {e}")
        return []
    
    def create(self, password=DEFAULT_PASSWORD):
        """Create a new temporary email"""
        domains = self.get_domains()
        if not domains:
            raise Exception("No email domains available")
        
        domain = random.choice(domains)
        gen = UsernameGenerator(8, 12)
        username = gen.generate().lower()
        address = f"{username}@{domain}"
        
        # Create account
        try:
            resp = requests.post(
                f"{self.BASE_URL}/accounts",
                json={"address": address, "password": password},
                timeout=10
            )
            
            if resp.status_code == 201:
                data = resp.json()
                self.account_id = data.get("id")
                self.address = address
                self.password = password
                
                # Get token
                token_resp = requests.post(
                    f"{self.BASE_URL}/token",
                    json={"address": address, "password": password},
                    timeout=10
                )
                
                if token_resp.status_code == 200:
                    self.token = token_resp.json().get("token")
                    return True
        except Exception as e:
            print(f"Error creating email: {e}")
        
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
# ROBLOX ACCOUNT CREATOR
# ============================================================

class RobloxCreator:
    """Create Roblox accounts using Selenium + Firefox"""
    
    def __init__(self, headless=True):
        self.headless = headless
        self.driver = None
    
    def setup_driver(self):
        """Initialize Firefox WebDriver"""
        options = Options()
        
        if self.headless:
            options.add_argument("--headless")
        
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.set_preference("intl.accept_languages", "en-US, en")
        
        # Try to find geckodriver
        geckodriver_path = "/data/data/com.termux/files/usr/bin/geckodriver"
        if not os.path.exists(geckodriver_path):
            geckodriver_path = "geckodriver"  # Use PATH
        
        try:
            service = Service(geckodriver_path)
            self.driver = webdriver.Firefox(service=service, options=options)
            self.driver.set_window_size(1920, 1080)
            return True
        except Exception as e:
            print(f"Error setting up Firefox: {e}")
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
    
    def create_account(self, password=DEFAULT_PASSWORD, email_obj=None):
        """Create a Roblox account"""
        if not self.driver:
            if not self.setup_driver():
                return None
        
        username = self.generate_valid_username()
        print(f"Creating account: {username}")
        
        try:
            # Navigate to signup page
            self.driver.get("https://www.roblox.com/CreateAccount")
            wait = WebDriverWait(self.driver, 30)
            
            # Accept cookies if present
            try:
                cookie_btn = wait.until(EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, ".cookie-btn, .btn-primary-md.btn-min-width")
                ))
                cookie_btn.click()
            except:
                pass
            
            # Fill birthday
            month_dropdown = wait.until(EC.presence_of_element_located((By.ID, "MonthDropdown")))
            Select(month_dropdown).select_by_value("Jan")
            
            day_dropdown = self.driver.find_element(By.ID, "DayDropdown")
            Select(day_dropdown).select_by_value("15")
            
            year_dropdown = self.driver.find_element(By.ID, "YearDropdown")
            current_year = datetime.now().year - 19
            Select(year_dropdown).select_by_value(str(current_year))
            
            # Fill username
            username_input = self.driver.find_element(By.ID, "signup-username")
            username_input.clear()
            username_input.send_keys(username)
            
            # Fill password
            password_input = self.driver.find_element(By.ID, "signup-password")
            password_input.clear()
            password_input.send_keys(password)
            
            time.sleep(2)
            
            # Click signup button
            signup_btn = self.driver.find_element(By.ID, "signup-button")
            signup_btn.click()
            
            print("Signup submitted, waiting for CAPTCHA/redirect...")
            
            # Wait for either CAPTCHA or home page
            # This is where NopeCHA would handle the CAPTCHA
            try:
                wait.until(lambda d: "home" in d.current_url.lower() or "arkose" in d.page_source.lower())
            except TimeoutException:
                print("Timeout waiting for signup result")
            
            # Check if we made it to home
            if "home" in self.driver.current_url.lower():
                print(f"Account created successfully: {username}")
                
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
                print("Account creation may have failed (CAPTCHA?)")
                return None
                
        except Exception as e:
            print(f"Error during signup: {e}")
            return None
    
    def add_email(self, email):
        """Add email to account"""
        try:
            self.driver.get("https://www.roblox.com/my/account#!/info")
            wait = WebDriverWait(self.driver, 10)
            
            # Find and click "Add Email"
            add_email_btn = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//*[contains(text(), 'Add Email')]")
            ))
            add_email_btn.click()
            
            # Find email input and fill
            email_input = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[type='email'], input[name*='email']")
            ))
            email_input.send_keys(email)
            
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

def save_account(account, filename="accounts_termux.txt"):
    """Save account to file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    line = f"{account['username']}:{account['password']}"
    if account.get('email'):
        line += f" | Email: {account['email']}"
    line += f" | Created: {timestamp}\n"
    
    with open(filename, "a", encoding="utf-8") as f:
        f.write(line)
    
    # Also save simple format for The Forge script
    with open("login_queue.txt", "a", encoding="utf-8") as f:
        f.write(f"{account['username']}:{account['password']}\n")
    
    print(f"Account saved: {account['username']}")


# ============================================================
# MAIN
# ============================================================

async def main():
    print("=" * 50)
    print("  Termux Roblox Account Creator")
    print("  Firefox + Selenium Version")
    print("=" * 50)
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
        print(f"\n--- Account {i + 1}/{count} ---")
        
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
            print("Waiting 5 seconds before next account...")
            await asyncio.sleep(5)
    
    creator.close()
    
    print()
    print("=" * 50)
    print(f"Created {len(created_accounts)}/{count} accounts")
    print("Accounts saved to: accounts_termux.txt")
    print("Login queue saved to: login_queue.txt")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
