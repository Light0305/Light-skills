from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11
    tomllib = None  # type: ignore[assignment]


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


# Project contact placeholder. Override with LITSEARCH_MAILTO or UNPAYWALL_EMAIL.
# Unpaywall and polite pools only need a contact string, not a registered key.
DEFAULT_CONTACT_EMAIL = "litsearch@users.noreply.github.com"


def _repo_root() -> Path:
    # src/litsearch/config.py -> repository root
    try:
        return Path(__file__).resolve().parents[2]
    except IndexError:  # pragma: no cover
        return Path.cwd()


def _candidate_env_files() -> list[Path]:
    paths: list[Path] = []
    explicit = os.environ.get("LITSEARCH_ENV_FILE", "").strip()
    if explicit:
        paths.append(Path(explicit))
    paths.append(_repo_root() / ".env")
    paths.append(Path.cwd() / ".env")
    paths.append(Path.home() / ".config" / "litsearch" / ".env")
    return paths


def load_dotenv(paths: list[Path] | None = None) -> Path | None:
    """Load the first existing .env without overriding real environment variables.

    This is a deliberately small parser: KEY=VALUE, optional quotes, comments.
    Secrets are never printed or logged.
    """
    for path in paths or _candidate_env_files():
        if not path.is_file():
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.lower().startswith("export "):
                line = line[7:].strip()
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and value:
                os.environ.setdefault(key, value)
        return path
    return None


# Load .env at import time so Config() and ad-hoc scripts see the same values.
load_dotenv()

_ENV_FOR_FIELD = {
    "mailto": "LITSEARCH_MAILTO",
    "ncbi_api_key": "NCBI_API_KEY",
    "openalex_api_key": "OPENALEX_API_KEY",
    "s2_api_key": "S2_API_KEY",
    "unpaywall_email": "UNPAYWALL_EMAIL",
    "cache_dir": "LITSEARCH_CACHE_DIR",
    "timeout": "LITSEARCH_TIMEOUT_SECONDS",
    "user_agent": "LITSEARCH_USER_AGENT",
    "allow_keyless_optional": "LITSEARCH_ALLOW_KEYLESS_OPTIONAL",
}


@dataclass
class Config:
    mailto: str = field(default_factory=lambda: _env("LITSEARCH_MAILTO") or DEFAULT_CONTACT_EMAIL)
    ncbi_api_key: str = field(default_factory=lambda: _env("NCBI_API_KEY"))
    openalex_api_key: str = field(default_factory=lambda: _env("OPENALEX_API_KEY"))
    s2_api_key: str = field(default_factory=lambda: _env("S2_API_KEY"))
    unpaywall_email: str = field(
        default_factory=lambda: _env("UNPAYWALL_EMAIL")
        or _env("LITSEARCH_MAILTO")
        or DEFAULT_CONTACT_EMAIL
    )
    cache_dir: Path = field(
        default_factory=lambda: Path(
            _env("LITSEARCH_CACHE_DIR", str(Path.home() / ".cache" / "litsearch"))
        )
    )
    timeout: int = field(default_factory=lambda: int(_env("LITSEARCH_TIMEOUT_SECONDS", "30") or 30))
    user_agent: str = field(default_factory=lambda: _env("LITSEARCH_USER_AGENT"))
    allow_keyless_optional: bool = field(
        default_factory=lambda: _env("LITSEARCH_ALLOW_KEYLESS_OPTIONAL", "").lower() in {"1", "true", "yes"}
    )

    def ua(self) -> str:
        if self.user_agent:
            return self.user_agent
        suffix = f" (+{self.mailto})" if self.mailto else ""
        return f"litsearch/0.1{suffix}"

    def min_interval(self, host: str) -> float:
        host = host.lower()
        if "arxiv.org" in host:
            return 3.0
        if "ncbi.nlm.nih.gov" in host:
            return 0.11 if self.ncbi_api_key else 0.34
        if "crossref.org" in host:
            return 1.0
        if "europepmc.org" in host:
            return 0.2
        if "openaire.eu" in host:
            # Anonymous ~60 req/hour; the compiler caps OpenAIRE to 2 queries/run.
            return 1.0
        if "doaj.org" in host:
            return 0.5
        if "dblp.org" in host:
            return 1.0
        if "opencitations.net" in host:
            return 0.34
        if "openalex.org" in host:
            return 0.2 if self.openalex_api_key else 1.0
        if "semanticscholar.org" in host:
            # Free keys guarantee ~1 request/second. Stay at or below that;
            # keyless requests share a contended public pool.
            return 1.1
        return 0.5


def _candidate_config_files() -> list[Path]:
    paths: list[Path] = []
    explicit = os.environ.get("LITSEARCH_CONFIG", "").strip()
    if explicit:
        paths.append(Path(explicit))
    paths.append(_repo_root() / "litsearch.toml")
    paths.append(Path.cwd() / "litsearch.toml")
    paths.append(Path.home() / ".config" / "litsearch" / "litsearch.toml")
    return paths


def load_config(config_file: str | Path | None = None) -> Config:
    load_dotenv()
    cfg = Config()
    if config_file is not None:
        path = Path(config_file)
    else:
        path = next((p for p in _candidate_config_files() if p.is_file()), Path("litsearch.toml"))
    if path.exists() and tomllib is not None:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
        section = data.get("litsearch", data)
        for key, env_name in _ENV_FOR_FIELD.items():
            if key in section and section[key] not in ("", None) and not os.environ.get(env_name):
                if key == "cache_dir":
                    cfg.cache_dir = Path(section[key])
                elif key == "timeout":
                    cfg.timeout = int(section[key])
                elif key == "allow_keyless_optional":
                    cfg.allow_keyless_optional = bool(section[key])
                else:
                    setattr(cfg, key, str(section[key]))
    return cfg
