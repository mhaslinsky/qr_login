"""Rate limiting for the public login endpoint."""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class RateLimitEntry:
    count: int = 0
    window_start: float = field(default_factory=time.time)


@dataclass
class CooldownEntry:
    last_notification: float = 0


class RateLimiter:
    def __init__(
        self,
        max_per_ip: int,
        ip_window: int,
        max_global: int,
        global_window: int,
        notification_cooldown: int,
    ):
        self.max_per_ip = max_per_ip
        self.ip_window = ip_window
        self.max_global = max_global
        self.global_window = global_window
        self.notification_cooldown = notification_cooldown

        self._ip_limits: Dict[str, RateLimitEntry] = defaultdict(RateLimitEntry)
        self._global_limit = RateLimitEntry()
        self._cooldowns: Dict[str, CooldownEntry] = defaultdict(CooldownEntry)

    def _cleanup_expired(self, now: float) -> None:
        expired_ips = [
            ip
            for ip, entry in self._ip_limits.items()
            if now - entry.window_start > self.ip_window
        ]
        for ip in expired_ips:
            del self._ip_limits[ip]

        if now - self._global_limit.window_start > self.global_window:
            self._global_limit = RateLimitEntry()

        expired_cooldowns = [
            key
            for key, entry in self._cooldowns.items()
            if now - entry.last_notification > self.notification_cooldown
        ]
        for key in expired_cooldowns:
            del self._cooldowns[key]

    def check_ip_limit(self, ip: str) -> bool:
        now = time.time()
        self._cleanup_expired(now)

        entry = self._ip_limits[ip]
        if now - entry.window_start > self.ip_window:
            entry.count = 0
            entry.window_start = now

        if entry.count >= self.max_per_ip:
            return False

        entry.count += 1
        return True

    def check_global_limit(self) -> bool:
        now = time.time()
        self._cleanup_expired(now)

        if now - self._global_limit.window_start > self.global_window:
            self._global_limit.count = 0
            self._global_limit.window_start = now

        if self._global_limit.count >= self.max_global:
            return False

        self._global_limit.count += 1
        return True

    def check_notification_cooldown(self, key: str) -> bool:
        now = time.time()
        self._cleanup_expired(now)

        entry = self._cooldowns[key]
        if now - entry.last_notification < self.notification_cooldown:
            return False

        entry.last_notification = now
        return True

    def get_ip_remaining(self, ip: str) -> int:
        now = time.time()
        self._cleanup_expired(now)
        entry = self._ip_limits.get(ip)
        if not entry or now - entry.window_start > self.ip_window:
            return self.max_per_ip
        return max(0, self.max_per_ip - entry.count)

    def get_global_remaining(self) -> int:
        now = time.time()
        self._cleanup_expired(now)
        if now - self._global_limit.window_start > self.global_window:
            return self.max_global
        return max(0, self.max_global - self._global_limit.count)

    def get_cooldown_remaining(self, key: str) -> int:
        now = time.time()
        self._cleanup_expired(now)
        entry = self._cooldowns.get(key)
        if not entry:
            return 0
        remaining = self.notification_cooldown - (now - entry.last_notification)
        return max(0, int(remaining))