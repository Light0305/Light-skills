"""Actual expansion pipeline with mocked providers and synthetic bibliographic data."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from litsearch.adapters.base import CitationResult
from litsearch.citations import expand_citations
from litsearch.config import Config
from litsearch.io import read_json, read_jsonl, write_json, write_jsonl
from litsearch.models import CitationEdge, Paper, ScreeningRow
from litsearch.normalize import make_edge_id, make_paper_id
from litsearch.query import default_plan


class CitationIntakeTests(unittest.TestCase):
    def check_direction(self, direction):
        with tempfile.TemporaryDirectory(prefix="litsearch-citation-fixture-") as tmp:
            root = Path(tmp)
            seed = Paper(paper_id=make_paper_id(doi="10.9999/seed"), title="Synthetic seed", doi="10.9999/seed")
            write_jsonl(root / "papers.jsonl", [seed.to_dict()])
            write_jsonl(root / "screening.jsonl", [ScreeningRow(paper_id=seed.paper_id, decision="include", reason_code="IN_SCOPE").to_dict()])
            write_json(root / "search_log.json", {"totals": {"identified": 1, "unique": 1}})
            plan = default_plan("synthetic citation fixture", domain="general")
            write_json(root / "query_plan.json", plan)

            class Provider:
                def __init__(self, name):
                    self.name = name

                def citations(self, selected, side, limit):
                    alias = "synthetic_" + self.name
                    paper = Paper(paper_id=alias, title="Synthetic cited report", doi="10.9999/shared")
                    source, target = (alias, selected.paper_id) if side == "forward" else (selected.paper_id, alias)
                    edge = CitationEdge(edge_id=make_edge_id(source, target, side, self.name),
                                        source_paper_id=source, target_paper_id=target, direction=side,
                                        relation="citation" if side == "forward" else "reference", provider=self.name)
                    return CitationResult(source=self.name, papers=[paper], edges=[edge])

            with patch("litsearch.http.HttpClient"), patch("litsearch.citations.get_adapter", side_effect=lambda name, *_: Provider(name)):
                result = expand_citations(root, plan, Config(cache_dir=root / "cache"),
                                          sources=["fixture_a", "fixture_b"], directions=[direction], seed_paper_ids=[seed.paper_id])
            ids = {p["paper_id"] for p in read_jsonl(root / "papers.jsonl")}
            edges = read_jsonl(root / "citation_edges.jsonl")
            self.assertEqual(len(ids), 2)
            self.assertEqual(len(edges), 2)
            for edge in edges:
                self.assertIn(edge["source_paper_id"], ids)
                self.assertIn(edge["target_paper_id"], ids)
            self.assertEqual(result["records_fetched"], 2)
            self.assertEqual(result["new_papers"], 1)
            totals = read_json(root / "search_log.json")["totals"]
            self.assertEqual(totals["identified"], 3)
            self.assertEqual(totals["duplicates_removed"], 1)

    def test_backward_edges_remap_every_provider_alias(self):
        self.check_direction("backward")

    def test_forward_edges_remap_source_identities(self):
        self.check_direction("forward")


if __name__ == "__main__":
    unittest.main()
