#!/usr/bin/env python3
"""
openrouter_automation skill - Automate OpenRouter API key retrieval.
Enhanced with browser session copying from existing browser profiles.

Flow options:
1. Check email → Extract link → Login → Get API key
2. Copy existing browser session → Navigate to OpenRouter → Get API key (no login needed)
3. Use saved storage_state → Get API key

Auto-installs Playwright if missing.
"""
import json
import re
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime


def get_info():
    return {
        "name": "openrouter_automation",
        "version": "v1",
        "description": "Automate OpenRouter login and API key retrieval via email, browser session copy, or saved state.",
        "capabilities": ["automation", "openrouter", "api", "browser", "email", "session_copy"],
        "actions": [
            "get_api_key_from_email",
            "get_api_key_from_session",
            "get_api_key_from_storage_state",
            "save_browser_session",
            "login_and_get_key",
            "save_key",
            "load_key",
            "check_key_validity",
            "list_available_browsers"
        ]
    }


def health_check():
    """Check if dependencies are available."""
    try:
        # Check if we can import required modules
        import imaplib
        import smtplib
        # Check Playwright availability
        try:
            from playwright.sync_api import sync_playwright
            return True
        except ImportError:
            return True  # Still functional without Playwright for email mode
    except ImportError:
        return False


