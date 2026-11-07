#!/usr/bin/env python
"""Small signature helpers for rebuilding a captured JS parameter.

This is not a universal crypto tool. It gives the L2 lane a deterministic place
to check common hash/HMAC/timestamp/canonical-JSON constructions before writing
site-specific code.

Examples:
    python sign_lab.py demo
    python sign_lab.py hash --algo sha256 --text "a=1&b=2"
    python sign_lab.py hmac --algo sha256 --key secret --text "a=1&b=2"
    python sign_lab.py b64 --text "hello"
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any


def text_bytes(value: str) -> bytes:
    return value.encode("utf-8")


def hash_text(text: str, algo: str = "sha256") -> str:
    return hashlib.new(algo, text_bytes(text)).hexdigest()


def hash_upper(text: str, algo: str = "sha256") -> str:
    return hash_text(text, algo).upper()


def hmac_hex(key: str, text: str, algo: str = "sha256") -> str:
    return hmac.new(text_bytes(key), text_bytes(text), algo).hexdigest()


def hmac_base64(key: str, text: str, algo: str = "sha256") -> str:
    digest = hmac.new(text_bytes(key), text_bytes(text), algo).digest()
    return base64.b64encode(digest).decode("ascii")


def b64(text: str) -> str:
    return base64.b64encode(text_bytes(text)).decode("ascii")


def b64url(text: str) -> str:
    return base64.urlsafe_b64encode(text_bytes(text)).decode("ascii").rstrip("=")


def canonical_json(value: Any, *, sort_keys: bool = True, separators: tuple[str, str] = (",", ":")) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=sort_keys, separators=separators)


def js_timestamp_ms() -> int:
    return int(time.time() * 1000)


def nonce_hex(length: int = 16) -> str:
    return secrets.token_hex(max(1, length))


def demo() -> None:
    print("hash sha256('abc') =", hash_text("abc", "sha256"))
    print("hmac_sha256('key','abc') =", hmac_hex("key", "abc", "sha256"))
    print("b64('hello') =", b64("hello"))
    print("b64url('hello') =", b64url("hello"))
    print("canonical_json =", canonical_json({"b": 2, "a": 1}))
    print("js_timestamp_ms =", js_timestamp_ms())
    print("nonce_hex =", nonce_hex())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Signature construction helpers.")
    sub = parser.add_subparsers(dest="command", required=True)

    demo_parser = sub.add_parser("demo", help="Print known vectors.")
    demo_parser.set_defaults(func=lambda _: demo())

    hash_parser = sub.add_parser("hash", help="Hash a UTF-8 string.")
    hash_parser.add_argument("--algo", default="sha256", choices=["md5", "sha1", "sha256", "sha512"])
    hash_parser.add_argument("--text", required=True)
    hash_parser.add_argument("--upper", action="store_true")
    hash_parser.set_defaults(
        func=lambda args: print(hash_upper(args.text, args.algo) if args.upper else hash_text(args.text, args.algo))
    )

    hmac_parser = sub.add_parser("hmac", help="HMAC a UTF-8 string.")
    hmac_parser.add_argument("--algo", default="sha256", choices=["md5", "sha1", "sha256", "sha512"])
    hmac_parser.add_argument("--key", required=True)
    hmac_parser.add_argument("--text", required=True)
    hmac_parser.add_argument("--encoding", default="hex", choices=["hex", "base64"])
    hmac_parser.set_defaults(
        func=lambda args: print(
            hmac_base64(args.key, args.text, args.algo)
            if args.encoding == "base64"
            else hmac_hex(args.key, args.text, args.algo)
        )
    )

    b64_parser = sub.add_parser("b64", help="Base64 a UTF-8 string.")
    b64_parser.add_argument("--text", required=True)
    b64_parser.add_argument("--url", action="store_true")
    b64_parser.set_defaults(func=lambda args: print(b64url(args.text) if args.url else b64(args.text)))

    json_parser = sub.add_parser("json", help="Canonicalize a JSON object.")
    json_parser.add_argument("--value", required=True, help="JSON object string.")
    json_parser.set_defaults(func=lambda args: print(canonical_json(json.loads(args.value))))

    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
