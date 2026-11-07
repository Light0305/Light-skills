"""Plan image generation or call a user-configured OpenAI-compatible Image API.

The assistant discovers native host tools and publishes the prompt first. This
helper cannot invoke a host's tool, inspect image quality, or rebuild vectors.
Only generate + a custom route sends a request; plan is always offline.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import math
import os
from pathlib import Path
import socket
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

SKILL = Path(__file__).resolve().parents[1]
MAX_BYTES = 64 * 1024 * 1024
USER_AGENT = 'light-diagram/1.0'
PROVIDERS = {"auto", "builtin", "custom", "prompt_only"}


class ServiceError(ValueError):
    """A safe error that contains neither credentials nor provider response text."""


def emit(value):
    print(json.dumps(value, ensure_ascii=False), flush=True)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def file_record(path):
    path = Path(path).resolve()
    return {"path": str(path), "sha256": digest(path.read_bytes())}


def read_prompt(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig")
    if not text.strip():
        raise ServiceError("Prompt file is empty.")
    return text, {"path": str(path), "sha256": digest(raw)}


def load_config(explicit=None):
    """Explicit file > dedicated environment variable > skill-local config.

    An explicitly named missing file is an error, not a hidden default switch.
    The example is never discovered automatically.
    """
    configured = explicit or os.environ.get("LIGHT_DIAGRAM_IMAGE_CONFIG")
    path = Path(configured).expanduser() if configured else SKILL / "imagegen.local.json"
    if not path.is_file():
        if configured:
            raise ServiceError("The selected image configuration file does not exist.")
        return {}, None
    try:
        config = json.loads(path.read_text("utf-8-sig"))
    except (ValueError, OSError):
        raise ServiceError("Image configuration is not readable JSON.") from None
    if not isinstance(config, dict):
        raise ServiceError("Image configuration must be a JSON object.")
    return config, str(path.resolve())


def checked_url(url, *, query_allowed=False):
    if not isinstance(url, str):
        raise ServiceError("Service URL must be text.")
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        raise ServiceError("Service URL is malformed.") from None
    if not parts.hostname or parts.username or parts.password or parts.fragment:
        raise ServiceError("URL requires a host and cannot contain credentials or fragments.")
    local = parts.hostname in {"localhost", "127.0.0.1", "::1"}
    if parts.scheme != "https" and not (parts.scheme == "http" and local):
        raise ServiceError("Use HTTPS, or HTTP on localhost for a local service.")
    if parts.query and not query_allowed:
        raise ServiceError("Put API credentials in the key fields, not the service URL query.")
    return url


def custom_settings(config):
    if config.get("api_style", "openai_images") != "openai_images":
        raise ServiceError("This adapter supports api_style=openai_images only.")
    url = config.get("url")
    if not url and config.get("base_url"):
        base = checked_url(config["base_url"])
        if base.rstrip("/").endswith("/images/generations"):
            raise ServiceError("Use url for the full endpoint, or base_url for its API prefix.")
        if urlsplit(base).path in ('', '/'):
            base = base.rstrip('/') + '/v1'
        url = base.rstrip("/") + "/images/generations"
    if not url:
        raise ServiceError("Custom generation needs url or base_url.")
    checked_url(url)
    # Users often paste the service origin or its /v1 prefix into url. Complete
    # only these unambiguous cases, preserving explicit/custom endpoint paths.
    path = urlsplit(url).path.rstrip('/')
    if not path:
        url = url.rstrip('/') + '/v1/images/generations'
    elif path == '/v1':
        url = url.rstrip('/') + '/images/generations'
    model = config.get("model")
    if not isinstance(model, str) or not model.strip() or model.startswith("YOUR_"):
        raise ServiceError("Custom generation needs an actual image model name.")
    env_name = config.get("api_key_env")
    if env_name is not None and (not isinstance(env_name, str) or not env_name):
        raise ServiceError("api_key_env must name an environment variable.")
    key = os.environ.get(env_name, "") if env_name else ""
    key = key or config.get("api_key", "")
    auth = config.get("auth", "bearer")
    if auth not in {"bearer", "none"}:
        raise ServiceError("auth must be bearer or none.")
    if not isinstance(key, str):
        raise ServiceError("API key must be text.")
    if auth == "bearer" and (not key.strip() or key.startswith("YOUR_")):
        raise ServiceError("API key is missing; set api_key_env or api_key.")
    if "\r" in key or "\n" in key:
        raise ServiceError("API key cannot contain line breaks.")
    timeout = config.get("timeout_seconds", 180)
    if (not isinstance(timeout, (int, float)) or isinstance(timeout, bool)
            or not math.isfinite(timeout) or timeout <= 0):
        raise ServiceError("timeout_seconds must be a positive finite number.")
    params = config.get("params", {})
    if not isinstance(params, dict):
        raise ServiceError("params must be a JSON object.")
    if any(k in params for k in ("prompt", "model", "stream", "api_key", "authorization")):
        raise ServiceError("params cannot override prompt/model or contain streaming/auth fields.")
    count = params.get("n", 1)
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        raise ServiceError("params.n must be a positive integer.")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if auth == "bearer":
        headers["Authorization"] = "Bearer " + key
    return {"url": url, "model": model, "timeout": timeout,
            "params": params, "headers": headers}


def select_route(config, host_available="unknown", provider=None):
    policy = provider or config.get("provider", "auto")
    if policy not in PROVIDERS:
        raise ServiceError("provider must be auto, builtin, custom or prompt_only.")
    if host_available not in {"yes", "no", "unknown"}:
        raise ServiceError("Host capability must be yes, no or unknown.")
    result = {"policy": policy, "host_available": host_available}
    if policy == "prompt_only":
        return dict(result, selected="prompt_only", reason="explicit_prompt_only")
    if policy == "builtin":
        return dict(result, selected="builtin" if host_available == "yes" else "prompt_only",
                    reason="explicit_builtin" if host_available == "yes" else "builtin_not_available")
    if policy == "auto" and host_available == "yes":
        return dict(result, selected="builtin", reason="host_tool_preferred")
    if policy == "auto" and host_available == "unknown":
        return dict(result, selected="discovery_required", reason="discover_host_tools_first")
    if not config:
        return dict(result, selected="prompt_only", reason="no_custom_configuration")
    try:
        custom_settings(config)
    except ServiceError as exc:
        return dict(result, selected="prompt_only", reason="custom_configuration_incomplete", detail=str(exc))
    return dict(result, selected="custom", reason="explicit_custom" if policy == "custom" else "configured_fallback")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch(request, timeout):
    """No automatic generation retries or credential-carrying redirects."""
    if not request.has_header('User-agent'):
        request.add_header('User-Agent', USER_AGENT)
    try:
        with build_opener(NoRedirect()).open(request, timeout=timeout) as response:
            raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise ServiceError("Service output exceeds the 64 MiB response limit.")
            return raw
    except HTTPError as exc:
        code = exc.code
        exc.close()
        raise ServiceError(f"Service returned HTTP {code}; no automatic retry was made.") from None
    except (URLError, TimeoutError, socket.timeout, OSError, ValueError):
        raise ServiceError("Service connection/download failed; no automatic retry was made.") from None


def image_extension(raw):
    if raw.startswith(b"\x89PNG\r\n\x1a\n") and raw[12:16] == b"IHDR" and b"IEND" in raw[-12:]:
        ext = ".png"
    elif raw.startswith(b"\xff\xd8\xff") and raw.endswith(b"\xff\xd9"):
        ext = ".jpg"
    elif raw.startswith(b"RIFF") and raw[8:12] == b"WEBP" and len(raw) >= 20:
        ext = ".webp"
    else:
        raise ServiceError("Service returned no supported PNG/JPEG/WebP image bytes.")
    try:
        from PIL import Image
    except ImportError:
        return ext
    import io
    try:
        with Image.open(io.BytesIO(raw)) as im:
            im.verify()
    except Exception:
        raise ServiceError("Returned image failed decoding checks.") from None
    return ext


def extract_images(response, timeout):
    if not isinstance(response, dict) or not isinstance(response.get("data"), list) or not response["data"]:
        raise ServiceError("Response has no images in data; text/job IDs are not completed generation.")
    images = []
    for item in response["data"]:
        if not isinstance(item, dict):
            raise ServiceError("Image entry is malformed.")
        if item.get("b64_json"):
            try:
                raw = base64.b64decode(item["b64_json"], validate=True)
            except (binascii.Error, ValueError, TypeError):
                raise ServiceError("Response image base64 is malformed.") from None
        elif item.get("url"):
            # Downloaded assets receive NO API key/Authorization header, even on the same host.
            url = checked_url(item["url"], query_allowed=True)
            raw = fetch(Request(url, headers={"Accept": "image/*"}), timeout)
        else:
            raise ServiceError("Image entry contains neither b64_json nor url.")
        if len(raw) > MAX_BYTES:
            raise ServiceError("Returned image exceeds the 64 MiB limit.")
        images.append((raw, image_extension(raw)))
    return images


def save_record(path, value):
    temporary = path.with_suffix(".writing")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def generate_custom(config, prompt_path, output_dir, expected_sha256=None):
    settings = custom_settings(config)
    text, original = read_prompt(prompt_path)
    if expected_sha256 is not None and original['sha256'] != expected_sha256:
        raise ServiceError("Prompt changed after publication; publish the new version first.")
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    saved_prompt = output_dir / "prompt-executed.txt"
    # Preserve the exact published bytes and refuse a changed prompt before sending.
    saved_prompt.write_bytes(Path(original["path"]).read_bytes())
    if file_record(saved_prompt)["sha256"] != original["sha256"]:
        raise ServiceError("Prompt changed while preparing the request; nothing was sent.")
    body = {"n": 1, **settings["params"], "model": settings["model"], "prompt": text}
    payload = json.dumps(body, ensure_ascii=False, allow_nan=False).encode("utf-8")
    parts = urlsplit(settings["url"])
    record = {"schema_version": "1.0", "status": "in_progress", "provider": "custom",
              "api_style": "openai_images", "model": settings["model"],
              "endpoint": urlunsplit((parts.scheme, parts.netloc, parts.path, "", "")),
              "calls_this_run": 0, "published_prompt": original,
              "executed_prompt": None, "request_sha256": digest(payload), "images": [],
              "review_status": "not_run"}
    record_path = output_dir / "generation.json"
    save_record(record_path, record)
    try:
        request = Request(settings["url"], data=payload, headers=settings["headers"], method="POST")
        record["calls_this_run"] = 1
        record["executed_prompt"] = file_record(saved_prompt)
        save_record(record_path, record)
        raw = fetch(request, settings["timeout"])
        try:
            response = json.loads(raw)
        except (ValueError, UnicodeError):
            raise ServiceError("Service returned non-JSON content.") from None
        images = extract_images(response, settings["timeout"])
        for index, (image_bytes, ext) in enumerate(images, 1):
            target = output_dir / f"image-{index:02d}{ext}"
            with target.open("xb") as handle:
                handle.write(image_bytes)
            record["images"].append(file_record(target))
        record["status"] = "generated"
    except ServiceError as exc:
        record.update(status="failed", error=str(exc))
    except (OSError, ValueError, TypeError):
        record.update(status="failed", error="Request or output processing failed; prompt retained; no automatic retry.")
    save_record(record_path, record)
    return dict(record, record=file_record(record_path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "generate"))
    parser.add_argument("--prompt", type=Path, required=True)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--host-available", choices=("yes", "no", "unknown"), default="unknown")
    parser.add_argument("--provider", choices=sorted(PROVIDERS))
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--prompt-published", action="store_true",
                        help="Assert that the assistant already showed the complete prompt or its file link to the user.")
    args = parser.parse_args()
    try:
        _, prompt = read_prompt(args.prompt)
        emit({"event": "prompt_ready", "prompt": prompt})
        # Explicit prompt-only delivery does not read credentials or unrelated broken config.
        if args.provider == "prompt_only":
            config, config_path = {}, None
        else:
            try:
                config, config_path = load_config(args.config)
            except ServiceError as exc:
                if args.host_available == 'yes' and args.provider in (None, 'auto', 'builtin'):
                    config, config_path = {}, None
                    emit({"event": "configuration_notice", "detail": str(exc), "action": "use_available_host_tool"})
                else:
                    emit({"selected": "prompt_only", "reason": "configuration_unreadable", "detail": str(exc), "prompt": prompt})
                    return 2
        route = select_route(config, args.host_available, args.provider)
        emit({"event": "generation_plan", **route, "prompt": prompt, "config": config_path})
        if args.command == "plan" or route["selected"] != "custom":
            return 2 if route["selected"] == "discovery_required" or route["reason"] == "custom_configuration_incomplete" else 0
        if not args.prompt_published:
            raise ServiceError("Publish the prompt/file link before generation, then pass --prompt-published.")
        if args.output_dir is None:
            raise ServiceError("Custom generation requires a new --output-dir.")
        result = generate_custom(config, args.prompt, args.output_dir, expected_sha256=prompt['sha256'])
        emit({"event": "generation_result", **result})
        return 0 if result["status"] == "generated" else 2
    except (ServiceError, OSError, UnicodeError, ValueError) as exc:
        message = str(exc) if isinstance(exc, ServiceError) else "Local input/output or configuration failed; no automatic retry."
        emit({"event": "error", "error": message})
        return 2


if __name__ == "__main__":
    sys.exit(main())
