#!/usr/bin/env python3
"""
clipboard skill - Clipboard operations using xclip/xsel/wl-copy/pbpaste fallbacks.
Supports: copy, paste, clear
"""
import subprocess
import json
import shutil
import os


def get_info():
    return {
        "name": "clipboard",
        "version": "v1",
        "description": "Clipboard operations: copy, paste, clear. Uses xclip/xsel/wl-copy/pbpaste.",
        "capabilities": ["clipboard", "copy", "paste"],
        "actions": ["copy", "paste", "clear"]
    }


def health_check():
    """Check if any clipboard tool is available."""
    tools = ["xclip", "xsel", "wl-copy", "pbcopy", "pbpaste"]
    for tool in tools:
        if shutil.which(tool):
            return True
    return False


class ClipboardSkill:
    """Clipboard operations with multiple backend support."""

    def _detect_backend(self):
        """Detect available clipboard backend."""
        # Wayland
        if os.environ.get("WAYLAND_DISPLAY") and shutil.which("wl-copy"):
            return "wl-copy"
        # macOS
        if shutil.which("pbcopy") and shutil.which("pbpaste"):
            return "macos"
        # X11 - prefer xclip
        if shutil.which("xclip"):
            return "xclip"
        if shutil.which("xsel"):
            return "xsel"
        return None

    def copy(self, text):
        """Copy text to clipboard."""
        try:
            backend = self._detect_backend()
            if not backend:
                return {"success": False, "error": "No clipboard tool found (xclip, xsel, wl-copy, pbcopy)"}
            
            if backend == "wl-copy":
                proc = subprocess.run(
                    ["wl-copy"],
                    input=text,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
            elif backend == "macos":
                proc = subprocess.run(
                    ["pbcopy"],
                    input=text,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
            elif backend == "xclip":
                proc = subprocess.run(
                    ["xclip", "-selection", "clipboard"],
                    input=text,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
            elif backend == "xsel":
                proc = subprocess.run(
                    ["xsel", "--clipboard", "--input"],
                    input=text,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
            
            if proc.returncode == 0:
                return {
                    "success": True,
                    "action": "copy",
                    "length": len(text),
                    "backend": backend
                }
            else:
                return {
                    "success": False,
                    "error": f"Clipboard command failed: {proc.stderr}",
                    "backend": backend
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def paste(self):
        """Paste text from clipboard."""
        try:
            backend = self._detect_backend()
            if not backend:
                return {"success": False, "error": "No clipboard tool found"}
            
            if backend == "wl-copy":
                # wl-paste for paste
                proc = subprocess.run(
                    ["wl-paste"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
            elif backend == "macos":
                proc = subprocess.run(
                    ["pbpaste"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
            elif backend == "xclip":
                proc = subprocess.run(
                    ["xclip", "-selection", "clipboard", "-o"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
            elif backend == "xsel":
                proc = subprocess.run(
                    ["xsel", "--clipboard", "--output"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
            
            if proc.returncode == 0:
                return {
                    "success": True,
                    "action": "paste",
                    "text": proc.stdout,
                    "length": len(proc.stdout),
                    "backend": backend
                }
            else:
                return {
                    "success": False,
                    "error": f"Clipboard paste failed: {proc.stderr}",
                    "backend": backend
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def clear(self):
        """Clear clipboard."""
        try:
            backend = self._detect_backend()
            if not backend:
                return {"success": False, "error": "No clipboard tool found"}
            
            # Copy empty string to clear
            if backend == "wl-copy":
                proc = subprocess.run(["wl-copy", ""], capture_output=True, timeout=5)
            elif backend == "macos":
                proc = subprocess.run(["pbcopy"], input="", capture_output=True, text=True, timeout=5)
            elif backend == "xclip":
                proc = subprocess.run(
                    ["xclip", "-selection", "clipboard"],
                    input="",
                    capture_output=True,
                    text=True,
                    timeout=5
                )
            elif backend == "xsel":
                proc = subprocess.run(
                    ["xsel", "--clipboard", "--delete"],
                    capture_output=True,
                    timeout=5
                )
            
            if proc.returncode == 0:
                return {"success": True, "action": "clear", "backend": backend}
            else:
                return {"success": False, "error": "Failed to clear clipboard"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def execute(self, input_data: dict) -> dict:
        """evo-engine interface."""
        action = input_data.get("action", "paste")
        
        if action == "copy":
            text = input_data.get("text", "")
            if not text:
                return {"success": False, "error": "No text provided for copy"}
            return self.copy(text)
        elif action == "paste":
            return self.paste()
        elif action == "clear":
            return self.clear()
        else:
            return {"success": False, "error": f"Unknown action: {action}"}


def execute(input_data: dict) -> dict:
    return ClipboardSkill().execute(input_data)


if __name__ == "__main__":
    skill = ClipboardSkill()
    print(f"Info: {json.dumps(get_info(), indent=2)}")
    print(f"Health: {health_check()}")
    print(f"Backend: {skill._detect_backend() or 'none'}")
    
    # Test copy and paste
    test_text = "Hello from clipboard skill!"
    print(f"\nCopy: {test_text}")
    copy_result = skill.copy(test_text)
    print(json.dumps(copy_result, indent=2))
    
    print("\nPaste:")
    paste_result = skill.paste()
    print(json.dumps(paste_result, indent=2))
