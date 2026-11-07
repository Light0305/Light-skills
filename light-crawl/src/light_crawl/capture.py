"""Capture an HTTP or browser response into the case fixture bus."""

from __future__ import annotations

import hashlib
import shutil
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .models import Phase, PHASE_ORDER
from .integrity import fingerprint
from .probe import DEFAULT_HEADERS, _normalize_url, _safe_headers
from .state import CaseStore, LightCrawlError
from .utils import system_chrome_path, utc_now, write_json


MAX_CAPTURE_BYTES = 10_000_000


@dataclass
class CaptureResult:
    url: str
    final_url: str
    status: int
    headers: dict[str, str]
    content_type: str
    body: bytes
    elapsed_ms: int
    body_path: Path
    meta_path: Path
    request_path: Path
    sha256: str
    engine: str
    truncated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "final_url": self.final_url,
            "status": self.status,
            "headers": self.headers,
            "content_type": self.content_type,
            "bytes": len(self.body),
            "elapsed_ms": self.elapsed_ms,
            "body_path": str(self.body_path),
            "meta_path": str(self.meta_path),
            "request_path": str(self.request_path),
            "sha256": self.sha256,
            "engine": self.engine,
            "truncated": self.truncated,
        }


def _extension(content_type: str, body: bytes) -> str:
    lowered = (content_type or "").lower()
    if "json" in lowered:
        return ".json"
    if "html" in lowered or "xml" in lowered:
        return ".html"
    if "text/" in lowered:
        return ".txt"
    if body.lstrip().startswith((b"{", b"[")):
        return ".json"
    return ".bin"


def _request_headers(headers: dict[str, str], *, engine: str) -> dict[str, str]:
    if engine.startswith("scrapling"):
        return {"accept": "text/html,application/json", "user-agent": "scrapling-stealth"}
    return {
        "accept": headers.get("Accept", ""),
        "accept-language": headers.get("Accept-Language", ""),
        "user-agent": headers.get("User-Agent", ""),
    }


