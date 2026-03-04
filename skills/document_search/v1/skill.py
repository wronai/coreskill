#!/usr/bin/env python3
"""
document_search skill - Search and find documents across filesystem.
Supports: full-text search, metadata search, filters by type/date/size.
Uses stdlib only - no external dependencies.
"""
import os
import re
import json
from pathlib import Path
from datetime import datetime, timedelta
from fnmatch import fnmatch


def get_info():
    return {
        "name": "document_search",
        "version": "v1",
        "description": "Search documents by content, name, type, date, size. Full-text search with indexing.",
        "capabilities": ["search", "documents", "files", "indexing"],
        "actions": ["search_by_name", "search_by_content", "search_by_metadata", "index_directory", "find_duplicates"]
    }


def health_check():
    return True


class DocumentSearchSkill:
    """Document search and indexing system."""

    # Common document extensions
    DOC_EXTENSIONS = {
        'text': ['.txt', '.md', '.rst', '.log'],
        'code': ['.py', '.js', '.html', '.css', '.java', '.cpp', '.c', '.h', '.go', '.rs'],
        'data': ['.json', '.xml', '.csv', '.yaml', '.yml', '.sql'],
        'office': ['.doc', '.docx', '.odt', '.rtf'],
        'pdf': ['.pdf'],
        'archive': ['.zip', '.tar', '.gz', '.bz2', '.7z'],
        'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp'],
        'all_docs': ['.txt', '.md', '.doc', '.docx', '.odt', '.pdf', '.rtf']
    }

    def __init__(self):
        self.index_cache = {}
        self.cache_dir = Path.home() / ".evo_document_search"
        self.cache_dir.mkdir(exist_ok=True)

    def search_by_name(self, pattern, path=".", recursive=True, case_sensitive=False):
        """Search documents by filename pattern."""
        try:
            search_path = Path(path).expanduser().resolve()
            if not search_path.exists():
                return {"success": False, "error": f"Path not found: {path}"}

            results = []
            pattern_lower = pattern.lower() if not case_sensitive else pattern

            if recursive:
                files = search_path.rglob("*")
            else:
                files = search_path.iterdir()

            for file_path in files:
                if file_path.is_file():
                    name = file_path.name
                    compare_name = name if case_sensitive else name.lower()

                    if fnmatch(compare_name, pattern_lower) or pattern_lower in compare_name:
                        stat = file_path.stat()
                        results.append({
                            "path": str(file_path),
                            "name": name,
                            "size": stat.st_size,
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "extension": file_path.suffix.lower()
                        })

            # Sort by modification time (newest first)
            results.sort(key=lambda x: x["modified"], reverse=True)

            return {
                "success": True,
                "query": pattern,
                "path": str(search_path),
                "count": len(results),
                "results": results[:100]  # Limit results
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def search_by_content(self, query, path=".", extensions=None, recursive=True, case_sensitive=False):
        """Full-text search within documents."""
        try:
            search_path = Path(path).expanduser().resolve()
            if not search_path.exists():
                return {"success": False, "error": f"Path not found: {path}"}

            # Default to text files if no extensions specified
            if extensions is None:
                extensions = self.DOC_EXTENSIONS['text'] + self.DOC_EXTENSIONS['code'] + self.DOC_EXTENSIONS['data']

            # Normalize extensions
            ext_set = set(ext.lower() if ext.startswith('.') else f'.{ext.lower()}' for ext in extensions)

            results = []
            query_lower = query.lower() if not case_sensitive else query

            if recursive:
                files = search_path.rglob("*")
            else:
                files = search_path.iterdir()

            for file_path in files:
                if not file_path.is_file():
                    continue

                if file_path.suffix.lower() not in ext_set:
                    continue

                try:
                    # Try to read as text
                    content = self._read_file_content(file_path)
                    if content is None:
                        continue

                    compare_content = content if case_sensitive else content.lower()

                    if query_lower in compare_content:
                        # Find context around match
                        matches = self._find_matches(content, query, case_sensitive)

                        stat = file_path.stat()
                        results.append({
                            "path": str(file_path),
                            "name": file_path.name,
                            "size": stat.st_size,
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "match_count": len(matches),
                            "contexts": matches[:3]  # Show first 3 matches
                        })

                except Exception as e:
                    continue  # Skip files that can't be read

            # Sort by match count
            results.sort(key=lambda x: x["match_count"], reverse=True)

            return {
                "success": True,
                "query": query,
                "path": str(search_path),
                "extensions": list(ext_set),
                "count": len(results),
                "results": results[:50]
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _read_file_content(self, file_path, max_size=10*1024*1024):
        """Read file content as text."""
        try:
            # Check file size
            size = file_path.stat().st_size
            if size > max_size:
                return None

            # Try different encodings
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']

            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                        return f.read()
                except (UnicodeDecodeError, UnicodeError):
                    continue

            return None

        except Exception:
            return None

    def _find_matches(self, content, query, case_sensitive=False, context_chars=50):
        """Find all matches with surrounding context."""
        matches = []
        flags = 0 if case_sensitive else re.IGNORECASE

        for match in re.finditer(re.escape(query), content, flags):
            start = max(0, match.start() - context_chars)
            end = min(len(content), match.end() + context_chars)
            context = content[start:end].replace('\n', ' ')
            matches.append(context.strip())

        return matches

    def search_by_metadata(self, path=".", min_size=None, max_size=None, modified_after=None, modified_before=None, extensions=None):
        """Search by file metadata (size, date, type)."""
        try:
            search_path = Path(path).expanduser().resolve()
            if not search_path.exists():
                return {"success": False, "error": f"Path not found: {path}"}

            results = []

            # Parse date filters
            after_dt = self._parse_date(modified_after) if modified_after else None
            before_dt = self._parse_date(modified_before) if modified_before else None

            # Parse size filters
            min_bytes = self._parse_size(min_size) if min_size else None
            max_bytes = self._parse_size(max_size) if max_size else None

            # Extension filter
            ext_set = None
            if extensions:
                ext_set = set(ext.lower() if ext.startswith('.') else f'.{ext.lower()}' for ext in extensions)

            for file_path in search_path.rglob("*"):
                if not file_path.is_file():
                    continue

                # Check extension
                if ext_set and file_path.suffix.lower() not in ext_set:
                    continue

                stat = file_path.stat()
                size = stat.st_size
                mtime = datetime.fromtimestamp(stat.st_mtime)

                # Check size filters
                if min_bytes is not None and size < min_bytes:
                    continue
                if max_bytes is not None and size > max_bytes:
                    continue

                # Check date filters
                if after_dt and mtime < after_dt:
                    continue
                if before_dt and mtime > before_dt:
                    continue

                results.append({
                    "path": str(file_path),
                    "name": file_path.name,
                    "size": size,
                    "size_human": self._human_readable_size(size),
                    "modified": mtime.isoformat(),
                    "extension": file_path.suffix.lower()
                })

            # Sort by size (largest first)
            results.sort(key=lambda x: x["size"], reverse=True)

            return {
                "success": True,
                "path": str(search_path),
                "filters": {
                    "min_size": min_size,
                    "max_size": max_size,
                    "modified_after": modified_after,
                    "modified_before": modified_before,
                    "extensions": extensions
                },
                "count": len(results),
                "results": results[:100]
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def find_duplicates(self, path=".", hash_method="size"):
        """Find duplicate files."""
        try:
            search_path = Path(path).expanduser().resolve()
            if not search_path.exists():
                return {"success": False, "error": f"Path not found: {path}"}

            # Group by size first (fast)
            size_groups = {}

            for file_path in search_path.rglob("*"):
                if not file_path.is_file():
                    continue

                try:
                    size = file_path.stat().st_size
                    if size not in size_groups:
                        size_groups[size] = []
                    size_groups[size].append(str(file_path))
                except:
                    continue

            # Find groups with more than one file
            duplicates = []
            for size, files in size_groups.items():
                if len(files) > 1 and size > 0:
                    duplicates.append({
                        "size": size,
                        "size_human": self._human_readable_size(size),
                        "count": len(files),
                        "files": files
                    })

            # Sort by total wasted space
            duplicates.sort(key=lambda x: x["size"] * (x["count"] - 1), reverse=True)

            return {
                "success": True,
                "path": str(search_path),
                "duplicate_groups": len(duplicates),
                "total_duplicates": sum(d["count"] for d in duplicates),
                "potential_savings": sum(d["size"] * (d["count"] - 1) for d in duplicates),
                "duplicates": duplicates[:20]
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def index_directory(self, path=".", rebuild=False):
        """Create search index for directory (simplified)."""
        try:
            search_path = Path(path).expanduser().resolve()
            if not search_path.exists():
                return {"success": False, "error": f"Path not found: {path}"}

            # Count files by type
            stats = {
                "total_files": 0,
                "total_size": 0,
                "by_extension": {}
            }

            for file_path in search_path.rglob("*"):
                if not file_path.is_file():
                    continue

                try:
                    stat = file_path.stat()
                    stats["total_files"] += 1
                    stats["total_size"] += stat.st_size

                    ext = file_path.suffix.lower() or "(no extension)"
                    if ext not in stats["by_extension"]:
                        stats["by_extension"][ext] = {"count": 0, "size": 0}
                    stats["by_extension"][ext]["count"] += 1
                    stats["by_extension"][ext]["size"] += stat.st_size

                except:
                    continue

            # Sort extensions by count
            stats["by_extension"] = dict(sorted(
                stats["by_extension"].items(),
                key=lambda x: x[1]["count"],
                reverse=True
            )[:20])

            return {
                "success": True,
                "path": str(search_path),
                "indexed": stats["total_files"],
                "total_size_human": self._human_readable_size(stats["total_size"]),
                "statistics": stats
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _parse_date(self, date_str):
        """Parse date string to datetime."""
        formats = [
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M",
            "%d/%m/%Y",
            "%d.%m.%Y"
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except:
                continue
        return None

    def _parse_size(self, size_str):
        """Parse size string to bytes."""
        size_str = size_str.upper().strip()
        multipliers = {
            'B': 1,
            'KB': 1024,
            'MB': 1024**2,
            'GB': 1024**3,
            'K': 1024,
            'M': 1024**2,
            'G': 1024**3
        }

        for suffix, mult in multipliers.items():
            if size_str.endswith(suffix):
                num = size_str[:-len(suffix)].strip()
                return int(float(num) * mult)

        return int(size_str)

    def _human_readable_size(self, size_bytes):
        """Convert bytes to human readable."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} PB"

    def execute(self, input_data: dict) -> dict:
        """evo-engine interface."""
        action = input_data.get("action", "search_by_name")

        if action == "search_by_name":
            return self.search_by_name(
                input_data.get("pattern", "*"),
                input_data.get("path", "."),
                input_data.get("recursive", True),
                input_data.get("case_sensitive", False)
            )
        elif action == "search_by_content":
            return self.search_by_content(
                input_data.get("query", ""),
                input_data.get("path", "."),
                input_data.get("extensions"),
                input_data.get("recursive", True),
                input_data.get("case_sensitive", False)
            )
        elif action == "search_by_metadata":
            return self.search_by_metadata(
                input_data.get("path", "."),
                input_data.get("min_size"),
                input_data.get("max_size"),
                input_data.get("modified_after"),
                input_data.get("modified_before"),
                input_data.get("extensions")
            )
        elif action == "find_duplicates":
            return self.find_duplicates(
                input_data.get("path", "."),
                input_data.get("hash_method", "size")
            )
        elif action == "index_directory":
            return self.index_directory(
                input_data.get("path", "."),
                input_data.get("rebuild", False)
            )
        else:
            return {"success": False, "error": f"Unknown action: {action}"}


def execute(input_data: dict) -> dict:
    return DocumentSearchSkill().execute(input_data)


if __name__ == "__main__":
    skill = DocumentSearchSkill()
    print(f"Info: {json.dumps(get_info(), indent=2)}")
    print(f"Health: {health_check()}")

    # Test searches
    print("\nTest search by name:")
    result = skill.search_by_name("*.py", path=".", recursive=False)
    print(f"Found {result.get('count', 0)} Python files")
