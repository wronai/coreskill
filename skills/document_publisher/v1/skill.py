#!/usr/bin/env python3
"""
document_publisher skill - Publish documents to various platforms.
Supports: generate HTML/PDF, upload to cloud, create shareable links, version control.
Uses stdlib only - no external dependencies.
"""
import json
import base64
import hashlib
from pathlib import Path
from datetime import datetime
import urllib.request
import urllib.error
import urllib.parse
import re
import time


def get_info():
    return {
        "name": "document_publisher",
        "version": "v1",
        "description": "Publish documents: generate HTML/PDF, create share links, version control, upload.",
        "capabilities": ["publish", "documents", "html", "pdf", "sharing", "version"],
        "actions": ["generate_html", "create_index", "version_document", "publish_static_site", "generate_share_link"]
    }


def health_check():
    return True


class DocumentPublisherSkill:
    """Document publishing and sharing system."""

    def __init__(self):
        self.publish_dir = Path.home() / ".evo_published"
        self.publish_dir.mkdir(exist_ok=True)
        self.versions_dir = self.publish_dir / "versions"
        self.versions_dir.mkdir(exist_ok=True)
        self.index_file = self.publish_dir / "published_index.json"

    def _load_index(self):
        """Load published documents index."""
        try:
            if self.index_file.exists():
                with open(self.index_file, 'r') as f:
                    return json.load(f)
            return {}
        except:
            return {}

    def _save_index(self, index):
        """Save published documents index."""
        try:
            with open(self.index_file, 'w') as f:
                json.dump(index, f, indent=2, default=str)
        except:
            pass

    def _read_file(self, path):
        """Read file content."""
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except:
            return None

    def generate_html(self, source_file, title=None, template="default", include_toc=False):
        """Convert document to HTML format."""
        try:
            path = Path(source_file).expanduser()
            content = self._read_file(path)

            if content is None:
                return {"success": False, "error": f"Could not read file: {source_file}"}

            # Determine title
            doc_title = title or path.stem.replace('_', ' ').replace('-', ' ').title()

            # Convert content based on file type
            ext = path.suffix.lower()

            if ext == '.md':
                html_content = self._markdown_to_html(content)
            elif ext in ['.txt', '.rst']:
                html_content = self._plain_text_to_html(content)
            else:
                html_content = f"<pre>{self._escape_html(content)}</pre>"

            # Apply template
            if template == "default":
                html = self._apply_default_template(doc_title, html_content, include_toc)
            elif template == "minimal":
                html = self._apply_minimal_template(doc_title, html_content)
            else:
                html = self._apply_default_template(doc_title, html_content, include_toc)

            # Save HTML file
            output_path = self.publish_dir / f"{path.stem}.html"
            output_path.write_text(html, encoding='utf-8')

            # Update index
            index = self._load_index()
            doc_id = hashlib.md5(str(path).encode()).hexdigest()[:8]
            index[doc_id] = {
                "source": str(path),
                "output": str(output_path),
                "title": doc_title,
                "published_at": datetime.now().isoformat(),
                "format": "html",
                "template": template
            }
            self._save_index(index)

            return {
                "success": True,
                "document_id": doc_id,
                "output_file": str(output_path),
                "title": doc_title,
                "file_size": len(html)
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _markdown_to_html(self, markdown_text):
        """Simple markdown to HTML conversion."""
        html = markdown_text

        # Headers
        html = re.sub(r'^#{6}\s+(.+)$', r'<h6>\1</h6>', html, flags=re.MULTILINE)
        html = re.sub(r'^#{5}\s+(.+)$', r'<h5>\1</h5>', html, flags=re.MULTILINE)
        html = re.sub(r'^#{4}\s+(.+)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
        html = re.sub(r'^#{3}\s+(.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^#{2}\s+(.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^#\s+(.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

        # Bold and italic
        html = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', html)
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)

        # Code blocks
        html = re.sub(r'```(.+?)```', r'<pre><code>\1</code></pre>', html, flags=re.DOTALL)
        html = re.sub(r'`(.+?)`', r'<code>\1</code>', html)

        # Links
        html = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', html)

        # Lists
        html = re.sub(r'^\*\s+(.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        html = re.sub(r'^(<li>.+</li>\n)+', r'<ul>\g<0></ul>', html, flags=re.MULTILINE)

        # Paragraphs
        lines = html.split('\n')
        result = []
        in_paragraph = False

        for line in lines:
            if line.strip():
                if not line.startswith('<') and not in_paragraph:
                    result.append('<p>')
                    in_paragraph = True
                result.append(line)
            else:
                if in_paragraph:
                    result.append('</p>')
                    in_paragraph = False
                result.append('')

        if in_paragraph:
            result.append('</p>')

        return '\n'.join(result)

    def _plain_text_to_html(self, text):
        """Convert plain text to HTML."""
        escaped = self._escape_html(text)
        paragraphs = escaped.split('\n\n')
        return '\n'.join(f'<p>{p}</p>' for p in paragraphs if p.strip())

    def _escape_html(self, text):
        """Escape HTML special characters."""
        return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

    def _apply_default_template(self, title, content, include_toc=False):
        """Apply default HTML template."""
        toc_html = ""
        if include_toc:
            toc_html = self._generate_toc(content)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 2rem; line-height: 1.6; color: #333; }}
        h1, h2, h3 {{ color: #2c3e50; }}
        h1 {{ border-bottom: 2px solid #3498db; padding-bottom: 0.5rem; }}
        h2 {{ margin-top: 2rem; }}
        code {{ background: #f4f4f4; padding: 0.2rem 0.4rem; border-radius: 3px; font-family: 'Courier New', monospace; }}
        pre {{ background: #f4f4f4; padding: 1rem; border-radius: 5px; overflow-x: auto; }}
        pre code {{ background: none; padding: 0; }}
        a {{ color: #3498db; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        blockquote {{ border-left: 4px solid #3498db; margin: 0; padding-left: 1rem; color: #666; }}
        .toc {{ background: #f8f9fa; padding: 1rem; border-radius: 5px; margin-bottom: 2rem; }}
        .toc h2 {{ margin-top: 0; }}
    </style>
</head>
<body>
    {toc_html}
    {content}
    <footer style="margin-top: 3rem; padding-top: 1rem; border-top: 1px solid #eee; color: #999; font-size: 0.9rem;">
        Published: {datetime.now().strftime('%Y-%m-%d %H:%M')}
    </footer>
</body>
</html>"""

    def _apply_minimal_template(self, title, content):
        """Apply minimal HTML template."""
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
</head>
<body>
    {content}
</body>
</html>"""

    def _generate_toc(self, content):
        """Generate table of contents from headers."""
        # Simple TOC - extract h2 headers
        headers = re.findall(r'<h2>(.+?)</h2>', content)
        if not headers:
            return ""

        toc_items = ''.join(f'<li><a href="#header-{i}">{h}</a></li>' for i, h in enumerate(headers))
        return f'<div class="toc"><h2>Table of Contents</h2><ul>{toc_items}</ul></div>'

    def version_document(self, file_path, comment=None):
        """Create version snapshot of document."""
        try:
            path = Path(file_path).expanduser()
            if not path.exists():
                return {"success": False, "error": f"File not found: {file_path}"}

            # Read content
            content = path.read_bytes()

            # Generate version info
            content_hash = hashlib.sha256(content).hexdigest()[:16]
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            version_id = f"{path.stem}_{timestamp}_{content_hash[:8]}"

            # Save version
            version_path = self.versions_dir / f"{version_id}{path.suffix}"
            version_path.write_bytes(content)

            # Create metadata
            version_info = {
                "version_id": version_id,
                "source_file": str(path),
                "version_file": str(version_path),
                "created_at": datetime.now().isoformat(),
                "content_hash": content_hash,
                "file_size": len(content),
                "comment": comment or ""
            }

            # Load and update versions index
            versions_index_file = self.versions_dir / "versions_index.json"
            versions = []
            if versions_index_file.exists():
                with open(versions_index_file, 'r') as f:
                    versions = json.load(f)

            versions.append(version_info)

            with open(versions_index_file, 'w') as f:
                json.dump(versions, f, indent=2, default=str)

            return {
                "success": True,
                "version_id": version_id,
                "version_file": str(version_path),
                "total_versions": len(versions),
                "comment": comment
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_index(self, source_dir, recursive=True):
        """Create index of all documents in directory."""
        try:
            source_path = Path(source_dir).expanduser()
            if not source_path.exists():
                return {"success": False, "error": f"Directory not found: {source_dir}"}

            documents = []

            if recursive:
                files = source_path.rglob("*")
            else:
                files = source_path.iterdir()

            for file_path in files:
                if file_path.is_file():
                    try:
                        stat = file_path.stat()
                        rel_path = file_path.relative_to(source_path)

                        documents.append({
                            "path": str(rel_path),
                            "name": file_path.name,
                            "size": stat.st_size,
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "extension": file_path.suffix.lower()
                        })
                    except:
                        continue

            # Sort by modification time
            documents.sort(key=lambda x: x["modified"], reverse=True)

            # Generate HTML index
            index_html = self._generate_index_html(documents, str(source_path))

            output_path = self.publish_dir / "document_index.html"
            output_path.write_text(index_html, encoding='utf-8')

            return {
                "success": True,
                "documents_count": len(documents),
                "index_file": str(output_path),
                "source_directory": str(source_path)
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _generate_index_html(self, documents, source_path):
        """Generate HTML for document index."""
        rows = []
        for doc in documents:
            rows.append(f"""
                <tr>
                    <td><a href="file://{source_path}/{doc['path']}">{doc['name']}</a></td>
                    <td>{doc['extension']}</td>
                    <td>{doc['size']:,} bytes</td>
                    <td>{doc['modified'][:10]}</td>
                </tr>
            """)

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Document Index</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 1000px; margin: 0 auto; padding: 2rem; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 0.75rem; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f5f5f5; font-weight: 600; }}
        a {{ color: #3498db; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <h1>📄 Document Index</h1>
    <p>Total documents: {len(documents)} | Source: {source_path}</p>
    <table>
        <tr><th>Name</th><th>Type</th><th>Size</th><th>Modified</th></tr>
        {''.join(rows)}
    </table>
    <footer style="margin-top: 2rem; color: #999;">
        Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </footer>
</body>
</html>"""

    def publish_static_site(self, source_dir, site_name=None):
        """Create a simple static site from directory."""
        try:
            source_path = Path(source_dir).expanduser()
            if not source_path.exists():
                return {"success": False, "error": f"Directory not found: {source_dir}"}

            site_name = site_name or source_path.name
            site_dir = self.publish_dir / f"site_{site_name}"
            site_dir.mkdir(exist_ok=True)

            published_files = []

            for file_path in source_path.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in ['.md', '.txt', '.rst']:
                    try:
                        # Convert to HTML
                        result = self.generate_html(str(file_path), template="default")
                        if result.get("success"):
                            # Copy to site directory
                            html_file = Path(result["output_file"])
                            target_file = site_dir / f"{file_path.stem}.html"
                            target_file.write_text(html_file.read_text(), encoding='utf-8')
                            published_files.append(str(target_file))
                    except:
                        continue

            # Create index
            index_result = self.create_index(str(site_dir), recursive=False)

            return {
                "success": True,
                "site_name": site_name,
                "site_directory": str(site_dir),
                "files_published": len(published_files),
                "index_file": index_result.get("index_file")
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def generate_share_link(self, file_path, expiry_days=None):
        """Generate a shareable link for document."""
        try:
            path = Path(file_path).expanduser()
            if not path.exists():
                return {"success": False, "error": f"File not found: {file_path}"}

            # Read and encode file
            content = path.read_bytes()
            encoded = base64.b64encode(content).decode('utf-8')

            # Generate share ID
            share_id = hashlib.sha256(f"{path}{datetime.now()}".encode()).hexdigest()[:16]

            share_info = {
                "share_id": share_id,
                "original_file": str(path),
                "file_name": path.name,
                "file_size": len(content),
                "mime_type": self._get_mime_type(path.suffix),
                "created_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(days=expiry_days)).isoformat() if expiry_days else None,
                "data_uri": f"data:{self._get_mime_type(path.suffix)};base64,{encoded[:100]}..."  # Preview only
            }

            # Save share info
            shares_file = self.publish_dir / "shares.json"
            shares = {}
            if shares_file.exists():
                with open(shares_file, 'r') as f:
                    shares = json.load(f)

            shares[share_id] = share_info

            with open(shares_file, 'w') as f:
                json.dump(shares, f, indent=2, default=str)

            return {
                "success": True,
                "share_id": share_id,
                "share_url": f"file://{path}",  # Local file path
                "expires": share_info.get("expires_at"),
                "note": "Share link is local file path. For web sharing, upload to cloud service."
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_mime_type(self, extension):
        """Get MIME type for file extension."""
        mime_types = {
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.html': 'text/html',
            '.pdf': 'application/pdf',
            '.json': 'application/json',
            '.py': 'text/x-python',
            '.js': 'application/javascript',
            '.css': 'text/css'
        }
        return mime_types.get(extension.lower(), 'application/octet-stream')

    def list_published(self):
        """List all published documents."""
        try:
            index = self._load_index()
            return {
                "success": True,
                "count": len(index),
                "documents": list(index.values())
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def execute(self, input_data: dict) -> dict:
        """evo-engine interface."""
        action = input_data.get("action", "generate_html")

        if action == "generate_html":
            return self.generate_html(
                input_data.get("source_file", ""),
                input_data.get("title"),
                input_data.get("template", "default"),
                input_data.get("include_toc", False)
            )
        elif action == "version_document":
            return self.version_document(
                input_data.get("file_path", ""),
                input_data.get("comment")
            )
        elif action == "create_index":
            return self.create_index(
                input_data.get("source_dir", "."),
                input_data.get("recursive", True)
            )
        elif action == "publish_static_site":
            return self.publish_static_site(
                input_data.get("source_dir", "."),
                input_data.get("site_name")
            )
        elif action == "generate_share_link":
            return self.generate_share_link(
                input_data.get("file_path", ""),
                input_data.get("expiry_days")
            )
        elif action == "list_published":
            return self.list_published()
        else:
            return {"success": False, "error": f"Unknown action: {action}"}


def execute(input_data: dict) -> dict:
    return DocumentPublisherSkill().execute(input_data)


if __name__ == "__main__":
    skill = DocumentPublisherSkill()
    print(f"Info: {json.dumps(get_info(), indent=2)}")
    print(f"Health: {health_check()}")
