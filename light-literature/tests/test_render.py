from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from litsearch.demo import run_demo
from litsearch.render import verify_run


class RenderTests(unittest.TestCase):
    def test_offline_demo_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "demo"
            result = run_demo(run_dir, offline=True, lang="both")
            self.assertTrue(result["verified"])
            for name in ("report.en.md", "report.zh.md", "report.bilingual.md", "papers.jsonl", "screening.csv"):
                self.assertTrue((run_dir / name).exists(), name)
            en = (run_dir / "report.en.md").read_text(encoding="utf-8")
            zh = (run_dir / "report.zh.md").read_text(encoding="utf-8")
            self.assertIn("Literature Search Report", en)
            self.assertIn("文献检索报告", zh)
            self.assertNotIn("[[p_", en)
            self.assertNotIn("[zh missing]", zh)
            self.assertEqual(verify_run(run_dir), [])

    def test_exports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "demo"
            run_demo(run_dir, offline=True, lang="both")
            self.assertTrue((run_dir / "exports" / "references.bib").exists())
            self.assertTrue((run_dir / "exports" / "papers.csv").exists())


if __name__ == "__main__":
    unittest.main()
