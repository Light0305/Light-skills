from __future__ import annotations

import unittest

from litsearch.coverage import build_coverage
from litsearch.models import Paper
from litsearch.normalize import make_paper_id


def paper(title: str, qid: str) -> Paper:
    return Paper(
        paper_id=make_paper_id(title=title, year=2024),
        title=title,
        year=2024,
        source_records=[{"source": "test", "query_id": qid, "rank": 1}],
    )


class CoverageTests(unittest.TestCase):
    def test_new_and_revisited_queries(self) -> None:
        papers = [paper("A", "q1"), paper("B", "q2"), paper("C", "q1")]
        runs = [
            {"query_id": "q1", "source": "test", "status": "ok"},
            {"query_id": "q2", "source": "test", "status": "ok"},
        ]
        data = build_coverage(runs, papers)
        self.assertEqual(data["query_count"], 2)
        self.assertEqual(data["curve"][0]["new_unique"], 2)
        self.assertEqual(data["curve"][1]["new_unique"], 1)
        self.assertEqual(data["curve"][1]["cumulative_unique"], 3)
        self.assertFalse(data["coverage_plateau"])

    def test_plateau_on_repeated_results(self) -> None:
        p = Paper(
            paper_id=make_paper_id(title="A", year=2024),
            title="A",
            year=2024,
            source_records=[
                {"source": "test", "query_id": "q1", "rank": 1},
                {"source": "test", "query_id": "q2", "rank": 1},
            ],
        )
        runs = [
            {"query_id": "q1", "source": "test", "status": "ok"},
            {"query_id": "q2", "source": "test", "status": "ok"},
        ]
        data = build_coverage(runs, [p], plateau_window=1)
        self.assertEqual(data["curve"][1]["rediscovery_rate"], 1.0)
        self.assertTrue(data["coverage_plateau"])


if __name__ == "__main__":
    unittest.main()
