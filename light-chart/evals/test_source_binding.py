"""Synthetic file-drift and real export checks; not scientific or independent review."""
from pathlib import Path
from unittest import mock
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/light-chart/scripts"
sys.path.insert(0, str(SCRIPTS))
from source_binding import capture_sources, verify_sources, verify_report
from publication import save_figure, write_json
from review_tools import record_review, bind_exports, verify_exports
from editorial import figure_style
from review_cycle import stage_review, verify_stage


class SourceBindings(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="chart sources 中文 ")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.data = self.root / "observations.csv"
        self.data.write_text("time,value\n0,1\n1,2\n", encoding="utf-8")

    def test_file_capture_is_named_absolute_and_matches_actual_bytes(self):
        result = capture_sources({"observations": self.data})
        self.assertEqual(Path(result["observations"]["path"]), self.data)
        self.assertEqual(result["observations"]["sha256"], hashlib.sha256(self.data.read_bytes()).hexdigest())
        self.assertEqual(verify_sources({"source_manifest": result}), [])

    def test_file_source_data_is_included_once_and_memory_data_is_not_claimed_as_a_file(self):
        result = capture_sources({"raw": self.data}, source_data=str(self.data))
        self.assertEqual(list(result), ["raw"])
        self.assertEqual(capture_sources(source_data=pd.DataFrame({"x": [1]})), {})

    def test_path_and_sequence_inputs_are_supported_without_silent_name_collision(self):
        self.assertIn(self.data.name, capture_sources(self.data))
        self.assertIn(self.data.name, capture_sources([self.data]))
        other = self.root / "other"; other.mkdir()
        copy = other / self.data.name; copy.write_bytes(self.data.read_bytes())
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            capture_sources([self.data, copy])
        self.assertEqual(len(capture_sources({"first": self.data, "second": copy})), 2)

    def test_modified_missing_or_unreadable_sources_cannot_be_revalidated(self):
        report = {"source_manifest": capture_sources(source_data=self.data)}
        self.data.write_text("changed", encoding="utf-8")
        self.assertTrue(verify_sources(report))
        self.data.unlink()
        self.assertTrue(verify_sources(report))

    def test_legacy_pathless_sources_remain_readable_but_not_recheckable(self):
        report = {"source_manifest": {"raw": {"sha256": "legacy", "bytes": 20}}}
        self.assertIn("no recheckable", verify_sources(report)[0])
        self.assertEqual(verify_sources({}), [])

    def test_relative_source_path_does_not_depend_on_callers_working_directory(self):
        self.assertIn("not absolute", verify_sources({"source_manifest": {
            "raw": {"path": self.data.name, "sha256": "unknown"}}})[0])

    def test_bad_manifest_has_explicit_errors(self):
        for manifest in ([], {"raw": None}, {"raw": {}}):
            with self.subTest(manifest=manifest):
                self.assertTrue(verify_sources({"source_manifest": manifest}))
        with self.assertRaises((FileNotFoundError, ValueError)):
            capture_sources({"missing": self.root / "absent.csv"})


