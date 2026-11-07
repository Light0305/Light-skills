"""Offline delivery failure checks; real TeX/PDF smoke builds are separate."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('write_latex', ROOT / 'scripts/latex_project.py')
latex = importlib.util.module_from_spec(spec)
spec.loader.exec_module(latex)


class LatexProjectTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='write-latex-')
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.project = self.base / 'latex'
        self.output = self.base / 'build'

    def test_cli_never_selects_columns_for_the_user(self):
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/latex_project.py'),
                                 'init', str(self.project)], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.project.exists())

    def test_selected_projects_are_self_contained_and_do_not_edit_the_template(self):
        for layout in ('single', 'double'):
            with self.subTest(layout=layout):
                destination = self.base / layout / 'latex'
                result = latex.initialize(destination, layout)
                self.assertEqual(result['layout'], layout)
                self.assertFalse(result['compiled'])
                for resource in ('main.tex', 'lightwrite.sty', 'language.tex', 'metadata.tex',
                                 'sections/abstract.tex', 'sections/body.tex', 'references.bib'):
                    self.assertTrue((destination / resource).is_file(), resource)
                before = (latex.TEMPLATES / 'common' / 'sections/body.tex').read_bytes()
                (destination / 'sections/body.tex').write_text('Author material', encoding='utf-8')
                self.assertEqual((latex.TEMPLATES / 'common' / 'sections/body.tex').read_bytes(), before)

    def test_existing_project_and_user_template_are_never_overwritten(self):
        self.project.mkdir()
        source = self.project / 'main.tex'
        source.write_text('An adopted user template', encoding='utf-8')
        with self.assertRaises(latex.LatexError):
            latex.initialize(self.project, 'single')
        self.assertEqual(source.read_text(encoding='utf-8'), 'An adopted user template')
        self.assertEqual(list(self.project.iterdir()), [source])

    def test_unselected_layout_or_invalid_language_creates_nothing(self):
        for layout, language in ((None, 'en'), ('auto', 'en'), ('double', 'unknown')):
            with self.subTest(layout=layout, language=language), self.assertRaises(latex.LatexError):
                latex.initialize(self.project, layout, language)
            self.assertFalse(self.project.exists())

    def test_chinese_setting_is_preserved_with_the_source(self):
        result = latex.initialize(self.project, 'double', 'zh')
        self.assertEqual(result['language'], 'zh')
        self.assertIn('\\LWChinesetrue', (self.project / 'language.tex').read_text(encoding='utf-8'))
        self.assertFalse(result['compiled'])

    def test_final_log_rejects_unresolved_citations_references_labels_and_glyphs(self):
        for line in ("LaTeX Warning: Citation `unknown' on page 1 undefined on input line 8.",
                     'LaTeX Warning: There were undefined references.',
                     "LaTeX Warning: Label `eq:a' multiply defined.",
                     'Missing character: There is no 中 (U+4E2D) in font foo!',
                     'Package biblatex Warning: Please (re)run Biber on the file:'):
            with self.subTest(line=line):
                self.assertTrue(latex.log_issues(line)[0])
        failures, warnings = latex.log_issues(
            'Overfull \\hbox (4pt too wide)\nLaTeX Warning: Empty bibliography on input line 12.')
        self.assertFalse(failures)
        self.assertEqual(len(warnings), 2)

    def initialized(self):
        latex.initialize(self.project, 'double')
        self.output.mkdir()

    @patch.object(latex.shutil, 'which', return_value=None)
    def test_missing_tex_tools_cannot_be_called_compilation(self, which):
        latex.initialize(self.project, 'single')
        with self.assertRaises(latex.LatexError):
            latex.build(self.project)
        self.assertFalse(self.output.exists())

    @patch.object(latex.shutil, 'which', return_value='mock-tool')
    @patch.object(latex.subprocess, 'run')
    def test_failed_build_cannot_pass_using_an_old_pdf(self, run, which):
        self.initialized()
        pdf = self.output / 'main.pdf'
        pdf.write_bytes(b'%PDF-old')
        run.return_value = subprocess.CompletedProcess([], 1, 'Build failed')
        with self.assertRaises(latex.LatexError):
            latex.build(self.project)
        self.assertEqual(pdf.read_bytes(), b'%PDF-old')
        self.assertIn('Build failed', (self.output / 'latexmk-output.log').read_text())

    @patch.object(latex.shutil, 'which', return_value='mock-tool')
    @patch.object(latex.subprocess, 'run')
    def test_nominal_success_without_new_artifacts_is_not_accepted(self, run, which):
        self.initialized()
        run.return_value = subprocess.CompletedProcess([], 0, 'Nothing generated')
        with self.assertRaises(latex.LatexError):
            latex.build(self.project)
        (self.output / 'main.pdf').write_bytes(b'%PDF-old')
        (self.output / 'main.log').write_text('Old log', encoding='utf-8')
        with self.assertRaises(latex.LatexError):
            latex.build(self.project)

    @patch.object(latex.shutil, 'which', return_value='mock-tool')
    @patch.object(latex.subprocess, 'run')
    def test_successful_build_still_requires_visual_review(self, run, which):
        self.initialized()

        def compiler(*args, **kwargs):
            (self.output / 'main.pdf').write_bytes(b'%PDF-1.7\nMock build artifact')
            (self.output / 'main.log').write_text('Output written on main.pdf', encoding='utf-8')
            self.assertEqual(Path(kwargs['cwd']), self.project)
            self.assertIn('-outdir=../build', args[0])
            return subprocess.CompletedProcess([], 0, 'Mock compiler success')

        run.side_effect = compiler
        result = latex.build(self.project)
        self.assertEqual(result['status'], 'compiled')
        self.assertEqual(result['visual_review'], 'pending')
        self.assertEqual(Path(result['pdf']), self.output / 'main.pdf')

    @patch.object(latex.shutil, 'which', return_value='mock-tool')
    @patch.object(latex.subprocess, 'run')
    def test_timeout_keeps_diagnostics_and_never_reports_a_pdf(self, run, which):
        self.initialized()
        run.side_effect = subprocess.TimeoutExpired('mock-tool', 1, output=b'Partial build')
        with self.assertRaises(latex.LatexError):
            latex.build(self.project, timeout=1)
        self.assertEqual((self.output / 'latexmk-output.log').read_text(), 'Partial build')

    def test_source_and_output_cannot_replace_the_editable_main(self):
        latex.initialize(self.project, 'single')
        for kwargs in ({'main': '../outside.tex'}, {'output': self.project}, {'timeout': 0}):
            with self.subTest(kwargs=kwargs), self.assertRaises(latex.LatexError):
                latex.build(self.project, **kwargs)


if __name__ == '__main__':
    unittest.main()
