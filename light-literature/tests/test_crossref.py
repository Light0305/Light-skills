"""Provider route regressions using synthetic records and an in-memory client."""
from pathlib import Path
from types import SimpleNamespace
import unittest

from litsearch.adapters.crossref import BASE, SELECT, CrossrefAdapter
from litsearch.config import Config
from litsearch.models import Paper


class RouteClient:
    def __init__(self):
        self.calls = []

    def get(self, url, *, params, ttl):
        self.calls.append((url, params))
        item = {"DOI": "10.9999/fixture", "title": ["Synthetic provider fixture"],
                "reference": [{"DOI": "10.9999/reference", "article-title": "Synthetic reference"}]}
        if url != BASE and "select" in params:
            raise RuntimeError("This route does not support select")
        return SimpleNamespace(data={"message": {"items": [item]} if url == BASE else item})


class CrossrefRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = RouteClient()
        self.adapter = CrossrefAdapter(self.client, Config(mailto="fixture@example.invalid", cache_dir=Path("unused")))

    def test_collection_search_keeps_field_selection(self):
        result = self.adapter.search({"query": "synthetic provider fixture"}, 1)
        self.assertEqual(result.status, "ok")
        self.assertEqual(len(result.papers), 1)
        self.assertEqual(self.client.calls[0][1]["select"], SELECT)

    def test_single_doi_lookup_omits_unsupported_selection(self):
        paper = self.adapter.get_by_doi("10.9999/fixture")
        self.assertIsNotNone(paper)
        self.assertEqual(paper.doi, "10.9999/fixture")
        self.assertNotIn("select", self.client.calls[0][1])
        self.assertEqual(self.client.calls[0][1]["mailto"], "fixture@example.invalid")

    def test_backward_expansion_receives_reference_list(self):
        seed = Paper(paper_id="synthetic_seed", title="Synthetic seed", doi="10.9999/fixture")
        result = self.adapter.citations(seed, "backward", 1)
        self.assertEqual(result.status, "ok")
        self.assertEqual(len(result.edges), 1)
        self.assertEqual(result.papers[0].doi, "10.9999/reference")
        self.assertNotIn("select", self.client.calls[0][1])


if __name__ == "__main__":
    unittest.main()
