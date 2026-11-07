"""Static checks only: these do not run an LLM or evaluate generated images."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DocumentTests(unittest.TestCase):
    def test_skill_frontmatter(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        frontmatter = text.split("---", 2)[1]
        self.assertRegex(frontmatter, r"(?m)^name: light-diagram-prompt$")
        self.assertIn("description: >-", frontmatter)
        description = frontmatter.split("description: >-", 1)[1].strip()
        self.assertLessEqual(len(description), 1024)

    def test_referenced_bundled_files_exist(self):
        paths = [ROOT / "SKILL.md", ROOT / "README.md"]
        paths.extend((ROOT / "references").glob("*.md"))
        for path in paths:
            text = path.read_text(encoding="utf-8")
            refs = re.findall(r"`((?:references|scripts|tests)/[^`\n]+\.(?:md|py))`", text)
            for ref in refs:
                with self.subTest(document=path.name, reference=ref):
                    self.assertTrue((ROOT / ref).is_file())

    def test_markdown_fences_are_balanced(self):
        paths = [ROOT / "SKILL.md", ROOT / "README.md"]
        paths.extend((ROOT / "references").glob("*.md"))
        for path in paths:
            opening = None
            for line in path.read_text(encoding="utf-8").splitlines():
                match = re.match(r"^(`{3,}|~{3,})(.*)$", line)
                if not match:
                    continue
                marker, suffix = match.groups()
                if opening is None:
                    opening = marker
                elif marker[0] == opening[0] and len(marker) >= len(opening) and not suffix.strip():
                    opening = None
            with self.subTest(document=path.name):
                self.assertIsNone(opening)

    def test_complete_examples_have_no_placeholders(self):
        text = (ROOT / "references/worked-examples.md").read_text(encoding="utf-8")
        blocks = re.findall(r"```text\n(.*?)\n```", text, re.S)
        self.assertEqual(len(blocks), 6)
        for index, block in enumerate(blocks):
            with self.subTest(example=index + 1):
                self.assertNotRegex(block, r"\[[^\]\n]+\]|\{[A-Z_]+\}|<[^>\n]+>")
                if index < 5:
                    self.assertIn("only visible text allowed", block)
                    self.assertGreater(len(block), 500)

    def test_core_has_no_machine_specific_dependency(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("D:/", text)
        self.assertNotIn("D:\\", text)
        self.assertNotIn("3,658", text)
        self.assertIn("Missing corpus, metadata, or Pillow must not block", text)


if __name__ == "__main__":
    unittest.main()
