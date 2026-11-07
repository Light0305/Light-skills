from __future__ import annotations

import hashlib
import itertools
import os
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from .adapters import get_adapter
from .config import Config, load_config
from .io import read_jsonl, write_json, write_jsonl
from .models import Paper

OA_STATUSES = {"gold", "green", "hybrid", "bronze", "open", "diamond"}
OA_HOSTS = {
    "arxiv.org",
    "aclanthology.org",
    "europepmc.org",
    "ncbi.nlm.nih.gov",
    "mdpi.com",
    "frontiersin.org",
    "researchsquare.com",
    "rogue-scholar.org",
    "zenodo.org",
    "hal.science",
    "openreview.net",
    "proceedings.mlr.press",
    "openaccess.thecvf.com",
    "jmlr.org",
}
MAX_BYTES = 100 * 1024 * 1024
MAX_SECONDS_PER_FILE = 45
MAX_TOTAL_SECONDS = 300


def _host(url: str) -> str:
    return (urlparse(url).netloc or "").lower()


def is_downloadable(paper: Paper, url: str) -> bool:
    host = _host(url)
    if paper.arxiv_id and "arxiv.org" in host:
        return True
    if any(host == h or host.endswith("." + h) for h in OA_HOSTS):
        return True
    return (paper.oa_status or "").lower() in OA_STATUSES


def candidate_urls(paper: Paper) -> list[str]:
    urls: list[str] = []
    if paper.arxiv_id:
        urls.append(f"https://arxiv.org/pdf/{paper.arxiv_id}")
    if paper.pmcid:
        urls.append(f"https://www.ncbi.nlm.nih.gov/pmc/articles/{paper.pmcid}/pdf/")
    if paper.pdf_url:
        urls.append(paper.pdf_url)
    seen = set()
    out = []
    for url in urls:
        if url and url not in seen:
            seen.add(url)
            out.append(url)
    return out


