"""Cheap, dependency-free HTTP probing.

The probe deliberately does not launch a browser. Its job is to answer one
question: which acquisition lane is worth trying first?
"""

from __future__ import annotations

import gzip
import re
import time
import zlib
from html.parser import HTMLParser
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from .models import PageKind, ProbeResult
from .utils import truncate, unique_preserve_order

MAX_BODY = 3_000_000
DEFAULT_TIMEOUT = 20

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "identity",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Upgrade-Insecure-Requests": "1",
}

SAFE_HEADERS = {
    "server",
    "content-type",
    "content-length",
    "content-encoding",
    "cf-ray",
    "cf-mitigated",
    "cf-cache-status",
    "x-powered-by",
    "via",
    "date",
    "cache-control",
    "location",
    "strict-transport-security",
}

CHALLENGE_MARKERS = (
    "just a moment",
    "enable javascript and cookies",
    "attention required",
    "cf-chl",
    "cf_chl",
    "checking your browser",
    "verify you are human",
    "captcha",
    "datadome",
    "perimeterx",
    "px-captcha",
    "access denied",
    "request blocked",
)

CAPTCHA_MARKERS = (
    "captcha",
    "recaptcha",
    "hcaptcha",
    "turnstile",
    "px-captcha",
    "geetest",
)

SIGNATURE_WORDS = (
    "sign",
    "signature",
    "encrypt",
    "decrypt",
    "nonce",
    "timestamp",
    "hmac",
    "aes",
    "rsa",
    "x-sign",
    "x-signature",
    "token",
)

SIGNATURE_RE = re.compile(
    r"\b(" + "|".join(re.escape(word) for word in SIGNATURE_WORDS) + r")\b",
    re.IGNORECASE,
)
QUERY_SIGNATURE_RE = re.compile(
    r"[?&](sign|signature|token|timestamp|nonce|encrypt|key)=", re.IGNORECASE
)
ABSOLUTE_URL_RE = re.compile(r"https?://[^\s\"'<>\\`]+", re.IGNORECASE)
RELATIVE_URL_RE = re.compile(r"[\"'`](/[^\"'`\s<>\\]{2,300})[\"'`]")
CALL_URL_RE = re.compile(
    r"(?:fetch|axios\.(?:get|post|put|patch|delete)|\.open)\(\s*[\"'`]([^\"'`]+)[\"'`]",
    re.IGNORECASE,
)
NEXT_DATA_RE = re.compile(r"__NEXT_DATA__", re.IGNORECASE)
NUXT_RE = re.compile(r"__NUXT__|window\.__NUXT__", re.IGNORECASE)
INITIAL_STATE_RE = re.compile(r"__INITIAL_STATE__|__APOLLO_STATE__|__PRELOADED_STATE__", re.IGNORECASE)
EMPTY_ROOT_RE = re.compile(
    r"<div[^>]+id=[\"'](?:root|app|__next)[\"'][^>]*>\s*</div>", re.IGNORECASE
)


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self.scripts: list[str] = []
        self.inline_script_bytes = 0
        self.inline_script_count = 0
        self.forms = 0
        self.meta_generator = ""
        self.lang = ""
        self.ld_json = False
        self._in_title = False
        self._in_script = False
        self._in_style = False
        self._script_is_ld_json = False
        self._script_has_src = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key.lower(): (value or "") for key, value in attrs}
        if tag == "html":
            self.lang = attributes.get("lang", "")
        elif tag == "title":
            self._in_title = True
        elif tag == "script":
            self._in_script = True
            self._script_has_src = bool(attributes.get("src"))
            self._script_is_ld_json = attributes.get("type", "").lower() == "application/ld+json"
            if self._script_has_src:
                self.scripts.append(attributes["src"])
            else:
                self.inline_script_count += 1
            if self._script_is_ld_json:
                self.ld_json = True
        elif tag == "style":
            self._in_style = True
        elif tag == "form":
            self.forms += 1
        elif tag == "meta":
            name = attributes.get("name", "").lower()
            if name == "generator":
                self.meta_generator = attributes.get("content", "")

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_parts.append(data)
        if self._in_script:
            if not self._script_has_src and not self._script_is_ld_json:
                self.inline_script_bytes += len(data.encode("utf-8", errors="ignore"))
            return
        if self._in_style:
            return
        self.text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag == "script":
            self._in_script = False
            self._script_has_src = False
            self._script_is_ld_json = False
        elif tag == "style":
            self._in_style = False


