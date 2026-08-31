#!/usr/bin/env python3
"""Local, auditable lifecycle manager for self-learning agent skills.

The script is intentionally standard-library only. It does not call a model,
change agent authority, or install a skill. It records observable evidence,
tracks independent reviews, gates promotion, measures probation usage, and keeps
an append-only hash-chained event ledger.
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import hmac
import json
import os
import re
import sys
import tempfile
import unicodedata
import uuid
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = 1
REVIEW_KINDS = ("evidence", "evaluation", "safety")
REVIEW_VERDICTS = ("pass", "fail")
OUTCOMES = ("pass", "fail", "partial")
RISK_LEVELS = ("low", "medium", "high", "critical")
CANDIDATE_STATES = (
    "draft",
    "quarantined",
    "probationary",
    "active",
    "archived",
)
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CANDIDATE_ID_RE = re.compile(r"^cand-[a-f0-9]{12}$")
ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
MAX_ARTIFACT_FILES = 500
MAX_ARTIFACT_BYTES = 10 * 1024 * 1024

DEFAULT_CONFIG: dict[str, Any] = {
    "schema_version": SCHEMA_VERSION,
    "require_independent_reviews": True,
    "auto_activate_low_risk": False,
    "require_owner_approval_for_activation": True,
    "approval_mode": "host-receipt",
    "approval_hmac_env": "SELF_LEARNING_APPROVAL_KEY",
    "probation_min_trials": 3,
    "activation_reliability": 0.80,
    "archive_min_trials": 5,
    "archive_reliability": 0.35,
    "failure_burst_limit": 3,
    "max_active_skills": 100,
    "allowed_auto_activation_scopes": ["project"],
    "protected_domains": [
        "identity",
        "mission",
        "authority",
        "permissions",
        "credentials",
        "security-policy",
        "billing",
        "production-write",
    ],
}

SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("OpenAI-style key", re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{16,}\b")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("authorization credential", re.compile(r"\b(?:Bearer|Basic)\s+[A-Za-z0-9._~+/=-]{20,}\b", re.I)),
    (
        "credential-bearing URI",
        re.compile(
            r"\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqp|kafka|https?)://"
            r"[^\s/@:]+:[^\s/@]+@",
            re.I,
        ),
    ),
)


class LearningError(RuntimeError):
    """Raised for a lifecycle or validation failure that should stop promotion."""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise LearningError(f"Value is not canonical JSON: {exc}") from exc


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent), text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def atomic_write_json(path: Path, value: Any) -> None:
    try:
        text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n"
    except (TypeError, ValueError) as exc:
        raise LearningError(f"Value is not valid JSON for {path}: {exc}") from exc
    atomic_write_text(path, text)


def collect_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from collect_strings(item)
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            yield from collect_strings(item)


def secret_findings(value: Any) -> list[str]:
    findings: set[str] = set()
    for text in collect_strings(value):
        for label, pattern in SECRET_PATTERNS:
            if pattern.search(text):
                findings.add(label)
    return sorted(findings)


def require_secret_safe(value: Any, context: str) -> None:
    findings = secret_findings(value)
    if findings:
        joined = ", ".join(findings)
        raise LearningError(
            f"Refusing to persist possible secret material in {context}: {joined}. "
            "Replace literal values with env-var, vault, selector, or tool pointers."
        )


def workspace_paths(root: Path) -> dict[str, Path]:
    return {
        "root": root,
        "config": root / "config.json",
        "ledger": root / "ledger.jsonl",
        "candidates": root / "candidates",
        "reports": root / "reports",
    }


def initialize(root: Path, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    paths = workspace_paths(root)
    root.mkdir(parents=True, exist_ok=True)
    paths["candidates"].mkdir(parents=True, exist_ok=True)
    paths["reports"].mkdir(parents=True, exist_ok=True)

    config = copy.deepcopy(DEFAULT_CONFIG)
    if overrides:
        unknown = sorted(set(overrides) - set(config))
        if unknown:
            raise LearningError(f"Unknown config keys: {', '.join(unknown)}")
        config.update(overrides)
    validate_config(config)

    if paths["config"].exists():
        if overrides:
            raise LearningError(
                "Config already exists; refusing to change learning governance through init. "
                "Use an owner-controlled edit and audit the workspace afterward."
            )
        existing = load_json(paths["config"])
        validate_config(existing)
        config = existing
    else:
        atomic_write_json(paths["config"], config)

    if not paths["ledger"].exists():
        atomic_write_text(paths["ledger"], "")
    verify_ledger(root)
    return config


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != SCHEMA_VERSION:
        raise LearningError(f"Unsupported config schema_version: {config.get('schema_version')!r}")
    for key in ("activation_reliability", "archive_reliability"):
        value = config.get(key)
        if not isinstance(value, (int, float)) or not 0 <= float(value) <= 1:
            raise LearningError(f"{key} must be between 0 and 1")
    for key in ("probation_min_trials", "archive_min_trials", "failure_burst_limit", "max_active_skills"):
        value = config.get(key)
        if not isinstance(value, int) or value < 1:
            raise LearningError(f"{key} must be a positive integer")
    if not isinstance(config.get("protected_domains"), list):
        raise LearningError("protected_domains must be a list")
    if not isinstance(config.get("allowed_auto_activation_scopes"), list):
        raise LearningError("allowed_auto_activation_scopes must be a list")
    if config.get("approval_mode") not in ("host-receipt", "local-manual"):
        raise LearningError("approval_mode must be host-receipt or local-manual")
    if not isinstance(config.get("approval_hmac_env"), str) or not config["approval_hmac_env"].strip():
        raise LearningError("approval_hmac_env must be a non-empty environment variable name")
    if not ENV_NAME_RE.fullmatch(config["approval_hmac_env"]):
        raise LearningError("approval_hmac_env is not a valid environment variable name")


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise LearningError(f"Missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise LearningError(f"Invalid JSON in {path}: {exc}") from exc


def load_config(root: Path) -> dict[str, Any]:
    config = load_json(workspace_paths(root)["config"])
    validate_config(config)
    return config


def _event_hash(event_without_hash: dict[str, Any]) -> str:
    return sha256_text(canonical_json(event_without_hash))


def read_ledger(root: Path) -> list[dict[str, Any]]:
    ledger_path = workspace_paths(root)["ledger"]
    if not ledger_path.exists():
        raise LearningError(f"Learning workspace is not initialized: {root}")

    events: list[dict[str, Any]] = []
    previous_hash = ""
    for line_number, raw_line in enumerate(ledger_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw_line.strip():
            continue
        try:
            event = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            raise LearningError(f"Invalid ledger JSON at line {line_number}: {exc}") from exc
        stored_hash = event.get("event_hash")
        unsigned = dict(event)
        unsigned.pop("event_hash", None)
        expected_hash = _event_hash(unsigned)
        if stored_hash != expected_hash:
            raise LearningError(f"Ledger hash mismatch at line {line_number}")
        if event.get("prev_hash", "") != previous_hash:
            raise LearningError(f"Ledger chain mismatch at line {line_number}")
        if event.get("schema_version") != SCHEMA_VERSION:
            raise LearningError(f"Unsupported ledger schema at line {line_number}")
        previous_hash = stored_hash
        events.append(event)
    return events


def verify_ledger(root: Path) -> dict[str, Any]:
    events = read_ledger(root)
    return {
        "valid": True,
        "events": len(events),
        "head_hash": events[-1]["event_hash"] if events else "",
    }


def append_event(root: Path, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    require_secret_safe(payload, f"event {event_type}")
    events = read_ledger(root)
    previous_hash = events[-1]["event_hash"] if events else ""
    event: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "event_id": str(uuid.uuid4()),
        "timestamp": utc_now(),
        "type": event_type,
        "payload": payload,
        "prev_hash": previous_hash,
    }
    event["event_hash"] = _event_hash(event)
    events.append(event)
    text = "".join(canonical_json(item) + "\n" for item in events)
    atomic_write_text(workspace_paths(root)["ledger"], text)
    return event


def record_experience(
    root: Path,
    *,
    task_id: str,
    outcome: str,
    summary: str,
    evidence: list[str],
    scope: str = "project",
    skill: str = "",
    failure_pattern: str = "",
    dead_ends: list[str] | None = None,
    metrics: dict[str, Any] | None = None,
    source_trust: str = "mixed",
) -> dict[str, Any]:
    if outcome not in OUTCOMES:
        raise LearningError(f"outcome must be one of: {', '.join(OUTCOMES)}")
    if source_trust not in ("trusted", "mixed", "untrusted"):
        raise LearningError("source_trust must be trusted, mixed, or untrusted")
    if not task_id.strip() or not summary.strip():
        raise LearningError("task_id and summary are required")
    clean_evidence = [item.strip() for item in evidence if item.strip()]
    if outcome == "pass" and not clean_evidence:
        raise LearningError("A passing outcome requires at least one observable evidence reference")
    payload = {
        "task_id": task_id.strip(),
        "outcome": outcome,
        "summary": summary.strip(),
        "evidence": clean_evidence,
        "scope": scope.strip(),
        "skill": skill.strip(),
        "failure_pattern": failure_pattern.strip(),
        "dead_ends": [item.strip() for item in (dead_ends or []) if item.strip()],
        "metrics": metrics or {},
        "source_trust": source_trust,
    }
    return append_event(root, "experience.recorded", payload)


def validate_name(name: str) -> None:
    if len(name) > 64 or not NAME_RE.fullmatch(name):
        raise LearningError(
            "name must be 1-64 lowercase letters, digits, or single hyphens, "
            "without leading/trailing/doubled hyphens"
        )


def validate_candidate_id(candidate_id: str) -> None:
    if not CANDIDATE_ID_RE.fullmatch(candidate_id):
        raise LearningError("candidate ID must match cand- followed by 12 lowercase hex characters")


def normalized_artifact_path(root: Path, raw_path: str) -> str:
    if not raw_path.strip():
        return ""
    resolved = Path(raw_path).expanduser().resolve()
    if not resolved.exists():
        raise LearningError(f"Candidate artifact path does not exist: {resolved}")
    project_root = root.parent.resolve()
    try:
        return resolved.relative_to(project_root).as_posix()
    except ValueError as exc:
        raise LearningError(
            "Candidate artifacts must stay inside the learning workspace's project root. "
            "Place a global workspace beside the global skill directory instead of persisting an absolute path."
        ) from exc


def resolve_artifact_path(root: Path, stored_path: str) -> Path | None:
    if not stored_path:
        return None
    path = Path(stored_path)
    if path.is_absolute():
        raise LearningError("Absolute candidate artifact paths are not allowed")
    resolved = (root.parent / path).resolve()
    try:
        resolved.relative_to(root.parent.resolve())
    except ValueError as exc:
        raise LearningError("Candidate artifact path escapes the project root") from exc
    return resolved


def artifact_files(path: Path) -> list[tuple[str, Path]]:
    if not path.exists():
        raise LearningError(f"Candidate artifact disappeared: {path}")
    if path.is_symlink():
        raise LearningError(f"Candidate artifact may not be a symlink: {path}")
    if path.is_file():
        files = [(path.name, path)]
    elif path.is_dir():
        files = []
        for item in sorted(path.rglob("*"), key=lambda p: p.relative_to(path).as_posix()):
            if item.is_symlink():
                raise LearningError(f"Candidate artifact tree may not contain symlinks: {item}")
            if item.is_file():
                files.append((item.relative_to(path).as_posix(), item))
    else:
        raise LearningError(f"Unsupported candidate artifact type: {path}")
    if len(files) > MAX_ARTIFACT_FILES:
        raise LearningError(f"Candidate artifact exceeds {MAX_ARTIFACT_FILES} files")
    total = sum(item.stat().st_size for _, item in files)
    if total > MAX_ARTIFACT_BYTES:
        raise LearningError(f"Candidate artifact exceeds {MAX_ARTIFACT_BYTES} bytes")
    return files


def artifact_secret_findings(path: Path) -> list[str]:
    findings: list[str] = []
    for relative, item in artifact_files(path):
        text = item.read_bytes().decode("utf-8", errors="ignore")
        for label in secret_findings(text):
            findings.append(f"{relative}: {label}")
    return findings


def hash_artifact(path: Path | None) -> str:
    if path is None:
        return ""
    records: list[dict[str, Any]] = []
    secret_hits: list[str] = []
    total = 0
    for relative, item in artifact_files(path):
        data = item.read_bytes()
        total += len(data)
        if total > MAX_ARTIFACT_BYTES:
            raise LearningError(f"Candidate artifact exceeds {MAX_ARTIFACT_BYTES} bytes")
        text = data.decode("utf-8", errors="ignore")
        for label in secret_findings(text):
            secret_hits.append(f"{relative}: {label}")
        records.append(
            {
                "path": relative,
                "size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    if secret_hits:
        raise LearningError("Candidate artifact contains possible secret material: " + "; ".join(secret_hits))
    return sha256_text(canonical_json(records))


def candidate_subject(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": candidate["candidate_id"],
        "version": candidate["version"],
        "name": candidate["name"],
        "risk": candidate["risk"],
        "scope": candidate["scope"],
        "source_event_ids": candidate["source_event_ids"],
        "failure_pattern": candidate["failure_pattern"],
        "verification": candidate["verification"],
        "applicability_boundary": candidate["applicability_boundary"],
        "expected_gain": candidate["expected_gain"],
        "skill_path": candidate["skill_path"],
        "artifact_hash": candidate["artifact_hash"],
        "protected_domains": candidate["protected_domains"],
    }


def candidate_subject_hash(candidate: dict[str, Any]) -> str:
    return sha256_text(canonical_json(candidate_subject(candidate)))


def verify_candidate_artifact(root: Path, candidate: dict[str, Any]) -> str:
    current = hash_artifact(resolve_artifact_path(root, candidate.get("skill_path", "")))
    if current != candidate.get("artifact_hash", ""):
        raise LearningError(
            "Candidate artifact changed after sealing. Run revise to create a new version "
            "and invalidate prior reviews/approval."
        )
    return current


def event_ids(root: Path) -> set[str]:
    return {event["event_id"] for event in read_ledger(root)}


def candidate_dir(root: Path, candidate_id: str) -> Path:
    validate_candidate_id(candidate_id)
    return workspace_paths(root)["candidates"] / candidate_id


def candidate_path(root: Path, candidate_id: str) -> Path:
    return candidate_dir(root, candidate_id) / "candidate.json"


def load_candidate(root: Path, candidate_id: str) -> dict[str, Any]:
    candidate = load_json(candidate_path(root, candidate_id))
    validate_candidate_shape(candidate)
    return candidate


def save_candidate(root: Path, candidate: dict[str, Any]) -> None:
    validate_candidate_shape(candidate)
    require_secret_safe(candidate, f"candidate {candidate.get('candidate_id')}")
    atomic_write_json(candidate_path(root, candidate["candidate_id"]), candidate)


def validate_candidate_shape(candidate: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "candidate_id",
        "name",
        "state",
        "risk",
        "scope",
        "source_event_ids",
        "failure_pattern",
        "verification",
        "applicability_boundary",
        "expected_gain",
        "skill_path",
        "artifact_hash",
        "protected_domains",
        "reviews",
        "trials",
        "passes",
        "reliability",
        "owner_approved",
        "approval_nonce",
        "version",
        "history",
    }
    missing = sorted(required - set(candidate))
    if missing:
        raise LearningError(f"Candidate missing fields: {', '.join(missing)}")
    if candidate["schema_version"] != SCHEMA_VERSION:
        raise LearningError("Unsupported candidate schema_version")
    validate_candidate_id(candidate["candidate_id"])
    validate_name(candidate["name"])
    if candidate["state"] not in CANDIDATE_STATES:
        raise LearningError(f"Invalid candidate state: {candidate['state']}")
    if candidate["risk"] not in RISK_LEVELS:
        raise LearningError(f"Invalid candidate risk: {candidate['risk']}")
    if not isinstance(candidate["reviews"], dict):
        raise LearningError("candidate reviews must be an object")
    if not isinstance(candidate["artifact_hash"], str):
        raise LearningError("candidate artifact_hash must be a string")
    if candidate["trials"] < 0 or candidate["passes"] < 0 or candidate["passes"] > candidate["trials"]:
        raise LearningError("Invalid trial/pass counters")
    expected = smoothed_reliability(candidate["passes"], candidate["trials"])
    if abs(float(candidate["reliability"]) - expected) > 1e-9:
        raise LearningError("Candidate reliability does not match pass/trial counters")


def create_candidate(
    root: Path,
    *,
    name: str,
    source_event_ids: list[str],
    failure_pattern: str,
    verification: str,
    applicability_boundary: str,
    risk: str = "medium",
    scope: str = "project",
    expected_gain: str = "",
    skill_path: str = "",
    protected_domains: list[str] | None = None,
) -> dict[str, Any]:
    validate_name(name)
    if risk not in RISK_LEVELS:
        raise LearningError(f"risk must be one of: {', '.join(RISK_LEVELS)}")
    if not source_event_ids:
        raise LearningError("At least one source event is required")
    missing = sorted(set(source_event_ids) - event_ids(root))
    if missing:
        raise LearningError(f"Unknown source event IDs: {', '.join(missing)}")
    if not failure_pattern.strip() or not verification.strip() or not applicability_boundary.strip():
        raise LearningError("failure_pattern, verification, and applicability_boundary are required")

    candidate_id = f"cand-{uuid.uuid4().hex[:12]}"
    now = utc_now()
    stored_skill_path = normalized_artifact_path(root, skill_path) if skill_path.strip() else ""
    artifact_hash = hash_artifact(resolve_artifact_path(root, stored_skill_path))
    candidate: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "candidate_id": candidate_id,
        "name": name,
        "state": "quarantined",
        "risk": risk,
        "scope": scope,
        "created_at": now,
        "updated_at": now,
        "source_event_ids": source_event_ids,
        "failure_pattern": failure_pattern.strip(),
        "verification": verification.strip(),
        "applicability_boundary": applicability_boundary.strip(),
        "expected_gain": expected_gain.strip(),
        "skill_path": stored_skill_path,
        "artifact_hash": artifact_hash,
        "protected_domains": sorted(set(protected_domains or [])),
        "reviews": {},
        "trials": 0,
        "passes": 0,
        "reliability": smoothed_reliability(0, 0),
        "recent_outcomes": [],
        "owner_approved": False,
        "owner_approval": None,
        "approval_nonce": uuid.uuid4().hex,
        "version": 1,
        "history": [
            {
                "timestamp": now,
                "action": "created",
                "state": "quarantined",
                "reason": "Awaiting evidence, evaluation, and safety reviews",
            }
        ],
    }
    save_candidate(root, candidate)
    append_event(
        root,
        "candidate.created",
        {
            "candidate_id": candidate_id,
            "name": name,
            "risk": risk,
            "scope": scope,
            "source_event_ids": source_event_ids,
            "subject_hash": candidate_subject_hash(candidate),
        },
    )
    return candidate


def submit_review(
    root: Path,
    *,
    candidate_id: str,
    kind: str,
    verdict: str,
    reviewer: str,
    notes: str,
    independent: bool,
    evidence: list[str] | None = None,
) -> dict[str, Any]:
    if kind not in REVIEW_KINDS:
        raise LearningError(f"kind must be one of: {', '.join(REVIEW_KINDS)}")
    if verdict not in REVIEW_VERDICTS:
        raise LearningError(f"verdict must be one of: {', '.join(REVIEW_VERDICTS)}")
    if not reviewer.strip() or not notes.strip():
        raise LearningError("reviewer and notes are required")

    candidate = load_candidate(root, candidate_id)
    if candidate["state"] not in ("draft", "quarantined"):
        raise LearningError(f"Cannot review candidate in state {candidate['state']}; revise it first")
    verify_candidate_artifact(root, candidate)
    subject_hash = candidate_subject_hash(candidate)
    review = {
        "review_id": f"review-{uuid.uuid4().hex[:12]}",
        "kind": kind,
        "verdict": verdict,
        "reviewer": reviewer.strip(),
        "independent": bool(independent),
        "notes": notes.strip(),
        "evidence": [item.strip() for item in (evidence or []) if item.strip()],
        "timestamp": utc_now(),
        "candidate_version": candidate["version"],
        "subject_hash": subject_hash,
    }
    candidate["reviews"][kind] = review
    candidate["updated_at"] = utc_now()
    candidate["history"].append(
        {
            "timestamp": review["timestamp"],
            "action": "reviewed",
            "kind": kind,
            "verdict": verdict,
            "review_id": review["review_id"],
        }
    )
    save_candidate(root, candidate)
    append_event(
        root,
        "candidate.reviewed",
        {
            "candidate_id": candidate_id,
            "candidate_version": candidate["version"],
            "subject_hash": subject_hash,
            "review": review,
        },
    )
    return candidate


def normalize_identity(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return " ".join(normalized.casefold().split())


def review_gate(candidate: dict[str, Any], config: dict[str, Any]) -> tuple[bool, list[str]]:
    failures: list[str] = []
    subject_hash = candidate_subject_hash(candidate)
    for kind in REVIEW_KINDS:
        review = candidate["reviews"].get(kind)
        if not review:
            failures.append(f"missing {kind} review")
            continue
        if review.get("candidate_version") != candidate["version"]:
            failures.append(f"stale {kind} review")
        if review.get("subject_hash") != subject_hash:
            failures.append(f"{kind} review is bound to different content")
        if review.get("verdict") != "pass":
            failures.append(f"{kind} review did not pass")
        if config["require_independent_reviews"] and not review.get("independent"):
            failures.append(f"{kind} review is not independent")
    reviewers = [candidate["reviews"].get(kind, {}).get("reviewer") for kind in REVIEW_KINDS]
    reviewers = [normalize_identity(item) for item in reviewers if item]
    if config["require_independent_reviews"] and len(set(reviewers)) != len(reviewers):
        failures.append("reviewers are not distinct")
    return not failures, failures


def approval_request(root: Path, *, candidate_id: str) -> dict[str, Any]:
    candidate = load_candidate(root, candidate_id)
    verify_candidate_artifact(root, candidate)
    return {
        "schema_version": SCHEMA_VERSION,
        "candidate_id": candidate_id,
        "candidate_version": candidate["version"],
        "subject_hash": candidate_subject_hash(candidate),
        "approval_nonce": candidate["approval_nonce"],
        "requested_at": utc_now(),
        "decision": "approve",
    }


def _verify_host_receipt(config: dict[str, Any], request: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version",
        "candidate_id",
        "candidate_version",
        "subject_hash",
        "approval_nonce",
        "decision",
        "approver",
        "authority_ref",
        "approved_at",
        "signature",
    }
    missing = sorted(required - set(receipt))
    if missing:
        raise LearningError(f"Approval receipt missing fields: {', '.join(missing)}")
    for field in (
        "schema_version",
        "candidate_id",
        "candidate_version",
        "subject_hash",
        "approval_nonce",
        "decision",
    ):
        if receipt.get(field) != request.get(field):
            raise LearningError(f"Approval receipt {field} does not match current candidate")
    if not str(receipt.get("approver", "")).strip() or not str(receipt.get("authority_ref", "")).strip():
        raise LearningError("Approval receipt requires approver and authority_ref")
    env_name = config["approval_hmac_env"]
    key = os.environ.get(env_name)
    if not key:
        raise LearningError(
            f"Host-governed approval requires HMAC key in {env_name}; "
            "the agent process should not have access to that key"
        )
    if len(key.encode("utf-8")) < 32:
        raise LearningError("Host approval HMAC key must be at least 32 bytes")
    unsigned = dict(receipt)
    signature = str(unsigned.pop("signature"))
    expected = hmac.new(key.encode("utf-8"), canonical_json(unsigned).encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise LearningError("Approval receipt signature is invalid")
    require_secret_safe(unsigned, "approval receipt")
    verified = dict(unsigned)
    verified["signature"] = signature
    verified["mode"] = "host-receipt"
    return verified


def approve_candidate(
    root: Path,
    *,
    candidate_id: str,
    receipt_path: Path | None = None,
    reviewer: str = "",
    authority_ref: str = "",
    notes: str = "",
) -> dict[str, Any]:
    config = load_config(root)
    candidate = load_candidate(root, candidate_id)
    verify_candidate_artifact(root, candidate)
    if candidate["state"] != "probationary":
        raise LearningError("Approval is accepted only after triple review and promotion to probation")
    if candidate.get("owner_approved"):
        raise LearningError("This candidate version already has an approval receipt")
    passed, failures = review_gate(candidate, config)
    if not passed:
        raise LearningError("Approval blocked by current triple-review gate: " + "; ".join(failures))
    request = approval_request(root, candidate_id=candidate_id)

    if config["approval_mode"] == "host-receipt":
        if receipt_path is None:
            raise LearningError("host-receipt approval requires --receipt")
        receipt = load_json(receipt_path)
        if not isinstance(receipt, dict):
            raise LearningError("Approval receipt must be a JSON object")
        approval = _verify_host_receipt(config, request, receipt)
    else:
        if receipt_path is not None:
            raise LearningError("local-manual approval does not accept --receipt")
        if not reviewer.strip() or not authority_ref.strip():
            raise LearningError("local-manual approval requires reviewer and authority_ref")
        approval = {
            **request,
            "approver": reviewer.strip(),
            "authority_ref": authority_ref.strip(),
            "approved_at": utc_now(),
            "notes": notes.strip(),
            "mode": "local-manual",
        }
        require_secret_safe(approval, "local approval")

    candidate["owner_approved"] = True
    candidate["owner_approval"] = approval
    candidate["updated_at"] = utc_now()
    candidate["history"].append(
        {
            "timestamp": candidate["updated_at"],
            "action": "owner-approved",
            "reviewer": approval["approver"],
            "authority_ref": approval["authority_ref"],
            "mode": approval["mode"],
        }
    )
    save_candidate(root, candidate)
    append_event(
        root,
        "candidate.owner-approved",
        {
            "candidate_id": candidate_id,
            "candidate_version": candidate["version"],
            "subject_hash": candidate_subject_hash(candidate),
            "approval_nonce": candidate["approval_nonce"],
            "approval": approval,
        },
    )
    if (
        candidate["trials"] >= config["probation_min_trials"]
        and candidate["reliability"] >= config["activation_reliability"]
    ):
        allowed, reason = activation_allowed(root, candidate, config)
        if allowed and active_candidate_count(root) < config["max_active_skills"]:
            candidate["state"] = "active"
            candidate["updated_at"] = utc_now()
            candidate["history"].append(
                {
                    "timestamp": candidate["updated_at"],
                    "action": "activated",
                    "reason": reason,
                }
            )
            save_candidate(root, candidate)
            append_event(
                root,
                "candidate.activated",
                {
                    "candidate_id": candidate_id,
                    "candidate_version": candidate["version"],
                    "subject_hash": candidate_subject_hash(candidate),
                    "reason": reason,
                },
            )
    return candidate


def approval_event_valid(root: Path, candidate: dict[str, Any]) -> tuple[bool, str]:
    approval = candidate.get("owner_approval")
    if not candidate.get("owner_approved") or not isinstance(approval, dict):
        return False, "no approval is recorded"
    expected = {
        "candidate_id": candidate["candidate_id"],
        "candidate_version": candidate["version"],
        "subject_hash": candidate_subject_hash(candidate),
        "approval_nonce": candidate["approval_nonce"],
    }
    for key, value in expected.items():
        if approval.get(key) != value:
            return False, f"approval {key} is stale or mismatched"
    matching_event = False
    for event in read_ledger(root):
        if event.get("type") != "candidate.owner-approved":
            continue
        payload = event.get("payload", {})
        if all(payload.get(key) == value for key, value in expected.items()):
            if payload.get("approval") == approval:
                matching_event = True
    if not matching_event:
        return False, "approval is not anchored in the immutable ledger"
    return True, "valid owner/governor approval receipt"


def protected_candidate(candidate: dict[str, Any], config: dict[str, Any]) -> bool:
    protected = set(str(item) for item in config["protected_domains"])
    declared = set(str(item) for item in candidate.get("protected_domains", []))
    haystack = " ".join(
        [
            candidate.get("name", ""),
            candidate.get("failure_pattern", ""),
            candidate.get("applicability_boundary", ""),
        ]
    ).lower()
    return bool(protected & declared) or any(term.lower() in haystack for term in protected)


def promote_candidate(root: Path, *, candidate_id: str) -> dict[str, Any]:
    config = load_config(root)
    candidate = load_candidate(root, candidate_id)
    verify_candidate_artifact(root, candidate)
    if candidate["state"] not in ("draft", "quarantined"):
        raise LearningError(f"Candidate must be draft or quarantined, got {candidate['state']}")
    passed, failures = review_gate(candidate, config)
    if not passed:
        raise LearningError("Triple-review gate failed: " + "; ".join(failures))
    candidate["state"] = "probationary"
    candidate["updated_at"] = utc_now()
    candidate["history"].append(
        {
            "timestamp": candidate["updated_at"],
            "action": "promoted-to-probation",
            "state": "probationary",
        }
    )
    save_candidate(root, candidate)
    append_event(
        root,
        "candidate.probation-started",
        {
            "candidate_id": candidate_id,
            "candidate_version": candidate["version"],
            "review_ids": {kind: candidate["reviews"][kind]["review_id"] for kind in REVIEW_KINDS},
        },
    )
    return candidate


def smoothed_reliability(passes: int, trials: int) -> float:
    return (passes + 1) / (trials + 2)


def active_candidate_count(root: Path) -> int:
    count = 0
    candidates_root = workspace_paths(root)["candidates"]
    for path in candidates_root.glob("*/candidate.json"):
        candidate = load_json(path)
        if candidate.get("state") == "active":
            count += 1
    return count


def activation_allowed(root: Path, candidate: dict[str, Any], config: dict[str, Any]) -> tuple[bool, str]:
    approval_valid, approval_reason = approval_event_valid(root, candidate)
    if protected_candidate(candidate, config):
        if not approval_valid:
            return False, "protected-domain changes always require owner approval"
    if config["require_owner_approval_for_activation"] and not approval_valid:
        return False, "owner approval is required by config"
    if approval_valid:
        return True, approval_reason
    if candidate["risk"] != "low":
        return False, "only low-risk candidates may auto-activate"
    if not config["auto_activate_low_risk"]:
        return False, "low-risk auto-activation is disabled"
    if candidate["scope"] not in config["allowed_auto_activation_scopes"]:
        return False, "scope is not allowlisted for auto-activation"
    return True, "low-risk auto-activation policy passed"


def record_usage(
    root: Path,
    *,
    candidate_id: str,
    outcome: str,
    evidence: list[str],
    notes: str = "",
    metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if outcome not in ("pass", "fail"):
        raise LearningError("usage outcome must be pass or fail")
    clean_evidence = [item.strip() for item in evidence if item.strip()]
    if not clean_evidence:
        raise LearningError("Every probation/active usage requires observable evidence")
    config = load_config(root)
    candidate = load_candidate(root, candidate_id)
    verify_candidate_artifact(root, candidate)
    if candidate["state"] not in ("probationary", "active"):
        raise LearningError(f"Usage can only be recorded for probationary/active candidates, got {candidate['state']}")
    reviews_passed, review_failures = review_gate(candidate, config)
    if not reviews_passed:
        raise LearningError("Usage blocked by current triple-review gate: " + "; ".join(review_failures))
    if candidate["state"] == "active":
        still_allowed, reason = activation_allowed(root, candidate, config)
        if not still_allowed:
            raise LearningError(f"Active candidate is no longer authorized: {reason}")

    old_state = candidate["state"]
    candidate["trials"] += 1
    if outcome == "pass":
        candidate["passes"] += 1
    candidate["reliability"] = smoothed_reliability(candidate["passes"], candidate["trials"])
    candidate["recent_outcomes"] = (candidate.get("recent_outcomes", []) + [outcome])[-10:]
    transition_reason = ""

    failure_burst = candidate["recent_outcomes"][-config["failure_burst_limit"] :]
    should_archive = (
        len(failure_burst) == config["failure_burst_limit"]
        and all(item == "fail" for item in failure_burst)
    ) or (
        candidate["trials"] >= config["archive_min_trials"]
        and candidate["reliability"] < config["archive_reliability"]
    )
    if should_archive:
        candidate["state"] = "archived"
        transition_reason = "reliability/failure-burst safety threshold reached"
    elif (
        candidate["state"] == "probationary"
        and candidate["trials"] >= config["probation_min_trials"]
        and candidate["reliability"] >= config["activation_reliability"]
    ):
        allowed, reason = activation_allowed(root, candidate, config)
        if allowed:
            if active_candidate_count(root) >= config["max_active_skills"]:
                transition_reason = "activation held: active-skill cap reached"
            else:
                candidate["state"] = "active"
                transition_reason = reason
        else:
            transition_reason = f"activation held: {reason}"

    now = utc_now()
    usage = {
        "timestamp": now,
        "outcome": outcome,
        "evidence": clean_evidence,
        "notes": notes.strip(),
        "metrics": metrics or {},
        "trials": candidate["trials"],
        "passes": candidate["passes"],
        "reliability": candidate["reliability"],
        "state_before": old_state,
        "state_after": candidate["state"],
        "transition_reason": transition_reason,
    }
    candidate["updated_at"] = now
    candidate["history"].append({"action": "usage", **usage})
    save_candidate(root, candidate)
    append_event(
        root,
        "candidate.usage-recorded",
        {
            "candidate_id": candidate_id,
            "candidate_version": candidate["version"],
            "usage": usage,
        },
    )
    return candidate


def revise_candidate(
    root: Path,
    *,
    candidate_id: str,
    reason: str,
    failure_pattern: str | None = None,
    verification: str | None = None,
    applicability_boundary: str | None = None,
    risk: str | None = None,
    scope: str | None = None,
    expected_gain: str | None = None,
    skill_path: str | None = None,
    protected_domains: list[str] | None = None,
) -> dict[str, Any]:
    if not reason.strip():
        raise LearningError("revision reason is required")
    candidate = load_candidate(root, candidate_id)
    old_version = candidate["version"]
    old_state = candidate["state"]
    if risk is not None and risk not in RISK_LEVELS:
        raise LearningError(f"risk must be one of: {', '.join(RISK_LEVELS)}")
    if failure_pattern is not None:
        candidate["failure_pattern"] = failure_pattern.strip()
    if verification is not None:
        candidate["verification"] = verification.strip()
    if applicability_boundary is not None:
        candidate["applicability_boundary"] = applicability_boundary.strip()
    if risk is not None:
        candidate["risk"] = risk
    if scope is not None:
        candidate["scope"] = scope.strip()
    if expected_gain is not None:
        candidate["expected_gain"] = expected_gain.strip()
    if skill_path is not None:
        candidate["skill_path"] = normalized_artifact_path(root, skill_path) if skill_path.strip() else ""
    if protected_domains is not None:
        candidate["protected_domains"] = sorted(set(protected_domains))
    if not candidate["failure_pattern"] or not candidate["verification"] or not candidate["applicability_boundary"]:
        raise LearningError("failure_pattern, verification, and applicability_boundary may not be empty")
    candidate["version"] += 1
    candidate["artifact_hash"] = hash_artifact(resolve_artifact_path(root, candidate["skill_path"]))
    candidate["state"] = "quarantined"
    candidate["reviews"] = {}
    candidate["trials"] = 0
    candidate["passes"] = 0
    candidate["reliability"] = smoothed_reliability(0, 0)
    candidate["recent_outcomes"] = []
    candidate["owner_approved"] = False
    candidate["owner_approval"] = None
    candidate["approval_nonce"] = uuid.uuid4().hex
    candidate["updated_at"] = utc_now()
    candidate["history"].append(
        {
            "timestamp": candidate["updated_at"],
            "action": "revised",
            "from_version": old_version,
            "from_state": old_state,
            "to_version": candidate["version"],
            "reason": reason.strip(),
            "subject_hash": candidate_subject_hash(candidate),
        }
    )
    save_candidate(root, candidate)
    append_event(
        root,
        "candidate.revised",
        {
            "candidate_id": candidate_id,
            "from_version": old_version,
            "to_version": candidate["version"],
            "reason": reason.strip(),
            "subject_hash": candidate_subject_hash(candidate),
        },
    )
    return candidate


def archive_candidate(root: Path, *, candidate_id: str, reason: str) -> dict[str, Any]:
    if not reason.strip():
        raise LearningError("archive reason is required")
    candidate = load_candidate(root, candidate_id)
    old_state = candidate["state"]
    candidate["state"] = "archived"
    candidate["updated_at"] = utc_now()
    candidate["history"].append(
        {
            "timestamp": candidate["updated_at"],
            "action": "archived",
            "from_state": old_state,
            "reason": reason.strip(),
        }
    )
    save_candidate(root, candidate)
    append_event(
        root,
        "candidate.archived",
        {"candidate_id": candidate_id, "from_state": old_state, "reason": reason.strip()},
    )
    return candidate


def list_candidates(root: Path) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for path in sorted(workspace_paths(root)["candidates"].glob("*/candidate.json")):
        candidate = load_json(path)
        validate_candidate_shape(candidate)
        candidates.append(candidate)
    return candidates


def normalize_failure_pattern(value: str) -> str:
    return " ".join(value.lower().split())


def curriculum_queue(root: Path, *, limit: int = 10) -> list[dict[str, Any]]:
    """Rank observable learning gaps without inventing goals or running work."""
    if limit < 1:
        raise LearningError("limit must be a positive integer")
    groups: dict[str, dict[str, Any]] = {}
    for event in read_ledger(root):
        if event.get("type") != "experience.recorded":
            continue
        payload = event.get("payload", {})
        pattern = str(payload.get("failure_pattern", "")).strip()
        if not pattern:
            continue
        key = normalize_failure_pattern(pattern)
        item = groups.setdefault(
            key,
            {
                "type": "unresolved-failure-pattern",
                "failure_pattern": pattern,
                "event_ids": [],
                "recurrence": 0,
                "failures": 0,
                "partials": 0,
                "passes": 0,
                "evidence_refs": 0,
                "dead_ends": 0,
            },
        )
        item["event_ids"].append(event["event_id"])
        item["recurrence"] += 1
        outcome = payload.get("outcome")
        if outcome == "fail":
            item["failures"] += 1
        elif outcome == "partial":
            item["partials"] += 1
        elif outcome == "pass":
            item["passes"] += 1
        item["evidence_refs"] += len(payload.get("evidence", []))
        item["dead_ends"] += len(payload.get("dead_ends", []))

    candidates = list_candidates(root)
    covered: dict[str, list[dict[str, str]]] = {}
    opportunities: list[dict[str, Any]] = []
    for candidate in candidates:
        key = normalize_failure_pattern(candidate.get("failure_pattern", ""))
        if key:
            covered.setdefault(key, []).append(
                {"candidate_id": candidate["candidate_id"], "state": candidate["state"]}
            )
        recent_failures = candidate.get("recent_outcomes", [])[-3:].count("fail")
        if candidate["state"] == "active" and (
            recent_failures > 0 or candidate["reliability"] < 0.70
        ):
            opportunities.append(
                {
                    "type": "reevaluate-active-candidate",
                    "candidate_id": candidate["candidate_id"],
                    "name": candidate["name"],
                    "reason": "recent failure or reliability below 0.70",
                    "priority": round(5 + recent_failures * 3 + (0.70 - candidate["reliability"]) * 10, 3),
                }
            )

    for key, item in groups.items():
        live_cover = [entry for entry in covered.get(key, []) if entry["state"] != "archived"]
        negative_weight = item["failures"] * 2 + item["partials"]
        evidence_factor = 1 + min(item["evidence_refs"], 5) * 0.1
        dead_end_factor = 1 + min(item["dead_ends"], 3) * 0.15
        score = item["recurrence"] * (1 + negative_weight) * evidence_factor * dead_end_factor
        item["priority"] = round(score, 3)
        item["covered_by"] = live_cover
        if live_cover:
            item["recommended_action"] = "evaluate or revise the existing candidate; do not duplicate it"
            item["priority"] = round(item["priority"] * 0.6, 3)
        else:
            item["recommended_action"] = "reproduce, establish a baseline, and draft one bounded candidate"
        opportunities.append(item)

    opportunities.sort(key=lambda item: (-float(item.get("priority", 0)), str(item.get("type", ""))))
    return opportunities[:limit]


def next_actions(root: Path) -> dict[str, Any]:
    config = load_config(root)
    actions: list[dict[str, Any]] = []
    for candidate in list_candidates(root):
        candidate_id = candidate["candidate_id"]
        try:
            verify_candidate_artifact(root, candidate)
        except LearningError as exc:
            actions.append(
                {
                    "candidate_id": candidate_id,
                    "name": candidate["name"],
                    "priority": 100,
                    "action": "revise",
                    "reason": str(exc),
                }
            )
            continue
        if candidate["state"] in ("draft", "quarantined"):
            passed, failures = review_gate(candidate, config)
            if not passed:
                actions.append(
                    {
                        "candidate_id": candidate_id,
                        "name": candidate["name"],
                        "priority": 80,
                        "action": "complete-triple-review",
                        "reason": "; ".join(failures),
                    }
                )
            else:
                actions.append(
                    {
                        "candidate_id": candidate_id,
                        "name": candidate["name"],
                        "priority": 70,
                        "action": "promote-to-probation",
                        "reason": "current evidence, evaluation, and safety reviews pass",
                    }
                )
        elif candidate["state"] == "probationary":
            if candidate["trials"] < config["probation_min_trials"]:
                actions.append(
                    {
                        "candidate_id": candidate_id,
                        "name": candidate["name"],
                        "priority": 60,
                        "action": "run-judged-probation-case",
                        "reason": f"{config['probation_min_trials'] - candidate['trials']} minimum trials remain",
                    }
                )
            elif candidate["reliability"] < config["activation_reliability"]:
                actions.append(
                    {
                        "candidate_id": candidate_id,
                        "name": candidate["name"],
                        "priority": 65,
                        "action": "revise-or-gather-disconfirming-evidence",
                        "reason": f"reliability {candidate['reliability']:.3f} is below activation threshold",
                    }
                )
            else:
                activation_ready, reason = activation_allowed(root, candidate, config)
                if not activation_ready:
                    actions.append(
                        {
                            "candidate_id": candidate_id,
                            "name": candidate["name"],
                            "priority": 55,
                            "action": "obtain-owner-governor-approval",
                            "reason": reason,
                        }
                    )
                else:
                    actions.append(
                        {
                            "candidate_id": candidate_id,
                            "name": candidate["name"],
                            "priority": 50,
                            "action": "record-next-judged-use",
                            "reason": "activation conditions are ready to be evaluated",
                        }
                    )
        elif candidate["state"] == "active":
            if "fail" in candidate.get("recent_outcomes", [])[-3:]:
                actions.append(
                    {
                        "candidate_id": candidate_id,
                        "name": candidate["name"],
                        "priority": 75,
                        "action": "replay-and-consider-revision",
                        "reason": "an active candidate has a recent judged failure",
                    }
                )
    actions.sort(key=lambda item: (-int(item["priority"]), item["candidate_id"]))
    return {
        "candidate_actions": actions,
        "curriculum_opportunities": curriculum_queue(root, limit=3),
    }


def generate_report(root: Path) -> str:
    ledger = verify_ledger(root)
    candidates = list_candidates(root)
    state_counts = {state: 0 for state in CANDIDATE_STATES}
    for candidate in candidates:
        state_counts[candidate["state"]] += 1

    lines = [
        "# Learning lifecycle report",
        "",
        f"Generated: {utc_now()}",
        f"Ledger events: {ledger['events']}",
        f"Ledger head: `{ledger['head_hash'] or 'empty'}`",
        "",
        "## State summary",
        "",
    ]
    for state in CANDIDATE_STATES:
        lines.append(f"- {state}: {state_counts[state]}")
    lines.extend(["", "## Candidates", ""])
    if not candidates:
        lines.append("No candidates.")
    for candidate in candidates:
        review_status = ", ".join(
            f"{kind}={candidate['reviews'].get(kind, {}).get('verdict', 'missing')}"
            for kind in REVIEW_KINDS
        )
        lines.extend(
            [
                f"### {candidate['name']} (`{candidate['candidate_id']}`)",
                "",
                f"- State: {candidate['state']}",
                f"- Risk/scope: {candidate['risk']} / {candidate['scope']}",
                f"- Version: {candidate['version']}",
                f"- Reliability: {candidate['reliability']:.3f} ({candidate['passes']}/{candidate['trials']} passes)",
                f"- Owner approved: {str(candidate['owner_approved']).lower()}",
                f"- Reviews: {review_status}",
                f"- Boundary: {candidate['applicability_boundary']}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def write_report(root: Path, output: Path | None = None) -> Path:
    report = generate_report(root)
    output = output or (workspace_paths(root)["reports"] / "latest.md")
    atomic_write_text(output, report)
    return output


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise LearningError("SKILL.md must begin with YAML frontmatter")
    try:
        end = next(index for index in range(1, len(lines)) if lines[index].strip() == "---")
    except StopIteration as exc:
        raise LearningError("SKILL.md frontmatter is not closed") from exc
    front_lines = lines[1:end]
    values: dict[str, str] = {}
    current_key: str | None = None
    block: list[str] = []

    def flush() -> None:
        nonlocal current_key, block
        if current_key is not None:
            values[current_key] = " ".join(part.strip() for part in block if part.strip()).strip()
        current_key = None
        block = []

    for raw in front_lines:
        match = re.match(r"^([A-Za-z][A-Za-z0-9_-]*):(?:\s*(.*))?$", raw)
        if match:
            flush()
            key, value = match.group(1), (match.group(2) or "").strip()
            if value in (">", "|", ">-", "|-"):
                current_key = key
                block = []
            else:
                values[key] = value.strip('"\'')
        elif current_key is not None and (raw.startswith(" ") or not raw.strip()):
            block.append(raw)
    flush()
    body = "\n".join(lines[end + 1 :])
    return values, body


def validate_skill(path: Path, *, harvested: bool = False) -> dict[str, Any]:
    skill_path = path / "SKILL.md" if path.is_dir() else path
    artifact_root = path if path.is_dir() else skill_path
    errors: list[str] = []
    warnings: list[str] = []
    if not skill_path.exists():
        return {"valid": False, "errors": [f"Missing {skill_path}"], "warnings": []}
    text = skill_path.read_text(encoding="utf-8")
    try:
        frontmatter, body = parse_frontmatter(text)
    except LearningError as exc:
        return {"valid": False, "errors": [str(exc)], "warnings": []}

    name = frontmatter.get("name", "")
    description = frontmatter.get("description", "")
    if not name:
        errors.append("frontmatter.name is required")
    else:
        try:
            validate_name(name)
        except LearningError as exc:
            errors.append(str(exc))
        if name != skill_path.parent.name:
            errors.append("frontmatter.name must match the parent directory name")
    if not description:
        errors.append("frontmatter.description is required")
    elif len(description) > 1024:
        errors.append("frontmatter.description exceeds 1024 characters")
    elif not re.search(r"\b(?:use|when)\b", description, re.I):
        warnings.append("description should clearly state when the skill is used")
    if len(text.splitlines()) > 500:
        errors.append("SKILL.md exceeds 500 lines")
    try:
        package_findings = artifact_secret_findings(artifact_root)
    except LearningError as exc:
        errors.append(str(exc))
        package_findings = []
    if package_findings:
        errors.append("possible secret material: " + "; ".join(package_findings))
    if harvested:
        required_markers = {
            "applicability boundary": r"applicability boundary|when not to use|scope boundary",
            "verification": r"verified by|verification|passing check",
            "failure pattern": r"failure pattern",
            "dead-end": r"what didn.t work|ruled-out dead-end|dead end",
            "rollback": r"rollback|archive|revert",
        }
        lowered = body.lower()
        for label, pattern in required_markers.items():
            if not re.search(pattern, lowered, re.I):
                errors.append(f"harvested skill is missing {label}")
    return {
        "valid": not errors,
        "path": str(skill_path),
        "name": name,
        "description_length": len(description),
        "lines": len(text.splitlines()),
        "errors": errors,
        "warnings": warnings,
    }


def audit_workspace(root: Path) -> dict[str, Any]:
    ledger = verify_ledger(root)
    config = load_config(root)
    candidates = list_candidates(root)
    issues: list[str] = []
    for candidate in candidates:
        try:
            verify_candidate_artifact(root, candidate)
        except LearningError as exc:
            issues.append(f"{candidate['candidate_id']}: {exc}")
        passed, failures = review_gate(candidate, config)
        if candidate["state"] in ("probationary", "active") and not passed:
            issues.append(f"{candidate['candidate_id']}: durable state without current triple review ({'; '.join(failures)})")
        if candidate["state"] == "active":
            allowed, reason = activation_allowed(root, candidate, config)
            if not allowed:
                issues.append(f"{candidate['candidate_id']}: active but activation policy fails ({reason})")
    return {
        "valid": not issues,
        "ledger": ledger,
        "candidates": len(candidates),
        "issues": issues,
    }


def parse_json_arg(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LearningError(f"Invalid JSON argument: {exc}") from exc
    if not isinstance(value, dict):
        raise LearningError("JSON argument must be an object")
    return value


def output_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False))


def add_root_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--root", type=Path, default=Path(".agent-learning"), help="Learning workspace")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    init_parser = sub.add_parser("init", help="Initialize a learning workspace")
    add_root_argument(init_parser)
    init_parser.add_argument("--config-json", help="Override default config with a JSON object")

    record_parser = sub.add_parser("record", help="Record an observable task outcome")
    add_root_argument(record_parser)
    record_parser.add_argument("--task-id", required=True)
    record_parser.add_argument("--outcome", choices=OUTCOMES, required=True)
    record_parser.add_argument("--summary", required=True)
    record_parser.add_argument("--evidence", action="append", default=[])
    record_parser.add_argument("--scope", default="project")
    record_parser.add_argument("--skill", default="")
    record_parser.add_argument("--failure-pattern", default="")
    record_parser.add_argument("--dead-end", action="append", default=[])
    record_parser.add_argument("--metrics-json")
    record_parser.add_argument("--source-trust", choices=("trusted", "mixed", "untrusted"), default="mixed")

    candidate_parser = sub.add_parser("candidate", help="Create a quarantined learning candidate")
    add_root_argument(candidate_parser)
    candidate_parser.add_argument("--name", required=True)
    candidate_parser.add_argument("--source-event", action="append", required=True)
    candidate_parser.add_argument("--failure-pattern", required=True)
    candidate_parser.add_argument("--verification", required=True)
    candidate_parser.add_argument("--boundary", required=True)
    candidate_parser.add_argument("--risk", choices=RISK_LEVELS, default="medium")
    candidate_parser.add_argument("--scope", default="project")
    candidate_parser.add_argument("--expected-gain", default="")
    candidate_parser.add_argument("--skill-path", default="")
    candidate_parser.add_argument("--protected-domain", action="append", default=[])

    review_parser = sub.add_parser("review", help="Submit one independent review")
    add_root_argument(review_parser)
    review_parser.add_argument("--candidate", required=True)
    review_parser.add_argument("--kind", choices=REVIEW_KINDS, required=True)
    review_parser.add_argument("--verdict", choices=REVIEW_VERDICTS, required=True)
    review_parser.add_argument("--reviewer", required=True)
    review_parser.add_argument("--notes", required=True)
    review_parser.add_argument("--evidence", action="append", default=[])
    review_parser.add_argument("--independent", action="store_true")

    approval_request_parser = sub.add_parser(
        "approval-request", help="Emit the exact candidate/version/hash payload for a host approval receipt"
    )
    add_root_argument(approval_request_parser)
    approval_request_parser.add_argument("--candidate", required=True)

    approve_parser = sub.add_parser("approve", help="Record a verified host receipt or explicit local-manual approval")
    add_root_argument(approve_parser)
    approve_parser.add_argument("--candidate", required=True)
    approve_parser.add_argument("--receipt", type=Path)
    approve_parser.add_argument("--reviewer", default="")
    approve_parser.add_argument("--authority-ref", default="")
    approve_parser.add_argument("--notes", default="")

    promote_parser = sub.add_parser("promote", help="Move a triple-reviewed candidate into probation")
    add_root_argument(promote_parser)
    promote_parser.add_argument("--candidate", required=True)

    usage_parser = sub.add_parser("usage", help="Record a judged probation/active invocation")
    add_root_argument(usage_parser)
    usage_parser.add_argument("--candidate", required=True)
    usage_parser.add_argument("--outcome", choices=("pass", "fail"), required=True)
    usage_parser.add_argument("--evidence", action="append", required=True)
    usage_parser.add_argument("--notes", default="")
    usage_parser.add_argument("--metrics-json")

    revise_parser = sub.add_parser("revise", help="Quarantine a new candidate version and reset reviews")
    add_root_argument(revise_parser)
    revise_parser.add_argument("--candidate", required=True)
    revise_parser.add_argument("--reason", required=True)
    revise_parser.add_argument("--failure-pattern")
    revise_parser.add_argument("--verification")
    revise_parser.add_argument("--boundary")
    revise_parser.add_argument("--risk", choices=RISK_LEVELS)
    revise_parser.add_argument("--scope")
    revise_parser.add_argument("--expected-gain")
    revise_parser.add_argument("--skill-path")
    revise_parser.add_argument("--protected-domain", action="append")

    archive_parser = sub.add_parser("archive", help="Archive a candidate immediately")
    add_root_argument(archive_parser)
    archive_parser.add_argument("--candidate", required=True)
    archive_parser.add_argument("--reason", required=True)

    report_parser = sub.add_parser("report", help="Write a human-readable lifecycle report")
    add_root_argument(report_parser)
    report_parser.add_argument("--output", type=Path)

    queue_parser = sub.add_parser("queue", help="Rank evidence-backed learning gaps for a bounded curriculum run")
    add_root_argument(queue_parser)
    queue_parser.add_argument("--limit", type=int, default=10)

    next_parser = sub.add_parser("next", help="Show the next lifecycle gate and top curriculum opportunities")
    add_root_argument(next_parser)

    verify_parser = sub.add_parser("verify-ledger", help="Verify the immutable event hash chain")
    add_root_argument(verify_parser)

    audit_parser = sub.add_parser("audit", help="Audit ledger, candidate state, reviews, and governance")
    add_root_argument(audit_parser)

    validate_parser = sub.add_parser("validate-skill", help="Validate Agent Skills structure and safety")
    validate_parser.add_argument("path", type=Path)
    validate_parser.add_argument("--harvested", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            config = initialize(args.root, parse_json_arg(args.config_json))
            output_json({"root": str(args.root), "config": config})
        elif args.command == "record":
            initialize(args.root)
            output_json(
                record_experience(
                    args.root,
                    task_id=args.task_id,
                    outcome=args.outcome,
                    summary=args.summary,
                    evidence=args.evidence,
                    scope=args.scope,
                    skill=args.skill,
                    failure_pattern=args.failure_pattern,
                    dead_ends=args.dead_end,
                    metrics=parse_json_arg(args.metrics_json),
                    source_trust=args.source_trust,
                )
            )
        elif args.command == "candidate":
            initialize(args.root)
            output_json(
                create_candidate(
                    args.root,
                    name=args.name,
                    source_event_ids=args.source_event,
                    failure_pattern=args.failure_pattern,
                    verification=args.verification,
                    applicability_boundary=args.boundary,
                    risk=args.risk,
                    scope=args.scope,
                    expected_gain=args.expected_gain,
                    skill_path=args.skill_path,
                    protected_domains=args.protected_domain,
                )
            )
        elif args.command == "review":
            initialize(args.root)
            output_json(
                submit_review(
                    args.root,
                    candidate_id=args.candidate,
                    kind=args.kind,
                    verdict=args.verdict,
                    reviewer=args.reviewer,
                    notes=args.notes,
                    independent=args.independent,
                    evidence=args.evidence,
                )
            )
        elif args.command == "approval-request":
            initialize(args.root)
            output_json(approval_request(args.root, candidate_id=args.candidate))
        elif args.command == "approve":
            initialize(args.root)
            output_json(
                approve_candidate(
                    args.root,
                    candidate_id=args.candidate,
                    receipt_path=args.receipt,
                    reviewer=args.reviewer,
                    authority_ref=args.authority_ref,
                    notes=args.notes,
                )
            )
        elif args.command == "promote":
            initialize(args.root)
            output_json(promote_candidate(args.root, candidate_id=args.candidate))
        elif args.command == "usage":
            initialize(args.root)
            output_json(
                record_usage(
                    args.root,
                    candidate_id=args.candidate,
                    outcome=args.outcome,
                    evidence=args.evidence,
                    notes=args.notes,
                    metrics=parse_json_arg(args.metrics_json),
                )
            )
        elif args.command == "revise":
            initialize(args.root)
            output_json(
                revise_candidate(
                    args.root,
                    candidate_id=args.candidate,
                    reason=args.reason,
                    failure_pattern=args.failure_pattern,
                    verification=args.verification,
                    applicability_boundary=args.boundary,
                    risk=args.risk,
                    scope=args.scope,
                    expected_gain=args.expected_gain,
                    skill_path=args.skill_path,
                    protected_domains=args.protected_domain,
                )
            )
        elif args.command == "archive":
            initialize(args.root)
            output_json(archive_candidate(args.root, candidate_id=args.candidate, reason=args.reason))
        elif args.command == "report":
            initialize(args.root)
            path = write_report(args.root, args.output)
            output_json({"report": str(path)})
        elif args.command == "queue":
            initialize(args.root)
            output_json(curriculum_queue(args.root, limit=args.limit))
        elif args.command == "next":
            initialize(args.root)
            output_json(next_actions(args.root))
        elif args.command == "verify-ledger":
            output_json(verify_ledger(args.root))
        elif args.command == "audit":
            initialize(args.root)
            result = audit_workspace(args.root)
            output_json(result)
            return 0 if result["valid"] else 1
        elif args.command == "validate-skill":
            result = validate_skill(args.path, harvested=args.harvested)
            output_json(result)
            return 0 if result["valid"] else 1
        else:  # pragma: no cover
            parser.error("Unknown command")
    except LearningError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
