#!/usr/bin/env python3
"""
document_reader skill - Read and extract text from PDF, DOCX, TXT, markdown files.
Uses stdlib and subprocess fallbacks (pdftotext, catdoc).
"""
import subprocess
import json
import shutil
from pathlib import Path
import re


def get_info():
    return {
        "name": "document_reader",
        "version": "v1",
        "description": "Extract text from PDF, DOCX, TXT, MD files. Uses pdftotext/catdoc or pure-python fallbacks.",
        "capabilities": ["documents", "pdf", "docx", "text", "extraction"],
        "actions": ["read", "extract", "info", "search"]
    }


def health_check():
    """Check if any document tools are available."""
    tools = ["pdftotext", "catdoc", "pandoc"]
    for tool in tools:
        if shutil.which(tool):
            return True
    # Pure python fallback always works for text files
    return True


class DocumentReaderSkill:
    """Extract text from various document formats."""

    def _detect_file_type(self, filepath):
        """Detect file type from extension and content."""
        path = Path(filepath)
        ext = path.suffix.lower()
        
        type_map = {
            '.pdf': 'pdf',
            '.docx': 'docx',
            '.doc': 'doc',
            '.txt': 'text',
            '.md': 'markdown',
            '.markdown': 'markdown',
            '.rst': 'text',
            '.html': 'html',
            '.htm': 'html',
            '.csv': 'csv',
            '.json': 'json',
            '.xml': 'xml',
        }
        return type_map.get(ext, 'unknown')

    def _read_text_file(self, filepath, encoding=None, max_chars=50000):
        """Read plain text file with encoding detection."""
        try:
            path = Path(filepath)
            if not path.exists():
                return {"success": False, "error": f"File not found: {filepath}"}
            
            # Try common encodings
            encodings = [encoding, 'utf-8', 'latin-1', 'cp1252', 'iso-8859-1'] if encoding else ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            
            for enc in encodings:
                if not enc:
                    continue
                try:
                    with open(path, 'r', encoding=enc, errors='replace') as f:
                        content = f.read(max_chars)
                        return {
                            "success": True,
                            "type": "text",
                            "encoding": enc,
                            "content": content,
                            "length": len(content),
                            "truncated": path.stat().st_size > max_chars
                        }
                except UnicodeDecodeError:
                    continue
            
            # Last resort: read as binary and decode with replace
            with open(path, 'rb') as f:
                content = f.read(max_chars).decode('utf-8', errors='replace')
                return {
                    "success": True,
                    "type": "text",
                    "encoding": "binary-fallback",
                    "content": content,
                    "length": len(content),
                    "truncated": path.stat().st_size > max_chars
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _read_pdf(self, filepath, max_pages=50):
        """Extract text from PDF using pdftotext or pure-python fallback."""
        try:
            path = Path(filepath)
            if not path.exists():
                return {"success": False, "error": f"File not found: {filepath}"}
            
            # Try pdftotext first (fastest)
            if shutil.which("pdftotext"):
                result = subprocess.run(
                    ["pdftotext", "-layout", "-nopgbrk", str(path), "-"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0:
                    content = result.stdout[:50000]
                    return {
                        "success": True,
                        "type": "pdf",
                        "method": "pdftotext",
                        "content": content,
                        "length": len(content),
                        "pages": min(max_pages, len(result.stdout) // 2000)  # Rough estimate
                    }
            
            # Try pdfplumber if available
            try:
                import pdfplumber
                with pdfplumber.open(path) as pdf:
                    text_parts = []
                    for i, page in enumerate(pdf.pages[:max_pages]):
                        text = page.extract_text()
                        if text:
                            text_parts.append(f"--- Page {i+1} ---\n{text}")
                    content = "\n\n".join(text_parts)
                    return {
                        "success": True,
                        "type": "pdf",
                        "method": "pdfplumber",
                        "content": content[:50000],
                        "length": len(content),
                        "pages": len(pdf.pages[:max_pages])
                    }
            except ImportError:
                pass
            
            # Fallback: pure python PDF text extraction (very basic)
            return self._read_pdf_basic(path, max_pages)
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _read_pdf_basic(self, path, max_pages=50):
        """Basic PDF text extraction using string matching."""
        try:
            # Read PDF as binary and look for text streams
            content = path.read_bytes()
            
            # Find text between BT (Begin Text) and ET (End Text) markers
            text_parts = []
            i = 0
            pages_found = 0
            
            while i < len(content) - 2 and pages_found < max_pages:
                # Look for BT marker
                bt_idx = content.find(b'BT', i)
                if bt_idx == -1:
                    break
                
                # Look for ET marker
                et_idx = content.find(b'ET', bt_idx)
                if et_idx == -1:
                    break
                
                # Extract text between
                text_section = content[bt_idx:et_idx]
                
                # Look for text strings (Tj or TJ operators)
                text_matches = re.findall(rb'\(([^)]+)\)', text_section)
                if text_matches:
                    decoded = []
                    for match in text_matches:
                        try:
                            decoded.append(match.decode('latin-1'))
                        except:
                            pass
                    if decoded:
                        text_parts.append("".join(decoded))
                
                i = et_idx + 2
                pages_found += 1
            
            extracted = " ".join(text_parts)[:50000]
            return {
                "success": True,
                "type": "pdf",
                "method": "basic-extraction",
                "content": extracted,
                "length": len(extracted),
                "note": "Basic extraction - install pdftotext or pdfplumber for better results"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _read_docx(self, filepath):
        """Extract text from DOCX using unzip/pandoc or python-docx fallback."""
        try:
            path = Path(filepath)
            if not path.exists():
                return {"success": False, "error": f"File not found: {filepath}"}
            
            # Try pandoc first
            if shutil.which("pandoc"):
                result = subprocess.run(
                    ["pandoc", str(path), "-t", "plain"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0:
                    return {
                        "success": True,
                        "type": "docx",
                        "method": "pandoc",
                        "content": result.stdout[:50000],
                        "length": len(result.stdout)
                    }
            
            # Try python-docx
            try:
                import docx
                doc = docx.Document(path)
                paragraphs = []
                for para in doc.paragraphs:
                    if para.text.strip():
                        paragraphs.append(para.text)
                content = "\n\n".join(paragraphs)
                return {
                    "success": True,
                    "type": "docx",
                    "method": "python-docx",
                    "content": content[:50000],
                    "length": len(content)
                }
            except ImportError:
                pass
            
            # Fallback: unzip and parse word/document.xml
            return self._read_docx_basic(path)
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _read_docx_basic(self, path):
        """Basic DOCX extraction using unzip and XML parsing."""
        try:
            import zipfile
            import xml.etree.ElementTree as ET
            
            with zipfile.ZipFile(path, 'r') as zf:
                # Read word/document.xml
                xml_content = zf.read('word/document.xml')
            
            # Parse XML and extract text
            root = ET.fromstring(xml_content)
            
            # DOCX namespace
            ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            
            text_parts = []
            for elem in root.iter():
                if elem.tag.endswith('}t'):  # w:t elements contain text
                    if elem.text:
                        text_parts.append(elem.text)
            
            content = "".join(text_parts)[:50000]
            return {
                "success": True,
                "type": "docx",
                "method": "xml-extraction",
                "content": content,
                "length": len(content),
                "note": "Basic extraction - install pandoc or python-docx for better results"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _read_html(self, filepath):
        """Extract text from HTML."""
        try:
            from html.parser import HTMLParser
            
            class TextExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.text = []
                    self.skip_tags = {'script', 'style', 'noscript', 'head'}
                    self._skip = False
                
                def handle_starttag(self, tag, attrs):
                    if tag in self.skip_tags:
                        self._skip = True
                
                def handle_endtag(self, tag):
                    if tag in self.skip_tags:
                        self._skip = False
                    if tag in ['p', 'div', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li']:
                        self.text.append('\n')
                
                def handle_data(self, data):
                    if not self._skip:
                        self.text.append(data)
            
            parser = TextExtractor()
            content = Path(filepath).read_text(encoding='utf-8', errors='replace')
            parser.feed(content)
            
            text = "".join(parser.text)[:50000]
            # Clean up multiple newlines
            text = re.sub(r'\n{3,}', '\n\n', text)
            
            return {
                "success": True,
                "type": "html",
                "content": text.strip(),
                "length": len(text)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def read(self, filepath, max_chars=50000):
        """Read any supported document type."""
        try:
            path = Path(filepath)
            if not path.exists():
                return {"success": False, "error": f"File not found: {filepath}"}
            
            file_type = self._detect_file_type(filepath)
            
            if file_type == 'pdf':
                return self._read_pdf(filepath)
            elif file_type in ['docx', 'doc']:
                return self._read_docx(filepath)
            elif file_type == 'html':
                return self._read_html(filepath)
            elif file_type in ['text', 'markdown', 'csv', 'json', 'xml']:
                return self._read_text_file(filepath, max_chars=max_chars)
            else:
                # Try as text file
                return self._read_text_file(filepath, max_chars=max_chars)
                
        except Exception as e:
            return {"success": False, "error": str(e)}

    def extract(self, filepath, pages=None):
        """Extract text with optional page range (for PDFs)."""
        return self.read(filepath)

    def info(self, filepath):
        """Get document metadata."""
        try:
            path = Path(filepath)
            if not path.exists():
                return {"success": False, "error": f"File not found: {filepath}"}
            
            stat = path.stat()
            file_type = self._detect_file_type(filepath)
            
            info = {
                "success": True,
                "name": path.name,
                "type": file_type,
                "size": stat.st_size,
                "size_human": self._format_size(stat.st_size),
                "modified": stat.st_mtime,
            }
            
            # Try to get page/word count for supported formats
            if file_type == 'pdf':
                result = self._read_pdf(filepath, max_pages=1)
                if result.get("success"):
                    info["pages_estimate"] = result.get("pages", "unknown")
            
            return info
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _format_size(self, size_bytes):
        """Format bytes to human readable."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

    def search(self, filepath, query, case_sensitive=False):
        """Search for text in document."""
        try:
            result = self.read(filepath)
            if not result.get("success"):
                return result
            
            content = result.get("content", "")
            
            if not case_sensitive:
                content_search = content.lower()
                query_search = query.lower()
            else:
                content_search = content
                query_search = query
            
            matches = []
            start = 0
            while True:
                idx = content_search.find(query_search, start)
                if idx == -1:
                    break
                # Get context around match
                context_start = max(0, idx - 50)
                context_end = min(len(content), idx + len(query) + 50)
                context = content[context_start:context_end]
                matches.append({
                    "position": idx,
                    "context": context.replace('\n', ' ')
                })
                start = idx + len(query)
            
            return {
                "success": True,
                "query": query,
                "matches_count": len(matches),
                "matches": matches[:20]  # Limit matches
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def execute(self, input_data: dict) -> dict:
        """evo-engine interface."""
        action = input_data.get("action", "read")
        filepath = input_data.get("file", input_data.get("path", ""))
        
        if action == "read":
            return self.read(filepath, input_data.get("max_chars", 50000))
        elif action == "extract":
            return self.extract(filepath, input_data.get("pages"))
        elif action == "info":
            return self.info(filepath)
        elif action == "search":
            return self.search(filepath, input_data.get("query", ""), input_data.get("case_sensitive", False))
        else:
            return {"success": False, "error": f"Unknown action: {action}"}


def execute(input_data: dict) -> dict:
    return DocumentReaderSkill().execute(input_data)


if __name__ == "__main__":
    skill = DocumentReaderSkill()
    print(f"Info: {json.dumps(get_info(), indent=2)}")
    print(f"Health: {health_check()}")
    
    # Test on README if available
    test_file = "/home/tom/github/wronai/coreskill/README.md"
    if Path(test_file).exists():
        print(f"\nRead {test_file}:")
        result = skill.read(test_file, max_chars=1000)
        print(json.dumps(result, indent=2, ensure_ascii=False)[:500] + "...")
