from __future__ import annotations

import unittest

from litsearch.models import Paper
from litsearch.normalize import make_paper_id
from litsearch.query import default_plan
from litsearch.scoring import score_papers


def paper(title: str, year: int, cites: int, *, retracted: bool = False, abstract: str = "retrieval augmented generation") -> Paper:
    return Paper(
        paper_id=make_paper_id(title=title, year=year),
        title=title,
        abstract=abstract,
        year=year,
        cited_by_count=cites,
        is_retracted=retracted,
        authors=["Alice Smith"],
        venue="Demo",
        type="article",
        doi=f"10.5555/{abs(hash(title))}",
        source_records=[{"source": "test", "rank": 1}],
        evidence_depth="abstract",
    )


class ScoringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.plan = default_plan("retrieval augmented generation for literature review", domain="cs")
        self.plan["concept_blocks"][0]["terms"] = [{"text": "retrieval", "lang": "en", "type": "free", "vocab": "none"}]

    def test_recent_relevant_beats_old_cited_irrelevant(self) -> None:
        recent = paper("Retrieval augmented generation for review", 2025, 0)
        old = paper("A history of library catalogues", 2000, 100000, abstract="library catalogues")
        score_papers([recent, old], self.plan, current_year=2026)
        self.assertGreater(recent.discovery_score["total"], old.discovery_score["total"])

    def test_components_sum_to_total(self) -> None:
        p = paper("Retrieval augmented generation", 2020, 10)
        score_papers([p], self.plan, current_year=2026)
        score = p.discovery_score
        self.assertAlmostEqual(score["total"], sum(score["components"].values()), places=1)

    def test_retracted_penalty(self) -> None:
        normal = paper("Retrieval augmented generation", 2024, 10)
        bad = paper("Retrieval augmented generation", 2024, 10, retracted=True)
        score_papers([normal, bad], self.plan, current_year=2026)
        self.assertLess(bad.discovery_score["total"], normal.discovery_score["total"])


if __name__ == "__main__":
    unittest.main()