def _save_fixtures(
    store: CaseStore,
    *,
    url: str,
    final_url: str,
    status: int,
    headers: dict[str, str],
    content_type: str,
    body: bytes,
    elapsed_ms: int,
    request_headers: dict[str, str],
    engine: str,
    network: list[dict[str, Any]] | None = None,
    truncated: bool = False,
) -> CaptureResult:
    digest = hashlib.sha256(body).hexdigest()
    extension = _extension(content_type, body)
    if headers.get('content-encoding', '').lower() not in ('', 'identity'):
        extension = '.bin'
    capture_dir = store.fixtures_dir / 'captures' / ('CAP-' + uuid.uuid4().hex)
    capture_dir.mkdir(parents=True, exist_ok=False)
    body_path = capture_dir / f"response{extension}"
    body_path.write_bytes(body)

    request_path = capture_dir / "request.json"
    write_json(
        request_path,
        {
            "method": "GET",
            "url": url,
            "headers": request_headers,
            "params": {},
            "json": None,
            "data": None,
            "cookies": {},
            "engine": engine,
        },
    )

    meta_path = capture_dir / "response.meta.json"
    meta = {
        "url": url,
        "final_url": final_url,
        "status": status,
        "content_type": content_type,
        "bytes": len(body),
        "sha256": digest,
        "body_path": body_path.relative_to(store.directory).as_posix(),
        "truncated": truncated,
        "representation": 'rendered_browser_body' if engine.startswith('scrapling') else 'http_response_bytes',
        "request_headers_recording": 'logical allow-list only; not a full wire request',
        "elapsed_ms": elapsed_ms,
        "fetched_at": utc_now(),
        "headers": headers,
        "engine": engine,
        "note": "Headers are allow-listed; cookies and authorization are not persisted.",
    }
    if network:
        meta["network"] = network
    write_json(meta_path, meta)
    for path, kind in ((body_path, 'capture_body'), (request_path, 'capture_request'), (meta_path, 'capture_meta')):
        relative = path.relative_to(store.directory).as_posix()
        store.state.artifacts[relative] = {**fingerprint(path), 'kind': kind, 'label': path.name, 'added_at': utc_now()}
        # Compatibility working copies; evidence and handoffs always use the versioned files.
        shutil.copy2(path, store.fixtures_dir / path.name)

    store.state.metrics.update(
        {
            "last_capture_status": status,
            "last_capture_bytes": len(body),
            "last_capture_ms": elapsed_ms,
            "last_capture_at": utc_now(),
            "last_capture_meta": meta_path.relative_to(store.directory).as_posix(),
            "last_capture_truncated": truncated,
        }
    )
    if engine.startswith("scrapling"):
        store.state.metrics["last_capture_browser_seconds"] = round(elapsed_ms / 1000, 3)
    store.save()
    store.add_evidence(
        phase=store.state.phase,
        source="light-crawl capture",
        action=f"GET {url} via {engine}",
        observation=(
            f"status={status}; bytes={len(body)}; content_type={content_type or 'unknown'}; "
            f"fixture={body_path.relative_to(store.directory).as_posix()}"
        ),
        inference="raw response captured for offline selector/schema work",
        confidence="high" if status < 400 else "medium",
        artifact=body_path.relative_to(store.directory).as_posix(),
        metadata={'capture_meta': meta_path.relative_to(store.directory).as_posix(), 'sha256': digest,
                  'truncated': truncated, 'status': status},
    )

    current_index = PHASE_ORDER.index(Phase(store.state.phase))
    captured_index = PHASE_ORDER.index(Phase.CAPTURED)
    if current_index < captured_index:
        store.advance(Phase.CAPTURED, f"captured {body_path.name} ({len(body)} bytes)")

    return CaptureResult(
        url=url,
        final_url=final_url,
        status=status,
        headers=headers,
        content_type=content_type,
        body=body,
        elapsed_ms=elapsed_ms,
        body_path=body_path,
        meta_path=meta_path,
        request_path=request_path,
        sha256=digest,
        engine=engine,
        truncated=truncated,
    )


def _capture_http(
    store: CaseStore,
    url: str,
    *,
    timeout: int,
    max_bytes: int,
    extra_headers: dict[str, str] | None,
) -> CaptureResult:
    headers = dict(DEFAULT_HEADERS)
    if extra_headers:
        headers.update(extra_headers)
    request = Request(url, headers=headers, method="GET")

    started = time.perf_counter()
    try:
        with urlopen(request, timeout=max(1, timeout)) as response:
            raw = response.read(max_bytes + 1)
            status = int(getattr(response, "status", 0) or 0)
            final_url = response.geturl()
            response_headers = _safe_headers(response.headers)
            content_type = response_headers.get("content-type", "")
    except HTTPError as error:
        raw = error.read(max_bytes + 1)
        status = int(error.code or 0)
        final_url = str(error.geturl() or url)
        response_headers = _safe_headers(error.headers)
        content_type = response_headers.get("content-type", "")
    except (URLError, TimeoutError, OSError, ValueError) as error:
        raise LightCrawlError(f"capture failed for {url}: {error}") from error

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    truncated = len(raw) > max_bytes
    if truncated:
        raw = raw[:max_bytes]
        store.add_blocker(f"capture truncated at {max_bytes} bytes; inspect manually if the body matters")

    return _save_fixtures(
        store,
        url=url,
        final_url=final_url,
        status=status,
        headers=response_headers,
        content_type=content_type,
        body=raw,
        elapsed_ms=elapsed_ms,
        request_headers=_request_headers(headers, engine="http"),
        engine="http",
        truncated=truncated,
    )


