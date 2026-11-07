from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

from .io import ensure_dir


def _key(method: str, url: str, params: dict[str, Any]) -> str:
    payload = json.dumps(
        {"method": method, "url": url, "params": params},
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def get(cache_dir: str | Path, method: str, url: str, params: dict[str, Any], ttl: int) -> Any:
    path = Path(cache_dir) / f"{_key(method, url, params)}.json"
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except (OSError, ValueError):
        return None
    if time.time() - float(payload.get("ts", 0)) > ttl:
        return None
    return payload.get("data")


def set(cache_dir: str | Path, method: str, url: str, params: dict[str, Any], data: Any) -> None:
    ensure_dir(cache_dir)
    path = Path(cache_dir) / f"{_key(method, url, params)}.json"
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump({"ts": time.time(), "data": data}, fh, ensure_ascii=False)
    os.replace(tmp, path)
