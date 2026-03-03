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
    def _is_interactive(self, command):
        """Detect commands that need terminal stdin (sudo, passwd, etc.)."""
        cmd_lower = command.lower().strip()
        return any(cmd_lower.startswith(p) for p in ("sudo ", "passwd", "ssh "))

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
        env = {**os.environ, "DEBIAN_FRONTEND": "noninteractive"}

        print(f"\033[2m$ {command}\033[0m", flush=True)

        try:
            interactive = self._is_interactive(command)

            if interactive:
                # Interactive: pass stdin/stdout through to terminal
                proc = subprocess.Popen(
                    ["bash", "-c", command],
                    cwd=cwd, env=env,
                )
                try:
                    proc.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    return {"success": False, "command": command,
                            "error": f"Command timed out after {timeout}s"}
                return {
                    "success": proc.returncode == 0,
                    "command": command,
                    "exit_code": proc.returncode,
                    "stdout": "(interactive — output shown in terminal)",
                    "stderr": "",
                }
            else:
                # Non-interactive: capture + stream output line by line
                proc = subprocess.Popen(
                    ["bash", "-c", command],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, cwd=cwd, env=env,
                )
                stdout_lines = []
                line_count = 0
                for line in proc.stdout:
                    line_count += 1
                    if line_count <= MAX_OUTPUT_LINES:
                        stdout_lines.append(line.rstrip("\n"))
                        print(f"\033[2m  {line}\033[0m", end="", flush=True)
                    elif line_count == MAX_OUTPUT_LINES + 1:
                        print(f"\033[2m  ... (truncating output)\033[0m", flush=True)

                stderr = proc.stderr.read() if proc.stderr else ""
                proc.wait(timeout=10)

                stdout = "\n".join(stdout_lines)
                if line_count > MAX_OUTPUT_LINES:
                    stdout += f"\n... (truncated, {line_count} total lines)"

                if stderr.strip() and proc.returncode != 0:
                    print(f"\033[31m  stderr: {stderr.strip()[:200]}\033[0m", flush=True)

                return {
                    "success": proc.returncode == 0,
                    "command": command,
                    "exit_code": proc.returncode,
                    "stdout": stdout,
                    "stderr": stderr[:2000] if stderr else "",
                    "error": stderr[:500] if proc.returncode != 0 and stderr else None,
                }

        except subprocess.TimeoutExpired:
            return {"success": False, "command": command,
                    "error": f"Command timed out after {timeout}s"}
        except Exception as e:
            return {"success": False, "command": command, "error": str(e)}


def execute(input_data: dict) -> dict:
    return ShellSkill().execute(input_data)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = " ".join(sys.argv[1:])
    else:
        cmd = "echo 'Hello from shell skill' && uname -a"
    print(json.dumps(execute({"command": cmd}), indent=2, ensure_ascii=False))
