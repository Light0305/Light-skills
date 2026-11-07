from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any

from ..models import Paper
from ..normalize import authors_from_string, make_paper_id, normalize_doi, normalize_pmcid, normalize_pmid, now_iso
from .base import Adapter, SearchResult

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def _text(el: ET.Element | None) -> str:
    if el is None:
        return ""
    return " ".join("".join(el.itertext()).split())


class PubMedAdapter(Adapter):
    name = "pubmed"

    def _common(self) -> dict[str, Any]:
        params: dict[str, Any] = {"db": "pubmed", "tool": "litsearch"}
        if self.config.mailto:
            params["email"] = self.config.mailto
        if self.config.ncbi_api_key:
            params["api_key"] = self.config.ncbi_api_key
        return params

    def search(self, query: dict[str, Any], limit: int) -> SearchResult:
        params = self._common()
        params.update(
            {
                "term": query["query"],
                "retmode": "json",
                "retmax": limit,
                "sort": "pub_date" if query.get("sort") == "recent" else "relevance",
            }
        )
        try:
            resp = self.client.get(f"{BASE}/esearch.fcgi", params=params, ttl=86400)
            ids = (resp.data.get("esearchresult") or {}).get("idlist") or []
            if not ids:
                return SearchResult(source=self.name, status="empty")
            fetch_params = self._common()
            fetch_params.update({"id": ",".join(ids), "retmode": "xml", "rettype": "abstract"})
            xml_resp = self.client.get(f"{BASE}/efetch.fcgi", params=fetch_params, parse="text", ttl=7 * 86400)
        except Exception as exc:  # noqa: BLE001
            status = "rate_limited" if getattr(exc, "status", None) == 429 else "error"
            return SearchResult(source=self.name, status=status, error=str(exc))
        try:
            root = ET.fromstring(xml_resp.data)
        except ET.ParseError as exc:
            return SearchResult(source=self.name, status="error", error=f"XML parse error: {exc}")
        papers = []
        for rank, article in enumerate(root.findall(".//PubmedArticle")):
            paper = self._parse(article, query, rank)
            if paper is not None:
                papers.append(paper)
        return SearchResult(source=self.name, papers=papers, raw_count=len(ids))

    def _parse(self, article: ET.Element, query: dict[str, Any], rank: int) -> Paper | None:
        pmid = _text(article.find(".//MedlineCitation/PMID"))
        title = _text(article.find(".//Article/ArticleTitle"))
        if not title:
            return None
        abstract_parts = []
        for node in article.findall(".//Abstract/AbstractText"):
            label = node.get("Label", "")
            text = _text(node)
            if text:
                abstract_parts.append(f"{label}: {text}" if label else text)
        abstract = " ".join(abstract_parts)
        authors = []
        for author in article.findall(".//AuthorList/Author"):
            last = _text(author.find("LastName"))
            fore = _text(author.find("ForeName"))
            collective = _text(author.find("CollectiveName"))
            if last:
                authors.append(f"{last} {fore}".strip())
            elif collective:
                authors.append(collective)
        journal = _text(article.find(".//Journal/Title"))
        year_text = _text(article.find(".//JournalIssue/PubDate/Year"))
        if not year_text:
            medline = _text(article.find(".//JournalIssue/PubDate/MedlineDate"))
            match = re.search(r"(19|20)\d{2}", medline)
            year_text = match.group(0) if match else ""
        try:
            year = int(year_text) if year_text else None
        except ValueError:
            year = None
        doi = normalize_doi(_text(article.find(".//ArticleIdList/ArticleId[@IdType='doi']")))
        pmcid = normalize_pmcid(_text(article.find(".//ArticleIdList/ArticleId[@IdType='pmc']")))
        pub_types = [_text(x) for x in article.findall(".//PublicationTypeList/PublicationType")]
        is_retracted = any("retract" in p.lower() for p in pub_types)
        concepts = [_text(x) for x in article.findall(".//MeshHeading/DescriptorName")]
        language = _text(article.find(".//Language"))
        url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""
        record = self.source_record(query, rank, url)
        record["source_id"] = pmid
        return Paper(
            paper_id=make_paper_id(doi=doi, pmid=normalize_pmid(pmid), pmcid=pmcid, title=title, year=year),
            title=title,
            abstract=abstract,
            authors=authors,
            year=year,
            venue=journal,
            type=pub_types[0] if pub_types else "article",
            doi=doi,
            pmid=normalize_pmid(pmid),
            pmcid=pmcid,
            url=url,
            is_retracted=is_retracted,
            is_preprint=False,
            language=language,
            concepts=concepts,
            source_records=[record],
            evidence_depth="abstract" if abstract else "metadata_only",
            created_at=now_iso(),
        )
