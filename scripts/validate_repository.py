#!/usr/bin/env python3
"""Validate repository structure, metadata, links, JSON, and the core skill."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_VERSION = "2.0.0"
REQUIRED_FILES = (
    "LICENSE",
    "README.md",
    "AGENTS.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "skills.sh.json",
    ".claude-plugin/marketplace.json",
    ".cursor/rules/self-learning.mdc",
    ".github/workflows/validate.yml",
    "skills/self-learning/SKILL.md",
    "skills/self-learning/scripts/learning_cycle.py",
    "skills/self-learning/assets/SKILL.template.md",
    "skills/self-learning/assets/lesson-receipt.template.json",
    "skills/self-learning/assets/eval-case.template.json",
    "skills/self-learning/assets/approval-receipt.template.json",
    "skills/self-learning/assets/curriculum-trigger.template.json",
    "skills/self-learning/assets/review-prompts.md",
    "skills/self-learning/assets/learning-config.example.json",
    "skills/self-learning/references/architecture.md",
    "skills/self-learning/references/review-protocol.md",
    "skills/self-learning/references/autonomous-curriculum.md",
    "skills/self-learning/references/approval.md",
    "skills/self-learning/references/research-foundations.md",
    "skills/self-learning/references/teamon-one.md",
    "skills/self-learning/references/skill-authoring.md",
    "tests/test_learning_cycle.py",
    "tests/test_cli.py",
)
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


def load_learning_module():
    path = ROOT / "skills/self-learning/scripts/learning_cycle.py"
    spec = importlib.util.spec_from_file_location("learning_cycle_validation", path)
    if not spec or not spec.loader:
        raise RuntimeError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def local_link_errors(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    for raw_target in LINK_RE.findall(text):
        target = raw_target.strip()
        if " " in target and not target.startswith("<"):
            target = target.split(" ", 1)[0]
        target = target.strip("<>")
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        target = unquote(target.split("#", 1)[0])
        if not target:
            continue
        resolved = (path.parent / target).resolve()
        try:
            resolved.relative_to(ROOT)
        except ValueError:
            errors.append(f"{path.relative_to(ROOT)}: link escapes repository: {raw_target}")
            continue
        if not resolved.exists():
            errors.append(f"{path.relative_to(ROOT)}: missing link target: {raw_target}")
    return errors


def main() -> int:
    errors: list[str] = []

    for relative in REQUIRED_FILES:
        if not (ROOT / relative).exists():
            errors.append(f"missing required file: {relative}")

    json_files = sorted(ROOT.rglob("*.json"))
    for path in json_files:
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid JSON {path.relative_to(ROOT)}: {exc}")

    marketplace_path = ROOT / ".claude-plugin/marketplace.json"
    if marketplace_path.exists():
        marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
        if marketplace.get("owner", {}).get("name") != "natural0101":
            errors.append("marketplace owner must be natural0101")
        if marketplace.get("metadata", {}).get("version") != EXPECTED_VERSION:
            errors.append("marketplace metadata version mismatch")
        for plugin in marketplace.get("plugins", []):
            if plugin.get("version") != EXPECTED_VERSION:
                errors.append(f"plugin version mismatch: {plugin.get('name')}")

    learning = load_learning_module()
    validation = learning.validate_skill(ROOT / "skills/self-learning")
    errors.extend(f"core skill: {item}" for item in validation["errors"])
    frontmatter, _ = learning.parse_frontmatter(
        (ROOT / "skills/self-learning/SKILL.md").read_text(encoding="utf-8")
    )
    if frontmatter.get("name") != "self-learning":
        errors.append("core skill name mismatch")

    skill_text = (ROOT / "skills/self-learning/SKILL.md").read_text(encoding="utf-8")
    if "skills/self-learning/scripts/learning_cycle.py" in skill_text:
        errors.append("core skill hardcodes source-repository script path instead of installed skill root")
    if f'version: "{EXPECTED_VERSION}"' not in skill_text:
        errors.append("core skill version mismatch")

    for path in sorted(ROOT.rglob("*.md")):
        errors.extend(local_link_errors(path))

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "valid": True,
                "required_files": len(REQUIRED_FILES),
                "json_files": len(json_files),
                "core_skill_lines": validation["lines"],
                "core_skill_description_length": validation["description_length"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
