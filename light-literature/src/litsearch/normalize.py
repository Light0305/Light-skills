from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import datetime, timezone


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_doi(value: str | None) -> str:
    if not value:
        return ""
    value = str(value).strip().lower()
    value = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", "", value)
    value = value.strip().rstrip(".,;")
    return value


def normalize_arxiv(value: str | None) -> str:
    if not value:
        return ""
    value = str(value).strip()
    value = re.sub(r"^https?://arxiv\.org/(abs|pdf)/", "", value, flags=re.I)
    value = re.sub(r"^arxiv:\s*", "", value, flags=re.I)
    value = re.sub(r"v\d+$", "", value)
    return value.strip()


def normalize_pmid(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"^pmid:\s*", "", str(value).strip(), flags=re.I)


def normalize_pmcid(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"^pmcid:\s*", "", str(value).strip(), flags=re.I).upper()


def normalize_title(value: str | None) -> str:
    """Comparison key: NFKC, lowercase, strip tags/punctuation, collapse space."""
    if not value:
        return ""
    text = unicodedata.normalize("NFKC", str(value))
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.lower()
    text = re.sub(r"[\W_]+", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def title_key(value: str | None) -> str:
    """Remove leading English articles for the comparison key only."""
    text = normalize_title(value)
    return re.sub(r"^(a|an|the)\s+", "", text)


def normalize_person(value: str | None) -> str:
    if not value:
        return ""
    text = unicodedata.normalize("NFKC", str(value)).lower()
    text = re.sub(r"[^\w\s一-鿿]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def surname(value: str | None) -> str:
    text = normalize_person(value)
    if not text:
        return ""
    parts = text.split()
    return parts[-1] if parts else text


def authors_from_string(value: str | None) -> list[str]:
    if not value:
        return []
    text = str(value)
    if ";" in text:
        parts = re.split(r"\s*;\s*", text)
    else:
        parts = re.split(r"\s*,\s*", text)
    return [p.strip() for p in parts if p.strip()]


def _hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def canonical_key(
    *,
    doi: str = "",
    pmid: str = "",
    pmcid: str = "",
    arxiv_id: str = "",
    openalex_id: str = "",
    s2_id: str = "",
    title: str = "",
    year: int | None = None,
) -> str:
    doi = normalize_doi(doi)
    if doi:
        return f"doi:{doi}"
    pmid = normalize_pmid(pmid)
    if pmid:
        return f"pmid:{pmid}"
    pmcid = normalize_pmcid(pmcid)
    if pmcid:
        return f"pmcid:{pmcid}"
    arxiv_id = normalize_arxiv(arxiv_id)
    if arxiv_id:
        return f"arxiv:{arxiv_id}"
    if openalex_id:
        return f"openalex:{openalex_id}"
    if s2_id:
        return f"s2:{s2_id}"
    return f"title:{title_key(title)}|year:{year or ''}"


def make_paper_id(**kwargs) -> str:
    return "p_" + _hash(canonical_key(**kwargs))


def make_edge_id(source: str, target: str, direction: str, provider: str) -> str:
    return "e_" + _hash(f"{source}|{target}|{direction}|{provider}")


def tokenize(text: str) -> set[str]:
    """Token set for English and CJK. CJK uses characters plus bigrams."""
    if not text:
        return set()
    text = unicodedata.normalize("NFKC", text).lower()
    latin = re.findall(r"[a-z0-9]+", text)
    cjk = re.findall(r"[一-鿿]", text)
    bigrams = [cjk[i] + cjk[i + 1] for i in range(len(cjk) - 1)]
    return set(latin) | set(cjk) | set(bigrams)
