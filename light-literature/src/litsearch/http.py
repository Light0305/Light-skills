from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse, urlunparse

import requests

from . import cache
from .config import Config


class HttpError(RuntimeError):
    def __init__(self, status: int, message: str, url: str = "") -> None:
        super().__init__(message)
        self.status = status
        self.url = url


@dataclass
class Response:
    data: Any
    status: int
    url: str
    cache_hit: bool = False


class HttpClient:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": config.ua(), "Accept": "application/json, text/xml, */*"})
        self._last: dict[str, float] = {}

    def _throttle(self, url: str) -> None:
        host = urlparse(url).netloc.lower()
        interval = self.config.min_interval(host)
        last = self._last.get(host)
        if last is not None:
            wait = interval - (time.monotonic() - last)
            if wait > 0:
                time.sleep(wait)
        self._last[host] = time.monotonic()

    @staticmethod
    def _cache_url(url: str) -> str:
        # The query string may contain API keys. Cache key should still be stable,
        # but we avoid persisting the full URL in logs.
        return urlunparse(urlparse(url)._replace(query=""))

    def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        *,
        headers: dict[str, str] | None = None,
        parse: str = "json",
        ttl: int = 86400,
        use_cache: bool = True,
        refresh: bool = False,
        timeout: int | None = None,
        retries: int = 3,
    ) -> Response:
        params = {k: v for k, v in (params or {}).items() if v is not None}
        cache_url = self._cache_url(url)
        if use_cache and not refresh:
            cached = cache.get(self.config.cache_dir, "GET", cache_url, params, ttl)
            if cached is not None:
                return Response(cached, 200, url, cache_hit=True)

        last_error: Exception | None = None
        retries = max(0, retries)
        for attempt in range(retries + 1):
            self._throttle(url)
            try:
                resp = self.session.get(
                    url,
                    params=params,
                    headers=headers or {},
                    timeout=timeout or self.config.timeout,
                )
            except requests.RequestException as exc:
                last_error = exc
                if attempt >= retries:
                    raise HttpError(0, str(exc), url) from exc
                time.sleep(1.5**attempt)
                continue

            if resp.status_code == 429 or 500 <= resp.status_code < 600:
                retry_after = resp.headers.get("Retry-After")
                delay = float(retry_after) if retry_after and retry_after.isdigit() else 1.5**attempt
                last_error = HttpError(resp.status_code, resp.text[:200], url)
                if attempt >= retries:
                    raise last_error
                time.sleep(min(delay, 60))
                continue

            if resp.status_code >= 400:
                raise HttpError(resp.status_code, resp.text[:300], url)

            if parse == "json":
                try:
                    data = resp.json()
                except ValueError as exc:
                    raise HttpError(resp.status_code, "Invalid JSON response", url) from exc
            else:
                data = resp.text

            if use_cache:
                cache.set(self.config.cache_dir, "GET", cache_url, params, data)
            return Response(data, resp.status_code, url)

        raise HttpError(0, str(last_error or "request failed"), url)


def redact_params(params: dict[str, Any]) -> dict[str, Any]:
    secret_keys = {"api_key", "key", "x-api-key", "apikey", "token"}
    return {
        k: ("***" if k.lower() in secret_keys else v)
        for k, v in params.items()
    }
