#!/usr/bin/env python3
"""
AdaptiveResourceMonitor — EWMA-based resource trend detection.

Extends ResourceMonitor with:
- Periodic sampling via psutil (CPU%, RAM%, disk I/O)
- EWMA (Exponentially Weighted Moving Average) smoothing for trend detection
- Alert thresholds with hysteresis to avoid flapping
- Resource pressure scoring for provider selection hints
"""
import time
import threading
from collections import deque
from typing import Dict, Optional, List, Tuple

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False

from .config import cpr, C


class EWMATracker:
    """Exponentially Weighted Moving Average for a single metric."""

    def __init__(self, alpha: float = 0.3, window: int = 60):
        self.alpha = alpha        # smoothing factor (0..1), higher = more reactive
        self._value: Optional[float] = None
        self._history: deque = deque(maxlen=window)
        self._last_ts: float = 0.0

    @property
    def value(self) -> Optional[float]:
        return self._value

    def update(self, raw: float) -> float:
        """Feed a new sample. Returns smoothed value."""
        now = time.time()
        if self._value is None:
            self._value = raw
        else:
            self._value = self.alpha * raw + (1 - self.alpha) * self._value
        self._history.append((now, raw, self._value))
        self._last_ts = now
        return self._value

    @property
    def trend(self) -> str:
        """Detect trend: 'rising', 'falling', 'stable'."""
        if len(self._history) < 5:
            return "stable"
        recent = [v for _, _, v in list(self._history)[-5:]]
        older = [v for _, _, v in list(self._history)[-10:-5]] or recent[:1]
        avg_recent = sum(recent) / len(recent)
        avg_older = sum(older) / len(older)
        diff = avg_recent - avg_older
        if diff > 3.0:
            return "rising"
        elif diff < -3.0:
            return "falling"
        return "stable"

    @property
    def history_summary(self) -> Dict:
        """Return min/max/avg/current over window."""
        if not self._history:
            return {"min": 0, "max": 0, "avg": 0, "current": 0, "trend": "stable"}
        vals = [v for _, v, _ in self._history]
        return {
            "min": round(min(vals), 1),
            "max": round(max(vals), 1),
            "avg": round(sum(vals) / len(vals), 1),
            "current": round(self._value or 0, 1),
            "trend": self.trend,
        }


class AdaptiveResourceMonitor:
    """EWMA-enhanced resource monitoring with alert thresholds.

    Usage:
        monitor = AdaptiveResourceMonitor()
        monitor.start(interval=5)  # sample every 5s in background
        ...
        pressure = monitor.pressure_score()  # 0.0 (idle) .. 1.0 (overloaded)
        alerts = monitor.check_alerts()
        monitor.stop()
    """

    # Alert thresholds (percentage)
    CPU_HIGH = 85.0
    CPU_CRITICAL = 95.0
    RAM_HIGH = 80.0
    RAM_CRITICAL = 90.0
    DISK_HIGH = 85.0

    # Hysteresis: must drop this much below threshold to clear alert
    HYSTERESIS = 5.0

    def __init__(self, alpha: float = 0.3, window: int = 60):
        self.cpu = EWMATracker(alpha=alpha, window=window)
        self.ram = EWMATracker(alpha=alpha, window=window)
        self.disk = EWMATracker(alpha=alpha, window=window)
        self._alerts: Dict[str, bool] = {}
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._sample_count = 0
        self._lock = threading.Lock()

    def sample(self):
        """Take one resource sample and update EWMA trackers."""
        if not _HAS_PSUTIL:
            return

        with self._lock:
            cpu_pct = psutil.cpu_percent(interval=0.1)
            ram_pct = psutil.virtual_memory().percent
            disk_pct = psutil.disk_usage("/").percent

            self.cpu.update(cpu_pct)
            self.ram.update(ram_pct)
            self.disk.update(disk_pct)
            self._sample_count += 1

    def start(self, interval: float = 5.0):
        """Start background sampling thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()

        def _loop():
            while not self._stop_event.is_set():
                try:
                    self.sample()
                except Exception:
                    pass
                self._stop_event.wait(timeout=interval)

        self._thread = threading.Thread(target=_loop, daemon=True, name="adaptive-monitor")
        self._thread.start()

    def stop(self):
        """Stop background sampling."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def pressure_score(self) -> float:
        """Combined resource pressure: 0.0 (idle) .. 1.0 (overloaded).

        Useful for provider selection: prefer lighter providers when pressure > 0.6.
        """
        if not _HAS_PSUTIL or self._sample_count == 0:
            return 0.0

        with self._lock:
            cpu_v = (self.cpu.value or 0) / 100.0
            ram_v = (self.ram.value or 0) / 100.0
            disk_v = (self.disk.value or 0) / 100.0

        # Weighted: RAM matters most for ML workloads
        score = cpu_v * 0.3 + ram_v * 0.5 + disk_v * 0.2
        return round(min(score, 1.0), 3)

    def check_alerts(self) -> List[Tuple[str, str, float]]:
        """Check thresholds with hysteresis. Returns list of (metric, level, value)."""
        alerts = []
        if self._sample_count == 0:
            return alerts

        with self._lock:
            checks = [
                ("cpu", self.cpu.value or 0, self.CPU_HIGH, self.CPU_CRITICAL),
                ("ram", self.ram.value or 0, self.RAM_HIGH, self.RAM_CRITICAL),
                ("disk", self.disk.value or 0, self.DISK_HIGH, 100.0),
            ]

        for metric, val, high_th, crit_th in checks:
            key_crit = f"{metric}_critical"
            key_high = f"{metric}_high"

            # Critical
            if val >= crit_th:
                if not self._alerts.get(key_crit):
                    self._alerts[key_crit] = True
                    alerts.append((metric, "critical", round(val, 1)))
            elif val < crit_th - self.HYSTERESIS:
                self._alerts[key_crit] = False

            # High
            if val >= high_th and not self._alerts.get(key_crit):
                if not self._alerts.get(key_high):
                    self._alerts[key_high] = True
                    alerts.append((metric, "high", round(val, 1)))
            elif val < high_th - self.HYSTERESIS:
                self._alerts[key_high] = False

        return alerts

    def snapshot(self) -> Dict:
        """Current state summary."""
        return {
            "available": _HAS_PSUTIL,
            "samples": self._sample_count,
            "running": self.is_running,
            "pressure": self.pressure_score(),
            "cpu": self.cpu.history_summary,
            "ram": self.ram.history_summary,
            "disk": self.disk.history_summary,
            "alerts": {k: v for k, v in self._alerts.items() if v},
        }

    def format_status(self) -> str:
        """One-line status string for display."""
        if not _HAS_PSUTIL or self._sample_count == 0:
            return "AdaptiveMonitor: no data"
        s = self.snapshot()
        return (
            f"CPU: {s['cpu']['current']}%({s['cpu']['trend']}) | "
            f"RAM: {s['ram']['current']}%({s['ram']['trend']}) | "
            f"Disk: {s['disk']['current']}% | "
            f"Pressure: {s['pressure']:.0%}"
        )
