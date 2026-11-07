from __future__ import annotations

import unittest

from litsearch.config import Config
from litsearch.query import compile_plan, default_plan, plan_warnings, validate_plan


class QueryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.plan = default_plan(
            "retrieval augmented generation for literature review",
            domain="cs",
            languages=["en"],
        )
        self.config = Config()

    def test_direction_decomposes_into_blocks(self) -> None:
        self.assertGreaterEqual(len(self.plan["concept_blocks"]), 2)
        self.assertTrue(any("retrieval" in b["label"]["en"].lower() for b in self.plan["concept_blocks"]))

    def test_plan_validates_non_strict(self) -> None:
        validate_plan(self.plan)

    def test_europepmc_query(self) -> None:
        compiled = compile_plan(self.plan, self.config, sources=["europepmc"])
        query = compiled["queries"][0]["query"]
        self.assertIn("TITLE_ABS", query)
        self.assertIn("PUB_YEAR", query)
        self.assertIn("AND", query)

    def test_pubmed_query(self) -> None:
        compiled = compile_plan(self.plan, self.config, sources=["pubmed"])
        query = compiled["queries"][0]["query"]
        self.assertIn("[tiab]", query)
        self.assertIn("[dp]", query)

    def test_arxiv_query(self) -> None:
        compiled = compile_plan(self.plan, self.config, sources=["arxiv"])
        query = compiled["queries"][0]["query"]
        self.assertIn("all:", query)
        self.assertIn("submittedDate", query)

    def test_openaire_operator_limit(self) -> None:
        compiled = compile_plan(self.plan, self.config, sources=["openaire"])
        query = compiled["queries"][0]["query"]
        operators = query.count(" OR ") + query.count(" AND ")
        self.assertLessEqual(operators, 4)

    def test_keyless_default_bundle(self) -> None:
        plan = default_plan("retrieval augmented generation", domain="cs")
        enabled = plan["source_policy"]["enabled"]
        self.assertIn("openaire", enabled)
        self.assertNotIn("semantic_scholar", enabled)

    def test_chinese_only_block_warns(self) -> None:
        plan = default_plan("人工智能在科学文献综述中的应用", domain="general")
        self.assertTrue(plan_warnings(plan))

    def test_direction_en_builds_english_blocks(self) -> None:
        plan = default_plan(
            "人工智能在科学文献综述中的应用",
            direction_en="artificial intelligence for scientific literature review",
            domain="cs",
        )
        self.assertTrue(plan["concept_blocks"])
        for block in plan["concept_blocks"]:
            for term in block["terms"]:
                self.assertFalse(any("一" <= ch <= "鿿" for ch in term["text"]))


if __name__ == "__main__":
    unittest.main()