def _download(url: str, target: Path, config: Config) -> dict[str, Any]:
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": config.ua(), "Accept": "application/pdf,*/*"},
            timeout=(10, 30),
            stream=True,
            allow_redirects=True,
        )
    except requests.RequestException as exc:
        return {"status": "error", "reason": str(exc)[:200]}
    with resp:
        if resp.status_code in {401, 403}:
            return {"status": "blocked", "reason": f"HTTP {resp.status_code}"}
        if resp.status_code != 200:
            return {"status": "http_error", "reason": f"HTTP {resp.status_code}"}
        content_type = resp.headers.get("Content-Type", "").lower()
        length = resp.headers.get("Content-Length")
        if length and length.isdigit() and int(length) > MAX_BYTES:
            return {"status": "too_large", "reason": f"Content-Length {length}"}
        chunks = resp.iter_content(chunk_size=1024 * 256)
        try:
            first = next(chunks)
        except StopIteration:
            return {"status": "empty", "reason": "empty response"}
        except requests.RequestException as exc:
            return {"status": "error", "reason": str(exc)[:200]}
        if b"%PDF" not in first[:1024] and "application/pdf" not in content_type:
            return {
                "status": "not_pdf",
                "reason": f"content-type={content_type or 'unknown'}",
            }
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(".part")
        digest = hashlib.sha256()
        total = 0
        started = time.monotonic()
        try:
            with tmp.open("wb") as fh:
                for chunk in itertools.chain([first], chunks):
                    if time.monotonic() - started > MAX_SECONDS_PER_FILE:
                        raise TimeoutError("download exceeded time cap")
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > MAX_BYTES:
                        raise ValueError("file exceeds size cap")
                    digest.update(chunk)
                    fh.write(chunk)
        except Exception as exc:  # noqa: BLE001
            tmp.unlink(missing_ok=True)
            return {"status": "error", "reason": str(exc)[:200]}
        os.replace(tmp, target)
        return {
            "status": "downloaded",
            "path": str(target),
            "bytes": total,
            "sha256": digest.hexdigest(),
            "content_type": content_type,
        }


def fetch_pdfs(
    run_dir: str | Path,
    *,
    limit: int = 20,
    out_dir: str | Path | None = None,
    config: Config | None = None,
) -> dict[str, Any]:
    config = config or load_config()
    run_dir = Path(run_dir)
    out_dir = Path(out_dir) if out_dir else run_dir / "pdfs"
    papers = [Paper.from_dict(x) for x in read_jsonl(run_dir / "papers.jsonl")]
    papers.sort(key=lambda p: p.discovery_score.get("total", 0), reverse=True)
    client = None
    unpaywall = None
    items: list[dict[str, Any]] = []
    downloaded = 0
    already_present = 0
    unavailable = 0
    checked = 0
    started_total = time.monotonic()
    for paper in papers:
        if checked >= limit:
            break
        if time.monotonic() - started_total > MAX_TOTAL_SECONDS:
            items.append(
                {
                    "paper_id": paper.paper_id,
                    "title": paper.title,
                    "doi": paper.doi,
                    "status": "budget_exhausted",
                    "reason": f"total time budget {MAX_TOTAL_SECONDS}s exhausted",
                }
            )
            break
        if paper.pdf_path and Path(paper.pdf_path).exists():
            already_present += 1
            items.append(
                {
                    "paper_id": paper.paper_id,
                    "title": paper.title,
                    "doi": paper.doi,
                    "status": "already_present",
                    "path": paper.pdf_path,
                }
            )
            continue
        urls = candidate_urls(paper)
        if paper.doi and config.unpaywall_email:
            if client is None:
                from .http import HttpClient

                client = HttpClient(config)
                unpaywall = get_adapter("unpaywall", client, config)
            data = unpaywall.enrich(paper) if unpaywall else {}
            if data.get("pdf_url"):
                paper.pdf_url = data["pdf_url"]
            if data.get("oa_status"):
                paper.oa_status = data["oa_status"]
            if data.get("license"):
                paper.license = data["license"]
            for url in data.get("pdf_urls", []) or []:
                if url and url not in urls:
                    urls.append(url)
        if not urls:
            items.append(
                {
                    "paper_id": paper.paper_id,
                    "title": paper.title,
                    "doi": paper.doi,
                    "status": "unavailable",
                    "reason": "no DOI/arXiv/PDF URL",
                }
            )
            unavailable += 1
            continue
        checked += 1
        result: dict[str, Any] | None = None
        used_url = ""
        for url in urls:
            if not is_downloadable(paper, url):
                result = {
                    "status": "unavailable",
                    "reason": "not confirmed OA; use institutional access or author copy",
                }
                continue
            target = out_dir / f"{paper.paper_id}.pdf"
            attempt = _download(url, target, config)
            if attempt.get("status") == "downloaded":
                result = attempt
                used_url = url
                break
            result = attempt
        if result and result.get("status") == "downloaded":
            paper.pdf_path = str(result["path"])
            paper.pdf_status = "downloaded"
            paper.pdf_source = used_url
            paper.pdf_sha256 = str(result.get("sha256", ""))
            downloaded += 1
            items.append(
                {
                    "paper_id": paper.paper_id,
                    "title": paper.title,
                    "doi": paper.doi,
                    "status": "downloaded",
                    "path": result["path"],
                    "url": used_url,
                    "bytes": result.get("bytes", 0),
                    "sha256": result.get("sha256", ""),
                    "content_type": result.get("content_type", ""),
                }
            )
        else:
            paper.pdf_status = str((result or {}).get("status", "unavailable"))
            unavailable += 1
            items.append(
                {
                    "paper_id": paper.paper_id,
                    "title": paper.title,
                    "doi": paper.doi,
                    "status": paper.pdf_status,
                    "reason": str((result or {}).get("reason", "")),
                }
            )
    write_jsonl(run_dir / "papers.jsonl", [p.to_dict() for p in papers])
    summary = {
        "status": "ok",
        "limit": limit,
        "checked": checked,
        "downloaded": downloaded,
        "already_present": already_present,
        "available": downloaded + already_present,
        "unavailable": unavailable,
        "out_dir": str(out_dir),
        "items": items,
    }
    write_json(run_dir / "pdf_manifest.json", summary)
    return summary
