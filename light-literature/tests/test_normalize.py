from __future__ import annotations

import unittest

from litsearch.models import Paper
from litsearch.normalize import make_paper_id, normalize_arxiv, normalize_doi, normalize_title


class NormalizeTests(unittest.TestCase):
    def test_doi(self) -> None:
        self.assertEqual(normalize_doi("https://doi.org/10.1234/ABC."), "10.1234/abc")
        self.assertEqual(normalize_doi("doi: 10.1000/xyz "), "10.1000/xyz")
        self.assertEqual(normalize_doi(None), "")

    def test_arxiv(self) -> None:
        self.assertEqual(normalize_arxiv("arXiv:2308.02443v2"), "2308.02443")
        self.assertEqual(normalize_arxiv("https://arxiv.org/abs/2308.02443v1"), "2308.02443")

    def test_title(self) -> None:
        self.assertEqual(normalize_title("The  Quick, Brown Fox!"), "the quick brown fox")

    def test_paper_id_stable(self) -> None:
        a = make_paper_id(doi="https://doi.org/10.1234/ABC", title="X", year=2024)
        b = make_paper_id(doi="10.1234/abc", title="Different title", year=2020)
        self.assertEqual(a, b)
        self.assertTrue(a.startswith("p_"))

    def test_paper_roundtrip(self) -> None:
        paper = Paper(paper_id="p_1234567890ab", title="T", doi="10.1/x")
        self.assertEqual(Paper.from_dict(paper.to_dict()).doi, "10.1/x")


if __name__ == "__main__":
    unittest.main()
