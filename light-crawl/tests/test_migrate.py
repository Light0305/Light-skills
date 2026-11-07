from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from light_crawl.migrate import migrate_site_pack


class MigrateTests(unittest.TestCase):
    def _pack(self, root: Path) -> Path:
        pack = root / "pack"
        (pack / "spider").mkdir(parents=True)
        (pack / "fixtures").mkdir()
        (pack / "spider" / "spider.py").write_text("print('ok')\n", encoding="utf-8")
        (pack / "spider" / "site.json").write_text("{}", encoding="utf-8")
        (pack / "verify.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
        (pack / "site.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "domain": "local",
                    "lane": "L0_STATIC",
                    "delivery": "single",
                }
            ),
            encoding="utf-8",
        )
        return pack

    def test_dry_run_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pack = self._pack(Path(tmp))
            result = migrate_site_pack(pack, write=False)
            self.assertTrue(result["changed"])
            self.assertFalse(result["wrote"])
            data = json.loads((pack / "site.json").read_text(encoding="utf-8"))
            self.assertEqual(data["schema_version"], 1)

    def test_write_adds_v2_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pack = self._pack(Path(tmp))
            result = migrate_site_pack(pack, write=True)
            self.assertTrue(result["wrote"])
            data = json.loads((pack / "site.json").read_text(encoding="utf-8"))
            self.assertEqual(data["schema_version"], 2)
            self.assertEqual(data["version"], 1)
            self.assertIn("last_verified_at", data)
            self.assertIn("spider", data["entrypoints"])
            self.assertTrue(data["policy"]["robots_txt_obey"])
            self.assertEqual(data["migration"]["from"], 1)

    def test_current_schema_is_noop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pack = self._pack(Path(tmp))
            migrate_site_pack(pack, write=True)
            result = migrate_site_pack(pack, write=True)
            self.assertFalse(result["changed"])
            self.assertFalse(result["wrote"])


if __name__ == "__main__":
    unittest.main()
