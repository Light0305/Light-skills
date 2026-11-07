"""Turn a cheap probe into an explicit acquisition route."""

from __future__ import annotations

from pathlib import PurePosixPath

from .models import Delivery, Lane, PageKind, ProbeResult, RouteDecision, TargetProfile


APP_KINDS = {
    "app",
    "electron",
    "asar",
    "apk",
    "ipa",
    "native",
    "binary",
    "har",
    "saz",
    "pcap",
    "firmware",
}

APP_SUFFIXES = {
    ".asar",
    ".apk",
    ".ipa",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".har",
    ".saz",
    ".pcap",
    ".pcapng",
    ".bin",
    ".elf",
}

STRONG_SIGNATURE_HINTS = {"sign", "signature", "encrypt", "decrypt", "hmac", "x-sign", "x-signature"}


def _is_app_target(target: TargetProfile) -> bool:
    if target.kind.lower() in APP_KINDS:
        return True
    suffix = PurePosixPath(target.url.replace("\\", "/")).suffix.lower()
    return suffix in APP_SUFFIXES


def _signed_signal(probe: ProbeResult) -> bool:
    hints = {hint.lower() for hint in probe.signature_hints}
    strong = bool(hints & STRONG_SIGNATURE_HINTS)
    has_api = bool(probe.api_candidates) or probe.page_kind == PageKind.JSON_API.value
    return has_api and (strong or len(hints) >= 2)


