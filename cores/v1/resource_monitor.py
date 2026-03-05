#!/usr/bin/env python3
"""
evo-engine ResourceMonitor — system resource detection for skill provider selection.
"""
import os
import shutil
import subprocess
from pathlib import Path


class ResourceMonitor:
    """Detects CPU, RAM, GPU, disk, installed packages."""

    _gpu_cache = None  # class-level: GPU doesn't change during process

    def __init__(self):
        self._cache = {}
        self._cache_ttl = 10  # seconds
        self._snapshot_cache = None
        self._snapshot_ts = 0

    def snapshot(self) -> dict:
        import time
        now = time.monotonic()
        if self._snapshot_cache and (now - self._snapshot_ts) < self._cache_ttl:
            # Update volatile fields only
            self._snapshot_cache["ram_available_mb"] = self._ram_available()
            return self._snapshot_cache
        self._snapshot_cache = {
            "cpu_count": self._cpu_count(),
            "ram_total_mb": self._ram_total(),
            "ram_available_mb": self._ram_available(),
            "disk_free_mb": self._disk_free(),
            "gpu": self._detect_gpu(),
            "python_packages": self._installed_packages(),
            "system_commands": {},  # populated on demand
        }
        self._snapshot_ts = now
        return self._snapshot_cache

    # --- CPU ---
    def _cpu_count(self) -> int:
        return os.cpu_count() or 1

    # --- RAM ---
    def _ram_total(self) -> int:
        try:
            import psutil
            return psutil.virtual_memory().total // (1024 * 1024)
        except ImportError:
            return self._ram_from_proc("MemTotal")

    def _ram_available(self) -> int:
        try:
            import psutil
            return psutil.virtual_memory().available // (1024 * 1024)
        except ImportError:
            return self._ram_from_proc("MemAvailable")

    def _ram_from_proc(self, field: str) -> int:
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith(field):
                        return int(line.split()[1]) // 1024  # kB -> MB
        except (FileNotFoundError, ValueError):
            pass
        return 0

    # --- Disk ---
    def _disk_free(self) -> int:
        try:
            return shutil.disk_usage("/").free // (1024 * 1024)
        except Exception:
            return 0

    # --- GPU ---
    def _detect_gpu(self) -> dict:
        if ResourceMonitor._gpu_cache is not None:
            return ResourceMonitor._gpu_cache

        # Try torch first
        try:
            import torch
            if torch.cuda.is_available():
                result = {
                    "available": True,
                    "type": "cuda",
                    "name": torch.cuda.get_device_name(0),
                    "vram_mb": torch.cuda.get_device_properties(0).total_mem // (1024 * 1024),
                }
                ResourceMonitor._gpu_cache = result
                return result
        except (ImportError, Exception):
            pass

        # Try nvidia-smi
        try:
            r = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5
            )
            if r.returncode == 0 and r.stdout.strip():
                parts = r.stdout.strip().split(", ")
                result = {
                    "available": True,
                    "type": "cuda",
                    "name": parts[0],
                    "vram_mb": int(parts[1]) if len(parts) > 1 else 0,
                }
                ResourceMonitor._gpu_cache = result
                return result
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Try ROCm (AMD)
        try:
            r = subprocess.run(["rocm-smi", "--showproductname"], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                result = {"available": True, "type": "rocm", "name": "AMD GPU"}
                ResourceMonitor._gpu_cache = result
                return result
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        ResourceMonitor._gpu_cache = {"available": False, "type": None}
        return ResourceMonitor._gpu_cache

    # --- Python packages ---
    def _installed_packages(self) -> dict:
        """Return {package_name: version} for installed packages."""
        pkgs = {}
        try:
            import importlib.metadata
            for dist in importlib.metadata.distributions():
                pkgs[dist.metadata["Name"].lower()] = dist.version
        except Exception:
            pass
        return pkgs

    # --- System commands ---
    def has_command(self, cmd: str) -> bool:
        return shutil.which(cmd) is not None

    def has_python_package(self, name: str) -> bool:
        try:
            __import__(name.replace("-", "_"))
            return True
        except ImportError:
            return False

    # --- Requirement checking ---
    def _check_gpu_req(self, requirements):
        """Check GPU requirements. Returns (ok, reason)."""
        if not requirements.get("gpu"):
            return True, ""
        gpu = self._detect_gpu()
        if not gpu["available"]:
            return False, "GPU required but not detected"
        min_vram = requirements.get("min_vram_mb", 0)
        if min_vram and gpu.get("vram_mb", 0) < min_vram:
            return False, f"Need {min_vram}MB VRAM, have {gpu.get('vram_mb', 0)}MB"
        return True, ""

    def _check_resource_limits(self, requirements):
        """Check RAM and disk requirements. Returns (ok, reason)."""
        min_ram = requirements.get("min_ram_mb", 0)
        if min_ram:
            avail = self._ram_available()
            if avail < min_ram:
                return False, f"Need {min_ram}MB RAM, have {avail}MB available"
        min_disk = requirements.get("min_disk_mb", 0)
        if min_disk:
            free = self._disk_free()
            if free < min_disk:
                return False, f"Need {min_disk}MB disk, have {free}MB free"
        return True, ""

    def _check_packages_and_commands(self, requirements):
        """Check python packages, system commands, env vars. Returns (ok, reason)."""
        for pkg in requirements.get("python_packages", []):
            name = pkg.split(">=")[0].split("==")[0].split("<")[0].strip()
            if not self.has_python_package(name):
                return False, f"Python package '{name}' not installed"
        for cmd in requirements.get("system_packages", []):
            if not self.has_command(cmd):
                return False, f"System command '{cmd}' not found"
        sys_any = requirements.get("system_packages_any", [])
        if sys_any and not any(self.has_command(cmd) for cmd in sys_any):
            return False, f"Need one of system commands: {', '.join(sys_any)}"
        for key in requirements.get("env_vars", []):
            if not os.environ.get(key, "").strip():
                return False, f"Env var '{key}' is required"
        return True, ""

    @staticmethod
    def _check_files(requirements):
        """Check file existence requirements. Returns (ok, reason)."""
        files_any = requirements.get("files_any", [])
        if files_any:
            if not any(
                Path(os.path.expanduser(os.path.expandvars(str(p)))).exists()
                for p in files_any
            ):
                return False, "None of required files exist"
        for p in requirements.get("files_all", []):
            pp = Path(os.path.expanduser(os.path.expandvars(str(p))))
            if not pp.exists():
                return False, f"Required file not found: {pp}"
        return True, ""

    def can_run(self, requirements: dict) -> tuple:
        """Check if system meets requirements. Returns (bool, reason)."""
        requirements = requirements or {}
        for checker in (
            lambda: self._check_gpu_req(requirements),
            lambda: self._check_resource_limits(requirements),
            lambda: self._check_packages_and_commands(requirements),
            lambda: self._check_files(requirements),
        ):
            ok, reason = checker()
            if not ok:
                return False, reason
        return True, "OK"
