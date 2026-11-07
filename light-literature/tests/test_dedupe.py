from __future__ import annotations

import unittest

from litsearch.dedupe import dedupe_papers
from litsearch.models import Paper
from litsearch.normalize import make_paper_id


def paper(doi: str, title: str, year: int, *, preprint: bool = False, authors: list[str] | None = None) -> Paper:
    return Paper(
        paper_id=make_paper_id(doi=doi, title=title, year=year),
        title=title,
        doi=doi,
        year=year,
        authors=authors or ["Alice Smith", "Bob Jones"],
        is_preprint=preprint,
        abstract="abstract",
    )


class DedupeTests(unittest.TestCase):
    def test_same_doi_merges(self) -> None:
        merged, log = dedupe_papers([paper("10.1/x", "A paper", 2024), paper("10.1/X", "A paper", 2024)])
        self.assertEqual(len(merged), 1)
        self.assertEqual(log["duplicates_removed"], 1)

    def test_preprint_and_published_keep_separate_dois(self) -> None:
        arxiv = paper("10.48550/arxiv.1234", "A study of things", 2023, preprint=True)
        published = paper("10.1000/journal.1", "A study of things", 2024, preprint=False)
        merged, log = dedupe_papers([arxiv, published])
        self.assertEqual(len(merged), 2)
        self.assertTrue(log["possible_duplicates"])

    def test_different_papers_same_title_do_not_merge(self) -> None:
        a = paper("10.1000/a", "Editorial", 2020, authors=["Alice Smith"])
        b = paper("10.1000/b", "Editorial", 2021, authors=["Carol Brown"])
        merged, _ = dedupe_papers([a, b])
        self.assertEqual(len(merged), 2)

    def test_strong_identifier_beats_title(self) -> None:
        a = paper("10.1000/a", "Title A", 2020)
        b = paper("10.1000/b", "Title A", 2020)
        b.pmid = "12345"
        merged, _ = dedupe_papers([a, b])
        # Different valid DOIs and no preprint relation -> keep separate.
        self.assertEqual(len(merged), 2)


if __name__ == "__main__":
    unittest.main()