def _normalize_url(url: str) -> str:
    value = (url or "").strip()
    if not value:
        raise ValueError("URL is empty")
    if "://" not in value:
        value = "https://" + value
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme}")
    if not parsed.netloc:
        raise ValueError(f"URL has no host: {value}")
    return value


def _decode_body(raw: bytes, content_type: str, content_encoding: str) -> str:
    if content_encoding.lower() == "gzip":
        try:
            raw = gzip.decompress(raw)
        except OSError:
            pass
    elif content_encoding.lower() == "deflate":
        try:
            raw = zlib.decompress(raw)
        except zlib.error:
            pass

    charset = "utf-8"
    match = re.search(r"charset=([A-Za-z0-9._-]+)", content_type or "", re.IGNORECASE)
    if match:
        charset = match.group(1)
    try:
        return raw.decode(charset, errors="replace")
    except LookupError:
        return raw.decode("utf-8", errors="replace")


def _safe_headers(headers: object) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in dict(headers).items():
        key_lower = key.lower()
        if key_lower in SAFE_HEADERS:
            result[key_lower] = truncate(str(value), 500)
    return result


def _looks_like_api(value: str) -> bool:
    lowered = value.lower()
    if len(value) > 500:
        return False
    markers = ("/api", "graphql", ".json", "/v1/", "/v2/", "/v3/", "ajax", "xhr", "/rest/")
    return any(marker in lowered for marker in markers)


def _extract_api_candidates(body: str, script_srcs: Iterable[str], base_url: str) -> list[str]:
    candidates: list[str] = []
    for match in ABSOLUTE_URL_RE.findall(body):
        if _looks_like_api(match):
            candidates.append(match)
    for match in RELATIVE_URL_RE.findall(body):
        if _looks_like_api(match):
            candidates.append(urljoin(base_url, match))
    for match in CALL_URL_RE.findall(body):
        if _looks_like_api(match):
            candidates.append(urljoin(base_url, match))
    for src in script_srcs:
        if _looks_like_api(src):
            candidates.append(urljoin(base_url, src))
    return unique_preserve_order(candidates)[:20]


def _extract_signature_hints(body: str, script_srcs: Iterable[str]) -> list[str]:
    haystack = "\n".join([body, *script_srcs])
    hits = [match.group(1).lower() for match in SIGNATURE_RE.finditer(haystack)]
    return unique_preserve_order(hits)[:12]


def analyze_html(
    html: str,
    *,
    url: str,
    status: int,
    content_type: str,
    headers: dict[str, str],
) -> ProbeResult:
    parser = PageParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        pass

    title = " ".join(parser.title_parts).strip()
    text = re.sub(r"\s+", " ", " ".join(parser.text_parts)).strip()
    lowered = html.lower()
    script_count = len(parser.scripts) + parser.inline_script_count
    next_data = bool(NEXT_DATA_RE.search(html))
    nuxt = bool(NUXT_RE.search(html))
    initial_state = bool(INITIAL_STATE_RE.search(html))
    empty_root = bool(EMPTY_ROOT_RE.search(html))
    thin_inline_shell = len(text) < 200 and parser.inline_script_bytes >= 1000
    challenge = any(marker in lowered for marker in CHALLENGE_MARKERS)
    captcha = any(marker in lowered for marker in CAPTCHA_MARKERS)
    cloudflare = "cf-ray" in headers or "cloudflare" in headers.get("server", "").lower()
    signed_query = bool(QUERY_SIGNATURE_RE.search(html))

    if content_type and "json" in content_type.lower():
        page_kind = PageKind.JSON_API.value
    elif status in {403, 429} or challenge:
        page_kind = PageKind.BLOCKED.value
    elif status >= 400:
        page_kind = PageKind.UNKNOWN.value
    elif (
        next_data
        or nuxt
        or initial_state
        or empty_root
        or thin_inline_shell
        or (script_count >= 5 and len(text) < 400)
    ):
        page_kind = PageKind.SPA_SHELL.value
    elif len(text) >= 200 or (len(text) >= 50 and script_count <= 2):
        page_kind = PageKind.STATIC_HTML.value
    elif script_count:
        page_kind = PageKind.SPA_SHELL.value
    else:
        page_kind = PageKind.UNKNOWN.value

    signature_hints = _extract_signature_hints(html, parser.scripts)
    if signed_query and "sign" not in signature_hints:
        signature_hints.append("sign")

    return ProbeResult(
        url=url,
        final_url=url,
        status=status,
        content_type=content_type,
        bytes_read=len(html.encode("utf-8", errors="ignore")),
        title=title,
        lang=parser.lang,
        page_kind=page_kind,
        script_count=script_count,
        inline_script_bytes=parser.inline_script_bytes,
        form_count=parser.forms,
        visible_text_chars=len(text),
        api_candidates=_extract_api_candidates(html, parser.scripts, url),
        signature_hints=signature_hints,
        cloudflare=cloudflare,
        challenge=challenge,
        captcha=captcha,
        next_data=next_data,
        nuxt=nuxt,
        initial_state=initial_state,
        ld_json=parser.ld_json,
        meta_generator=parser.meta_generator,
        body_preview=truncate(text or html, 600),
        headers=headers,
    )


