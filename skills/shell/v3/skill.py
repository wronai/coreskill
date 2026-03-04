imports
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

def _load_blocked_commands():
    """Load blocked dangerous commands from system config file."""
    # Find project root (3 levels up from this file: skill.py -> v1 -> shell -> skills)
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    config_path = project_root / "config" / "system.json"
    
    fallback = (
        "rm -rf /", "rm -rf /*", "mkfs", "dd if=/dev/zero",
        "format", "fdisk", ":(){ :|:& };:",
    )
    
    if not config_path.exists():
        return fallback
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            blocked = config.get("blocking", {}).get("blocked_commands", [])
            return tuple(blocked) if blocked else fallback
    except Exception:
        return fallback


# Commands that require explicit confirmation (destructive)
DANGEROUS_PREFIXES = (
    "rm ", "rm -", "mkfs", "dd ", "format ",
    "> /dev/", "chmod 777", ":(){ :",
)

# Commands that are always blocked - loaded from config
BLOCKED_COMMANDS = _load_blocked_commands()

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
    if shutil.which("bash"):
        return {"status": "ok"}
    else:
        return {"status": "error", "message": "bash not found"}


class ShellSkill:
    def _is_interactive(self, command):
        """Detect commands that need terminal stdin (sudo, passwd, etc.)."""
        cmd_lower = command.lower().strip()
        return any(cmd_lower.startswith(p) for p in ("sudo ", "passwd", "ssh "))

    def execute(self, params: dict) -> dict:
        command = params.get("text", "").strip()
        if not command:
            return {"success": False, "error": "No command provided"}

        # Safety check
        cmd_lower = command.lower().strip()
        for blocked in BLOCKED_COMMANDS:
            if blocked in cmd_lower:
                return {"success": False, "error": f"Blocked dangerous command: {command}"}
        
        # Check for dangerous prefixes as well
        for prefix in DANGEROUS_PREFIXES:
            if cmd_lower.startswith(prefix):
                 return {"success": False, "error": f"Blocked dangerous command prefix: {command}"}

        timeout = MAX_TIMEOUT
        # Attempt to extract timeout from command if it looks like a number
        try:
            parts = command.split()
            if parts[0].lower() == "timeout" and len(parts) > 1 and parts[1].isdigit():
                timeout = min(int(parts[1]), MAX_TIMEOUT)
                command = " ".join(parts[2:]) # Remove timeout and duration from command
        except Exception:
            pass # Ignore if parsing fails

        cwd = os.path.expanduser("~")
        env = {**os.environ, "DEBIAN_FRONTEND": "noninteractive"}

        # Use print for logging, but don't include in the final output unless it's stdout/stderr
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
                
                # Read stdout line by line
                stdout_iter = iter(proc.stdout.readline, '')
                for line in stdout_iter:
                    line_count += 1
                    if line_count <= MAX_OUTPUT_LINES:
                        stdout_lines.append(line.rstrip("\n"))
                        print(f"\033[2m  {line}\033[0m", end="", flush=True)
                    elif line_count == MAX_OUTPUT_LINES + 1:
                        print(f"\033[2m  ... (truncating output)\033[0m", flush=True)
                        break # Stop reading stdout if truncated

                # Read stderr after stdout is processed or loop broken
                stderr_output = proc.stderr.read() if proc.stderr else ""
                
                try:
                    proc.wait(timeout=10) # Short timeout for process completion
                except subprocess.TimeoutExpired:
                    proc.kill()
                    return {"success": False, "command": command,
                            "error": f"Command process did not terminate cleanly after {timeout}s"}

                stdout = "\n".join(stdout_lines)
                if line_count > MAX_OUTPUT_LINES:
                    stdout += f"\n... (truncated, {line_count} total lines)"

                stderr_log = stderr_output.strip()
                if stderr_log and proc.returncode != 0:
                    print(f"\033[31m  stderr: {stderr_log[:200]}\033[0m", flush=True)

                error_message = None
                if proc.returncode != 0 and stderr_log:
                    error_message = stderr_log[:500]
                elif proc.returncode != 0:
                    error_message = f"Command failed with exit code {proc.returncode}"

                return {
                    "success": proc.returncode == 0,
                    "command": command,
                    "exit_code": proc.returncode,
                    "stdout": stdout,
                    "stderr": stderr_log[:2000] if stderr_log else "",
                    "error": error_message,
                }

        except subprocess.TimeoutExpired:
            return {"success": False, "command": command,
                    "error": f"Command timed out after {timeout}s"}
        except FileNotFoundError:
            return {"success": False, "command": command, "error": f"Command not found: {command.split()[0]}"}
        except Exception as e:
            return {"success": False, "command": command, "error": str(e)}


def execute(params: dict) -> dict:
    return ShellSkill().execute(params)


if __name__ == "__main__":
    # Example usage:
    # python your_skill_file.py "ls -l"
    # python your_skill_file.py "echo 'Hello World'"
    # python your_skill_file.py "timeout 5 sleep 10"
    
    if len(sys.argv) > 1:
        cmd_text = " ".join(sys.argv[1:])
    else:
        # Default command if none provided
        cmd_text = "echo 'Hello from shell skill' && uname -a"
        
    result = execute({"text": cmd_text})
    print("\n--- Execution Result ---")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # Example of how to use the health check
    print("\n--- Health Check ---")
    print(json.dumps(health_check(), indent=2, ensure_ascii=False))

    # Example of how to use get_info
    print("\n--- Skill Info ---")
    print(json.dumps(get_info(), indent=2, ensure_ascii=False))