#!/usr/bin/env python3
"""
document_editor skill - Edit and manipulate documents.
Supports: text replacement, formatting, merge, split, templates.
Uses stdlib only - no external dependencies.
"""
import json
import re
from pathlib import Path
from datetime import datetime
from difflib import unified_diff


def get_info():
    return {
        "name": "document_editor",
        "version": "v1",
        "description": "Edit documents: replace text, format, merge, split, templates, find/replace.",
        "capabilities": ["edit", "documents", "format", "merge", "templates"],
        "actions": ["find_replace", "insert_text", "delete_lines", "format_text", "merge_files", "split_file", "apply_template"]
    }


def health_check():
    return True


class DocumentEditorSkill:
    """Document editing and manipulation."""

    def __init__(self):
        self.backup_dir = Path.home() / ".evo_document_backups"
        self.backup_dir.mkdir(exist_ok=True)

    def _read_file(self, path):
        """Read file with fallback encodings."""
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        for encoding in encodings:
            try:
                with open(path, 'r', encoding=encoding) as f:
                    return f.read(), encoding
            except (UnicodeDecodeError, UnicodeError):
                continue
        return None, None

    def _write_file(self, path, content, encoding='utf-8'):
        """Write file with backup."""
        path = Path(path)

        # Create backup if file exists
        if path.exists():
            backup_name = f"{path.name}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
            backup_path = self.backup_dir / backup_name
            try:
                path.rename(backup_path)
                path.write_text(content, encoding=encoding)
                return True, str(backup_path)
            except Exception as e:
                return False, str(e)
        else:
            try:
                path.write_text(content, encoding=encoding)
                return True, None
            except Exception as e:
                return False, str(e)

    def find_replace(self, file_path, find, replace, use_regex=False, case_sensitive=True, count=0):
        """Find and replace text in file."""
        try:
            path = Path(file_path).expanduser()
            content, encoding = self._read_file(path)

            if content is None:
                return {"success": False, "error": f"Could not read file: {file_path}"}

            original = content

            if use_regex:
                flags = 0 if case_sensitive else re.IGNORECASE
                if count > 0:
                    new_content = re.sub(find, replace, content, count=count, flags=flags)
                else:
                    new_content = re.sub(find, replace, content, flags=flags)
            else:
                if case_sensitive:
                    if count > 0:
                        new_content = content.replace(find, replace, count)
                    else:
                        new_content = content.replace(find, replace)
                else:
                    # Case insensitive replace
                    pattern = re.compile(re.escape(find), re.IGNORECASE)
                    if count > 0:
                        new_content = pattern.sub(replace, content, count=count)
                    else:
                        new_content = pattern.sub(replace, content)

            # Count replacements
            if use_regex:
                flags = 0 if case_sensitive else re.IGNORECASE
                replacements = len(re.findall(find, original, flags)) if count == 0 else min(count, len(re.findall(find, original, flags)))
            else:
                if case_sensitive:
                    replacements = original.count(find) if count == 0 else min(count, original.count(find))
                else:
                    pattern = re.compile(re.escape(find), re.IGNORECASE)
                    replacements = len(pattern.findall(original)) if count == 0 else min(count, len(pattern.findall(original)))

            # Write file
            success, backup = self._write_file(path, new_content, encoding or 'utf-8')

            if not success:
                return {"success": False, "error": f"Could not write file: {backup}"}

            return {
                "success": True,
                "file": str(path),
                "replacements": replacements,
                "backup_created": backup is not None,
                "backup_path": backup
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def insert_text(self, file_path, text, position="end", line_number=None, after_pattern=None):
        """Insert text at specific position."""
        try:
            path = Path(file_path).expanduser()
            content, encoding = self._read_file(path)

            if content is None:
                return {"success": False, "error": f"Could not read file: {file_path}"}

            lines = content.split('\n')

            if position == "end":
                new_lines = lines + [text]
            elif position == "start":
                new_lines = [text] + lines
            elif position == "after_line" and line_number is not None:
                idx = min(line_number, len(lines))
                new_lines = lines[:idx] + [text] + lines[idx:]
            elif position == "before_line" and line_number is not None:
                idx = max(0, line_number - 1)
                new_lines = lines[:idx] + [text] + lines[idx:]
            elif position == "after_pattern" and after_pattern:
                new_lines = []
                inserted = False
                for line in lines:
                    new_lines.append(line)
                    if after_pattern in line and not inserted:
                        new_lines.append(text)
                        inserted = True
                if not inserted:
                    new_lines.append(text)
            else:
                return {"success": False, "error": "Invalid position or missing parameters"}

            new_content = '\n'.join(new_lines)

            success, backup = self._write_file(path, new_content, encoding or 'utf-8')

            return {
                "success": True,
                "file": str(path),
                "lines_before": len(lines),
                "lines_after": len(new_lines),
                "backup_created": backup is not None,
                "backup_path": backup
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_lines(self, file_path, start_line, end_line=None):
        """Delete lines from file."""
        try:
            path = Path(file_path).expanduser()
            content, encoding = self._read_file(path)

            if content is None:
                return {"success": False, "error": f"Could not read file: {file_path}"}

            lines = content.split('\n')
            end = end_line or start_line

            if start_line < 1 or end > len(lines):
                return {"success": False, "error": "Line numbers out of range"}

            deleted = lines[start_line - 1:end]
            new_lines = lines[:start_line - 1] + lines[end:]
            new_content = '\n'.join(new_lines)

            success, backup = self._write_file(path, new_content, encoding or 'utf-8')

            return {
                "success": True,
                "file": str(path),
                "deleted_lines": len(deleted),
                "deleted_content": '\n'.join(deleted) if deleted else "",
                "lines_before": len(lines),
                "lines_after": len(new_lines),
                "backup_created": backup is not None
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def format_text(self, text, format_type):
        """Format text (uppercase, lowercase, title case, etc)."""
        try:
            if format_type == "uppercase":
                result = text.upper()
            elif format_type == "lowercase":
                result = text.lower()
            elif format_type == "title":
                result = text.title()
            elif format_type == "capitalize":
                result = text.capitalize()
            elif format_type == "remove_extra_spaces":
                result = ' '.join(text.split())
            elif format_type == "remove_empty_lines":
                lines = [line for line in text.split('\n') if line.strip()]
                result = '\n'.join(lines)
            elif format_type == "trim":
                result = '\n'.join(line.strip() for line in text.split('\n'))
            elif format_type == "sort_lines":
                lines = text.split('\n')
                lines.sort()
                result = '\n'.join(lines)
            elif format_type == "reverse_lines":
                lines = text.split('\n')
                lines.reverse()
                result = '\n'.join(lines)
            elif format_type == "unique_lines":
                seen = set()
                lines = []
                for line in text.split('\n'):
                    if line not in seen:
                        seen.add(line)
                        lines.append(line)
                result = '\n'.join(lines)
            else:
                return {"success": False, "error": f"Unknown format type: {format_type}"}

            return {
                "success": True,
                "format_type": format_type,
                "original_length": len(text),
                "result_length": len(result),
                "result": result
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def merge_files(self, input_files, output_file, separator="\n\n"):
        """Merge multiple files into one."""
        try:
            merged_content = []
            file_info = []

            for file_path in input_files:
                path = Path(file_path).expanduser()
                content, encoding = self._read_file(path)

                if content is not None:
                    merged_content.append(f"<!-- File: {path.name} -->")
                    merged_content.append(content)
                    file_info.append({
                        "file": str(path),
                        "size": len(content),
                        "encoding": encoding
                    })
                else:
                    file_info.append({
                        "file": str(path),
                        "error": "Could not read"
                    })

            final_content = separator.join(merged_content)

            output_path = Path(output_file).expanduser()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(final_content, encoding='utf-8')

            return {
                "success": True,
                "output_file": str(output_path),
                "files_merged": len([f for f in file_info if "error" not in f]),
                "total_size": len(final_content),
                "file_info": file_info
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def split_file(self, file_path, output_dir, lines_per_file=100, prefix="part"):
        """Split file into multiple smaller files."""
        try:
            path = Path(file_path).expanduser()
            content, encoding = self._read_file(path)

            if content is None:
                return {"success": False, "error": f"Could not read file: {file_path}"}

            lines = content.split('\n')
            total_lines = len(lines)

            output_path = Path(output_dir).expanduser()
            output_path.mkdir(parents=True, exist_ok=True)

            created_files = []
            part_num = 1

            for i in range(0, total_lines, lines_per_file):
                chunk = lines[i:i + lines_per_file]
                output_file = output_path / f"{prefix}_{part_num:03d}.txt"
                output_file.write_text('\n'.join(chunk), encoding=encoding or 'utf-8')
                created_files.append({
                    "file": str(output_file),
                    "lines": len(chunk),
                    "start_line": i + 1,
                    "end_line": min(i + len(chunk), total_lines)
                })
                part_num += 1

            return {
                "success": True,
                "original_file": str(path),
                "total_lines": total_lines,
                "files_created": len(created_files),
                "output_dir": str(output_path),
                "parts": created_files
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def apply_template(self, template, variables, output_file=None):
        """Apply variables to template string."""
        try:
            result = template
            for key, value in variables.items():
                placeholder = f"{{{{{key}}}}}"
                result = result.replace(placeholder, str(value))

            response = {
                "success": True,
                "template_applied": True,
                "variables_replaced": len(variables),
                "result_preview": result[:500] if len(result) > 500 else result,
                "result_length": len(result)
            }

            if output_file:
                output_path = Path(output_file).expanduser()
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(result, encoding='utf-8')
                response["output_file"] = str(output_path)
                response["saved"] = True

            return response

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_diff(self, file1, file2):
        """Get diff between two files."""
        try:
            path1 = Path(file1).expanduser()
            path2 = Path(file2).expanduser()

            content1, _ = self._read_file(path1)
            content2, _ = self._read_file(path2)

            if content1 is None or content2 is None:
                return {"success": False, "error": "Could not read one or both files"}

            lines1 = content1.split('\n')
            lines2 = content2.split('\n')

            diff = list(unified_diff(lines1, lines2, fromfile=str(path1), tofile=str(path2)))

            return {
                "success": True,
                "file1": str(path1),
                "file2": str(path2),
                "diff_lines": len(diff),
                "has_differences": len(diff) > 0,
                "diff": '\n'.join(diff) if diff else "Files are identical"
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def execute(self, input_data: dict) -> dict:
        """evo-engine interface."""
        action = input_data.get("action", "find_replace")

        if action == "find_replace":
            return self.find_replace(
                input_data.get("file_path", ""),
                input_data.get("find", ""),
                input_data.get("replace", ""),
                input_data.get("use_regex", False),
                input_data.get("case_sensitive", True),
                input_data.get("count", 0)
            )
        elif action == "insert_text":
            return self.insert_text(
                input_data.get("file_path", ""),
                input_data.get("text", ""),
                input_data.get("position", "end"),
                input_data.get("line_number"),
                input_data.get("after_pattern")
            )
        elif action == "delete_lines":
            return self.delete_lines(
                input_data.get("file_path", ""),
                input_data.get("start_line", 1),
                input_data.get("end_line")
            )
        elif action == "format_text":
            return self.format_text(
                input_data.get("text", ""),
                input_data.get("format_type", "trim")
            )
        elif action == "merge_files":
            return self.merge_files(
                input_data.get("input_files", []),
                input_data.get("output_file", ""),
                input_data.get("separator", "\n\n")
            )
        elif action == "split_file":
            return self.split_file(
                input_data.get("file_path", ""),
                input_data.get("output_dir", "."),
                input_data.get("lines_per_file", 100),
                input_data.get("prefix", "part")
            )
        elif action == "apply_template":
            return self.apply_template(
                input_data.get("template", ""),
                input_data.get("variables", {}),
                input_data.get("output_file")
            )
        elif action == "get_diff":
            return self.get_diff(
                input_data.get("file1", ""),
                input_data.get("file2", "")
            )
        else:
            return {"success": False, "error": f"Unknown action: {action}"}


def execute(input_data: dict) -> dict:
    return DocumentEditorSkill().execute(input_data)


if __name__ == "__main__":
    skill = DocumentEditorSkill()
    print(f"Info: {json.dumps(get_info(), indent=2)}")
    print(f"Health: {health_check()}")

    # Test format
    print("\nTest format_text:")
    result = skill.format_text("  hello   world  ", "remove_extra_spaces")
    print(json.dumps(result, indent=2))
