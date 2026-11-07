from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from litsearch.io import write_json
from litsearch.prisma import build_prisma_s_audit


class PrismaTests(unittest.TestCase):
    def test_sixteen_items_and_statuses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            write_json(
                run / "query_plan.json",
                {
                    "filters": {"year_from": 2020, "year_to": 2026, "languages": ["en"], "include_preprints": True},
                    "source_policy": {"enabled": ["openalex", "crossref"]},
                },
            )
            write_json(run / "compiled_queries.json", {"sources": ["openalex", "crossref"], "queries": []})
            write_json(
                run / "search_log.json",
                {
                    "started_at": "2026-10-22T00:00:00+00:00",
                    "source_runs": [
                        {"source": "openalex", "status": "ok"},
                        {"source": "crossref", "status": "ok"},
                    ],
                    "totals": {"identified": 10},
                },
            )
            write_json(run / "merge_log.json", {"duplicates_removed": 2})
            data = build_prisma_s_audit(run)
            self.assertEqual(len(data["items"]), 16)
            self.assertEqual(data["items"][0]["status"], "performed")
            self.assertEqual(data["items"][4]["status"], "pending")
            self.assertEqual(data["items"][7]["status"], "performed")
            self.assertTrue((run / "prisma_s_audit.json").exists())


if __name__ == "__main__":
    unittest.main()
