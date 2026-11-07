"""Case state, artifact bus, and evidence ledger."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .models import CaseState, EvidenceEntry, PHASE_ORDER, Phase, TargetProfile
from .scaffold import scope_markdown
from .integrity import content_hash, fingerprint, tree_records
from .utils import (
    append_jsonl,
    case_id,
    ensure_dir,
    read_json,
    read_jsonl,
    safe_copy,
    sha256_file,
    slugify,
    truncate,
    utc_now,
    write_json,
)


class LightCrawlError(RuntimeError):
    """A user-facing error that the CLI should print without a traceback."""


class CaseStore:
    """A directory-backed case with a typed state file and append-only evidence."""

    def __init__(self, directory: Path, state: CaseState) -> None:
        self.directory = Path(directory)
        self.state = state

    # ------------------------------------------------------------------ paths
    @property
    def case_file(self) -> Path:
        return self.directory / "case.json"

    @property
    def scope_file(self) -> Path:
        return self.directory / "scope.md"

    @property
    def target_file(self) -> Path:
        return self.directory / "target.json"

    @property
    def probe_file(self) -> Path:
        return self.directory / "probe.json"

    @property
    def route_file(self) -> Path:
        return self.directory / "route.json"

    @property
    def evidence_file(self) -> Path:
        return self.directory / "evidence.jsonl"

    @property
    def artifacts_dir(self) -> Path:
        return self.directory / "artifacts"

    @property
    def har_dir(self) -> Path:
        return self.directory / "har"

    @property
    def fixtures_dir(self) -> Path:
        return self.directory / "fixtures"

    @property
    def repro_dir(self) -> Path:
        return self.directory / "repro"

    @property
    def spider_dir(self) -> Path:
        return self.directory / "spider"

    @property
    def reports_dir(self) -> Path:
        return self.directory / "reports"

    @property
    def report_file(self) -> Path:
        return self.reports_dir / "report.md"

    @property
    def target(self) -> TargetProfile:
        return TargetProfile.from_dict(self.state.target)

    # ----------------------------------------------------------------- create
    @classmethod
    def create(
        cls,
        case_root: Path,
        slug: str,
        target: TargetProfile,
        *,
        force: bool = False,
    ) -> "CaseStore":
        case_root = ensure_dir(Path(case_root))
        safe_slug = slugify(slug)
        directory = case_root / safe_slug
        if directory.exists() and not force:
            raise LightCrawlError(f"Case already exists: {directory}. Use --force to replace it.")
        if directory.exists() and force:
            shutil.rmtree(directory)
        ensure_dir(directory)
        for child in ("artifacts", "har", "fixtures", "repro", "spider", "reports"):
            ensure_dir(directory / child)

        state = CaseState(
            schema_version=1,
            case_id=case_id(safe_slug),
            slug=safe_slug,
            target=target.to_dict(),
            phase=Phase.INTAKE.value,
            history=[
                {
                    "ts": utc_now(),
                    "phase": Phase.INTAKE.value,
                    "note": "case created",
                }
            ],
        )
        store = cls(directory, state)
        write_json(store.target_file, target.to_dict())
        store.scope_file.write_text(scope_markdown(safe_slug, target), encoding="utf-8", newline="\n")
        store.evidence_file.touch()
        store.save()
        return store

    # ------------------------------------------------------------------- load
    @classmethod
    def load(cls, directory: Path) -> "CaseStore":
        directory = Path(directory)
        data = read_json(directory / "case.json")
        if not data:
            raise LightCrawlError(f"Not a light-crawl case (missing case.json): {directory}")
        return cls(directory, CaseState.from_dict(data))

    @classmethod
    def resolve(cls, value: str, case_root: Path) -> "CaseStore":
        candidate = Path(value)
        if candidate.is_dir() and (candidate / "case.json").exists():
            return cls.load(candidate)
        root_candidate = Path(case_root) / value
        if root_candidate.is_dir() and (root_candidate / "case.json").exists():
            return cls.load(root_candidate)
        raise LightCrawlError(
            f"Case not found: {value}. Pass a case directory or a slug under {Path(case_root).resolve()}."
        )

    # ------------------------------------------------------------------- save
    def save(self) -> None:
        self.state.updated_at = utc_now()
        write_json(self.case_file, self.state.to_dict())

    def advance(
        self,
        phase: Phase | str,
        note: str = "",
        *,
        lane: str | None = None,
        delivery: str | None = None,
    ) -> None:
        new_phase = Phase(phase)
        current_index = PHASE_ORDER.index(Phase(self.state.phase))
        new_index = PHASE_ORDER.index(new_phase)
        if new_index < current_index:
            raise LightCrawlError(
                f"Cannot move backwards from {self.state.phase} to {new_phase.value}; "
                "create a new case for a new hypothesis."
            )
        self.state.phase = new_phase.value
        if lane is not None:
            self.state.lane = lane
        if delivery is not None:
            self.state.delivery = delivery
        self.state.history.append(
            {
                "ts": utc_now(),
                "phase": new_phase.value,
                "note": note,
            }
        )
        self.save()

    # --------------------------------------------------------------- evidence
    def add_evidence(
        self,
        *,
        phase: str,
        source: str,
        action: str,
        observation: str,
        inference: str = "",
        confidence: str = "medium",
        artifact: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> EvidenceEntry:
        existing = read_jsonl(self.evidence_file)
        evidence = EvidenceEntry(
            evidence_id=f"E{len(existing) + 1:04d}",
            ts=utc_now(),
            phase=phase,
            source=source,
            action=action,
            observation=truncate(observation, 4000),
            inference=truncate(inference, 4000),
            confidence=confidence,
            artifact=artifact,
            metadata=metadata or {},
        )
        append_jsonl(self.evidence_file, evidence.to_dict())
        self.save()
        return evidence

    def evidence(self) -> list[dict[str, Any]]:
        return read_jsonl(self.evidence_file)

    # --------------------------------------------------------------- artifacts
    def add_artifact(self, path: Path, label: str = "") -> str:
        source = Path(path)
        if not source.exists():
            raise LightCrawlError(f"Artifact does not exist: {source}")
        name = slugify(label or source.name, default="artifact")
        try:
            records = tree_records(source) if source.is_dir() else None
            info = ({'sha256': content_hash(records), 'bytes': sum(r['bytes'] for r in records),
                     'kind': 'directory', 'records': records} if records is not None else fingerprint(source))
            suffix = '' if records is not None else source.suffix
            target = self.artifacts_dir / f"{name}-{info['sha256'][:16]}{suffix}"
            if not target.exists():
                safe_copy(source, target)
            actual = tree_records(target) if records is not None else fingerprint(target)
            if actual != (records if records is not None else info):
                raise ValueError('Artifact changed during copy, or existing archive is damaged')
        except (ValueError, OSError) as error:
            raise LightCrawlError(str(error)) from error
        relative = target.relative_to(self.directory).as_posix()
        self.state.artifacts.setdefault(relative, {
            "label": label or source.name,
            **info,
            "added_at": utc_now(),
        })
        self.save()
        return relative

    def record_metric(self, key: str, value: Any) -> None:
        self.state.metrics[key] = value
        self.save()

    def add_blocker(self, blocker: str) -> None:
        text = truncate(blocker, 1000)
        if text and text not in self.state.blockers:
            self.state.blockers.append(text)
            self.save()

    def remove_blocker(self, index: int) -> None:
        if 0 <= index < len(self.state.blockers):
            self.state.blockers.pop(index)
            self.save()

    # ------------------------------------------------------------------ views
    def summary(self) -> dict[str, Any]:
        return {
            "case_id": self.state.case_id,
            "slug": self.state.slug,
            "phase": self.state.phase,
            "lane": self.state.lane,
            "delivery": self.state.delivery,
            "target": self.state.target,
            "evidence_count": len(self.evidence()),
            "artifacts": len(self.state.artifacts),
            "blockers": self.state.blockers,
            "directory": str(self.directory.resolve()),
        }


def load_probe(store: CaseStore):
    from .models import ProbeResult

    data = read_json(store.probe_file)
    if not data:
        raise LightCrawlError(
            f"No probe found for {store.state.slug}. Run `light-crawl probe {store.directory}` first."
        )
    return ProbeResult.from_dict(data)


def load_route(store: CaseStore):
    from .models import RouteDecision

    data = read_json(store.route_file)
    if not data:
        raise LightCrawlError(
            f"No route found for {store.state.slug}. Run `light-crawl route {store.directory}` first."
        )
    return RouteDecision.from_dict(data)
