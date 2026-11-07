from __future__ import annotations

import unittest

from litsearch.models import Paper
from litsearch.normalize import make_paper_id
from litsearch.query import default_plan
from litsearch.screening import prescreen, validate_screening


def paper(title: str, year: int) -> Paper:
    return Paper(
        paper_id=make_paper_id(title=title, year=year),
        title=title,
        abstract="abstract",
        year=year,
        authors=["Alice Smith"],
        venue="Demo",
        doi=f"10.5555/{year}",
        evidence_depth="abstract",
    )


class ScreeningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.plan = default_plan("retrieval augmented generation", domain="cs")
        self.plan["filters"]["year_from"] = 2020
        self.plan["filters"]["year_to"] = 2026
        self.plan["filters"]["languages"] = ["en"]

    def test_date_filter(self) -> None:
        rows = prescreen([paper("Old", 2010)], self.plan)
        self.assertEqual(rows[0].decision, "exclude")
        self.assertEqual(rows[0].reason_code, "DATE_RANGE")

    def test_default_maybe(self) -> None:
        rows = prescreen([paper("New", 2022)], self.plan)
        self.assertEqual(rows[0].decision, "maybe")
        self.assertEqual(rows[0].reason_code, "PENDING_REVIEW")

    def test_include_requires_reason(self) -> None:
        rows = prescreen([paper("New", 2022)], self.plan)
        rows[0].decision = "include"
        errors = validate_screening(rows, {rows[0].paper_id})
        self.assertTrue(any("include requires" in e for e in errors))

    def test_short_abstract_requires_review_instead_of_exclusion(self) -> None:
        self.plan["filters"]["min_abstract_chars"] = 100
        row = prescreen([paper("New", 2022)], self.plan)[0]
        self.assertEqual(row.decision, "maybe")
        self.assertEqual(row.reason_code, "INSUFFICIENT_EVIDENCE")
        self.assertEqual(row.confidence, "low")

    def test_missing_abstract_can_still_be_eligible(self) -> None:
        self.plan["filters"]["min_abstract_chars"] = 100
        candidate = paper("New", 2022)
        candidate.abstract = ""
        row = prescreen([candidate], self.plan)[0]
        self.assertEqual(row.decision, "maybe")

    def test_confirmed_out_of_scope_is_not_hidden_by_short_abstract(self) -> None:
        self.plan["filters"]["min_abstract_chars"] = 100
        row = prescreen([paper("Old", 2010)], self.plan)[0]
        self.assertEqual(row.decision, "exclude")
        self.assertEqual(row.reason_code, "DATE_RANGE")

    def test_in_scope_reason_cannot_explain_exclusion(self) -> None:
        rows = prescreen([paper("New", 2022)], self.plan)
        rows[0].decision, rows[0].reason_code = "exclude", "IN_SCOPE"
        self.assertTrue(validate_screening(rows, {rows[0].paper_id}))

    def test_negative_reason_cannot_explain_inclusion(self) -> None:
        rows = prescreen([paper("New", 2022)], self.plan)
        rows[0].decision, rows[0].reason_code = "include", "WRONG_DESIGN"
        self.assertTrue(validate_screening(rows, {rows[0].paper_id}))


if __name__ == "__main__":
    unittest.main()
