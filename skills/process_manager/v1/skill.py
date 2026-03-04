#!/usr/bin/env python3
"""
process_manager skill - Process management using stdlib only.
Supports: list, find, kill, info
"""
import os
import subprocess
import json
import signal
from pathlib import Path
from datetime import datetime, timezone


def get_info():
    return {
        "name": "process_manager",
        "version": "v1",
        "description": "Process management: list, find, kill, info. Stdlib + ps command fallback.",
        "capabilities": ["processes", "system", "management"],
        "actions": ["list", "find", "kill", "info"]
    }


def health_check():
    try:
        # Check if we can read /proc or run ps
        if os.path.exists("/proc"):
            return True
        result = subprocess.run(["ps", "aux"], capture_output=True, timeout=5)
        return result.returncode == 0
    except Exception:
        return False


class ProcessManagerSkill:
    """Process management using stdlib and ps command."""

    def _parse_proc_stat(self, pid_dir):
        """Parse /proc/PID/stat file."""
        try:
            stat_path = pid_dir / "stat"
            with open(stat_path, 'r') as f:
                stat_line = f.read()
            # Parse: pid (comm) state ppid ...
            parts = stat_line.split()
            pid = int(parts[0])
            # Command is in parentheses, may contain spaces
            start = stat_line.find('(')
            end = stat_line.rfind(')')
            comm = stat_line[start+1:end]
            state = parts[parts.index(stat_line[end+1:].split()[0])]
            return {"pid": pid, "name": comm, "state": state}
        except Exception:
            return None

    def _get_proc_info(self, pid):
        """Get process info from /proc."""
        try:
            pid_dir = Path(f"/proc/{pid}")
            if not pid_dir.exists():
                return None
            
            # Basic info from stat
            info = self._parse_proc_stat(pid_dir) or {"pid": pid}
            
            # Command line
            try:
                cmdline_path = pid_dir / "cmdline"
                with open(cmdline_path, 'r') as f:
                    cmdline = f.read().replace('\0', ' ').strip()
                    if cmdline:
                        info["command"] = cmdline[:200]
            except Exception:
                pass
            
            # Status info (PPID, UID, etc.)
            try:
                status_path = pid_dir / "status"
                with open(status_path, 'r') as f:
                    for line in f:
                        if line.startswith("PPid:"):
                            info["ppid"] = int(line.split()[1])
                        elif line.startswith("Uid:"):
                            info["uid"] = int(line.split()[1])
                        elif line.startswith("VmRSS:"):
                            info["memory_rss"] = line.split()[1] + " " + line.split()[2]
            except Exception:
                pass
            
            # Start time from stat file
            try:
                stat_path = pid_dir / "stat"
                with open(stat_path, 'r') as f:
                    parts = f.read().split()
                    # starttime is field 22 (index 21)
                    if len(parts) > 21:
                        # Convert jiffies to seconds (approximate)
                        uptime = Path("/proc/uptime").read_text().split()[0]
                        uptime_sec = float(uptime)
                        starttime_ticks = int(parts[21])
                        clock_ticks = os.sysconf(os.sysconf_names['SC_CLK_TCK'])
                        process_time = starttime_ticks / clock_ticks
                        start_sec = uptime_sec - process_time
                        info["start_time"] = datetime.fromtimestamp(
                            datetime.now().timestamp() - start_sec, timezone.utc
                        ).isoformat()
            except Exception:
                pass
            
            return info
        except Exception:
            return None

    def list_processes(self, limit=100):
        """List running processes."""
        try:
            processes = []
            
            # Try /proc first (Linux)
            if os.path.exists("/proc"):
                for entry in os.listdir("/proc"):
                    if entry.isdigit():
                        info = self._get_proc_info(int(entry))
                        if info:
                            processes.append(info)
                        if len(processes) >= limit:
                            break
            else:
                # Fallback to ps command
                result = subprocess.run(
                    ["ps", "aux"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')[1:]  # Skip header
                    for line in lines[:limit]:
                        parts = line.split(None, 10)
                        if len(parts) >= 11:
                            processes.append({
                                "user": parts[0],
                                "pid": int(parts[1]),
                                "cpu": parts[2],
                                "mem": parts[3],
                                "command": parts[10][:100]
                            })
            
            return {
                "success": True,
                "processes": processes,
                "count": len(processes),
                "source": "/proc" if os.path.exists("/proc") else "ps"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def find_process(self, name_pattern=None, pid=None):
        """Find process by name or PID."""
        try:
            if pid:
                info = self._get_proc_info(pid)
                if info:
                    return {"success": True, "process": info}
                return {"success": False, "error": f"Process {pid} not found"}
            
            if name_pattern:
                matches = []
                result = self.list_processes(limit=500)
                if result.get("success"):
                    for proc in result["processes"]:
                        name = proc.get("name", "")
                        command = proc.get("command", "")
                        if name_pattern.lower() in name.lower() or name_pattern.lower() in command.lower():
                            matches.append(proc)
                return {"success": True, "matches": matches, "count": len(matches)}
            
            return {"success": False, "error": "Specify name_pattern or pid"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def kill_process(self, pid, signal_name="TERM"):
        """Kill process by PID."""
        try:
            pid = int(pid)
            sig = getattr(signal, f"SIG{signal_name.upper()}", signal.SIGTERM)
            
            # Check if process exists
            if not self._get_proc_info(pid):
                return {"success": False, "error": f"Process {pid} not found"}
            
            os.kill(pid, sig)
            return {
                "success": True,
                "pid": pid,
                "signal": signal_name.upper(),
                "message": f"Sent {signal_name.upper()} to process {pid}"
            }
        except ProcessLookupError:
            return {"success": False, "error": f"Process {pid} not found"}
        except PermissionError:
            return {"success": False, "error": f"Permission denied to kill process {pid}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def process_info(self, pid):
        """Get detailed process info."""
        try:
            pid = int(pid)
            info = self._get_proc_info(pid)
            if not info:
                return {"success": False, "error": f"Process {pid} not found"}
            
            # Add children if available
            try:
                children = []
                result = self.list_processes(limit=500)
                if result.get("success"):
                    for proc in result["processes"]:
                        if proc.get("ppid") == pid:
                            children.append(proc["pid"])
                if children:
                    info["children"] = children
            except Exception:
                pass
            
            return {"success": True, "process": info}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def execute(self, input_data: dict) -> dict:
        """evo-engine interface."""
        action = input_data.get("action", "list")
        
        if action == "list":
            return self.list_processes(input_data.get("limit", 100))
        elif action == "find":
            return self.find_process(
                input_data.get("name"),
                input_data.get("pid")
            )
        elif action == "kill":
            return self.kill_process(
                input_data.get("pid"),
                input_data.get("signal", "TERM")
            )
        elif action == "info":
            return self.process_info(input_data.get("pid"))
        else:
            return {"success": False, "error": f"Unknown action: {action}"}


def execute(input_data: dict) -> dict:
    return ProcessManagerSkill().execute(input_data)


if __name__ == "__main__":
    skill = ProcessManagerSkill()
    print(f"Info: {json.dumps(get_info(), indent=2)}")
    print(f"Health: {health_check()}")
    print(f"\nTop 5 processes:")
    result = skill.list_processes(limit=5)
    print(json.dumps(result, indent=2, ensure_ascii=False))