def decide_route(probe: ProbeResult, target: TargetProfile) -> RouteDecision:
    delivery = Delivery.SPIDER.value if target.volume >= 1000 else Delivery.SINGLE.value
    reasons: list[str] = []
    tools: list[str] = []
    next_actions: list[str] = []
    stop_conditions: list[str] = [
        "Stop if the target is outside the user's authorization or robots/ToS boundary.",
        "Stop and ask a human when a CAPTCHA or account takeover is the only way forward.",
    ]

    if _is_app_target(target):
        lane = Lane.L4_APP.value
        confidence = 0.92
        reasons.append(f"target kind/suffix points to a packaged or native target: {target.kind}")
        tools.extend(["rea (CLI first, MCP on demand)", "har/saz inspection", "light-crawl report"])
        next_actions.extend(
            [
                "Run `rea` on the packaged artifact or saved capture before writing any spider.",
                "Extract endpoints, headers, signing inputs and replayable fixtures.",
                "Hand the resulting request contract back to the Scrapling lane.",
            ]
        )

    elif probe.error and probe.status == 0:
        lane = Lane.L1_DYNAMIC.value
        confidence = 0.3
        reasons.append(f"HTTP probe failed before classification: {probe.error}")
        tools.extend(["scrapling.StealthySession", "light-crawl probe --timeout 30"])
        next_actions.extend(
            [
                "Retry once with a longer timeout and a browser-like request.",
                "If the network path is the problem, verify DNS/proxy before using a browser.",
                "Open the page with js-reverse only after the network error is understood.",
            ]
        )

    elif probe.page_kind == PageKind.BLOCKED.value:
        lane = Lane.L3_BLOCKED.value
        confidence = 0.9
        reasons.append(
            "response is a block/challenge page"
            + (" (Cloudflare)" if probe.cloudflare else "")
            + (" (captcha marker)" if probe.captcha else "")
        )
        tools.extend(
            [
                "scrapling.StealthySession(solve_cloudflare=True)",
                "js-reverse (runtime inspection)",
                "js-reverse --cloak (only as a second instance)",
            ]
        )
        next_actions.extend(
            [
                "Try a normal browser-quality fetch first; do not start with cloak.",
                "If the challenge is interactive, stop and hand control to a human.",
                "Capture the successful session state before attempting scale.",
            ]
        )
        stop_conditions.append("Do not automate CAPTCHA solving against a target you do not own or have written permission to test.")

    elif _signed_signal(probe):
        lane = Lane.L2_SIGNED.value
        confidence = 0.78
        reasons.append(
            "API-shaped traffic plus signature/encryption hints: "
            + ", ".join(probe.signature_hints[:6])
        )
        tools.extend(
            [
                "js-reverse (XHR breakpoint, call frames, initiator)",
                "reverse-skill/js-reverse SOP (Observe → Capture → Rebuild → Patch → DeepDive)",
                "templates/repro/sign_lab.py",
                "templates/repro/replay.py",
            ]
        )
        next_actions.extend(
            [
                "In js-reverse, break on the target XHR/Fetch and capture one real request.",
                "Export the request body/headers and the script source around the caller.",
                "Rebuild the signature in a local script and verify against at least 10 fixtures.",
                "Only then generate the Scrapling spider.",
            ]
        )

    elif probe.page_kind == PageKind.JSON_API.value:
        lane = Lane.L0_API.value
        confidence = 0.9
        reasons.append("response is JSON/API-shaped")
        tools.extend(["scrapling.Fetcher", "templates/repro/replay.py", "templates/spider/generic_spider.py"])
        next_actions.extend(
            [
                "Replay the request outside the browser and record required headers.",
                "Find the pagination cursor or page parameter.",
                "Define the item schema and a dedupe key before scaling.",
            ]
        )

    elif probe.page_kind == PageKind.SPA_SHELL.value:
        lane = Lane.L1_DYNAMIC.value
        confidence = 0.76
        reasons.append(
            "page looks like a JS shell"
            + (" (Next.js)" if probe.next_data else "")
            + (" (Nuxt)" if probe.nuxt else "")
            + (" (initial state)" if probe.initial_state else "")
        )
        tools.extend(
            [
                "scrapling.StealthySession",
                "js-reverse (network and script inspection)",
                "templates/spider/generic_spider.py",
            ]
        )
        next_actions.extend(
            [
                "Open the page in a stealth session with `record_requests=True`.",
                "Look for the JSON API behind the rendered content before parsing DOM.",
                "If the API is clean, downgrade the case to L0_API and rebuild as HTTP.",
            ]
        )

    elif probe.page_kind == PageKind.STATIC_HTML.value:
        lane = Lane.L0_STATIC.value
        confidence = 0.82
        reasons.append(f"HTML contains meaningful server-rendered text ({probe.visible_text_chars} chars)")
        tools.extend(["scrapling.Fetcher", "templates/spider/generic_spider.py", "templates/verify/verify_case.py"])
        next_actions.extend(
            [
                "Write selectors against the saved HTML, not against a live browser.",
                "Sample three pages and confirm pagination before scaling.",
                "If the site blocks rapid requests, switch to a FetcherSession with throttling.",
            ]
        )

    else:
        lane = Lane.L1_DYNAMIC.value if probe.script_count else Lane.L0_STATIC.value
        confidence = 0.4
        reasons.append("probe did not match a strong signature; using the cheapest plausible lane")
        tools.extend(["scrapling.Fetcher", "scrapling.StealthySession"])
        next_actions.extend(
            [
                "Run one browser fetch and compare the DOM with the HTTP body.",
                "Record which lane actually worked in evidence.jsonl.",
            ]
        )

    if delivery == Delivery.SPIDER.value:
        reasons.append(f"target volume ({target.volume}) crosses the spider threshold (1000)")
        next_actions.append("Define concurrency, delay, retry and checkpoint policy before the first full run.")

    if target.auth and target.auth.lower() not in {"none", "public", "anonymous"}:
        reasons.append(f"authentication mode: {target.auth}")
        next_actions.append("Store session state outside the repository and never commit cookies or tokens.")

    if target.demo:
        reasons.append("offline demo case; no live target was contacted")

    return RouteDecision(
        lane=lane,
        delivery=delivery,
        confidence=confidence,
        reasons=reasons,
        next_actions=next_actions,
        tools=tools,
        stop_conditions=stop_conditions,
    )
