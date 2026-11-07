"""Filesystem behavior and native-initializer compatibility, using temporary fixtures."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

LAYOUT = Path(__file__).resolve().parents[1]
PACK = LAYOUT.parent
spec = importlib.util.spec_from_file_location("project_layout", LAYOUT / "scripts/project.py")
project = importlib.util.module_from_spec(spec)
spec.loader.exec_module(project)


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="light-layout-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "论文项目 含空格"

    def call(self, *args):
        return project.run(project.parser().parse_args([*args, "--root", str(self.root)]))

    def init(self):
        return self.call("init", "--name", "单篇论文及关联成果")

    def add(self, kind, title="测试任务", upstream=None):
        args = ["add", "--kind", kind, "--title", title]
        if upstream:
            args += ["--upstream", upstream]
        return self.call(*args)

    def native(self, skill, script, *args):
        result = subprocess.run([sys.executable, "-X", "utf8", str(PACK / skill / "scripts" / script), *map(str, args)],
                                capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_init_and_dry_run_do_not_create_unused_stages(self):
        self.call("init", "--name", "预览", "--dry-run")
        self.assertFalse(self.root.exists())
        self.init()
        self.assertEqual({p.name for p in self.root.iterdir()}, {"README.md", "project.json"})
        before = (self.root / "project.json").read_bytes()
        self.call("add", "--kind", "idea", "--title", "预览", "--dry-run")
        self.assertEqual(before, (self.root / "project.json").read_bytes())
        self.assertFalse((self.root / "Idea").exists())

    def test_empty_workspace_and_shared_figure_sequence(self):
        self.init()
        for kind, key in (("figure-data", "FIG-0001"), ("figure-methods", "FIG-0002"), ("figure-mechanisms", "FIG-0003")):
            result = self.add(kind, '中文/含:字符?')
            self.assertEqual(result["record"]["key"], key)
            self.assertEqual(list(Path(result["workspace"]).iterdir()), [])
            self.assertTrue(Path(result["workspace"]).is_relative_to(self.root))
        self.assertTrue(self.call("check")["ok"])

    def test_readme_outside_managed_region_is_preserved(self):
        self.root.mkdir()
        prefix = "# 我的论文\r\n\r\n作者手写结论：尚未验证。\r\n".encode()
        (self.root / "README.md").write_bytes(prefix)
        self.init()
        self.add("analysis")
        path = self.root / "README.md"
        self.assertTrue(path.read_bytes().startswith(prefix))
        with path.open("a", encoding="utf-8", newline="") as f:
            f.write("\r\n作者追加下一步。\r\n")
        self.call("refresh")
        self.assertTrue(path.read_bytes().endswith("\r\n作者追加下一步。\r\n".encode()))
        self.assertTrue(self.call("check")["ok"])

    def test_design_revision_does_not_clone_or_overwrite_research(self):
        self.init()
        old = self.add("design")
        original = Path(old["workspace"]) / "design.json"
        original.write_text('{"scientific_status":"draft"}', encoding="utf-8")
        data = original.read_bytes()
        new = self.call("revise", "--key", old["record"]["key"])
        self.assertEqual(new["record"]["key"], "PROT-0001@v02")
        self.assertEqual(new["record"]["supersedes"], "PROT-0001@v01")
        self.assertEqual(list(Path(new["workspace"]).iterdir()), [])
        self.assertEqual(original.read_bytes(), data)
        self.assertEqual(new["record"]["status"], "planned")

    def test_legacy_registration_never_moves_or_rewrites_native_files(self):
        self.init()
        old = self.root / "Analyses" / "旧结果"
        old.mkdir(parents=True)
        raw = old / "analysis.json"
        raw.write_bytes(b'{"fixture":true}\n')
        result = self.call("register", "--kind", "analysis", "--title", "已有结果", "--path", "Analyses/旧结果")
        self.assertEqual(result["record"]["path"], "Analyses/旧结果")
        self.call("update", "--key", "AN-0001", "--status", "archived")
        self.assertEqual(raw.read_bytes(), b'{"fixture":true}\n')
        self.assertFalse((self.root / "Analysis" / old.name).exists())

    def test_invalid_upstream_and_cycle_leave_registry_unchanged(self):
        self.init()
        self.add("idea")
        self.add("analysis", upstream="IDEA-0001")
        manifest = self.root / "project.json"
        before = manifest.read_bytes()
        with self.assertRaises(ValueError):
            self.call("update", "--key", "IDEA-0001", "--upstream", "AN-0001")
        with self.assertRaises(ValueError):
            self.add("design", upstream="UNKNOWN")
        self.assertEqual(manifest.read_bytes(), before)
        self.assertFalse((self.root / "Design").exists())

    def test_path_escape_and_case_duplicate_are_rejected(self):
        self.init()
        folder = self.root / "Legacy"
        folder.mkdir()
        self.call("register", "--kind", "idea", "--title", "旧", "--path", "Legacy")
        for path in ("../外部", str(folder), ".", "Legacy/../Legacy", "C:/outside"):
            with self.assertRaises(ValueError, msg=path):
                self.call("register", "--kind", "analysis", "--title", "错误路径", "--path", path)
        with self.assertRaises(ValueError):
            self.call("register", "--kind", "analysis", "--title", "重复", "--path", "Legacy")

    def test_lock_conflict_does_not_remove_other_writers_lock(self):
        self.init()
        lock = self.root / ".light-project.lock"
        lock.write_text("another writer", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            self.add("idea")
        self.assertEqual(lock.read_text(), "another writer")

    def test_broken_navigation_is_not_silently_overwritten(self):
        self.init()
        readme = self.root / "README.md"
        readme.write_text(project.START + "用户正文", encoding="utf-8")
        before = (self.root / "project.json").read_bytes()
        with self.assertRaises(ValueError):
            self.add("experiment")
        self.assertEqual((self.root / "project.json").read_bytes(), before)
        self.assertFalse((self.root / "Experiment").exists())

    def test_foreign_manifest_is_preserved(self):
        self.root.mkdir()
        path = self.root / "project.json"
        path.write_bytes(b'{"unrelated":1}')
        with self.assertRaises(ValueError):
            self.init()
        with self.assertRaises(ValueError):
            self.call("refresh")
        self.assertEqual(path.read_bytes(), b'{"unrelated":1}')

    def test_single_manuscript_and_library_ownership(self):
        self.init()
        library = self.add("literature")
        index = Path(library["workspace"]) / "README.md"
        index.write_text("Native literature index", encoding="utf-8")
        self.add("search")
        self.add("write")
        self.call("refresh")
        self.assertEqual(index.read_text(), "Native literature index")
        for kind in ("write", "literature"):
            with self.assertRaises(ValueError):
                self.add(kind)

    @unittest.skipUnless(sys.platform == "win32", "Windows junction behavior")
    def test_windows_junction_is_not_followed(self):
        self.init()
        outside = Path(self.tmp.name) / "external source"
        outside.mkdir()
        junction = self.root / "link"
        result = subprocess.run(["cmd", "/c", "mklink", "/J", str(junction), str(outside)],
                                capture_output=True)
        self.assertEqual(result.returncode, 0, (result.stdout + result.stderr).decode("utf-8", errors="replace"))
        try:
            with self.assertRaises(ValueError):
                self.call("register", "--kind", "analysis", "--title", "junction", "--path", "link")
        finally:
            junction.rmdir()  # Remove the junction itself, never traverse its target.

    def test_check_is_read_only_and_refresh_repairs_only_navigation(self):
        self.init()
        item = self.add("write")
        overview = self.root / "Write/00-Write总览.md"
        overview.unlink()
        manifest = (self.root / "project.json").read_bytes()
        self.assertFalse(self.call("check")["ok"])
        self.assertFalse(overview.exists())
        self.assertEqual((self.root / "project.json").read_bytes(), manifest)
        self.call("refresh")
        self.assertTrue(self.call("check")["ok"])
        Path(item["workspace"]).rmdir()
        with self.assertRaises(ValueError):
            self.call("refresh")  # Missing research is not hidden by navigation regeneration.

    def test_linked_navigation_is_rejected(self):
        self.init()
        target = Path(self.tmp.name) / "outside.md"
        target.write_text("must survive", encoding="utf-8")
        readme = self.root / "README.md"
        readme.unlink()
        try:
            readme.symlink_to(target)
        except OSError:
            self.skipTest("Symlink creation unavailable")
        with self.assertRaises(ValueError):
            self.call("refresh")
        self.assertEqual(target.read_text(), "must survive")

    def test_native_design_patent_analysis_and_crawl_initializers_accept_workspaces(self):
        self.init()
        idea = self.add("idea")
        ideas = json.loads((PACK / "light-idea/templates/ideas.example.json").read_text(encoding="utf-8"))
        (Path(idea["workspace"]) / "ideas.json").write_text(json.dumps(ideas), encoding="utf-8")
        design = self.add("design", upstream=idea["record"]["key"])
        self.native("light-design", "design_bridge.py", "ingest", "--ideas", idea["workspace"],
                    "--idea-id", "I01", "--out", design["workspace"])
        self.assertTrue((Path(design["workspace"]) / "design.json").is_file())
        patent = self.add("patent")
        self.native("light-patent", "init_case.py", "--title", "结构兼容测试", "--out", patent["workspace"])
        analysis = self.add("analysis")
        raw = self.root / "fixture.csv"
        raw.write_text("unit,value\n1,2\n", encoding="utf-8")
        self.native("light-anaysis", "analysis_bridge.py", "ingest", "--input", raw, "--out", analysis["workspace"])
        self.assertTrue((Path(analysis["workspace"]) / "analysis.json").is_file())
        crawl = self.add("acquisition")
        result = subprocess.run([sys.executable, "-X", "utf8", str(PACK / "light-crawl/run_light_crawl.py"),
                                 "new-case", "case", "--case-root", crawl["workspace"], "--target", "https://example.invalid"],
                                capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((Path(crawl["workspace"]) / "case/case.json").is_file())
        self.assertTrue(self.call("check")["ok"])


if __name__ == "__main__":
    unittest.main()
