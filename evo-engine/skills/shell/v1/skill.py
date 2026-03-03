#!/usr/bin/env python3
"""Shell Skill v1 — execute system commands and return output."""
import json
import os
import shutil
import subprocess
import shlex
import sys

# Commands that require explicit confirmation (destructive)
DANGEROUS_PREFIXES = (
    "rm ", "rm -", "mkfs", "dd ", "format ",
    "> /dev/", "chmod 777", ":(){ :",
)

# Commands that are always blocked
BLOCKED_COMMANDS = (
    "rm -rf /", "rm -rf /*", "mkfs", "dd if=/dev/zero",
)

MAX_OUTPUT_LINES = 200
MAX_TIMEOUT = 120


def get_info():
    return {
        "name": "shell",
        "version": "v1",
        "description": "Execute system commands (bash) and return output. "
                       "Supports: apt, pip, systemctl, ls, cat, grep, find, etc.",
        "capabilities": ["shell", "command", "system"],
    }


def health_check():
    return shutil.which("bash") is not None


class ShellSkill:
    def execute(self, input_data: dict) -> dict:
        command = input_data.get("command", "").strip()
        if not command:
            return {"success": False, "error": "No command provided"}

        # Safety check
        cmd_lower = command.lower().strip()
        for blocked in BLOCKED_COMMANDS:
            if blocked in cmd_lower:
                return {"success": False, "error": f"Blocked dangerous command: {command}"}

        timeout = min(int(input_data.get("timeout", 60)), MAX_TIMEOUT)
        cwd = input_data.get("cwd", os.path.expanduser("~"))

        try:
            result = subprocess.run(
                ["bash", "-c", command],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
                env={**os.environ, "DEBIAN_FRONTEND": "noninteractive"},
            )

            stdout = result.stdout
            stderr = result.stderr

            # Truncate very long output
            stdout_lines = stdout.split("\n")
            if len(stdout_lines) > MAX_OUTPUT_LINES:
                stdout = "\n".join(stdout_lines[:MAX_OUTPUT_LINES])
                stdout += f"\n... (truncated, {len(stdout_lines)} total lines)"

            return {
                "success": result.returncode == 0,
                "command": command,
                "exit_code": result.returncode,
                "stdout": stdout,
                "stderr": stderr[:2000] if stderr else "",
                "error": stderr[:500] if result.returncode != 0 and stderr else None,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "command": command,
                "error": f"Command timed out after {timeout}s",
            }
        except Exception as e:
            return {
                "success": False,
                "command": command,
                "error": str(e),
            }


def execute(input_data: dict) -> dict:
    return ShellSkill().execute(input_data)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = " ".join(sys.argv[1:])
    else:
        cmd = "echo 'Hello from shell skill' && uname -a"
    print(json.dumps(execute({"command": cmd}), indent=2, ensure_ascii=False))
