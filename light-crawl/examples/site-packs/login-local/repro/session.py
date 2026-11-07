#!/usr/bin/env python
"""Persist and restore cookies for the local login fixture.

On Windows the state file is encrypted with DPAPI (the current user's
credentials). On other platforms it falls back to a 0600 JSON file and marks the
protection mode explicitly. Credentials are never written; only the cookie jar.
"""

from __future__ import annotations

import ctypes
import json
import os
from pathlib import Path
from urllib.parse import urlparse

if os.name == "nt":
    import ctypes.wintypes as wintypes

    DWORD = wintypes.DWORD
else:  # pragma: no cover - only the type declaration differs
    DWORD = ctypes.c_uint32

try:
    from scrapling.fetchers import FetcherSession
except ImportError as error:  # pragma: no cover - only without Scrapling
    raise SystemExit(
        "Scrapling is required. Run: pip install -e \".[fetchers]\""
    ) from error


DPAPI_MAGIC = b"DPAPI1\n"
CRYPTPROTECT_UI_FORBIDDEN = 0x1


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_char)),
    ]


def _blob(data: bytes) -> tuple[_DataBlob, ctypes.Array]:
    buffer = ctypes.create_string_buffer(data)
    return _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char))), buffer


def _dpapi_call(function, blob: _DataBlob) -> bytes:
    out = _DataBlob()
    ok = function(
        ctypes.byref(blob),
        "light-crawl login state",
        None,
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(out),
    )
    if not ok:
        raise OSError(ctypes.get_last_error(), "DPAPI call failed")
    try:
        return ctypes.string_at(out.pbData, out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(out.pbData)


def protect_bytes(data: bytes) -> bytes:
    if os.name != "nt":
        raise RuntimeError("DPAPI encryption is only available on Windows.")
    blob, _buffer = _blob(data)
    return _dpapi_call(ctypes.windll.crypt32.CryptProtectData, blob)


def unprotect_bytes(data: bytes) -> bytes:
    if os.name != "nt":
        raise RuntimeError("DPAPI decryption is only available on Windows.")
    blob, _buffer = _blob(data)
    return _dpapi_call(ctypes.windll.crypt32.CryptUnprotectData, blob)


def _force_plain() -> bool:
    return os.environ.get("LIGHT_CRAWL_FORCE_PLAIN") == "1"


def save_state(
    path: str | Path,
    payload: dict,
    *,
    protection: str = "auto",
) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    use_dpapi = protection == "dpapi" or (
        protection == "auto" and os.name == "nt" and not _force_plain()
    )
    if use_dpapi:
        path.write_bytes(DPAPI_MAGIC + protect_bytes(raw))
    else:
        path.write_text(
            json.dumps({**payload, "protection": "plain-0600"}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        try:
            path.chmod(0o600)
        except OSError:
            pass
    return path


def load_state(path: str | Path) -> dict:
    path = Path(path)
    raw = path.read_bytes()
    if raw.startswith(DPAPI_MAGIC):
        raw = unprotect_bytes(raw[len(DPAPI_MAGIC):])
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Session state must be a JSON object.")
    return data


def _host(base: str) -> str:
    return urlparse(base).hostname or "127.0.0.1"


def save_cookies(session, path: str | Path, base: str) -> Path:
    cookies = session._curl_session.cookies.get_dict()
    payload = {
        "host": _host(base),
        "cookies": cookies,
        "protection": "dpapi" if os.name == "nt" and not _force_plain() else "plain-0600",
        "note": "Session state contains cookies only; credentials are never written.",
    }
    return save_state(path, payload)


def load_cookies(session, path: str | Path) -> None:
    payload = load_state(path)
    host = str(payload.get("host") or "")
    for name, value in (payload.get("cookies") or {}).items():
        session._curl_session.cookies.set(str(name), str(value), domain=host, path="/")


def login_and_save(base: str, state_path: str | Path):
    with FetcherSession(impersonate="chrome", stealthy_headers=True) as session:
        login = session.post(
            base.rstrip("/") + "/login",
            data={"username": "demo", "password": "demo"},
        )
        private = session.get(base.rstrip("/") + "/private")
        save_cookies(session, state_path, base)
        return login, private


def fetch_with_state(base: str, state_path: str | Path):
    with FetcherSession(impersonate="chrome", stealthy_headers=True) as session:
        load_cookies(session, state_path)
        return session.get(base.rstrip("/") + "/private")
