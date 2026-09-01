"""In-memory notification volume monitor.

Tracks how many notifications each app (package) sends in a sliding time window.
Flags **unusual volume** when counts exceed configured thresholds - a common
adware signal even when individual messages look borderline.

This is process-local (in-memory). For production, replace with Redis or a DB.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from functools import lru_cache
from threading import Lock

from ..config import (
    NOTIFICATION_MONITOR_ALERT_COUNT,
    NOTIFICATION_MONITOR_SPAM_ALERT_COUNT,
    NOTIFICATION_MONITOR_WINDOW_SECONDS,
)


@dataclass
class NotificationEvent:
    timestamp: float
    is_spam: bool
    text_preview: str = ""


@dataclass
class PackageStats:
    package: str
    total_in_window: int
    spam_in_window: int
    ham_in_window: int
    rate_per_minute: float
    unusual_volume: bool
    spam_heavy: bool
    recent_events: list[dict] = field(default_factory=list)


class NotificationMonitor:
    """Sliding-window tracker per Android package name."""

    def __init__(
        self,
        window_seconds: int = NOTIFICATION_MONITOR_WINDOW_SECONDS,
        alert_count: int = NOTIFICATION_MONITOR_ALERT_COUNT,
        spam_alert_count: int = NOTIFICATION_MONITOR_SPAM_ALERT_COUNT,
    ) -> None:
        self.window_seconds = window_seconds
        self.alert_count = alert_count
        self.spam_alert_count = spam_alert_count
        self._events: dict[str, deque[NotificationEvent]] = defaultdict(deque)
        self._lock = Lock()

    def _prune(self, package: str, now: float) -> None:
        cutoff = now - self.window_seconds
        q = self._events[package]
        while q and q[0].timestamp < cutoff:
            q.popleft()
        if not q:
            del self._events[package]

    def record(self, package: str, is_spam: bool, text: str = "") -> PackageStats:
        """Log one notification and return updated stats for the package."""
        now = time.time()
        preview = (text or "")[:120]
        with self._lock:
            self._events[package].append(NotificationEvent(now, is_spam, preview))
            self._prune(package, now)
            return self._stats_unlocked(package, now)

    def stats(self, package: str) -> PackageStats:
        """Current window stats without recording a new event."""
        now = time.time()
        with self._lock:
            self._prune(package, now)
            return self._stats_unlocked(package, now)

    def all_alerts(self) -> list[PackageStats]:
        """Packages currently flagged for unusual notification behaviour."""
        now = time.time()
        with self._lock:
            packages = list(self._events.keys())
            results = []
            for pkg in packages:
                self._prune(pkg, now)
                if pkg not in self._events:
                    continue
                s = self._stats_unlocked(pkg, now)
                if s.unusual_volume or s.spam_heavy:
                    results.append(s)
            return sorted(results, key=lambda s: s.total_in_window, reverse=True)

    def _stats_unlocked(self, package: str, now: float) -> PackageStats:
        q = self._events.get(package, deque())
        total = len(q)
        spam = sum(1 for e in q if e.is_spam)
        ham = total - spam
        minutes = max(self.window_seconds / 60.0, 1e-6)
        rate = total / minutes
        unusual = total >= self.alert_count
        spam_heavy = spam >= self.spam_alert_count
        recent = [
            {"timestamp": e.timestamp, "is_spam": e.is_spam, "text_preview": e.text_preview}
            for e in list(q)[-5:]
        ]
        return PackageStats(
            package=package,
            total_in_window=total,
            spam_in_window=spam,
            ham_in_window=ham,
            rate_per_minute=round(rate, 2),
            unusual_volume=unusual,
            spam_heavy=spam_heavy,
            recent_events=recent,
        )


@lru_cache(maxsize=1)
def get_notification_monitor() -> NotificationMonitor:
    return NotificationMonitor()
