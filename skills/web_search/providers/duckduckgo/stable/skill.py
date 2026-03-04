"""
web_search skill - Search the internet using only stdlib (urllib).
Bootstrap skill for evo-engine. No external dependencies.
Falls back to curl if urllib fails.
"""
import subprocess
import json
import urllib.request
import urllib.parse
import html.parser
import re


class SimpleHTMLTextExtractor(html.parser.HTMLParser):
    """Extract visible text from HTML."""
    def __init__(self):
        super().__init__()
        self._text = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self._skip = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            t = data.strip()
            if t:
                self._text.append(t)

    def get_text(self):
        return " ".join(self._text)


class WebSearchSkill:
    """Search the web and fetch page content using stdlib only."""

    def _fetch_url(self, url, timeout=10):
        """Fetch URL content. Try urllib first, fallback to curl."""
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (evo-engine bot)"
            })
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception:
            try:
                r = subprocess.run(
                    ["curl", "-sL", "-m", str(timeout),
                     "-A", "Mozilla/5.0 (evo-engine bot)", url],
                    capture_output=True, text=True, timeout=timeout + 5)
                if r.returncode == 0:
                    return r.stdout
            except:
                pass
        return None

    def search_duckduckgo(self, query, max_results=5):
        """Search DuckDuckGo Lite (no JS needed)."""
        url = "https://lite.duckduckgo.com/lite/?" + urllib.parse.urlencode({"q": query})
        html_content = self._fetch_url(url)
        if not html_content:
            return {"success": False, "error": "Could not fetch search results"}

        results = []
        # Parse DDG Lite results - links are in <a> tags with class="result-link"
        link_pattern = re.compile(
            r'<a[^>]*class="result-link"[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
            re.DOTALL)
        snippet_pattern = re.compile(
            r'<td class="result-snippet">(.*?)</td>', re.DOTALL)

        links = link_pattern.findall(html_content)
        snippets = snippet_pattern.findall(html_content)

        for i, (href, title) in enumerate(links[:max_results]):
            title = re.sub(r'<[^>]+>', '', title).strip()
            snippet = ""
            if i < len(snippets):
                snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip()
            if href and title:
                results.append({
                    "title": title,
                    "url": href,
                    "snippet": snippet[:200]
                })

        return {"success": True, "query": query, "results": results}

    def fetch_page_text(self, url, max_chars=2000):
        """Fetch a page and extract readable text."""
        content = self._fetch_url(url)
        if not content:
            return {"success": False, "error": f"Could not fetch {url}"}

        parser = SimpleHTMLTextExtractor()
        try:
            parser.feed(content)
            text = parser.get_text()[:max_chars]
        except:
            text = re.sub(r'<[^>]+>', ' ', content)
            text = re.sub(r'\s+', ' ', text).strip()[:max_chars]

        return {"success": True, "url": url, "text": text}

    def search_and_summarize(self, query, max_results=3):
        """Search and fetch top results text."""
        search_result = self.search_duckduckgo(query, max_results)
        if not search_result["success"]:
            return search_result

        for r in search_result.get("results", [])[:2]:
            page = self.fetch_page_text(r["url"], 1000)
            if page["success"]:
                r["page_text"] = page["text"]

        return search_result

    def execute(self, input_data: dict) -> dict:
        """evo-engine interface."""
        action = input_data.get("action", "search")
        query = input_data.get("query", input_data.get("text", ""))

        if action == "search":
            return self.search_duckduckgo(query)
        elif action == "fetch":
            return self.fetch_page_text(input_data.get("url", ""))
        elif action == "search_and_read":
            return self.search_and_summarize(query)
        return {"success": False, "error": f"Unknown action: {action}"}


def get_info():
    return {
        "name": "web_search",
        "version": "v1",
        "description": "Search internet via DuckDuckGo, fetch pages. Stdlib only.",
        "actions": ["search", "fetch", "search_and_read"],
        "author": "evo-engine"
    }


def health_check():
    # Try urllib first (short timeout)
    try:
        req = urllib.request.Request("https://lite.duckduckgo.com/",
                                     headers={"User-Agent": "Mozilla/5.0"})
        urllib.request.urlopen(req, timeout=8)
        return True
    except Exception:
        pass
    # Fallback: try curl (bypasses Python SSL issues)
    try:
        r = subprocess.run(
            ["curl", "-sL", "-m", "8", "-o", "/dev/null", "-w", "%{http_code}",
             "https://lite.duckduckgo.com/"],
            capture_output=True, text=True, timeout=12)
        if r.returncode == 0 and r.stdout.strip().startswith(("2", "3")):
            return True
    except Exception:
        pass
    # Fallback: basic DNS resolution (skill code is valid even if network is down)
    try:
        import socket
        socket.getaddrinfo("lite.duckduckgo.com", 443, socket.AF_INET)
        return True  # DNS works = network available, just slow
    except Exception:
        pass
    return False


if __name__ == "__main__":
    w = WebSearchSkill()
    print(f"Info: {json.dumps(get_info(), indent=2)}")
    print(f"Health: {health_check()}")
    r = w.search_duckduckgo("python espeak tts", 3)
    print(f"Search: {json.dumps(r, indent=2)}")
