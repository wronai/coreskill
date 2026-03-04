import subprocess
import json
import re
import urllib.request
import urllib.parse
import urllib.error
from html.parser import HTMLParser


class ContentSearchSkill:
    def __init__(self):
        self.name = "content_search"
        self.version = "v1"
        self.description = "Searches for content using web search when web_search returned empty results"

    def execute(self, params: dict) -> dict:
        try:
            text = params.get('text', '').strip()
            if not text:
                return {
                    'success': False,
                    'error': 'No search query provided',
                    'message': 'Please provide a search query after "znajdź"',
                    'spoken': 'Proszę podać zapytanie po słowie "znajdź"'
                }

            # Extract search query after 'znajdź'
            query = re.sub(r'^znajdź\s+', '', text, flags=re.IGNORECASE).strip()
            if not query:
                return {
                    'success': False,
                    'error': 'No search query provided',
                    'message': 'Please provide a search query after "znajdź"',
                    'spoken': 'Proszę podać zapytanie po słowie "znajdź"'
                }

            # Fallback: Use duckduckgo HTML search
            results = self._search_duckduckgo(query)
            if results:
                # Prepare spoken summary
                if len(results) == 1:
                    spoken = f"Znalazłem jeden wynik: {results[0]['title']}"
                else:
                    spoken = f"Znalazłem {len(results)} wyników. Pierwszy to: {results[0]['title']}"
                
                return {
                    'success': True,
                    'results': results,
                    'message': f"Found {len(results)} results using direct web search",
                    'spoken': spoken
                }
            else:
                return {
                    'success': False,
                    'error': 'No results found',
                    'message': 'No relevant content found on the web',
                    'spoken': 'Nie udało się znaleźć żadnych wyników'
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'An error occurred during content search',
                'spoken': 'Wystąpił błąd podczas wyszukiwania'
            }

    def _search_duckduckgo(self, query):
        """Search DuckDuckGo HTML interface and extract top results."""
        try:
            # URL encode query
            encoded_query = urllib.parse.quote(query)
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
            
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8')
            
            # Extract results using HTMLParser
            parser = DuckDuckGoParser()
            parser.feed(html)
            
            results = []
            for i, (title, url, snippet) in enumerate(zip(parser.titles, parser.urls, parser.snippets)):
                if i >= 5:  # Limit to top 5 results
                    break
                if title and url:
                    results.append({
                        'title': title.strip(),
                        'url': url.strip(),
                        'snippet': snippet.strip() if snippet else ''
                    })
            
            return results
        except Exception:
            return []


class DuckDuckGoParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.titles = []
        self.urls = []
        self.snippets = []
        self._in_result = False
        self._in_title = False
        self._in_url = False
        self._in_snippet = False
        self._current_title = ''
        self._current_url = ''
        self._current_snippet = ''
        self._depth = 0
        self._result_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        
        # Check for result divs (class="result" or class="result__a")
        if tag == 'div' and 'class' in attrs_dict:
            classes = attrs_dict['class']
            if 'result' in classes:
                self._in_result = True
                self._result_depth = self._depth
                self._current_title = ''
                self._current_url = ''
                self._current_snippet = ''
        
        if self._in_result:
            if tag == 'a' and 'href' in attrs_dict:
                href = attrs_dict['href']
                # Extract URL from ddg redirection
                if href.startswith('/l/?kh=1&uddg='):
                    url = urllib.parse.unquote(href.split('uddg=')[1])
                    self._current_url = url
                    self._in_url = True
                elif href.startswith('http'):
                    self._current_url = href
                    self._in_url = True
            
            if tag == 'a' and 'class' in attrs_dict and 'result__a' in attrs_dict['class']:
                self._in_title = True
            
            if tag == 'a' and 'class' in attrs_dict and 'result__snippet' in attrs_dict['class']:
                self._in_snippet = True

        self._depth += 1

    def handle_endtag(self, tag):
        if tag == 'div' and self._in_result and self._depth == self._result_depth + 1:
            # End of result block
            if self._current_title or self._current_url:
                self.titles.append(self._current_title)
                self.urls.append(self._current_url)
                self.snippets.append(self._current_snippet)
            self._in_result = False
        
        if self._in_result:
            if tag == 'a' and self._in_title:
                self._in_title = False
            if tag == 'a' and self._in_snippet:
                self._in_snippet = False
        
        self._depth -= 1

    def handle_data(self, data):
        if self._in_result:
            if self._in_title:
                self._current_title += data
            if self._in_snippet:
                self._current_snippet += data


def get_info() -> dict:
    return {
        'name': 'content_search',
        'version': 'v1',
        'description': 'Searches for content using web search when web_search returned empty results'
    }


def health_check() -> dict:
    try:
        # Check if espeak is available (for TTS capability)
        subprocess.run(['espeak', '--version'], capture_output=True, timeout=2)
        return {'status': 'ok'}
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return {'status': 'error', 'message': 'espeak not available'}


def execute(params: dict) -> dict:
    skill = ContentSearchSkill()
    return skill.execute(params)


if __name__ == '__main__':
    # Test block
    test_params = {'text': 'znajdź python tutorial'}
    result = execute(test_params)
    print(json.dumps(result, indent=2, ensure_ascii=False))