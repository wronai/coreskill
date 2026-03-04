#!/usr/bin/env python3
"""
url_codec skill - URL encoding/decoding, base64, HTML entities using stdlib only.
Supports: urlencode, urldecode, base64encode, base64decode, htmlencode, htmldecode
"""
import json
import urllib.parse
import base64
import html


def get_info():
    return {
        "name": "url_codec",
        "version": "v1",
        "description": "Encoding/decoding: URL, base64, HTML entities. Stdlib only.",
        "capabilities": ["encoding", "decoding", "url", "base64", "html"],
        "actions": ["urlencode", "urldecode", "base64encode", "base64decode", "htmlencode", "htmldecode"]
    }


def health_check():
    try:
        import urllib.parse
        import base64
        import html
        return True
    except Exception:
        return False


class URLCodecSkill:
    """Encoding and decoding using stdlib only."""

    def urlencode(self, text, safe=''):
        """URL encode text."""
        try:
            if not isinstance(text, str):
                text = str(text)
            result = urllib.parse.quote(text, safe=safe)
            return {
                "success": True,
                "action": "urlencode",
                "input": text[:100],
                "output": result,
                "length": len(result)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def urldecode(self, text):
        """URL decode text."""
        try:
            if not isinstance(text, str):
                text = str(text)
            result = urllib.parse.unquote(text)
            return {
                "success": True,
                "action": "urldecode",
                "input": text[:100],
                "output": result,
                "length": len(result)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def base64encode(self, text, url_safe=False):
        """Base64 encode text or bytes."""
        try:
            if isinstance(text, str):
                data = text.encode('utf-8')
            else:
                data = bytes(text)
            
            if url_safe:
                result = base64.urlsafe_b64encode(data).decode('ascii')
            else:
                result = base64.b64encode(data).decode('ascii')
            
            return {
                "success": True,
                "action": "base64encode",
                "url_safe": url_safe,
                "input_length": len(data),
                "output": result,
                "output_length": len(result)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def base64decode(self, text, url_safe=False, as_text=True):
        """Base64 decode to text or bytes."""
        try:
            if url_safe:
                data = base64.urlsafe_b64decode(text)
            else:
                data = base64.b64decode(text)
            
            if as_text:
                result = data.decode('utf-8')
            else:
                result = list(data)  # JSON serializable
            
            return {
                "success": True,
                "action": "base64decode",
                "url_safe": url_safe,
                "input_length": len(text),
                "output": result,
                "output_length": len(data),
                "as_text": as_text
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def htmlencode(self, text):
        """HTML entity encode."""
        try:
            result = html.escape(text)
            return {
                "success": True,
                "action": "htmlencode",
                "input": text[:100],
                "output": result,
                "length": len(result)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def htmldecode(self, text):
        """HTML entity decode."""
        try:
            result = html.unescape(text)
            return {
                "success": True,
                "action": "htmldecode",
                "input": text[:100],
                "output": result,
                "length": len(result)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def execute(self, input_data: dict) -> dict:
        """evo-engine interface."""
        action = input_data.get("action", "urlencode")
        text = input_data.get("text", input_data.get("data", ""))
        
        if action == "urlencode":
            return self.urlencode(text, input_data.get("safe", ''))
        elif action == "urldecode":
            return self.urldecode(text)
        elif action == "base64encode":
            return self.base64encode(text, input_data.get("url_safe", False))
        elif action == "base64decode":
            return self.base64decode(text, input_data.get("url_safe", False), input_data.get("as_text", True))
        elif action == "htmlencode":
            return self.htmlencode(text)
        elif action == "htmldecode":
            return self.htmldecode(text)
        else:
            return {"success": False, "error": f"Unknown action: {action}"}


def execute(input_data: dict) -> dict:
    return URLCodecSkill().execute(input_data)


if __name__ == "__main__":
    skill = URLCodecSkill()
    print(f"Info: {json.dumps(get_info(), indent=2)}")
    print(f"Health: {health_check()}")
    
    # Test examples
    tests = [
        {"action": "urlencode", "text": "hello world!"},
        {"action": "urldecode", "text": "hello%20world%21"},
        {"action": "base64encode", "text": "hello world"},
        {"action": "htmlencode", "text": "<script>alert('xss')</script>"},
    ]
    
    for test in tests:
        print(f"\n{test}:")
        print(json.dumps(skill.execute(test), indent=2, ensure_ascii=False))
