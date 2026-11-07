from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from light_crawl.cli import main


class CliTests(unittest.TestCase):
    def test_demo_creates_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "demo"
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = main(["demo", "--out", str(out), "--force"])
            self.assertEqual(code, 0)
            self.assertTrue((out / "reports" / "report.md").exists())
            report = (out / "reports" / "report.md").read_text(encoding="utf-8")
            self.assertIn("Not verified", report)
            self.assertIn("L0_STATIC", report)

    def test_new_case_and_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cases = Path(tmp) / "cases"
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = main(
                    [
                        "new-case",
                        "cli-case",
                        "--target",
                        "https://example.com",
                        "--authorized",
                        "--case-root",
                        str(cases),
                    ]
                )
            self.assertEqual(code, 0)
            self.assertTrue((cases / "cli-case" / "case.json").exists())
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = main(["status", "cli-case", "--case-root", str(cases)])
            self.assertEqual(code, 0)
            self.assertIn("INTAKE", stdout.getvalue())

    def test_advance_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cases = Path(tmp) / "cases"
            with redirect_stdout(io.StringIO()):
                main(
                    [
                        "new-case",
                        "advance-case",
                        "--target",
                        "https://example.com",
                        "--authorized",
                        "--case-root",
                        str(cases),
                    ]
                )
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = main(
                    [
                        "advance",
                        "advance-case",
                        "PROBED",
                        "--note",
                        "unit test",
                        "--case-root",
                        str(cases),
                    ]
                )
            self.assertEqual(code, 0)
            self.assertIn("PROBED", stdout.getvalue())

    def test_learn_without_code_returns_2(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cases = Path(tmp) / "cases"
            with redirect_stdout(io.StringIO()):
                main(
                    [
                        "new-case",
                        "empty-case",
                        "--target",
                        "https://example.com",
                        "--authorized",
                        "--case-root",
                        str(cases),
                    ]
                )
            stderr = io.StringIO()
            with redirect_stderr(stderr), redirect_stdout(io.StringIO()):
                code = main(
                    [
                        "learn",
                        str(cases / "empty-case"),
                        "--sites-root",
                        str(Path(tmp) / "sites"),
                    ]
                )
            self.assertEqual(code, 2)
            self.assertIn("learn requires a VERIFIED case", stderr.getvalue())

    def test_session_acquire_status_release(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "locks")
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = main(["session", "acquire", "unit-profile", "--owner", "case-a", "--root", root, "--json"])
            self.assertEqual(code, 0)
            self.assertIn('"owner": "case-a"', stdout.getvalue())

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = main(["session", "status", "unit-profile", "--root", root, "--json"])
            self.assertEqual(code, 0)
            self.assertIn('"owned": true', stdout.getvalue())

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = main(["session", "release", "unit-profile", "--owner", "case-a", "--root", root, "--json"])
            self.assertEqual(code, 0)
            self.assertIn('"released": true', stdout.getvalue())

    def test_site_list_and_show(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = main(["site", "list", "--json"])
        self.assertEqual(code, 0)
        data = json.loads(stdout.getvalue())
        domains = {item["domain"] for item in data}
        self.assertIn("books.toscrape.com", domains)
        self.assertIn("api.github.com", domains)

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = main(["site", "show", "examples/site-packs/books", "--json"])
        self.assertEqual(code, 0)
        info = json.loads(stdout.getvalue())
        self.assertEqual(info["expected_items"], 60)

    def test_benchmark_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = main(["benchmark", "--out", str(Path(tmp) / "out")])
            self.assertEqual(code, 0)
            self.assertIn("5/5", stdout.getvalue())

    def test_adapters_runs(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = main(["adapters"])
        self.assertEqual(code, 0)
        self.assertIn("scrapling", stdout.getvalue())
        self.assertIn("js_reverse", stdout.getvalue())
        self.assertIn("rea", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
