"""Typed records shared by the CLI, router and report renderer."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .utils import utc_now


class Phase(str, Enum):
    INTAKE = "INTAKE"
    PROBED = "PROBED"
    ROUTED = "ROUTED"
    CAPTURED = "CAPTURED"
    UNDERSTOOD = "UNDERSTOOD"
    REPRODUCED = "REPRODUCED"
    BUILT = "BUILT"
    VERIFIED = "VERIFIED"
    OPERATING = "OPERATING"
    LEARNED = "LEARNED"


PHASE_ORDER: tuple[Phase, ...] = (
    Phase.INTAKE,
    Phase.PROBED,
    Phase.ROUTED,
    Phase.CAPTURED,
    Phase.UNDERSTOOD,
    Phase.REPRODUCED,
    Phase.BUILT,
    Phase.VERIFIED,
    Phase.OPERATING,
    Phase.LEARNED,
)


class Lane(str, Enum):
    L0_STATIC = "L0_STATIC"
    L0_API = "L0_API"
    L1_DYNAMIC = "L1_DYNAMIC"
    L2_SIGNED = "L2_SIGNED"
    L3_BLOCKED = "L3_BLOCKED"
    L4_APP = "L4_APP"
    L5_SCALE = "L5_SCALE"


class Delivery(str, Enum):
    SINGLE = "single"
    SPIDER = "spider"


class PageKind(str, Enum):
    STATIC_HTML = "static_html"
    JSON_API = "json_api"
    SPA_SHELL = "spa_shell"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


@dataclass
class TargetProfile:
    url: str = ""
    kind: str = "web"
    volume: int = 1
    auth: str = "none"
    geo: str = ""
    authorized: bool = False
    notes: str = ""
    demo: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "kind": self.kind,
            "volume": self.volume,
            "auth": self.auth,
            "geo": self.geo,
            "authorized": self.authorized,
            "notes": self.notes,
            "demo": self.demo,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TargetProfile":
        return cls(
            url=str(data.get("url", "")),
            kind=str(data.get("kind", "web")),
            volume=int(data.get("volume", 1) or 1),
            auth=str(data.get("auth", "none")),
            geo=str(data.get("geo", "")),
            authorized=data.get("authorized") is True,
            notes=str(data.get("notes", "")),
            demo=bool(data.get("demo", False)),
        )


@dataclass
class ProbeResult:
    url: str
    final_url: str = ""
    status: int = 0
    content_type: str = ""
    elapsed_ms: int = 0
    bytes_read: int = 0
    title: str = ""
    lang: str = ""
    page_kind: str = PageKind.UNKNOWN.value
    script_count: int = 0
    inline_script_bytes: int = 0
    form_count: int = 0
    visible_text_chars: int = 0
    api_candidates: list[str] = field(default_factory=list)
    signature_hints: list[str] = field(default_factory=list)
    cloudflare: bool = False
    challenge: bool = False
    captcha: bool = False
    next_data: bool = False
    nuxt: bool = False
    initial_state: bool = False
    ld_json: bool = False
    meta_generator: str = ""
    body_preview: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    error: str = ""
    fetched_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "final_url": self.final_url,
            "status": self.status,
            "content_type": self.content_type,
            "elapsed_ms": self.elapsed_ms,
            "bytes_read": self.bytes_read,
            "title": self.title,
            "lang": self.lang,
            "page_kind": self.page_kind,
            "script_count": self.script_count,
            "inline_script_bytes": self.inline_script_bytes,
            "form_count": self.form_count,
            "visible_text_chars": self.visible_text_chars,
            "api_candidates": self.api_candidates,
            "signature_hints": self.signature_hints,
            "cloudflare": self.cloudflare,
            "challenge": self.challenge,
            "captcha": self.captcha,
            "next_data": self.next_data,
            "nuxt": self.nuxt,
            "initial_state": self.initial_state,
            "ld_json": self.ld_json,
            "meta_generator": self.meta_generator,
            "body_preview": self.body_preview,
            "headers": self.headers,
            "error": self.error,
            "fetched_at": self.fetched_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProbeResult":
        return cls(
            url=str(data.get("url", "")),
            final_url=str(data.get("final_url", "")),
            status=int(data.get("status", 0) or 0),
            content_type=str(data.get("content_type", "")),
            elapsed_ms=int(data.get("elapsed_ms", 0) or 0),
            bytes_read=int(data.get("bytes_read", 0) or 0),
            title=str(data.get("title", "")),
            lang=str(data.get("lang", "")),
            page_kind=str(data.get("page_kind", PageKind.UNKNOWN.value)),
            script_count=int(data.get("script_count", 0) or 0),
            inline_script_bytes=int(data.get("inline_script_bytes", 0) or 0),
            form_count=int(data.get("form_count", 0) or 0),
            visible_text_chars=int(data.get("visible_text_chars", 0) or 0),
            api_candidates=list(data.get("api_candidates", []) or []),
            signature_hints=list(data.get("signature_hints", []) or []),
            cloudflare=bool(data.get("cloudflare", False)),
            challenge=bool(data.get("challenge", False)),
            captcha=bool(data.get("captcha", False)),
            next_data=bool(data.get("next_data", False)),
            nuxt=bool(data.get("nuxt", False)),
            initial_state=bool(data.get("initial_state", False)),
            ld_json=bool(data.get("ld_json", False)),
            meta_generator=str(data.get("meta_generator", "")),
            body_preview=str(data.get("body_preview", "")),
            headers=dict(data.get("headers", {}) or {}),
            error=str(data.get("error", "")),
            fetched_at=str(data.get("fetched_at", utc_now())),
        )


@dataclass
class RouteDecision:
    lane: str
    delivery: str
    confidence: float
    reasons: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    stop_conditions: list[str] = field(default_factory=list)
    decided_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "lane": self.lane,
            "delivery": self.delivery,
            "confidence": round(float(self.confidence), 3),
            "reasons": self.reasons,
            "next_actions": self.next_actions,
            "tools": self.tools,
            "stop_conditions": self.stop_conditions,
            "decided_at": self.decided_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RouteDecision":
        return cls(
            lane=str(data.get("lane", Lane.L1_DYNAMIC.value)),
            delivery=str(data.get("delivery", Delivery.SINGLE.value)),
            confidence=float(data.get("confidence", 0.5) or 0.5),
            reasons=list(data.get("reasons", []) or []),
            next_actions=list(data.get("next_actions", []) or []),
            tools=list(data.get("tools", []) or []),
            stop_conditions=list(data.get("stop_conditions", []) or []),
            decided_at=str(data.get("decided_at", utc_now())),
        )


@dataclass
class EvidenceEntry:
    evidence_id: str
    ts: str
    phase: str
    source: str
    action: str
    observation: str
    inference: str = ""
    confidence: str = "medium"
    artifact: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "ts": self.ts,
            "phase": self.phase,
            "source": self.source,
            "action": self.action,
            "observation": self.observation,
            "inference": self.inference,
            "confidence": self.confidence,
            "artifact": self.artifact,
            "metadata": self.metadata,
        }


@dataclass
class CaseState:
    schema_version: int
    case_id: str
    slug: str
    target: dict[str, Any]
    phase: str = Phase.INTAKE.value
    lane: str | None = None
    delivery: str | None = None
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    history: list[dict[str, Any]] = field(default_factory=list)
    artifacts: dict[str, str] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    blockers: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "case_id": self.case_id,
            "slug": self.slug,
            "target": self.target,
            "phase": self.phase,
            "lane": self.lane,
            "delivery": self.delivery,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "history": self.history,
            "artifacts": self.artifacts,
            "metrics": self.metrics,
            "blockers": self.blockers,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CaseState":
        return cls(
            schema_version=int(data.get("schema_version", 1) or 1),
            case_id=str(data.get("case_id", "")),
            slug=str(data.get("slug", "")),
            target=dict(data.get("target", {}) or {}),
            phase=str(data.get("phase", Phase.INTAKE.value)),
            lane=data.get("lane"),
            delivery=data.get("delivery"),
            created_at=str(data.get("created_at", utc_now())),
            updated_at=str(data.get("updated_at", utc_now())),
            history=list(data.get("history", []) or []),
            artifacts=dict(data.get("artifacts", {}) or {}),
            metrics=dict(data.get("metrics", {}) or {}),
            blockers=list(data.get("blockers", []) or []),
            notes=str(data.get("notes", "")),
        )
