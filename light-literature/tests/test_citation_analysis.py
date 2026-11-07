from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from litsearch.citation_analysis import analyze_citations
from litsearch.io import write_jsonl
from litsearch.models import CitationEdge, Paper
from litsearch.normalize import make_edge_id, make_paper_id


def paper(title: str) -> Paper:
    return Paper(paper_id=make_paper_id(title=title, year=2024), title=title, year=2024)


class CitationAnalysisTests(unittest.TestCase):
    def test_co_citation_and_bridge(self) -> None:
        a, b, c, d = paper("Seed A"), paper("Seed B"), paper("Cited by both"), paper("Cites both")
        edges = [
            CitationEdge(
                edge_id=make_edge_id(a.paper_id, c.paper_id, "backward", "test"),
                source_paper_id=a.paper_id,
                target_paper_id=c.paper_id,
                direction="backward",
                relation="reference",
                provider="test",
            ),
            CitationEdge(
                edge_id=make_edge_id(b.paper_id, c.paper_id, "backward", "test"),
                source_paper_id=b.paper_id,
                target_paper_id=c.paper_id,
                direction="backward",
                relation="reference",
                provider="test",
            ),
            CitationEdge(
                edge_id=make_edge_id(a.paper_id, d.paper_id, "forward", "test"),
                source_paper_id=a.paper_id,
                target_paper_id=d.paper_id,
                direction="forward",
                relation="citation",
                provider="test",
            ),
            CitationEdge(
                edge_id=make_edge_id(b.paper_id, d.paper_id, "forward", "test"),
                source_paper_id=b.paper_id,
                target_paper_id=d.paper_id,
                direction="forward",
                relation="citation",
                provider="test",
            ),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            write_jsonl(run / "papers.jsonl", [p.to_dict() for p in (a, b, c, d)])
            write_jsonl(run / "citation_edges.jsonl", [e.to_dict() for e in edges])
            data = analyze_citations(run)
            self.assertEqual(data["co_cited"][0]["paper_id"], c.paper_id)
            self.assertEqual(data["co_cited"][0]["count"], 2)
            self.assertEqual(data["bridges"][0]["paper_id"], d.paper_id)
            self.assertEqual(data["bridges"][0]["count"], 2)
            self.assertEqual(len(data["seed_pairs"]), 1)


if __name__ == "__main__":
    unittest.main()
