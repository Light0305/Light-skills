from __future__ import annotations

import unittest

from litsearch.models import Paper
from litsearch.normalize import make_paper_id
from litsearch.pdf import candidate_urls, is_downloadable


def paper(**kwargs) -> Paper:
    data = {"title": "A paper", "year": 2024}
    data.update(kwargs)
    return Paper(paper_id=make_paper_id(title=data["title"], year=data["year"]), **data)


class PDFTests(unittest.TestCase):
    def test_arxiv_candidate(self) -> None:
        p = paper(arxiv_id="2401.00001")
        urls = candidate_urls(p)
        self.assertIn("https://arxiv.org/pdf/2401.00001", urls)
        self.assertTrue(is_downloadable(p, "https://arxiv.org/pdf/2401.00001"))

    def test_doi_landing_is_not_automatically_downloadable(self) -> None:
        p = paper(doi="10.1000/example", pdf_url="https://doi.org/10.1000/example")
        self.assertFalse(is_downloadable(p, "https://doi.org/10.1000/example"))

    def test_oa_status_unlocks_publisher_host(self) -> None:
        p = paper(doi="10.1000/example", oa_status="gold", pdf_url="https://example.org/paper.pdf")
        self.assertTrue(is_downloadable(p, "https://example.org/paper.pdf"))

    def test_known_oa_host(self) -> None:
        p = paper(pdf_url="https://www.mdpi.com/123/pdf")
        self.assertTrue(is_downloadable(p, "https://www.mdpi.com/123/pdf"))


if __name__ == "__main__":
    unittest.main()
