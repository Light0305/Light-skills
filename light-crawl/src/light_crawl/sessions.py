"""A filesystem-backed single-owner lock for browser profiles.

The lock is intentionally small and boring: one JSON file per profile, a PID,
an owner label, and an expiry. It prevents two agents from launching the same
Chrome profile while still allowing a crashed process's lock to expire.
"""

from __future__ import annotations

import os
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from .state import LightCrawlError
from .utils import ensure_dir, slugify, utc_now, write_json, read_json


class SessionConflict(LightCrawlError):
    """Another owner currently holds the profile lock."""


@dataclass
class SessionLock:
    profile: str
    owner: str
    pid: int
    created_at: str
    expires_at: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile,
            "owner": self.owner,
            "pid": self.pid,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionLock":
        return cls(
            profile=str(data.get("profile", "")),
            owner=str(data.get("owner", "")),
            pid=int(data.get("pid", 0) or 0),
            created_at=str(data.get("created_at", utc_now())),
            expires_at=float(data.get("expires_at", 0) or 0),
            metadata=dict(data.get("metadata", {}) or {}),
        )

    @property
    def expired(self) -> bool:
        return self.expires_at <= time.time()


class SessionBroker:
    def __init__(self, root: Path | str = ".light-crawl/sessions") -> None:
        self.root = Path(root)
        ensure_dir(self.root)

    def lock_path(self, profile: str) -> Path:
        return self.root / f"{slugify(profile, default='profile')}.json"

    def read(self, profile: str) -> SessionLock | None:
        data = read_json(self.lock_path(profile), default=None)
        return SessionLock.from_dict(data) if data else None

    def list(self) -> list[SessionLock]:
        locks: list[SessionLock] = []
        for path in sorted(self.root.glob("*.json")):
            data = read_json(path, default=None)
            if data:
                locks.append(SessionLock.from_dict(data))
        return locks

    def acquire(
        self,
        profile: str,
        owner: str,
        *,
        ttl_seconds: int = 3600,
        metadata: dict[str, Any] | None = None,
        force: bool = False,
    ) -> SessionLock:
        if not owner.strip():
            raise LightCrawlError("Session owner must not be empty.")
        existing = self.read(profile)
        if existing and not existing.expired and existing.owner != owner and not force:
            raise SessionConflict(
                f"Profile '{profile}' is owned by '{existing.owner}' (pid {existing.pid}) "
                f"until {existing.expires_at:.0f}. Release it or wait for expiry."
            )
        lock = SessionLock(
            profile=profile,
            owner=owner,
            pid=os.getpid(),
            created_at=utc_now(),
            expires_at=time.time() + max(60, int(ttl_seconds)),
            metadata=metadata or {},
        )
        write_json(self.lock_path(profile), lock.to_dict())
        return lock

    def release(self, profile: str, owner: str) -> bool:
        existing = self.read(profile)
        if not existing:
            return False
        if existing.owner != owner:
            raise SessionConflict(
                f"Profile '{profile}' is owned by '{existing.owner}', not '{owner}'."
            )
        path = self.lock_path(profile)
        if path.exists():
            path.unlink()
        return True

    def cleanup(self) -> list[str]:
        removed: list[str] = []
        for lock in self.list():
            if lock.expired:
                path = self.lock_path(lock.profile)
                if path.exists():
                    path.unlink()
                    removed.append(lock.profile)
        return removed

    def status(self, profile: str) -> dict[str, Any]:
        lock = self.read(profile)
        if not lock:
            return {"profile": profile, "owned": False, "active": False}
        return {
            "profile": profile,
            "owned": True,
            "active": not lock.expired,
            "stale": lock.expired,
            "owner": lock.owner,
            "pid": lock.pid,
            "created_at": lock.created_at,
            "expires_at": lock.expires_at,
            "metadata": lock.metadata,
        }

    @contextmanager
    def session(
        self,
        profile: str,
        owner: str,
        *,
        ttl_seconds: int = 3600,
        metadata: dict[str, Any] | None = None,
    ) -> Iterator[SessionLock]:
        lock = self.acquire(profile, owner, ttl_seconds=ttl_seconds, metadata=metadata)
        try:
            yield lock
        finally:
            try:
                self.release(profile, owner)
            except SessionConflict:
                pass
