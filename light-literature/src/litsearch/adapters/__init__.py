from __future__ import annotations

from ..config import Config
from ..http import HttpClient
from .arxiv import ArxivAdapter
from .base import Adapter, CitationResult, SearchResult
from .crossref import CrossrefAdapter
from .dblp import DBLPAdapter
from .doaj import DOAJAdapter
from .europepmc import EuropePMCAdapter
from .openalex import OpenAlexAdapter
from .openaire import OpenAIREAdapter
from .opencitations import OpenCitationsAdapter
from .pubmed import PubMedAdapter
from .semantic_scholar import SemanticScholarAdapter
from .unpaywall import UnpaywallAdapter

# Search adapters. Unpaywall is lookup-only and lives in LOOKUP_ADAPTERS.
SEARCH_ADAPTERS: dict[str, type[Adapter]] = {
    "europepmc": EuropePMCAdapter,
    "pubmed": PubMedAdapter,
    "arxiv": ArxivAdapter,
    "crossref": CrossrefAdapter,
    "openaire": OpenAIREAdapter,
    "doaj": DOAJAdapter,
    "dblp": DBLPAdapter,
    "openalex": OpenAlexAdapter,
    "semantic_scholar": SemanticScholarAdapter,
    "opencitations": OpenCitationsAdapter,
}

LOOKUP_ADAPTERS: dict[str, type[Adapter]] = {
    "unpaywall": UnpaywallAdapter,
}

ADAPTERS: dict[str, type[Adapter]] = {**SEARCH_ADAPTERS, **LOOKUP_ADAPTERS}

# Keyless search sources. OpenAIRE is an all-discipline supplement; OpenAlex has a
# small keyless daily budget and works better with a key. DOAJ/DBLP are currently
# unstable/blocked on some networks, so they are experimental rather than default.
DEFAULT_SOURCES = ["openalex", "crossref", "europepmc", "openaire"]
OPTIONAL_SOURCES = ["semantic_scholar"]  # key required for predictability
EXPERIMENTAL_SOURCES = ["doaj", "dblp"]  # keyless, but upstream may 502/challenge
ALL_SOURCES = list(SEARCH_ADAPTERS)

DOMAIN_BUNDLES = {
    "general": ["openalex", "crossref", "europepmc", "openaire"],
    "biomed": ["pubmed", "europepmc", "openalex", "crossref", "openaire"],
    "cs": ["arxiv", "openalex", "crossref", "openaire"],
    "social": ["openalex", "crossref", "openaire"],
}

CITATION_SOURCES = ["europepmc", "opencitations", "crossref", "openalex", "semantic_scholar"]

# Capability matrix used by `sources`, `doctor`, and the report. Keep this
# descriptive rather than aspirational: a source that is currently blocked on
# some networks is marked here as unstable.
SOURCE_CAPABILITIES: dict[str, dict[str, object]] = {
    "europepmc": {
        "search": True, "citations": True, "abstract": True, "oa_links": True,
        "key": "none", "stability": "stable", "note": "biomedical + citation edges",
    },
    "pubmed": {
        "search": True, "citations": False, "abstract": True, "oa_links": False,
        "key": "optional NCBI", "stability": "stable", "note": "biomedical; no citation list endpoint",
    },
    "arxiv": {
        "search": True, "citations": False, "abstract": True, "oa_links": True,
        "key": "none", "stability": "stable", "note": "preprints; 3 s between requests",
    },
    "crossref": {
        "search": True, "citations": False, "abstract": True, "oa_links": True,
        "key": "none", "stability": "stable", "note": "DOI metadata; backward references only",
    },
    "openaire": {
        "search": True, "citations": False, "abstract": True, "oa_links": True,
        "key": "none", "stability": "stable", "note": "all-discipline repository aggregator; ~60/hour anonymous",
    },
    "doaj": {
        "search": True, "citations": False, "abstract": True, "oa_links": True,
        "key": "none", "stability": "experimental", "note": "502/403 observed on some networks",
    },
    "dblp": {
        "search": True, "citations": False, "abstract": False, "oa_links": False,
        "key": "none", "stability": "experimental", "note": "Anubis challenge observed on dblp.org",
    },
    "openalex": {
        "search": True, "citations": True, "abstract": True, "oa_links": True,
        "key": "optional free", "stability": "stable", "note": "broad discovery + citation graph; keyless has daily budget",
    },
    "semantic_scholar": {
        "search": True, "citations": True, "abstract": True, "oa_links": True,
        "key": "required for predictable use", "stability": "keyless-throttled",
        "note": "skipped unless S2_API_KEY is set",
    },
    "opencitations": {
        "search": False, "citations": True, "abstract": False, "oa_links": False,
        "key": "none", "stability": "stable", "note": "citation edges only; metadata-poor",
    },
    "unpaywall": {
        "search": False, "citations": False, "abstract": False, "oa_links": True,
        "key": "email only", "stability": "stable", "note": "DOI lookup; OA PDF locations",
    },
}


def get_adapter(name: str, client: HttpClient, config: Config) -> Adapter:
    try:
        cls = ADAPTERS[name]
    except KeyError as exc:
        raise ValueError(f"Unknown source: {name}") from exc
    return cls(client, config)


def requires_key(name: str, config: Config) -> bool:
    if name == "semantic_scholar":
        return not bool(config.s2_api_key)
    return False