class ExportBindings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temporary = tempfile.TemporaryDirectory(prefix="chart binding seed ")
        cls.addClassCleanup(temporary.cleanup)
        cls.seed = Path(temporary.name)
        for name, text in {"data.csv": "time,value\n0,1\n1,2\n",
                           "plot.py": "# Synthetic plotting code fixture\n",
                           "task.json": '{"synthetic_validation": true}',
                           "caption.md": "Synthetic response; no experimental claim."}.items():
            (cls.seed / name).write_text(text, encoding="utf-8")
        with figure_style():
            fig, ax = plt.subplots(layout="constrained")
            ax.plot([0, 1], [1, 2], marker="o")
            ax.set(xlabel="Time (h)", ylabel="Synthetic response (a.u.)")
            cls.report = save_figure(fig, cls.seed / "figure", size_mm=(125, 90),
                source_data=cls.seed / "data.csv",
                source_files={name: cls.seed / name for name in ("plot.py", "task.json", "caption.md")})
            plt.close(fig)
        if cls.report["automated_status"] in {"FAIL", "NOT_AUDITABLE"}:
            raise AssertionError(cls.report)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="chart binding case ")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "work"
        shutil.copytree(self.seed, self.root)
        self.report = json.loads((self.root / "figure.qa.json").read_text(encoding="utf-8"))
        for group in ("review_artifacts", "source_manifest"):
            for entry in self.report[group].values():
                entry["path"] = str(self.root / Path(entry["path"]).name)
        self.qa = self.root / "figure.qa.json"
        write_json(self.qa, self.report)

    def review(self):
        return record_review(self.qa,
            inspected=[entry["path"] for name, entry in self.report["review_artifacts"].items()
                       if name.endswith(".png")],
            observations=["Protocol fixture only; no visual or scientific verdict."])

    def test_real_exports_and_sources_are_bound_and_self_review_scope_is_explicit(self):
        self.assertIn("figure.svg", self.report["review_artifacts"])
        self.assertEqual(verify_report(self.report)["status"], "recorded_files_match")
        reviewed = self.review()
        self.assertEqual(reviewed["visual_review"]["binding_scope"], "exports_and_recorded_sources")
        self.assertEqual(len(reviewed["visual_review"]["source_hashes"]), 4)

    def test_source_changes_refuse_reuse_even_when_every_export_is_unchanged(self):
        for name in ("data.csv", "plot.py", "task.json", "caption.md"):
            with self.subTest(name=name):
                path = self.root / name; before = path.read_bytes()
                path.write_bytes(before + b"\nchanged")
                self.assertEqual(verify_exports(self.report), [])
                with self.assertRaisesRegex(ValueError, "Source changed"):
                    self.review()
                path.write_bytes(before)

    def test_changed_svg_is_refused_in_addition_to_pdf_and_png(self):
        (self.root / "figure.svg").write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "figure.svg changed"):
            self.review()

    def test_legacy_export_only_self_review_does_not_claim_source_verification(self):
        self.report.pop("source_manifest"); write_json(self.qa, self.report)
        result = self.review()
        self.assertEqual(result["visual_review"]["binding_scope"], "exports_only")
        self.assertEqual(result["visual_review"]["source_hashes"], {})

    def test_read_only_cli_detects_drift_and_does_not_refresh_qa(self):
        before = self.qa.read_bytes()
        (self.root / "data.csv").write_text("changed", encoding="utf-8")
        result = subprocess.run([sys.executable, "-X", "utf8", str(SCRIPTS / "source_binding.py"), str(self.qa)],
            capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(json.loads(result.stdout)["scope"], "exports_and_recorded_sources")
        self.assertEqual(self.qa.read_bytes(), before)

    def test_stage_rejects_qa_for_a_different_draft_before_creating_a_cycle(self):
        from PIL import Image
        other = self.root / "other.png"; Image.new("RGB", (50, 50), "navy").save(other)
        work = self.root / "review"
        with self.assertRaisesRegex(ValueError, "not bound"):
            stage_review(work, other, qa=self.qa, briefing="Synthetic protocol test", size_mm=(125, 90))
        self.assertFalse(work.exists())

    def test_stage_refuses_stale_sources_but_keeps_old_staged_packets_readable(self):
        work = self.root / "review"
        stage_review(work, self.root / "figure.png", pdf=self.root / "figure.pdf",
                     qa=self.qa, briefing="Synthetic protocol test", size_mm=(125, 90))
        (self.root / "data.csv").write_text("changed", encoding="utf-8")
        self.assertEqual(verify_stage(work, 0)["iteration"], 0)
        with self.assertRaisesRegex(ValueError, "Source changed"):
            stage_review(self.root / "new-review", self.root / "figure.png", qa=self.qa,
                         briefing="Synthetic protocol test", size_mm=(125, 90))

    def test_sources_changed_during_export_leave_failed_report_with_original_binding(self):
        import export_figure
        original = export_figure.export_figure
        code = self.root / "plot.py"
        def change_during_export(*args, **kwargs):
            paths = original(*args, **kwargs)
            code.write_text("# changed during export\n", encoding="utf-8")
            return paths
        with figure_style(), mock.patch.object(export_figure, "export_figure", side_effect=change_during_export):
            fig, ax = plt.subplots(layout="constrained"); ax.plot([0, 1], [1, 2])
            report = save_figure(fig, self.root / "concurrent", size_mm=(125, 90), source_files={"code": code})
            plt.close(fig)
        self.assertEqual(report["automated_status"], "FAIL")
        self.assertTrue(verify_sources(report))

    def test_native_r_records_paths_and_detects_changed_code_in_shared_checker(self):
        from r_runtime import run_r
        script = self.root / "native.R"
        helper = (SCRIPTS / "publication.R").as_posix()
        script.write_text(f'''source({json.dumps(helper)},encoding="UTF-8")
library(ggplot2)
d<-read.csv("data.csv")
p<-ggplot(d,aes(time,value))+geom_line()+geom_point()+labs(x="Time (h)",y="Synthetic response (a.u.)")+theme_light_chart()
save_figure_r(p,"native",width_mm=125,height_mm=90,review_plots=list(response=p),
              source_files=c(raw="data.csv",code="native.R"))
''', encoding="utf-8")
        result = run_r(script, cwd=self.root, timeout=90)
        self.assertEqual(result["returncode"], 0, result)
        report = json.loads((self.root / "native.qa.json").read_text(encoding="utf-8"))
        self.assertEqual(verify_report(report)["errors"], [])
        self.assertIn("native.svg", report["review_artifacts"])
        script.write_text("# changed\n", encoding="utf-8")
        self.assertTrue(verify_sources(report))

    def test_native_r_deleted_source_during_drawing_leaves_failed_qa(self):
        from r_runtime import run_r
        script = self.root / "delete-during-export.R"
        helper = (SCRIPTS / "publication.R").as_posix()
        script.write_text(f'''source({json.dumps(helper)},encoding="UTF-8")
library(ggplot2)
d<-read.csv("data.csv")
p<-ggplot(d,aes(time,value))+geom_line()+theme_light_chart()
drawer<-function(object) {{print(object);unlink("data.csv")}}
save_figure_r(p,"deleted",width_mm=125,height_mm=90,draw=drawer,
              source_files=c(raw="data.csv"))
''', encoding="utf-8")
        result = run_r(script, cwd=self.root, timeout=90)
        self.assertNotEqual(result["returncode"], 0, result)
        report = json.loads((self.root / "deleted.qa.json").read_text(encoding="utf-8"))
        self.assertEqual(report["automated_status"], "FAIL")
        self.assertTrue(verify_sources(report))

    def test_native_r_code_revision_does_not_become_a_data_change(self):
        from r_runtime import run_r
        from review_tools import compare_revisions
        script = self.root / "r-revision.R"
        helper = (SCRIPTS / "publication.R").as_posix()
        script.write_text(f'''source({json.dumps(helper)},encoding="UTF-8")
library(ggplot2)
d<-read.csv("data.csv")
p<-ggplot(d,aes(time,value))+geom_line()+theme_light_chart()
writeLines("Version 1","drawing-code.txt")
save_figure_r(p,"r-before",width_mm=125,height_mm=90,review_plots=list(response=p),
              source_files=c(raw="data.csv",code="drawing-code.txt"),data_sources="raw")
writeLines("Version 2: local style edit","drawing-code.txt")
save_figure_r(p,"r-after",width_mm=125,height_mm=90,review_plots=list(response=p),
              source_files=c(raw="data.csv",code="drawing-code.txt"),data_sources="raw")
''', encoding="utf-8")
        result = run_r(script, cwd=self.root, timeout=90)
        self.assertEqual(result["returncode"], 0, result)
        before = json.loads((self.root / "r-before.qa.json").read_text(encoding="utf-8"))
        after = json.loads((self.root / "r-after.qa.json").read_text(encoding="utf-8"))
        self.assertNotEqual(before["source_manifest"]["code"]["sha256"], after["source_manifest"]["code"]["sha256"])
        self.assertEqual(before["source_data_sha256"], after["source_data_sha256"])
        self.assertEqual(compare_revisions(before, after)["status"], "no_evidence_regression")
        self.assertTrue(verify_sources(before))
        self.assertEqual(verify_sources(after), [])


if __name__ == "__main__":
    unittest.main()