def analyze_json(
    body: str,
    *,
    url: str,
    status: int,
    content_type: str,
    headers: dict[str, str],
) -> ProbeResult:
    preview = truncate(body, 600)
    hints = _extract_signature_hints(body, [])
    return ProbeResult(
        url=url,
        final_url=url,
        status=status,
        content_type=content_type,
        bytes_read=len(body.encode("utf-8", errors="ignore")),
        page_kind=PageKind.JSON_API.value,
        visible_text_chars=len(body),
        api_candidates=[url],
        signature_hints=hints,
        body_preview=preview,
        headers=headers,
    )


def probe_target(
    url: str,
    *,
    timeout: int = DEFAULT_TIMEOUT,
    headers: dict[str, str] | None = None,
    method: str = "GET",
    body: bytes | None = None,
) -> ProbeResult:
    """Fetch a URL with a browser-like request and classify the response."""

    normalized = _normalize_url(url)
    request_headers = dict(DEFAULT_HEADERS)
    if headers:
        request_headers.update(headers)
    request = Request(normalized, headers=request_headers, method=method.upper(), data=body)
    started = time.perf_counter()

    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read(MAX_BODY + 1)
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            status = int(getattr(response, "status", 0) or 0)
            final_url = response.geturl()
            response_headers = _safe_headers(response.headers)
            content_type = response_headers.get("content-type", "")
            text = _decode_body(raw[:MAX_BODY], content_type, response_headers.get("content-encoding", ""))
            if "json" in content_type.lower() or text.lstrip().startswith(("{", "[")):
                result = analyze_json(
                    text,
                    url=normalized,
                    status=status,
                    content_type=content_type,
                    headers=response_headers,
                )
            else:
                result = analyze_html(
                    text,
                    url=normalized,
                    status=status,
                    content_type=content_type,
                    headers=response_headers,
                )
            result.final_url = final_url
            result.elapsed_ms = elapsed_ms
            result.bytes_read = len(raw)
            return result
    except HTTPError as error:
        raw = b""
        try:
            raw = error.read(MAX_BODY)
        except Exception:
            pass
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        response_headers = _safe_headers(error.headers)
        content_type = response_headers.get("content-type", "")
        text = _decode_body(raw, content_type, response_headers.get("content-encoding", ""))
        result = analyze_html(
            text,
            url=normalized,
            status=int(error.code or 0),
            content_type=content_type,
            headers=response_headers,
        )
        result.final_url = str(error.geturl() or normalized)
        result.elapsed_ms = elapsed_ms
        result.bytes_read = len(raw)
        if result.page_kind not in {PageKind.BLOCKED.value, PageKind.STATIC_HTML.value}:
            result.page_kind = PageKind.UNKNOWN.value
        return result
    except (URLError, TimeoutError, OSError, ValueError) as error:
        reason = getattr(error, "reason", error)
        return ProbeResult(
            url=normalized,
            status=0,
            error=str(reason),
            elapsed_ms=int((time.perf_counter() - started) * 1000),
        )
