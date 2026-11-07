from __future__ import annotations

import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from light_crawl.sessions import SessionBroker, SessionConflict
from light_crawl.utils import write_json


class SessionBrokerTests(unittest.TestCase):
    def test_acquire_conflict_and_release(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            broker = SessionBroker(Path(tmp))
            lock = broker.acquire("js-reverse-default", "case-a", ttl_seconds=120)
            self.assertEqual(lock.owner, "case-a")
            self.assertFalse(lock.expired)

            with self.assertRaises(SessionConflict):
                broker.acquire("js-reverse-default", "case-b", ttl_seconds=120)

            same = broker.acquire("js-reverse-default", "case-a", ttl_seconds=120)
            self.assertEqual(same.owner, "case-a")

            with self.assertRaises(SessionConflict):
                broker.release("js-reverse-default", "case-b")

            self.assertTrue(broker.release("js-reverse-default", "case-a"))
            self.assertFalse(broker.status("js-reverse-default")["owned"])

    def test_context_manager_releases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            broker = SessionBroker(Path(tmp))
            with broker.session("scrapling-stealth", "case-a", ttl_seconds=120):
                self.assertTrue(broker.status("scrapling-stealth")["active"])
            self.assertFalse(broker.status("scrapling-stealth")["owned"])

    def test_cleanup_removes_expired_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            broker = SessionBroker(Path(tmp))
            path = broker.lock_path("chrome-debug")
            write_json(
                path,
                {
                    "profile": "chrome-debug",
                    "owner": "dead-process",
                    "pid": 999999,
                    "created_at": "2026-01-01T00:00:00Z",
                    "expires_at": time.time() - 10,
                    "metadata": {},
                },
            )
            self.assertTrue(broker.status("chrome-debug")["stale"])
            removed = broker.cleanup()
            self.assertEqual(removed, ["chrome-debug"])
            self.assertFalse(broker.status("chrome-debug")["owned"])

    def test_force_takes_over(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            broker = SessionBroker(Path(tmp))
            broker.acquire("p", "a", ttl_seconds=120)
            lock = broker.acquire("p", "b", ttl_seconds=120, force=True)
            self.assertEqual(lock.owner, "b")


if __name__ == "__main__":
    unittest.main()
