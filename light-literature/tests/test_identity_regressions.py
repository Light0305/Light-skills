"""Synthetic bibliographic records; never use these as research evidence."""
import unittest

from litsearch.citations import _merge_new
from litsearch.dedupe import dedupe_papers
from litsearch.models import Paper
from litsearch.normalize import make_paper_id


def record(doi="", authors=None, title="Synthetic study of independent observations", **kwargs):
    return Paper(paper_id=make_paper_id(doi=doi, title=title, year=2024), title=title,
                 doi=doi, year=2024, authors=authors if authors is not None else ["Alice Smith"], **kwargs)


class IdentityRegressions(unittest.TestCase):
    def test_missing_authors_do_not_confirm_title_identity(self):
        a, b = record("10.9999/a"), record(authors=[])
        merged, log = dedupe_papers([a, b])
        self.assertEqual(len(merged), 2)
        self.assertTrue(log["possible_duplicates"])

    def test_shared_surname_does_not_confirm_author_identity(self):
        merged, _ = dedupe_papers([record("10.9999/a", ["Alice Smith"]), record(authors=["Carol Smith"])])
        self.assertEqual(len(merged), 2)

    def test_unidentified_record_cannot_bridge_conflicting_dois(self):
        merged, log = dedupe_papers([record("10.9999/a"), record(), record("10.9999/b")])
        self.assertEqual(len(merged), 3)
        self.assertTrue(log["possible_duplicates"])

    def test_preprint_and_publication_keep_distinct_report_identity(self):
        merged, log = dedupe_papers([record("10.9999/preprint", is_preprint=True), record("10.9999/published")])
        self.assertEqual(len(merged), 2)
        self.assertTrue(log["possible_duplicates"])

    def test_incremental_merge_normalizes_identifiers(self):
        original = record("10.9999/a")
        discovered = record("https://doi.org/10.9999/A")
        discovered.paper_id = "provider-alias"
        merged, aliases = _merge_new([original], [discovered])
        self.assertEqual(len(merged), 1)
        self.assertEqual(aliases["provider-alias"], original.paper_id)

    def test_incremental_merge_registers_newly_learned_identifiers(self):
        original = record("10.9999/a")
        enriched = record("10.9999/a", pmid="9999001")
        followup = record(title="Provider spelling variation", pmid="9999001")
        merged, aliases = _merge_new([original], [enriched, followup])
        self.assertEqual(len(merged), 1)
        self.assertEqual(aliases[followup.paper_id], original.paper_id)

    def test_incremental_merge_preserves_separate_doi_versions(self):
        original = record("10.9999/a", arxiv_id="2411.00001")
        followup = record("10.9999/b", arxiv_id="2411.00001")
        merged, _ = _merge_new([original], [followup])
        self.assertEqual(len(merged), 2)

    def test_repeated_deduplication_preserves_existing_version_aliases(self):
        original = record("10.9999/a")
        original.versions = [{"paper_id": "older-provider-alias", "doi": "10.9999/a"}]
        merged, _ = dedupe_papers([original, record("10.9999/a")])
        self.assertIn("older-provider-alias", {x["paper_id"] for x in merged[0].versions})

    def test_unmerged_sparse_records_have_distinct_repeatable_ids(self):
        a = record(authors=["Alice Smith"])
        b = record(authors=["Carol Smith"])
        merged, log = dedupe_papers([a, b])
        reverse, _ = dedupe_papers([b, a])
        ids = {p.paper_id for p in merged}
        self.assertEqual(len(ids), 2)
        self.assertEqual(ids, {p.paper_id for p in reverse})
        self.assertTrue(log["id_collisions"])
        for candidate in log["possible_duplicates"]:
            self.assertTrue(set(candidate["paper_ids"]).issubset(ids))

    def test_deduplication_does_not_mutate_sparse_input_identities(self):
        a, b = record(authors=["Alice Smith"]), record(authors=["Carol Smith"])
        originals = [p.paper_id for p in (a, b)]
        dedupe_papers([a, b])
        self.assertEqual([p.paper_id for p in (a, b)], originals)

    def test_full_author_year_and_distinctive_title_can_support_weak_merge(self):
        merged, _ = dedupe_papers([record("10.9999/a"), record()])
        self.assertEqual(len(merged), 1)


if __name__ == "__main__":
    unittest.main()
