from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from light_crawl.site import check_site_pack, read_site_pack_info


class SiteCheckTests(unittest.TestCase):
    def _pack(self, root: Path, last_verified: str = "2020-01-01T00:00:00Z") -> Path:
        pack = root / "pack"
        pack.mkdir()
        (pack / "site.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "version": 3,
                    "last_verified_at": last_verified,
                    "domain": "local",
                    "lane": "L0_STATIC",
                    "delivery": "single",
                    "run": {"expected_items": 1},
                }
            ),
            encoding="utf-8",
        )
        (pack / "verify.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
        return pack

    def test_check_updates_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pack = self._pack(Path(tmp))
            result = check_site_pack(pack, write=True)
            self.assertTrue(result["passed"])
            self.assertTrue(result["wrote_timestamp"])
            data = json.loads((pack / "site.json").read_text(encoding="utf-8"))
            self.assertNotEqual(data["last_verified_at"], "2020-01-01T00:00:00Z")
            info = read_site_pack_info(pack, stale_days=30)
            self.assertFalse(info.stale)
            self.assertEqual(info.version, 3)

    def test_old_timestamp_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pack = self._pack(Path(tmp), last_verified="2020-01-01T00:00:00Z")
            info = read_site_pack_info(pack, stale_days=30)
            self.assertTrue(info.stale)
            self.assertGreater(info.age_days or 0, 30)

    def test_failing_verifier_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pack = self._pack(Path(tmp))
            (pack / "verify.py").write_text("raise SystemExit(2)\n", encoding="utf-8")
            result = check_site_pack(pack, write=True)
            self.assertFalse(result["passed"])
            self.assertFalse(result["wrote_timestamp"])


if __name__ == "__main__":
    unittest.main()
