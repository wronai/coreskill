import subprocess
import json
import urllib.request
import urllib.parse
import html.parser
import re
import socket
import threading
import queue
import time
import os


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

    def execute(self, params: dict) -> dict:
        """evo-engine interface."""
        try:
            text = params.get("text", "")
            action = params.get("action", "search")
            
            # Extract query from text if not explicitly provided
            if action == "search" and not params.get("query"):
                query = text.strip() if text else "current events"
            else:
                query = params.get("query", text.strip() if text else "")
            
            if action == "search":
                result = self.search_duckduckgo(query)
                if result.get("success"):
                    spoken = f"Found {len(result.get('results', []))} results for '{query}'."
                    if result.get("results"):
                        spoken += f" Top result: {result['results'][0].get('title', 'No title')}."
                    result["spoken"] = spoken
                return result
            elif action == "fetch":
                url = params.get("url", "")
                if not url:
                    # Try to extract URL from text
                    url_match = re.search(r'https?://[^\s]+', text)
                    url = url_match.group(0) if url_match else ""
                result = self.fetch_page_text(url)
                if result.get("success"):
                    result["spoken"] = f"Page fetched successfully. Content preview: {result.get('text', '')[:200]}..."
                return result
            elif action == "search_and_read":
                result = self.search_and_summarize(query)
                if result.get("success"):
                    spoken = f"Found {len(result.get('results', []))} results for '{query}'."
                    if result.get("results"):
                        top_result = result['results'][0]
                        spoken += f" Top result: {top_result.get('title', 'No title')}."
                        if top_result.get('page_text'):
                            spoken += f" Summary: {top_result['page_text'][:200]}..."
                    result["spoken"] = spoken
                return result
            else:
                return {"success": False, "error": f"Unknown action: {action}", "spoken": f"Unknown action: {action}"}
        except Exception as e:
            return {"success": False, "error": str(e), "spoken": "An error occurred while processing your request."}


def get_info():
    return {
        "name": "web_search",
        "version": "v1",
        "description": "Search internet via DuckDuckGo, fetch pages. Stdlib only.",
        "actions": ["search", "fetch", "search_and_read"],
        "author": "evo-engine"
    }


def health_check():
    try:
        # Verify skill structure and imports (no network calls — DNS failure ≠ broken code)
        w = WebSearchSkill()
        assert callable(getattr(w, "execute", None))
        assert callable(getattr(w, "search_duckduckgo", None))
        assert callable(getattr(w, "fetch_page_text", None))
        # Verify stdlib imports are available
        import urllib.request, urllib.parse, html.parser
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def execute(params: dict) -> dict:
    """Module-level execute function."""
    skill = WebSearchSkill()
    return skill.execute(params)


if __name__ == "__main__":
    w = WebSearchSkill()
    print(f"Info: {json.dumps(get_info(), indent=2)}")
    health = health_check()
    print(f"Health: {json.dumps(health, indent=2)}")
    r = w.search_duckduckgo("python espeak tts", 3)
    print(f"Search: {json.dumps(r, indent=2)}")