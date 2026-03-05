#!/usr/bin/env python3
"""
ProactiveScheduler — lightweight periodic task scheduler using threading.

No external dependencies (replaces `schedule` package).
Runs registered tasks at configurable intervals in a daemon thread.

Built-in tasks:
- Resource monitoring (AdaptiveResourceMonitor sampling)
- GC cleanup (periodic garbage collection)
- Health checks (skill preflight verification)
"""
import time
import threading
from typing import Callable, Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .config import cpr, C


@dataclass
class ScheduledTask:
    """A task registered with the scheduler."""
    name: str
    callback: Callable
    interval_s: float          # seconds between runs
    enabled: bool = True
    last_run: float = 0.0      # timestamp of last execution
    run_count: int = 0
    error_count: int = 0
    last_error: str = ""
    last_duration_ms: float = 0.0


class ProactiveScheduler:
    """Thread-based periodic task scheduler.

    Usage:
        scheduler = ProactiveScheduler()
        scheduler.register("gc", gc_callback, interval_s=3600)
        scheduler.register("health", health_callback, interval_s=300)
        scheduler.start()
        ...
        scheduler.stop()
    """

    def __init__(self):
        self._tasks: Dict[str, ScheduledTask] = {}
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._tick_interval = 1.0  # check interval in seconds
        self._lock = threading.Lock()

    def register(self, name: str, callback: Callable,
                 interval_s: float, enabled: bool = True):
        """Register a periodic task."""
        with self._lock:
            self._tasks[name] = ScheduledTask(
                name=name,
                callback=callback,
                interval_s=interval_s,
                enabled=enabled,
            )

    def unregister(self, name: str):
        """Remove a task."""
        with self._lock:
            self._tasks.pop(name, None)

    def enable(self, name: str):
        """Enable a task."""
        with self._lock:
            if name in self._tasks:
                self._tasks[name].enabled = True

    def disable(self, name: str):
        """Disable a task without removing it."""
        with self._lock:
            if name in self._tasks:
                self._tasks[name].enabled = False

    def start(self):
        """Start the scheduler background thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()

        def _loop():
            while not self._stop_event.is_set():
                self._tick()
                self._stop_event.wait(timeout=self._tick_interval)

        self._thread = threading.Thread(
            target=_loop, daemon=True, name="proactive-scheduler")
        self._thread.start()

    def stop(self):
        """Stop the scheduler."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3.0)
            self._thread = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _tick(self):
        """Check all tasks and run those that are due."""
        now = time.time()
        with self._lock:
            tasks_snapshot = list(self._tasks.values())

        for task in tasks_snapshot:
            if not task.enabled:
                continue
            if now - task.last_run < task.interval_s:
                continue
            self._execute_task(task)

    def _execute_task(self, task: ScheduledTask):
        """Run a single task with error handling."""
        start = time.time()
        try:
            task.callback()
            task.run_count += 1
        except Exception as e:
            task.error_count += 1
            task.last_error = str(e)[:200]
        finally:
            task.last_run = time.time()
            task.last_duration_ms = (time.time() - start) * 1000

    def run_now(self, name: str) -> bool:
        """Manually trigger a task immediately. Returns True if found and executed."""
        with self._lock:
            task = self._tasks.get(name)
        if not task:
            return False
        self._execute_task(task)
        return True

    def status(self) -> List[Dict]:
        """Return status of all registered tasks."""
        with self._lock:
            tasks = list(self._tasks.values())
        result = []
        for t in tasks:
            result.append({
                "name": t.name,
                "enabled": t.enabled,
                "interval_s": t.interval_s,
                "runs": t.run_count,
                "errors": t.error_count,
                "last_error": t.last_error,
                "last_duration_ms": round(t.last_duration_ms, 1),
                "next_in_s": max(0, t.interval_s - (time.time() - t.last_run)),
            })
        return result

    def format_status(self) -> str:
        """Human-readable status summary."""
        tasks = self.status()
        if not tasks:
            return "Scheduler: brak zadań"
        lines = [f"Scheduler: {len(tasks)} zadań, {'aktywny' if self.is_running else 'zatrzymany'}"]
        for t in tasks:
            state = "✓" if t["enabled"] else "⏸"
            err = f" ({t['errors']} err)" if t["errors"] else ""
            lines.append(
                f"  {state} {t['name']}: co {t['interval_s']:.0f}s, "
                f"runs={t['runs']}{err}, next≈{t['next_in_s']:.0f}s"
            )
        return "\n".join(lines)


def _run_resource_check(adaptive_monitor, logger):
    """Check resource alerts and log them."""
    alerts = adaptive_monitor.check_alerts()
    for metric, level, val in alerts:
        cpr(C.YELLOW if level == "high" else C.RED,
            f"[MONITOR] ⚠ {metric} {level}: {val}%")
        if logger:
            logger.core("resource_alert", {"metric": metric, "level": level, "value": val})


def _run_periodic_gc(gc, logger):
    """Run garbage collection and log results."""
    reports = gc.cleanup_all(migrate=False, dry_run=False)
    total = sum(len(r.get("deleted", [])) for r in reports)
    if total > 0:
        cpr(C.DIM, f"[SCHEDULER] GC: usunięto {total} starych wersji")
        if logger:
            logger.core("scheduled_gc", {"deleted": total})


def _run_health_check(skill_manager, logger):
    """Check health of all skills and log broken ones."""
    broken = []
    for name in list(skill_manager.list_skills().keys()):
        try:
            if not skill_manager.check_health(name):
                broken.append(name)
        except Exception:
            broken.append(name)
    if broken and logger:
        logger.core("scheduled_health", {"broken": broken})


def setup_default_tasks(scheduler: 'ProactiveScheduler',
                        adaptive_monitor=None,
                        gc=None,
                        skill_manager=None,
                        logger=None):
    """Register standard proactive tasks.

    Args:
        scheduler: ProactiveScheduler instance
        adaptive_monitor: AdaptiveResourceMonitor (optional)
        gc: EvolutionGarbageCollector (optional)
        skill_manager: SkillManager (optional)
        logger: Logger (optional)
    """
    if adaptive_monitor:
        scheduler.register("resource_alerts",
                           lambda: _run_resource_check(adaptive_monitor, logger), interval_s=30)
    if gc:
        scheduler.register("periodic_gc",
                           lambda: _run_periodic_gc(gc, logger), interval_s=3600)
    if skill_manager:
        scheduler.register("health_check",
                           lambda: _run_health_check(skill_manager, logger), interval_s=300)
