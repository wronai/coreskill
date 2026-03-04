#!/usr/bin/env python3
"""
web_automation skill - Browser automation using Playwright.
Supports: navigate, click, type, screenshot, extract text, fill forms.
"""
import json
import subprocess
import shutil
import time
from pathlib import Path


def get_info():
    return {
        "name": "web_automation",
        "version": "v1",
        "description": "Browser automation using Playwright. Navigate, click, type, extract data.",
        "capabilities": ["browser", "automation", "playwright", "scraping"],
        "actions": ["navigate", "click", "type", "screenshot", "extract_text", "get_attribute", "wait", "evaluate"]
    }


def health_check():
    """Check if Playwright is available."""
    try:
        import playwright
        return True
    except ImportError:
        # Try to install
        try:
            subprocess.run(["pip", "install", "playwright"], check=True, capture_output=True)
            subprocess.run(["playwright", "install", "chromium"], check=True, capture_output=True)
            import playwright
            return True
        except:
            return False


class WebAutomationSkill:
    """Browser automation using Playwright."""

    def __init__(self):
        self.page = None
        self.browser = None
        self.context = None

    def _ensure_playwright(self):
        """Ensure Playwright is installed."""
        try:
            from playwright.sync_api import sync_playwright
            return sync_playwright
        except ImportError:
            try:
                subprocess.run(["pip", "install", "playwright"], capture_output=True, timeout=60)
                subprocess.run(["playwright", "install", "chromium"], capture_output=True, timeout=120)
                from playwright.sync_api import sync_playwright
                return sync_playwright
            except Exception as e:
                raise ImportError(f"Could not install Playwright: {e}")

    def _get_page(self, headless=True):
        """Get or create browser page."""
        if self.page is None:
            sync_playwright = self._ensure_playwright()
            self.p = sync_playwright().start()
            self.browser = self.p.chromium.launch(headless=headless)
            self.context = self.browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            self.page = self.context.new_page()
        return self.page

    def navigate(self, url, wait_until="networkidle", timeout=30000):
        """Navigate to URL."""
        try:
            page = self._get_page()
            response = page.goto(url, wait_until=wait_until, timeout=timeout)

            return {
                "success": True,
                "url": page.url,
                "title": page.title(),
                "status": response.status if response else None
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def click(self, selector, timeout=5000):
        """Click element by selector."""
        try:
            page = self._get_page()
            page.click(selector, timeout=timeout)
            return {"success": True, "action": "click", "selector": selector}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def type(self, selector, text, clear_first=True, timeout=5000):
        """Type text into element."""
        try:
            page = self._get_page()
            if clear_first:
                page.fill(selector, "", timeout=timeout)
            page.type(selector, text, timeout=timeout)
            return {"success": True, "action": "type", "selector": selector, "text_length": len(text)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def fill(self, selector, text, timeout=5000):
        """Fill form field (faster than type)."""
        try:
            page = self._get_page()
            page.fill(selector, text, timeout=timeout)
            return {"success": True, "action": "fill", "selector": selector}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def extract_text(self, selector=None, timeout=5000):
        """Extract text from page or element."""
        try:
            page = self._get_page()
            if selector:
                text = page.inner_text(selector, timeout=timeout)
            else:
                text = page.inner_text("body")
            return {
                "success": True,
                "text": text,
                "length": len(text)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_attribute(self, selector, attribute, timeout=5000):
        """Get attribute value from element."""
        try:
            page = self._get_page()
            value = page.get_attribute(selector, attribute, timeout=timeout)
            return {
                "success": True,
                "selector": selector,
                "attribute": attribute,
                "value": value
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def screenshot(self, path=None, full_page=False):
        """Take screenshot."""
        try:
            page = self._get_page()
            if path is None:
                path = f"/tmp/screenshot_{int(time.time())}.png"

            page.screenshot(path=path, full_page=full_page)
            return {
                "success": True,
                "path": path,
                "full_page": full_page
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def wait(self, milliseconds=1000):
        """Wait for specified time."""
        try:
            page = self._get_page()
            page.wait_for_timeout(milliseconds)
            return {"success": True, "waited_ms": milliseconds}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def wait_for_selector(self, selector, timeout=5000):
        """Wait for element to appear."""
        try:
            page = self._get_page()
            page.wait_for_selector(selector, timeout=timeout)
            return {"success": True, "selector": selector}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def evaluate(self, script):
        """Execute JavaScript on page."""
        try:
            page = self._get_page()
            result = page.evaluate(script)
            return {
                "success": True,
                "result": result
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def close(self):
        """Close browser."""
        try:
            if self.browser:
                self.browser.close()
            if hasattr(self, 'p'):
                self.p.stop()
            self.page = None
            self.browser = None
            self.context = None
            return {"success": True, "message": "Browser closed"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_cookies(self):
        """Get all cookies."""
        try:
            page = self._get_page()
            cookies = self.context.cookies()
            return {
                "success": True,
                "cookies": cookies
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def execute(self, input_data: dict) -> dict:
        """evo-engine interface."""
        action = input_data.get("action", "navigate")

        if action == "navigate":
            return self.navigate(
                input_data.get("url", ""),
                input_data.get("wait_until", "networkidle"),
                input_data.get("timeout", 30000)
            )
        elif action == "click":
            return self.click(
                input_data.get("selector", ""),
                input_data.get("timeout", 5000)
            )
        elif action == "type":
            return self.type(
                input_data.get("selector", ""),
                input_data.get("text", ""),
                input_data.get("clear_first", True),
                input_data.get("timeout", 5000)
            )
        elif action == "fill":
            return self.fill(
                input_data.get("selector", ""),
                input_data.get("text", ""),
                input_data.get("timeout", 5000)
            )
        elif action == "extract_text":
            return self.extract_text(
                input_data.get("selector"),
                input_data.get("timeout", 5000)
            )
        elif action == "get_attribute":
            return self.get_attribute(
                input_data.get("selector", ""),
                input_data.get("attribute", ""),
                input_data.get("timeout", 5000)
            )
        elif action == "screenshot":
            return self.screenshot(
                input_data.get("path"),
                input_data.get("full_page", False)
            )
        elif action == "wait":
            return self.wait(input_data.get("milliseconds", 1000))
        elif action == "wait_for_selector":
            return self.wait_for_selector(
                input_data.get("selector", ""),
                input_data.get("timeout", 5000)
            )
        elif action == "evaluate":
            return self.evaluate(input_data.get("script", ""))
        elif action == "get_cookies":
            return self.get_cookies()
        elif action == "close":
            return self.close()
        else:
            return {"success": False, "error": f"Unknown action: {action}"}


def execute(input_data: dict) -> dict:
    return WebAutomationSkill().execute(input_data)


if __name__ == "__main__":
    skill = WebAutomationSkill()
    print(f"Info: {json.dumps(get_info(), indent=2)}")
    print(f"Health: {health_check()}")