def _capture_browser(
    store: CaseStore,
    url: str,
    *,
    timeout: int,
    max_bytes: int,
    headed: bool,
    solve_cloudflare: bool,
    wait_selector: str,
) -> CaptureResult:
    try:
        from scrapling.fetchers import StealthySession
    except ImportError as error:  # pragma: no cover - exercised only without Scrapling
        raise LightCrawlError(
            "Browser capture needs Scrapling. Install with `pip install -e \".[fetchers]\"` "
            "and run `scrapling install`."
        ) from error

    started = time.perf_counter()
    network: list[dict[str, Any]] = []
    session_kwargs: dict[str, Any] = {
        "headless": not headed,
        "real_chrome": system_chrome_path() is not None,
        "network_idle": True,
        "record_requests": True,
        "timeout": max(1000, timeout * 1000),
    }
    fetch_kwargs: dict[str, Any] = {}
    if solve_cloudflare:
        fetch_kwargs["solve_cloudflare"] = True
    if wait_selector:
        fetch_kwargs["wait_selector"] = wait_selector

    try:
        with StealthySession(**session_kwargs) as session:
            page = session.fetch(url, **fetch_kwargs)
            raw = page.body if isinstance(page.body, (bytes, bytearray)) else b""
            if not raw:
                raw = (page.html_content or "").encode("utf-8", errors="replace")
            status = int(getattr(page, "status", 0) or 0)
            final_url = str(getattr(page, "url", url) or url)
            try:
                records = session.network.search(limit=200)
            except Exception:
                records = []
            for record in records:
                record_body = getattr(record, "body", b"") or b""
                network.append(
                    {
                        "url": str(getattr(record, "url", "")),
                        "status": int(getattr(record, "status", 0) or 0),
                        "bytes": len(record_body) if isinstance(record_body, (bytes, bytearray)) else 0,
                    }
                )
    except Exception as error:
        raise LightCrawlError(f"browser capture failed for {url}: {error}") from error

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    truncated = len(raw) > max_bytes
    if truncated:
        raw = raw[:max_bytes]
        store.add_blocker(f"browser capture truncated at {max_bytes} bytes")

    return _save_fixtures(
        store,
        url=url,
        final_url=final_url,
        status=status,
        headers={},
        content_type="text/html; charset=utf-8",
        body=raw,
        elapsed_ms=elapsed_ms,
        request_headers=_request_headers({}, engine="scrapling-stealth"),
        engine="scrapling-stealth",
        network=network,
        truncated=truncated,
    )


def capture_target(
    store: CaseStore,
    *,
    timeout: int = 20,
    max_bytes: int = MAX_CAPTURE_BYTES,
    extra_headers: dict[str, str] | None = None,
    engine: str = "http",
    headed: bool = False,
    solve_cloudflare: bool = False,
    wait_selector: str = "",
) -> CaptureResult:
    if not store.target.authorized:
        raise LightCrawlError('Confirm the authorized/public-data scope before sending traffic')
    if type(max_bytes) is not int or max_bytes < 1:
        raise LightCrawlError('max_bytes must be a positive integer')
    if not store.probe_file.exists():
        raise LightCrawlError(
            "capture needs a probe first. Run `light-crawl probe <case>` so the capture is tied to a route."
        )
    target = store.target
    if target.kind.lower() in {"app", "electron", "asar", "apk", "ipa", "native", "binary"}:
        raise LightCrawlError(
            "capture is for HTTP targets. Use the REA lane for packaged/native targets."
        )
    url = _normalize_url(target.url)

    if engine == "http":
        return _capture_http(
            store,
            url,
            timeout=timeout,
            max_bytes=max_bytes,
            extra_headers=extra_headers,
        )
    if engine == "scrapling":
        return _capture_browser(
            store,
            url,
            timeout=timeout,
            max_bytes=max_bytes,
            headed=headed,
            solve_cloudflare=solve_cloudflare,
            wait_selector=wait_selector,
        )
    raise LightCrawlError(f"Unknown capture engine: {engine}. Use http or scrapling.")
