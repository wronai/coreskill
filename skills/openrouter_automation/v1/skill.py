#!/usr/bin/env python3
"""
openrouter_automation skill - Automate OpenRouter API key retrieval.
Flow: Check email → Extract link → Login → Get API key.
"""
import json
import re
import os
from pathlib import Path


def get_info():
    return {
        "name": "openrouter_automation",
        "version": "v1",
        "description": "Automate OpenRouter login and API key retrieval via email link + browser automation.",
        "capabilities": ["automation", "openrouter", "api", "browser", "email"],
        "actions": ["get_api_key_from_email", "login_and_get_key", "save_key", "check_key_validity"]
    }


def health_check():
    """Check if dependencies are available."""
    try:
        # Check if we can import required modules
        import imaplib
        import smtplib
        return True
    except ImportError:
        return False


class OpenRouterAutomationSkill:
    """Automate OpenRouter API key retrieval workflow."""

    def __init__(self):
        self.config_dir = Path.home() / ".evo_openrouter"
        self.config_dir.mkdir(exist_ok=True)
        self.config_file = self.config_dir / "config.json"
        self.api_key_file = self.config_dir / "api_key.txt"

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
        elif action == "login_and_get_key":
            return self.login_and_get_key(
                input_data.get("credentials", {}),
                input_data.get("api_link")
            )
        elif action == "save_key":
            return self.save_key(input_data.get("api_key", ""))
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

    # Test link extraction
    test_text = """
    Your OpenRouter API key is ready!
    Access it here: https://openrouter.ai/keys
    Or view your account: https://openrouter.ai/account
    """
    print("\nExtract OpenRouter links:")
    print(json.dumps(skill.extract_openrouter_links(test_text), indent=2))
