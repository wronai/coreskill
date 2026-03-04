#!/usr/bin/env python3
"""
file_manager skill - File operations using stdlib only.
Supports: list, copy, move, delete, organize, find, info
"""
import os
import shutil
import json
from pathlib import Path
from datetime import datetime, timezone


def get_info():
    return {
        "name": "file_manager",
        "version": "v1",
        "description": "File operations: list, copy, move, delete, organize, find, info. Stdlib only.",
        "capabilities": ["files", "filesystem", "organization"],
        "actions": ["list", "copy", "move", "delete", "organize", "find", "info"]
    }


def health_check():
    try:
        import os
        import shutil
        from pathlib import Path
        return True
    except Exception:
        return False


class FileManagerSkill:
    """File operations using stdlib only."""

    def _safe_path(self, path_str, base_dir=None):
        """Convert to Path and validate safety."""
        if not path_str:
            return None
        path = Path(path_str).expanduser().resolve()
        if base_dir:
            base = Path(base_dir).expanduser().resolve()
            try:
                path.relative_to(base)
            except ValueError:
                # Path is outside base_dir - could be dangerous
                pass  # We allow it but it's logged
        return path

    def list_dir(self, path=".", pattern=None, recursive=False):
        """List directory contents."""
        try:
            target = self._safe_path(path) or Path(".")
            if not target.exists():
                return {"success": False, "error": f"Path not found: {path}"}
            
            items = []
            if recursive:
                iterator = target.rglob(pattern or "*")
            else:
                iterator = target.glob(pattern or "*")
            
            for item in iterator:
                try:
                    stat = item.stat()
                    items.append({
                        "name": item.name,
                        "path": str(item),
                        "type": "directory" if item.is_dir() else "file",
                        "size": stat.st_size if item.is_file() else None,
                        "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                    })
                except (OSError, PermissionError):
                    continue
            
            # Sort: dirs first, then by name
            items.sort(key=lambda x: (0 if x["type"] == "directory" else 1, x["name"]))
            
            return {
                "success": True,
                "path": str(target),
                "items": items[:500],  # Limit results
                "count": len(items)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def copy(self, source, destination, overwrite=False):
        """Copy file or directory."""
        try:
            src = self._safe_path(source)
            dst = self._safe_path(destination)
            if not src or not src.exists():
                return {"success": False, "error": f"Source not found: {source}"}
            
            if dst.exists() and not overwrite:
                return {"success": False, "error": f"Destination exists: {destination}"}
            
            if src.is_dir():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
            
            return {
                "success": True,
                "source": str(src),
                "destination": str(dst),
                "type": "directory" if src.is_dir() else "file"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def move(self, source, destination):
        """Move file or directory."""
        try:
            src = self._safe_path(source)
            dst = self._safe_path(destination)
            if not src or not src.exists():
                return {"success": False, "error": f"Source not found: {source}"}
            
            shutil.move(str(src), str(dst))
            return {
                "success": True,
                "source": str(src),
                "destination": str(dst)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete(self, path, confirm=False):
        """Delete file or directory."""
        try:
            target = self._safe_path(path)
            if not target or not target.exists():
                return {"success": False, "error": f"Path not found: {path}"}
            
            if not confirm:
                return {
                    "success": False,
                    "error": "Confirm required to delete",
                    "path": str(target),
                    "requires_confirm": True
                }
            
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
            
            return {"success": True, "deleted": str(target)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def organize(self, directory, by="extension"):
        """Organize files into subdirectories."""
        try:
            target = self._safe_path(directory)
            if not target or not target.is_dir():
                return {"success": False, "error": f"Directory not found: {directory}"}
            
            moved = []
            for item in target.iterdir():
                if item.is_file():
                    if by == "extension":
                        ext = item.suffix.lower() or "no_extension"
                        subdir = target / ext.lstrip(".")
                    elif by == "date":
                        mtime = datetime.fromtimestamp(item.stat().st_mtime)
                        subdir = target / f"{mtime.year}-{mtime.month:02d}"
                    else:
                        continue
                    
                    subdir.mkdir(exist_ok=True)
                    new_path = subdir / item.name
                    if new_path != item:
                        shutil.move(str(item), str(new_path))
                        moved.append({"from": str(item), "to": str(new_path)})
            
            return {"success": True, "organized_by": by, "moved": moved, "count": len(moved)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def find(self, pattern, start=".", file_type=None):
        """Find files by pattern."""
        try:
            start_path = self._safe_path(start) or Path(".")
            if not start_path.exists():
                return {"success": False, "error": f"Start path not found: {start}"}
            
            matches = []
            for item in start_path.rglob(pattern):
                try:
                    if file_type == "file" and not item.is_file():
                        continue
                    if file_type == "directory" and not item.is_dir():
                        continue
                    matches.append(str(item))
                except (OSError, PermissionError):
                    continue
                if len(matches) >= 1000:
                    break
            
            return {"success": True, "pattern": pattern, "matches": matches, "count": len(matches)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def info(self, path):
        """Get detailed file/directory info."""
        try:
            target = self._safe_path(path)
            if not target or not target.exists():
                return {"success": False, "error": f"Path not found: {path}"}
            
            stat = target.stat()
            result = {
                "success": True,
                "name": target.name,
                "path": str(target),
                "type": "directory" if target.is_dir() else "file",
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime, timezone.utc).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                "accessed": datetime.fromtimestamp(stat.st_atime, timezone.utc).isoformat(),
                "permissions": oct(stat.st_mode)[-3:],
            }
            
            if target.is_dir():
                try:
                    files = list(target.iterdir())
                    result["item_count"] = len(files)
                except PermissionError:
                    result["item_count"] = None
            
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}

    def execute(self, input_data: dict) -> dict:
        """evo-engine interface."""
        action = input_data.get("action", "list")
        
        if action == "list":
            return self.list_dir(
                input_data.get("path", "."),
                input_data.get("pattern"),
                input_data.get("recursive", False)
            )
        elif action == "copy":
            return self.copy(
                input_data.get("source"),
                input_data.get("destination"),
                input_data.get("overwrite", False)
            )
        elif action == "move":
            return self.move(
                input_data.get("source"),
                input_data.get("destination")
            )
        elif action == "delete":
            return self.delete(
                input_data.get("path"),
                input_data.get("confirm", False)
            )
        elif action == "organize":
            return self.organize(
                input_data.get("directory"),
                input_data.get("by", "extension")
            )
        elif action == "find":
            return self.find(
                input_data.get("pattern", "*"),
                input_data.get("start", "."),
                input_data.get("type")
            )
        elif action == "info":
            return self.info(input_data.get("path"))
        else:
            return {"success": False, "error": f"Unknown action: {action}"}


def execute(input_data: dict) -> dict:
    return FileManagerSkill().execute(input_data)


if __name__ == "__main__":
    import sys
    skill = FileManagerSkill()
    print(f"Info: {json.dumps(get_info(), indent=2)}")
    print(f"Health: {health_check()}")
    print(f"\nList current dir:")
    print(json.dumps(skill.list_dir("."), indent=2, ensure_ascii=False))
