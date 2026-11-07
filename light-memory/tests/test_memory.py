"""Behavior tests for scientific revision loops; all inputs are synthetic fixtures."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import memory_store as ms
import memory as cli


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="light-memory-")
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name) / "单篇论文 含空格"
        self.project.mkdir()
        self.report = self.project / "Analysis/AN-0001_测试/analysis-report.md"
        self.report.parent.mkdir(parents=True)
        self.report.write_text("# Synthetic fixture\nF01：评价器把缺失误计为零，当前比较需要重算。\n", encoding="utf-8")
        ms.initialize(self.project, "合成科研项目")

    def source(self):
        return {"kind": "file", "path": self.report.relative_to(self.project).as_posix(), "locator": "F01"}

    def item(self, **changes):
        base = {"kind": "finding", "scope": "analysis:AN-0001", "slot": "F01.evaluator",
                "text": "评价器把缺失误计为零，当前比较需要重算。", "epistemic": "source_reported",
                "sources": [self.source()]}
        base.update(changes)
        return base

    def capture(self, items=None, capture_id="session-1", changes=None, dry=False):
        spec = {"schema_version": "1.0", "capture_id": capture_id, "label": "Synthetic research update",
                "items": items if items is not None else [self.item()], "changes": changes or []}
        return ms.capture(self.project, spec, dry)

    def state(self, at=None):
        return ms.load(self.project, at)

    def packet(self, **kwargs):
        return cli.recall(self.project, self.state(), **kwargs)

    def test_initialization_starts_empty_and_never_overwrites(self):
        self.assertEqual(self.state()["records"], {})
        with self.assertRaises(ValueError):
            ms.initialize(self.project, "Second")
        self.assertFalse((self.project / "Idea").exists())

    def test_capture_keeps_ids_source_fingerprints_and_scope(self):
        out = self.capture()
        row = self.state()["records"]["MEM-0001"]
        self.assertEqual(out["memory_ids"], ["MEM-0001"])
        self.assertEqual(row["scope"], "analysis:AN-0001")
        self.assertEqual(row["sources"][0]["sha256"], ms.file_fingerprint(self.report)["sha256"])
        self.assertEqual(row["epistemic"], "source_reported")

    def test_same_capture_is_idempotent_even_if_source_later_changes(self):
        self.capture()
        self.report.write_text("Changed fixture", encoding="utf-8")
        self.assertTrue(self.capture()["idempotent"])
        self.assertEqual(len(self.state()["events"]), 1)
        self.assertIn("source_drift", self.packet()["needs_review"][0]["reasons"])
        with self.assertRaises(ValueError):
            self.capture([self.item(text="Different input")])

    def test_batch_validation_is_atomic(self):
        with self.assertRaises(ValueError):
            self.capture([self.item(), self.item(epistemic="invented")])
        self.assertEqual(list((self.project / "Memory/events").iterdir()), [])

    def test_dry_capture_never_writes_event_or_views(self):
        out = self.capture(dry=True)
        self.assertTrue(out["dry_run"])
        self.assertEqual(len(self.state()["events"]), 0)
        self.assertFalse((self.project / "Memory/current.md").exists())

    def test_chinese_recall_and_unmatched_query(self):
        self.capture()
        rows = self.packet(query="评价器缺失", compact=True)["items"]
        self.assertEqual(rows[0]["id"], "MEM-0001")
        self.assertEqual(self.packet(query="nevermatchingword")["items"], [])

    def test_memory_id_is_a_searchable_identity(self):
        self.capture()
        self.assertEqual(self.packet(query="MEM-0001")["items"][0]["id"], "MEM-0001")

    def test_query_explains_unmatched_conflicting_dependency(self):
        self.capture()
        self.capture([self.item(text="A competing evaluator diagnosis")], capture_id="conflict")
        self.capture([self.item(kind="next_step", slot="journal.action", text="选刊之后起草正文",
                                depends_on=["MEM-0001"])], capture_id="next")
        packet = self.packet(query="选刊")
        self.assertEqual(packet["items"], [])
        self.assertEqual(packet["conflicts"][0]["ids"], ["MEM-0001", "MEM-0002"])
        parents = {r["id"]: r for r in packet["dependency_context"]}
        self.assertIn("unresolved_conflict", parents["MEM-0001"]["reasons"])
        self.assertEqual(parents["MEM-0001"]["sources"][0]["path"], self.source()["path"])

    def test_query_locates_replacement_without_silently_rebinding(self):
        self.capture()
        self.capture([self.item(kind="next_step", slot="journal.action", text="选刊之后起草正文",
                                depends_on=["MEM-0001"])], capture_id="next")
        self.capture([self.item(text="New diagnosis", supersedes=["MEM-0001"], rationale="Checked new evidence")],
                     capture_id="replace")
        packet = self.packet(query="选刊")
        self.assertEqual(packet["items"], [])
        parents = {r["id"]: r for r in packet["dependency_context"]}
        self.assertEqual(parents["MEM-0001"]["superseded_by"], ["MEM-0003"])
        self.assertIn("MEM-0003", parents)
        self.assertEqual(self.state()["records"]["MEM-0002"]["depends_on"], ["MEM-0001"])

    def test_changed_resolution_evidence_is_reported_without_reopening(self):
        self.capture([self.item(kind="question", text="Is the evaluator repaired?")])
        close = self.project / "Review/closure.md"
        close.parent.mkdir()
        close.write_text("Checked repaired evaluator", encoding="utf-8")
        self.capture([], capture_id="close", changes=[{"id": "MEM-0001", "status": "resolved",
                     "reason": "Checked repair", "sources": [{"kind": "file", "path": "Review/closure.md", "locator": "repair"}]}])
        close.write_text("Closure evidence changed", encoding="utf-8")
        packet = self.packet()
        self.assertEqual(packet["closure_needs_review"][0]["id"], "MEM-0001")
        self.assertEqual(self.state()["records"]["MEM-0001"]["status"], "resolved")
        result = cli.execute(cli.parser().parse_args(["verify", "--project", str(self.project)]))
        self.assertFalse(result["ok"])
        self.assertIn("resolution_source_drift", result["needs_review"][0]["reasons"])

    def test_conflicting_same_scope_is_not_silently_resolved(self):
        self.capture()
        self.capture([self.item(text="Synthetic competing report: evaluator is correct")], capture_id="session-2")
        packet = self.packet()
        self.assertEqual(packet["items"], [])
        self.assertEqual(packet["conflicts"][0]["ids"], ["MEM-0001", "MEM-0002"])
        self.assertEqual(len(packet["needs_review"]), 2)

    def test_different_scopes_preserve_legitimate_differences(self):
        self.capture()
        self.capture([self.item(scope="analysis:AN-0002", text="A different condition is valid")], capture_id="session-2")
        self.assertEqual(self.packet()["conflicts"], [])
        self.assertEqual(len(self.packet()["items"]), 2)

    def test_supersession_retains_history_and_invalidates_downstream(self):
        self.capture()
        self.capture([self.item(kind="decision", slot="followup.action", text="重算之前暂缓比较。",
                                rationale="由 F01 的评价器问题触发。", depends_on=["MEM-0001"])], capture_id="session-2")
        self.capture([self.item(text="错误已修复，需重新读取新批次而不能复用旧比较。",
                                rationale="新的核对取代旧状态。", supersedes=["MEM-0001"])], capture_id="session-3")
        rows = self.state()["records"]
        self.assertEqual(rows["MEM-0001"]["status"], "superseded")
        packet = self.packet()
        self.assertEqual([r["id"] for r in packet["items"]], ["MEM-0003"])
        self.assertIn("dependency_needs_review:MEM-0001", packet["needs_review"][0]["reasons"])
        historical = self.packet(history=True, compact=True)
        self.assertEqual(historical["matched"], 3)

    def test_conflict_is_explicitly_resolved_by_replacement(self):
        self.capture()
        self.capture([self.item(text="Conflicting synthetic view")], capture_id="session-2")
        self.capture([self.item(text="已核对两种说法的范围，采用新的限定结论。", rationale="Scope reviewed in fixture.",
                                supersedes=["MEM-0001", "MEM-0002"])], capture_id="session-3")
        self.assertEqual(self.packet()["conflicts"], [])
        self.assertEqual(self.packet()["items"][0]["id"], "MEM-0003")

    def test_source_drift_propagates_to_dependent_decision(self):
        self.capture()
        conversation = {"kind": "conversation", "locator": "Synthetic analyst note", "excerpt": "重算之后再做选刊。"}
        self.capture([self.item(kind="next_step", scope="project", slot="next.action", text="重算之后再做选刊。",
                                depends_on=["MEM-0001"], sources=[conversation])], capture_id="session-2")
        self.report.write_text("The evaluator premise changed", encoding="utf-8")
        packet = self.packet()
        self.assertEqual(packet["items"], [])
        reasons = {r["id"]: r["reasons"] for r in packet["needs_review"]}
        self.assertIn("source_drift", reasons["MEM-0001"])
        self.assertIn("dependency_needs_review:MEM-0001", reasons["MEM-0002"])

    def test_missing_source_is_not_a_current_fact(self):
        self.capture()
        self.report.unlink()
        self.assertEqual(self.packet()["items"], [])
        self.assertEqual(self.packet()["needs_review"][0]["reasons"], ["source_drift"])

    def test_time_sensitive_web_policy_requires_review_after_expiry(self):
        source = {"kind": "web", "url": "https://example.invalid/policy", "accessed_on": "2026-11-06",
                  "locator": "Synthetic policy", "excerpt": "This fixture is not a real policy."}
        self.capture([self.item(kind="constraint", slot="journal.policy", sources=[source],
                                review_after="2000-01-01T00:00:00+00:00")])
        self.assertIn("review_due", self.packet()["needs_review"][0]["reasons"])

    def test_recorded_time_reconstruction_is_not_overwritten_by_later_decision(self):
        self.capture()
        cutoff = self.state()["events"][0]["recorded_at"]
        self.capture([self.item(text="Revised interpretation", rationale="New review", supersedes=["MEM-0001"])], capture_id="session-2")
        old = self.state(cutoff)
        self.assertEqual(len(old["records"]), 1)
        self.assertEqual(old["records"]["MEM-0001"]["status"], "active")
        self.assertEqual(self.state()["records"]["MEM-0001"]["status"], "superseded")

    def test_question_resolution_needs_evidence_and_preserves_old_text(self):
        self.capture([self.item(kind="question", text="F01 是否影响已选图的分母？")])
        self.capture([], capture_id="close-question", changes=[{"id": "MEM-0001", "status": "resolved",
                     "reason": "按 fixture 核对受影响图的分母。", "sources": [self.source()]}])
        self.assertEqual(self.state()["records"]["MEM-0001"]["status"], "resolved")
        self.assertEqual(self.packet()["items"], [])
        self.assertEqual(len(self.packet(compact=True, history=True)["items"]), 1)

    def test_retraction_is_not_scientific_confirmation(self):
        self.capture()
        self.capture([], capture_id="retract", changes=[{"id":"MEM-0001", "status":"retracted",
                     "reason":"Fixture premise unsupported", "sources":[self.source()]}])
        self.assertEqual(self.state()["records"]["MEM-0001"]["status"], "retracted")

    def test_invalid_cross_scope_and_self_dependency_are_refused(self):
        self.capture()
        with self.assertRaises(ValueError):
            self.capture([self.item(scope="other", supersedes=["MEM-0001"], rationale="Invalid cross-scope update")], capture_id="bad1")
        with self.assertRaises(ValueError):
            self.capture([self.item(supersedes=["MEM-0001"], depends_on=["MEM-0001"], rationale="Invalid dependency")], capture_id="bad2")
        self.assertEqual(len(self.state()["events"]), 1)

    def test_budget_never_returns_partial_memory(self):
        self.capture()
        out = self.packet(max_chars=256)
        self.assertEqual(out["items"], [])
        self.assertEqual(out["omitted_by_budget"], 1)
        self.assertLessEqual(out["content_characters"], 256)

    def test_history_tampering_and_missing_event_stop_new_capture(self):
        self.capture()
        path = self.project / "Memory/events/EVT-000001.json"
        event = ms.read_json(path)
        event["entries"][0]["text"] = "Unexpected tampering"
        path.write_text(json.dumps(event), encoding="utf-8")
        with self.assertRaises(ValueError):
            self.capture(capture_id="session-2")
        path.rename(path.with_name("EVT-000002.json"))
        with self.assertRaises(ValueError):
            self.state()

    def test_locked_writer_never_removes_other_lock(self):
        lock = self.project / "Memory/.write.lock"
        lock.write_text("another writer", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            self.capture()
        self.assertEqual(lock.read_text(), "another writer")

    def test_projection_is_rebuildable_and_unmanaged_notes_survive(self):
        self.capture()
        notes = self.project / "Memory/notes"
        notes.mkdir()
        note = notes / "manual.md"
        note.write_text("Human note", encoding="utf-8")
        cli.render(self.project)
        view = self.project / "Memory/current.md"
        first = view.read_bytes()
        view.unlink()
        cli.render(self.project)
        self.assertEqual(first, view.read_bytes())
        self.assertEqual(note.read_text(), "Human note")

    def test_unmanaged_existing_view_is_not_overwritten(self):
        view = self.project / "Memory/current.md"
        view.write_text("Do not overwrite authored context", encoding="utf-8")
        with self.assertRaises(ValueError):
            cli.render(self.project)
        self.assertEqual(view.read_text(), "Do not overwrite authored context")

    def test_relative_sources_work_after_project_copy(self):
        self.capture()
        target = Path(self.tmp.name) / "relocated project"
        shutil.copytree(self.project, target)
        checks, _ = ms.assess(target, ms.load(target))
        self.assertTrue(checks["MEM-0001"]["usable"])

    def test_project_binding_rejects_wrong_registry(self):
        other = Path(self.tmp.name) / "registered"
        other.mkdir()
        reg = other / "project.json"
        reg.write_text(json.dumps({"schema_version":"1.0", "layout_version":"1.0", "project_id":"P1"}))
        ms.initialize(other, "Bound")
        reg.write_text(json.dumps({"schema_version":"1.0", "layout_version":"1.0", "project_id":"P2"}))
        with self.assertRaises(ValueError):
            ms.load(other)

    def test_unsafe_sources_self_citation_and_wrong_excerpt_are_refused(self):
        for source in ({"kind":"file", "path":"../outside", "locator":"x"},
                       {"kind":"file", "path":"Memory/memory.json", "locator":"x"},
                       {"kind":"file", "path":"memory/memory.json", "locator":"case-insensitive self citation"},
                       {**self.source(), "excerpt":"not in source"}):
            with self.assertRaises(ValueError):
                self.capture([self.item(sources=[source])])
        self.assertEqual(len(self.state()["events"]), 0)

    def test_standalone_skill_copy_has_no_sibling_or_research_dependency(self):
        copied = Path(self.tmp.name) / "isolated-install/light-memory"
        for folder in ("scripts", "references", "assets", "agents"):
            shutil.copytree(ROOT / folder, copied / folder, ignore=shutil.ignore_patterns("__pycache__"))
        other = Path(self.tmp.name) / "isolated research"
        other.mkdir()
        tool = copied / "scripts/memory.py"
        for command in (("init", "--name", "Standalone fixture"), ("context",)):
            result = subprocess.run([sys.executable, "-X", "utf8", str(tool), *command, "--project", str(other)],
                                    capture_output=True, text=True, encoding="utf-8", timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(json.loads(result.stdout)["ok"])

    def test_native_design_analysis_review_outputs_remain_authoritative(self):
        pack = ROOT.parent
        idea = self.project / "Idea/IDEA-0001_主题"
        idea.mkdir(parents=True)
        shutil.copy2(pack / "light-idea/templates/ideas.example.json", idea / "ideas.json")
        design = self.project / "Design/PROT-0001_方案/v01"
        analysis = self.project / "Analysis/AN-0002_原生草稿"
        raw = self.project / "raw.csv"
        raw.write_text("unit,value\n1,2\n", encoding="utf-8")
        review = self.project / "Review/REV-0001_草稿/packet"
        commands = [
            [str(pack / "light-design/scripts/design_bridge.py"), "ingest", "--ideas", str(idea), "--idea-id", "I01", "--out", str(design)],
            [str(pack / "light-analysis/scripts/analysis_bridge.py"), "ingest", "--input", str(raw), "--out", str(analysis)],
            [str(pack / "light-review/scripts/review_packet.py"), "freeze", "--out", str(review), "--file", "context=" + str(design / "plan.md")],
        ]
        for command in commands:
            result = subprocess.run([sys.executable, "-X", "utf8", *command], capture_output=True,
                                    text=True, encoding="utf-8", timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        sources = [design / "design.json", analysis / "analysis.json", review / "packet.json"]
        before = {p: p.read_bytes() for p in sources}
        items = [self.item(kind="fact", scope="native:" + str(i), slot="workspace.initialized",
                           text="合成测试中已创建原生工作区，尚未完成科学内容或审查。",
                           sources=[{"kind":"file", "path":p.relative_to(self.project).as_posix(), "locator":"原生初始化身份与草稿记录"}])
                 for i, p in enumerate(sources)]
        self.capture(items)
        self.assertEqual(len(self.packet()["items"]), 3)
        self.assertEqual(before, {p: p.read_bytes() for p in sources})
        draft = ms.read_json(sources[1])
        draft["synthetic_revision_note"] = "Underlying draft changed; memory needs review"
        sources[1].write_text(json.dumps(draft), encoding="utf-8")
        packet = self.packet()
        self.assertEqual(len(packet["items"]), 2)
        self.assertEqual(packet["needs_review"][0]["id"], "MEM-0002")

    def test_cli_read_commands_do_not_write_project(self):
        self.capture()
        before = {p.relative_to(self.project): p.read_bytes() for p in self.project.rglob("*") if p.is_file()}
        for command in (("context", "--query", "评价器"), ("search", "--history"),
                        ("show", "--id", "MEM-0001"), ("timeline", "--id", "MEM-0001"), ("verify",)):
            result = subprocess.run([sys.executable, "-X", "utf8", str(ROOT/"scripts/memory.py"), *command,
                                     "--project", str(self.project)], capture_output=True, text=True, encoding="utf-8", timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            self.assertTrue(json.loads(result.stdout)["ok"])
        after = {p.relative_to(self.project): p.read_bytes() for p in self.project.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_cli_commit_survives_projection_failure_and_retry(self):
        view = self.project / "Memory/current.md"
        view.write_text("Authored content", encoding="utf-8")
        spec = self.project / "capture.json"
        spec.write_text(json.dumps({"schema_version":"1.0","capture_id":"cli1","label":"Fixture",
                                    "items":[self.item()],"changes":[]}), encoding="utf-8")
        args = cli.parser().parse_args(["capture","--project",str(self.project),"--spec",str(spec)])
        first = cli.execute(args)
        self.assertIn("view_warning", first)
        self.assertEqual(first["event_id"], "EVT-000001")
        self.assertTrue(cli.execute(args)["idempotent"])
        self.assertEqual(len(self.state()["events"]), 1)

    def test_strict_json_and_cross_project_isolation(self):
        path = Path(self.tmp.name) / "malformed.json"
        for content in ('{"a":1,"a":2}', '{"v":NaN}', '{"v":1e999}'):
            path.write_text(content)
            with self.assertRaises(ValueError):
                ms.read_json(path)
        self.capture()
        other = Path(self.tmp.name) / "another paper"
        other.mkdir()
        ms.initialize(other, "Another paper")
        self.assertEqual(cli.recall(other, ms.load(other))["items"], [])

    def test_directory_manager_leaves_native_memory_overview_owned_by_memory(self):
        spec = importlib.util.spec_from_file_location("project_manager", ROOT.parent/"project-layout/scripts/project.py")
        manager = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(manager)
        target = Path(self.tmp.name)/"managed research"
        def call(*args):
            return manager.run(manager.parser().parse_args([*args,"--root",str(target)]))
        call("init","--name","Managed fixture")
        workspace = call("add","--kind","memory","--title","Project memory")["workspace"]
        self.assertEqual(list(Path(workspace).iterdir()), [])
        ms.initialize(target,"Managed fixture")
        cli.render(target)
        overview = target/"Memory/00-Memory总览.md"
        before = overview.read_bytes()
        call("refresh")
        self.assertEqual(before, overview.read_bytes())
        self.assertTrue(call("check")["ok"])


if __name__ == "__main__":
    unittest.main()
