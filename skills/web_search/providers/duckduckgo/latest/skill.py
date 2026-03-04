import subprocess
import json
import urllib.request
import urllib.parse
import html.parser
import re
import socket
import threading
import time


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

    def scan_local_rtsp(self, ip_range="192.168.1.", ports=(554, 8554, 1935), timeout=2):
        """Scan local network for RTSP servers."""
        results = []
        threads = []
        lock = threading.Lock()

        def check_port(ip, port):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                result = sock.connect_ex((ip, port))
                sock.close()
                if result == 0:
                    with lock:
                        results.append({"ip": ip, "port": port, "service": "RTSP"})
            except:
                pass

        # Scan common local network ranges
        for i in range(1, 255):
            ip = f"{ip_range}{i}"
            for port in ports:
                t = threading.Thread(target=check_port, args=(ip, port))
                t.start()
                threads.append(t)
                # Limit concurrent threads
                if len(threads) >= 50:
                    for t in threads:
                        t.join()
                    threads = []

        for t in threads:
            t.join()

        return {"success": True, "scan_results": results}

    def execute(self, input_data: dict) -> dict:
        """evo-engine interface."""
        text = input_data.get("text", "")
        action = input_data.get("action", "search")

        # Extract query from text if not explicitly provided
        if action == "search" and not input_data.get("query"):
            query = text.strip()
        else:
            query = input_data.get("query", "")

        if action == "search":
            result = self.search_duckduckgo(query)
            if result["success"]:
                spoken = "Found {} results for '{}'. ".format(len(result.get("results", [])), query)
                if result.get("results"):
                    spoken += "Top result: {}.".format(result["results"][0].get("title", "No title"))
                result["spoken"] = spoken
            return result
        elif action == "fetch":
            result = self.fetch_page_text(input_data.get("url", ""))
            if result["success"]:
                result["spoken"] = "Fetched content from {}.".format(input_data.get("url", ""))
            return result
        elif action == "search_and_read":
            result = self.search_and_summarize(query)
            if result["success"]:
                spoken = "Found {} results for '{}'. ".format(len(result.get("results", [])), query)
                if result.get("results"):
                    spoken += "Top result: {}.".format(result["results"][0].get("title", "No title"))
                result["spoken"] = spoken
            return result
        elif action == "scan_rtsp":
            result = self.scan_local_rtsp()
            if result["success"]:
                if result.get("scan_results"):
                    devices = ", ".join([f"{r['ip']}:{r['port']}" for r in result["scan_results"]])
                    spoken = "Found {} RTSP devices: {}.".format(len(result["scan_results"]), devices)
                else:
                    spoken = "No RTSP devices found on the local network."
                result["spoken"] = spoken
            return result
        else:
            # Default to search if action is unrecognized but text is present
            if text:
                result = self.search_duckduckgo(text)
                if result["success"]:
                    spoken = "Found {} results for '{}'. ".format(len(result.get("results", [])), text)
                    if result.get("results"):
                        spoken += "Top result: {}.".format(result["results"][0].get("title", "No title"))
                    result["spoken"] = spoken
                return result
            return {"success": False, "error": f"Unknown action: {action}"}


def get_info():
    return {
        "name": "web_search",
        "version": "v1",
        "description": "Search internet via DuckDuckGo, fetch pages, scan for RTSP. Stdlib only.",
        "actions": ["search", "fetch", "search_and_read", "scan_rtsp"],
        "author": "evo-engine"
    }


def health_check():
    try:
        w = WebSearchSkill()
        assert callable(getattr(w, "execute", None))
        assert callable(getattr(w, "search_duckduckgo", None))
        assert callable(getattr(w, "fetch_page_text", None))
        assert callable(getattr(w, "scan_local_rtsp", None))
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
    print(f"Health: {json.dumps(health_check(), indent=2)}")
    
    # Test search
    r = w.search_duckduckgo("python espeak tts", 3)
    print(f"Search: {json.dumps(r, indent=2)}")
    
    # Test RTSP scan (limited scope for demo)
    print("Testing RTSP scan...")
    rtsp_result = w.scan_local_rtsp("127.0.0.", (554,), timeout=0.5)
    print(f"RTSP Scan: {json.dumps(rtsp_result, indent=2)}")