class OpenRouterAutomationSkill:
    """Automate OpenRouter API key retrieval workflow."""

    def __init__(self):
        self.config_dir = Path.home() / ".evo_openrouter"
        self.config_dir.mkdir(exist_ok=True)
        self.config_file = self.config_dir / "config.json"
        self.api_key_file = self.config_dir / "api_key.txt"
        self.storage_state_file = self.config_dir / "browser_storage_state.json"
        self.browser_profiles_dir = self.config_dir / "browser_profiles"
        self.browser_profiles_dir.mkdir(exist_ok=True)

    def _load_config(self):
        """Load saved configuration."""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            return {}
        except:
            return {}

    def _save_config(self, config):
        """Save configuration."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            pass

    def _get_browser_profiles(self):
        """Find available browser profiles with saved sessions."""
        profiles = {
            "chrome": [],
            "chromium": [],
            "firefox": [],
            "edge": [],
            "brave": [],
            "vivaldi": []
        }
        
        home = Path.home()
        
        # Standard Firefox profiles
        firefox_base = home / ".mozilla" / "firefox"
        if firefox_base.exists():
            profiles_ini = firefox_base / "profiles.ini"
            if profiles_ini.exists():
                with open(profiles_ini, 'r') as f:
                    content = f.read()
                    for match in re.finditer(r'Path=(.+)', content):
                        profile_path = firefox_base / match.group(1)
                        if profile_path.exists():
                            profiles["firefox"].append(str(profile_path))
        
        # Snap Firefox profiles (Ubuntu snap install)
        snap_firefox_base = home / "snap" / "firefox" / "common" / ".mozilla" / "firefox"
        if snap_firefox_base.exists():
            for profile_dir in snap_firefox_base.iterdir():
                if profile_dir.is_dir() and (profile_dir / "cookies.sqlite").exists():
                    profiles["firefox"].append(str(profile_dir))
        
        # Flatpak Firefox profiles
        flatpak_firefox_base = home / ".var" / "app" / "org.mozilla.firefox" / ".mozilla" / "firefox"
        if flatpak_firefox_base.exists():
            for profile_dir in flatpak_firefox_base.iterdir():
                if profile_dir.is_dir() and (profile_dir / "cookies.sqlite").exists():
                    profiles["firefox"].append(str(profile_dir))
        
        # Chrome profiles
        chrome_base = home / ".config" / "google-chrome"
        if chrome_base.exists():
            for profile in chrome_base.glob("*/"):
                if (profile / "Cookies").exists() or (profile / "Login Data").exists():
                    profiles["chrome"].append(str(profile))
        
        # Chromium profiles
        chromium_base = home / ".config" / "chromium"
        if chromium_base.exists():
            for profile in chromium_base.glob("*/"):
                if (profile / "Cookies").exists():
                    profiles["chromium"].append(str(profile))
        
        # Edge profiles
        edge_base = home / ".config" / "microsoft-edge"
        if edge_base.exists():
            for profile in edge_base.glob("*/"):
                if (profile / "Cookies").exists():
                    profiles["edge"].append(str(profile))
        
        # Brave profiles
        brave_base = home / ".config" / "BraveSoftware" / "Brave-Browser"
        if brave_base.exists():
            for profile in brave_base.glob("*/"):
                if (profile / "Cookies").exists():
                    profiles["brave"].append(str(profile))
        
        return profiles

    def _is_firefox_running(self):
        """Check if Firefox is currently running (including snap)."""
        try:
            # Check for regular firefox
            result = subprocess.run(
                ["pgrep", "-f", "firefox"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                return True
            
            # Check for snap firefox
            result2 = subprocess.run(
                ["ps", "aux"],
                capture_output=True, text=True
            )
            if "snap" in result2.stdout and "firefox" in result2.stdout:
                return True
                
            return False
        except:
            return False

    def _prepare_playwright_profile(self, source_profile):
        """Copy Firefox profile files for Playwright use (from nlp2cmd firefox_sessions)."""
        target_dir = self.config_dir / "firefox_playwright_profile"
        target_dir.mkdir(parents=True, exist_ok=True)
        
        source = Path(source_profile)
        
        # Files to copy (matching nlp2cmd firefox_sessions._SESSION_FILES)
        session_files = [
            "cookies.sqlite", "cookies.sqlite-wal", "cookies.sqlite-shm",
            "webappsstore.sqlite", "webappsstore.sqlite-wal", "webappsstore.sqlite-shm",
            "permissions.sqlite", "content-prefs.sqlite", "formhistory.sqlite",
            "cert9.db", "key4.db", "logins.json",
            "sessionstore.jsonlz4", "sessionCheckpoints.json",
            "storage.sqlite", "favicons.sqlite",
        ]
        
        # Directories with per-site storage
        session_dirs = ["storage", "sessionstore-backups"]
        
        copied = []
        for fname in session_files:
            src = source / fname
            dst = target_dir / fname
            if src.exists():
                try:
                    shutil.copy2(str(src), str(dst))
                    copied.append(fname)
                except Exception as e:
                    pass
        
        for dname in session_dirs:
            src = source / dname
            dst = target_dir / dname
            if src.exists():
                try:
                    if dst.exists():
                        shutil.rmtree(str(dst))
                    shutil.copytree(str(src), str(dst))
                    copied.append(dname + "/")
                except Exception as e:
                    pass
        
        return str(target_dir), copied

    def _get_default_firefox_profile(self):
        """Get Firefox profile path (snap priority, from nlp2cmd pattern)."""
        home = Path.home()
        
        # Snap Firefox (priority)
        snap_firefox_base = home / "snap" / "firefox" / "common" / ".mozilla" / "firefox"
        if snap_firefox_base.exists():
            for profile_dir in snap_firefox_base.iterdir():
                if profile_dir.is_dir() and (profile_dir / "cookies.sqlite").exists():
                    return str(profile_dir)
        
        # Standard Firefox
        firefox_dir = home / ".mozilla" / "firefox"
        if firefox_dir.exists():
            for profile_dir in firefox_dir.iterdir():
                if profile_dir.is_dir() and (profile_dir / "cookies.sqlite").exists():
                    return str(profile_dir)
        
        return None

    def list_available_browsers(self):
        """List browsers with saved sessions available for copying."""
        try:
            profiles = self._get_browser_profiles()
            
            available = []
            for browser, paths in profiles.items():
                if paths:
                    available.append({
                        "browser": browser,
                        "profiles": len(paths),
                        "paths": paths[:3]  # Limit output
                    })
            
            # Check for saved storage_state
            has_saved_session = self.storage_state_file.exists()
            
            return {
                "success": True,
                "browsers_found": len(available),
                "browsers": available,
                "has_saved_session": has_saved_session,
                "saved_session_path": str(self.storage_state_file) if has_saved_session else None
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def save_browser_session(self, storage_state=None):
        """Save current browser session state for future use."""
        try:
            if storage_state:
                with open(self.storage_state_file, 'w') as f:
                    json.dump(storage_state, f, indent=2)
                
                return {
                    "success": True,
                    "message": "Browser session saved",
                    "path": str(self.storage_state_file),
                    "timestamp": str(datetime.now())
                }
            else:
                return {
                    "success": False,
                    "error": "No storage_state provided"
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_api_key_from_storage_state(self, headless=True):
        """Get API key using saved browser storage state (already logged in)."""
        try:
            from playwright.sync_api import sync_playwright
            
            if not self.storage_state_file.exists():
                return {
                    "success": False,
                    "error": "No saved browser session found. Use save_browser_session first or try get_api_key_from_session",
                    "step": "no_storage_state"
                }
            
            # Load storage state
            with open(self.storage_state_file, 'r') as f:
                storage_state = json.load(f)
            
            with sync_playwright() as p:
                # Launch browser with storage state
                browser = p.chromium.launch(headless=headless)
                context = browser.new_context(storage_state=storage_state)
                page = context.new_page()
                
                # Navigate to OpenRouter keys page
                page.goto("https://openrouter.ai/keys", wait_until="networkidle")
                page.wait_for_timeout(2000)
                
                # Check if we're logged in
                page_text = page.inner_text("body")
                
                if "sign in" in page_text.lower() or "login" in page_text.lower():
                    browser.close()
                    return {
                        "success": False,
                        "error": "Session expired or invalid. Need to re-authenticate.",
                        "step": "session_invalid"
                    }
                
                # Look for API key on page
                api_key_pattern = r'sk-or-v1-[a-f0-9]{64}'
                api_keys = re.findall(api_key_pattern, page_text)
                
                if api_keys:
                    api_key = api_keys[0]
                    self.save_key(api_key)
                    
                    # Update storage state for future use
                    new_storage_state = context.storage_state()
                    self.save_browser_session(new_storage_state)
                    
                    browser.close()
                    
                    return {
                        "success": True,
                        "api_key": api_key,
                        "key_preview": api_key[:20] + "..." + api_key[-10:],
                        "step": "key_retrieved_from_storage_state",
                        "source": "saved_session"
                    }
                else:
                    browser.close()
                    return {
                        "success": False,
                        "error": "Could not find API key",
                        "step": "key_not_found"
                    }
                    
        except ImportError:
            return {
                "success": False,
                "error": "Playwright not installed. Install with: pip install playwright && playwright install chromium"
            }
        except Exception as e:
            return {"success": False, "error": str(e), "step": "browser_error"}

    def get_api_key_from_session(self, browser_type=None, profile_path=None, headless=True):
        """Copy API key from existing browser session (user already logged in).
        
        Uses nlp2cmd pattern: copy Firefox profile files before using with Playwright.
        Auto-installs Playwright if missing.
        """
        # Ensure Playwright is installed
        ensure_result = self._ensure_playwright()
        if not ensure_result.get("success"):
            return ensure_result
        
        try:
            from playwright.sync_api import sync_playwright
            
            # Auto-detect browser with active session
            if browser_type is None:
                if self._is_firefox_running() and self._get_default_firefox_profile():
                    browser_type = "firefox"
                    print("[INFO] Firefox detected as active, using Firefox profile")
                else:
                    browser_type = "chromium"
                    print("[INFO] Using Chromium profile")
            
            with sync_playwright() as p:
                # Determine browser type and launch options
                if browser_type == "firefox":
                    browser_class = p.firefox
                    # For Firefox, use nlp2cmd pattern: copy profile files first
                    source_profile = profile_path or self._get_default_firefox_profile()
                    if source_profile:
                        print(f"[INFO] Preparing Firefox profile copy from: {source_profile}")
                        user_data_dir, copied = self._prepare_playwright_profile(source_profile)
                        print(f"[INFO] Copied {len(copied)} files/directories")
                    else:
                        user_data_dir = None
                elif browser_type == "webkit":
                    browser_class = p.webkit
                    user_data_dir = None
                else:  # chromium, chrome, edge, brave
                    browser_class = p.chromium
                    user_data_dir = profile_path or self._get_default_chromium_profile()
                
                # Try to launch with user data dir if available
                if user_data_dir and Path(user_data_dir).exists():
                    try:
                        # Launch with persistent context (shares cookies/storage with regular browser)
                        context = browser_class.launch_persistent_context(
                            user_data_dir,
                            headless=headless,
                            args=['--disable-blink-features=AutomationControlled']
                        )
                        page = context.new_page()
                    except Exception as e:
                        print(f"[WARN] Could not launch with persistent context: {e}")
                        # Fall back to regular launch
                        browser = browser_class.launch(headless=headless)
                        context = browser.new_context()
                        page = context.new_page()
                else:
                    browser = browser_class.launch(headless=headless)
                    context = browser.new_context()
                    page = context.new_page()
                
                # Navigate to OpenRouter
                page.goto("https://openrouter.ai/keys", wait_until="networkidle")
                page.wait_for_timeout(3000)
                
                # Check login status
                page_text = page.inner_text("body")
                
                if "sign in" in page_text.lower() or "login" in page_text.lower():
                    # Not logged in - save state anyway but report it
                    storage_state = context.storage_state()
                    self.save_browser_session(storage_state)
                    
                    if 'browser' in locals():
                        browser.close()
                    else:
                        context.close()
                    
                    return {
                        "success": False,
                        "error": "Not logged into OpenRouter in this browser session",
                        "step": "not_logged_in",
                        "suggestion": "Please login to OpenRouter manually first, then run again"
                    }
                
                # Extract API key
                api_key_pattern = r'sk-or-v1-[a-f0-9]{64}'
                api_keys = re.findall(api_key_pattern, page_text)
                
                if api_keys:
                    api_key = api_keys[0]
                    self.save_key(api_key)
                    
                    # Save the session for future use
                    storage_state = context.storage_state()
                    self.save_browser_session(storage_state)
                    
                    if 'browser' in locals():
                        browser.close()
                    else:
                        context.close()
                    
                    return {
                        "success": True,
                        "api_key": api_key,
                        "key_preview": api_key[:20] + "..." + api_key[-10:],
                        "step": "key_retrieved_from_browser_session",
                        "source": browser_type,
                        "session_saved": True
                    }
                else:
                    if 'browser' in locals():
                        browser.close()
                    else:
                        context.close()
                    
                    return {
                        "success": False,
                        "error": "Could not find API key",
                        "step": "key_not_found"
                    }
                    
        except ImportError:
            return {
                "success": False,
                "error": "Playwright not installed. Install with: pip install playwright && playwright install"
            }
        except Exception as e:
            return {"success": False, "error": str(e), "step": "browser_error"}

    def _get_default_chromium_profile(self):
        """Get default Chromium/Chrome profile path."""
        home = Path.home()
        paths = [
            home / ".config" / "google-chrome" / "Default",
            home / ".config" / "chromium" / "Default",
            home / ".config" / "BraveSoftware" / "Brave-Browser" / "Default",
            home / ".config" / "microsoft-edge" / "Default",
        ]
        for path in paths:
            if path.exists():
                return str(path.parent)  # Return parent dir for persistent context
        return None

    def _get_default_firefox_profile(self):
        """Get default Firefox profile path."""
        home = Path.home()
        firefox_dir = home / ".mozilla" / "firefox"
        profiles_ini = firefox_dir / "profiles.ini"
        
        if profiles_ini.exists():
            with open(profiles_ini, 'r') as f:
                content = f.read()
                # Find default profile
                for match in re.finditer(r'\[Profile\d+\].*?Path=(.+?)\n.*?Default=1', content, re.DOTALL):
                    return str(firefox_dir / match.group(1))
                # Fallback to first profile
                for match in re.finditer(r'Path=(.+)', content):
                    return str(firefox_dir / match.group(1))
        return None

    def extract_openrouter_links(self, text):
        """Extract OpenRouter-related URLs from text."""
        try:
            # Look for OpenRouter URLs
            patterns = [
                r'https?://(?:www\.)?openrouter\.ai/[^\s<>"\']+',
                r'https?://openrouter\.ai/[^\s<>"\']+',
            ]

            urls = []
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                urls.extend(matches)

            # Filter for API key related links
            api_links = [url for url in urls if 'key' in url.lower() or 'api' in url.lower() or 'token' in url.lower()]

            return {
                "success": True,
                "all_urls": list(set(urls)),
                "api_links": list(set(api_links)),
                "count": len(urls)
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_api_key_from_email(self, email_config, search_criteria="FROM openrouter"):
        """Complete workflow: Check email → Extract link → Get API key."""
        try:
            # Step 1: Import and use email_client
            from ..email_client.v1.skill import EmailClientSkill

            email_client = EmailClientSkill()

            # Connect to IMAP
            connect_result = email_client.connect(
                server=email_config.get("imap_server", "imap.gmail.com"),
                username=email_config.get("username"),
                password=email_config.get("password"),
                port=email_config.get("imap_port", 993),
                use_ssl=True,
                protocol="imap"
            )

            if not connect_result.get("success"):
                return {"success": False, "error": f"Email connect failed: {connect_result.get('error')}", "step": "email_connect"}

            # Search for OpenRouter emails
            search_result = email_client.search(
                folder=email_config.get("folder", "INBOX"),
                criteria=search_criteria,
                limit=10
            )

            if not search_result.get("success"):
                return {"success": False, "error": "Email search failed", "step": "email_search"}

            messages = search_result.get("messages", [])
            if not messages:
                return {"success": False, "error": "No OpenRouter emails found", "step": "email_search"}

            # Read the most recent email
            latest_msg = messages[-1]
            read_result = email_client.read(latest_msg["id"], email_config.get("folder", "INBOX"))

            if not read_result.get("success"):
                return {"success": False, "error": "Could not read email", "step": "email_read"}

            # Extract text (both plain and HTML)
            email_text = read_result.get("body", "") + " " + read_result.get("html_body", "")

            # Extract links
            links_result = email_client.extract_links(email_text)

            if not links_result.get("success"):
                return {"success": False, "error": "Could not extract links", "step": "link_extraction"}

            # Filter for OpenRouter links
            openrouter_links = self.extract_openrouter_links(email_text)

            return {
                "success": True,
                "step": "email_processed",
                "email_subject": read_result.get("subject"),
                "email_from": read_result.get("from"),
                "all_links": links_result.get("urls", []),
                "openrouter_links": openrouter_links.get("all_urls", []),
                "api_links": openrouter_links.get("api_links", []),
                "email_preview": email_text[:500]
            }

        except Exception as e:
            return {"success": False, "error": str(e), "step": "unknown"}

    def login_and_get_key(self, credentials, api_link=None):
        """Login to OpenRouter and get API key using browser automation."""
        try:
            # Import web_automation skill
            from ..web_automation.v1.skill import WebAutomationSkill

            web = WebAutomationSkill()

            # Navigate to OpenRouter login or API link
            if api_link:
                nav_result = web.navigate(api_link)
            else:
                nav_result = web.navigate("https://openrouter.ai/keys")

            if not nav_result.get("success"):
                return {"success": False, "error": f"Navigation failed: {nav_result.get('error')}", "step": "navigate"}

            # Check if we're on login page
            page_text = web.extract_text().get("text", "")

            if "sign in" in page_text.lower() or "login" in page_text.lower():
                # Fill login form
                # OpenRouter uses different auth methods - try common selectors

                # Try Google/GitHub OAuth buttons first
                oauth_selectors = [
                    "button:has-text('Google')",
                    "button:has-text('GitHub')",
                    "button:has-text('Sign in with Google')",
                    "a:has-text('Google')",
                    "[aria-label*='Google']"
                ]

                for selector in oauth_selectors:
                    try:
                        web.click(selector)
                        web.wait(2000)
                        break
                    except:
                        continue

                # If email/password login is available
                try:
                    web.fill("input[type='email']", credentials.get("email", ""))
                    web.fill("input[type='password']", credentials.get("password", ""))
                    web.click("button[type='submit']")
                    web.wait(3000)
                except:
                    pass  # OAuth might have worked

            # Wait for page to load after login
            web.wait(3000)

            # Navigate to API keys page if not already there
            if "keys" not in web.navigate.__self__.page.url:
                web.navigate("https://openrouter.ai/keys")
                web.wait(2000)

            # Try to find API key on page
            page_text = web.extract_text().get("text", "")

            # Look for API key pattern
            api_key_pattern = r'sk-or-v1-[a-f0-9]{64}'
            api_keys = re.findall(api_key_pattern, page_text)

            if api_keys:
                api_key = api_keys[0]

                # Save key
                self.save_key(api_key)

                # Close browser
                web.close()

                return {
                    "success": True,
                    "api_key": api_key,
                    "key_preview": api_key[:20] + "..." + api_key[-10:],
                    "step": "key_retrieved"
                }
            else:
                # Take screenshot for debugging
                screenshot = web.screenshot(path="/tmp/openrouter_debug.png")

                return {
                    "success": False,
                    "error": "Could not find API key on page",
                    "step": "key_extraction",
                    "page_url": nav_result.get("url"),
                    "screenshot": screenshot.get("path") if screenshot.get("success") else None
                }

        except Exception as e:
            return {"success": False, "error": str(e), "step": "browser_automation"}

    def save_key(self, api_key):
        """Save API key to file."""
        try:
            with open(self.api_key_file, 'w') as f:
                f.write(api_key)

            # Also save to config
            config = self._load_config()
            config["api_key"] = api_key
            config["saved_at"] = str(datetime.now())
            self._save_config(config)

            return {"success": True, "message": "API key saved"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def save_key_to_env(self, api_key, env_path=".env"):
        """Save API key to .env file."""
        try:
            env_file = Path(env_path)
            
            # Read existing content
            if env_file.exists():
                content = env_file.read_text()
            else:
                content = ""
            
            # Replace or add OPENROUTER_API_KEY
            lines = content.split('\n')
            new_lines = []
            key_found = False
            
            for line in lines:
                if line.startswith('OPENROUTER_API_KEY='):
                    new_lines.append(f'OPENROUTER_API_KEY={api_key}')
                    key_found = True
                else:
                    new_lines.append(line)
            
            if not key_found:
                new_lines.append(f'OPENROUTER_API_KEY={api_key}')
            
            # Write back
            env_file.write_text('\n'.join(new_lines))
            
            return {"success": True, "message": f"API key saved to {env_path}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _ensure_playwright(self):
        """Ensure Playwright is installed. Auto-install if missing."""
        try:
            from playwright.sync_api import sync_playwright
            return {"success": True, "installed": True}
        except ImportError:
            print("[INFO] Playwright not found. Installing...")
            try:
                # Install playwright
                subprocess.run([sys.executable, "-m", "pip", "install", "playwright"], 
                           check=True, capture_output=True)
                # Install firefox browser
                subprocess.run([sys.executable, "-m", "playwright", "install", "firefox"],
                           check=True, capture_output=True)
                print("[INFO] Playwright installed successfully!")
                return {"success": True, "installed": True, "fresh_install": True}
            except Exception as e:
                return {"success": False, "error": str(e)}

    def load_key(self):
        """Load saved API key."""
        try:
            if self.api_key_file.exists():
                with open(self.api_key_file, 'r') as f:
                    api_key = f.read().strip()
                return {
                    "success": True,
                    "api_key": api_key,
                    "has_key": bool(api_key)
                }
            return {"success": True, "has_key": False, "api_key": None}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def check_key_validity(self, api_key=None):
        """Check if API key is valid by making test request."""
        try:
            key = api_key or self.load_key().get("api_key")

            if not key:
                return {"success": False, "error": "No API key available"}

            # Test with simple request to OpenRouter
            import urllib.request
            import json
            import datetime
            import time

            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/auth/key",
                headers={"Authorization": f"Bearer {key}"}
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read())
                return {
                    "success": True,
                    "valid": True,
                    "key_info": data
                }

        except Exception as e:
            return {"success": False, "error": str(e), "valid": False}

    def execute(self, input_data: dict) -> dict:
        """evo-engine interface."""
        action = input_data.get("action", "get_api_key_from_email")

        if action == "get_api_key_from_email":
            return self.get_api_key_from_email(
                input_data.get("email_config", {}),
                input_data.get("search_criteria", "FROM openrouter")
            )
        elif action == "get_api_key_from_session":
            return self.get_api_key_from_session(
                input_data.get("browser_type", "chromium"),
                input_data.get("profile_path"),
                input_data.get("headless", True)
            )
        elif action == "get_api_key_from_storage_state":
            return self.get_api_key_from_storage_state(
                input_data.get("headless", True)
            )
        elif action == "save_browser_session":
            return self.save_browser_session(
                input_data.get("storage_state")
            )
        elif action == "list_available_browsers":
            return self.list_available_browsers()
        elif action == "login_and_get_key":
            return self.login_and_get_key(
                input_data.get("credentials", {}),
                input_data.get("api_link")
            )
        elif action == "save_key":
            return self.save_key(input_data.get("api_key", ""))
        elif action == "save_key_to_env":
            return self.save_key_to_env(
                input_data.get("api_key", ""),
                input_data.get("env_path", ".env")
            )
        elif action == "load_key":
            return self.load_key()
        elif action == "check_key_validity":
            return self.check_key_validity(input_data.get("api_key"))
        else:
            return {"success": False, "error": f"Unknown action: {action}"}


def execute(input_data: dict) -> dict:
    return OpenRouterAutomationSkill().execute(input_data)


if __name__ == "__main__":
    skill = OpenRouterAutomationSkill()
    print(f"Info: {json.dumps(get_info(), indent=2)}")
    print(f"Health: {health_check()}")

    # Test list browsers
    print("\n=== Test: List Available Browsers ===")
    browsers = skill.list_available_browsers()
    print(json.dumps(browsers, indent=2))

    # Test link extraction
    test_text = """
    Your OpenRouter API key is ready!
    Access it here: https://openrouter.ai/keys
    Or view your account: https://openrouter.ai/account
    """
    print("\n=== Test: Extract OpenRouter Links ===")
    print(json.dumps(skill.extract_openrouter_links(test_text), indent=2))
    
    print("\n=== Browser Session Features ===")
    print("New actions available:")
    print("  - get_api_key_from_session: Copy from existing browser")
    print("  - get_api_key_from_storage_state: Use saved session")
    print("  - save_browser_session: Save current session")
    print("  - list_available_browsers: Find browser profiles")
