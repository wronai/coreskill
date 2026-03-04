import subprocess
import json
import urllib.request
import urllib.parse
import html.parser
import re
import socket
import threading
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

    def _scan_ip(self, ip, results, timeout=1.0):
        """Check if an IP has common RTSP ports open."""
        rtsp_ports = [554, 8554, 1935, 5554]
        for port in rtsp_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                result = sock.connect_ex((ip, port))
                sock.close()
                if result == 0:
                    results.append({
                        "ip": ip,
                        "port": port,
                        "url": f"rtsp://{ip}:{port}/stream",
                        "status": "open"
                    })
                    return True
            except:
                continue
        return False

    def scan_local_network(self):
        """Scan local network for RTSP cameras."""
        results = []
        # Get local IP to determine network range
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            # Extract network prefix (e.g., "192.168.1.")
            prefix = ".".join(local_ip.split(".")[:-1]) + "."
        except:
            return {"success": False, "error": "Could not determine local IP"}

        # Scan common IPs (1-20) in parallel
        threads = []
        for i in range(1, 21):
            ip = f"{prefix}{i}"
            t = threading.Thread(target=self._scan_ip, args=(ip, results))
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join(timeout=3.0)
        
        return {"success": True, "results": results}

    def execute(self, params: dict) -> dict:
        """evo-engine interface."""
        text = params.get("text", "")
        action = params.get("action", "search")
        
        # Parse action from text if not explicitly provided
        if action == "search":
            if "kamery" in text.lower() and ("rtsp" in text.lower() or "sieci" in text.lower()):
                action = "scan_local"
            elif "znajdź" in text.lower() or "szukaj" in text.lower():
                action = "search"
            elif "pobierz" in text.lower() or "pokaż" in text.lower():
                action = "fetch"
        
        if action == "scan_local":
            scan_result = self.scan_local_network()
            if scan_result["success"]:
                if scan_result["results"]:
                    spoken = f"Znaleziono {len(scan_result['results'])} urządzeń RTSP. "
                    for i, cam in enumerate(scan_result["results"][:3]):
                        spoken += f"Kamera na {cam['ip']}:{cam['port']}. "
                else:
                    spoken = "Nie znaleziono urządzeń RTSP w sieci lokalnej."
                return {
                    "success": True,
                    "results": scan_result["results"],
                    "spoken": spoken
                }
            else:
                return {
                    "success": False,
                    "error": scan_result.get("error", "Nie udało się przeskanować sieci"),
                    "spoken": "Nie udało się przeskanować sieci lokalnej."
                }
        
        elif action == "search":
            query = text.replace("znajdź", "").replace("szukaj", "").strip()
            if not query:
                query = "python"
            result = self.search_duckduckgo(query)
            if result["success"]:
                if result["results"]:
                    spoken = f"Znaleziono {len(result['results'])} wyników. Pierwszy: {result['results'][0]['title']}. "
                else:
                    spoken = "Nie znaleziono wyników."
                return {
                    "success": True,
                    "results": result["results"],
                    "spoken": spoken
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Błąd wyszukiwania"),
                    "spoken": "Wystąpił błąd podczas wyszukiwania."
                }
        
        elif action == "fetch":
            url = text.replace("pobierz", "").replace("pokaż", "").strip()
            if not url.startswith("http"):
                url = f"https://{url}"
            result = self.fetch_page_text(url)
            if result["success"]:
                return {
                    "success": True,
                    "text": result["text"],
                    "spoken": f"Załadowano stronę: {result['url']}. Treść: {result['text'][:200]}..."
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Błąd pobierania strony"),
                    "spoken": "Nie udało się pobrać strony."
                }
        
        elif action == "search_and_read":
            query = text.replace("znajdź", "").replace("szukaj", "").strip()
            if not query:
                query = "python"
            result = self.search_and_summarize(query)
            if result["success"]:
                if result["results"]:
                    spoken = f"Znaleziono {len(result['results'])} wyników. "
                    if result["results"][0].get("page_text"):
                        spoken += f"Pierwszy wynik: {result['results'][0]['page_text'][:200]}..."
                    else:
                        spoken += f"Pierwszy wynik: {result['results'][0]['title']}. "
                else:
                    spoken = "Nie znaleziono wyników."
                return {
                    "success": True,
                    "results": result["results"],
                    "spoken": spoken
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Błąd wyszukiwania"),
                    "spoken": "Wystąpił błąd podczas wyszukiwania."
                }
        
        else:
            return {
                "success": False,
                "error": f"Nieznana akcja: {action}",
                "spoken": f"Nie rozumiem akcji: {action}"
            }


def get_info() -> dict:
    return {
        "name": "web_search",
        "version": "v1",
        "description": "Search internet via DuckDuckGo, fetch pages, scan for RTSP cameras. Stdlib only.",
        "actions": ["search", "fetch", "search_and_read", "scan_local"],
        "author": "evo-engine"
    }


def health_check() -> dict:
    try:
        # Verify class structure and imports
        w = WebSearchSkill()
        assert callable(getattr(w, "execute", None))
        assert callable(getattr(w, "search_duckduckgo", None))
        assert callable(getattr(w, "fetch_page_text", None))
        assert callable(getattr(w, "scan_local_network", None))
        
        # Verify stdlib imports are available
        import urllib.request, urllib.parse, html.parser, socket, threading
        
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
    print(f"Health: {health_check()}")
    
    # Test search
    r = w.search_duckduckgo("python espeak tts", 3)
    print(f"Search: {json.dumps(r, indent=2)}")
    
    # Test local network scan (limited for demo)
    print("Scanning local network for RTSP cameras...")
    scan_r = w.scan_local_network()
    print(f"Scan: {json.dumps(scan_r, indent=2)}")