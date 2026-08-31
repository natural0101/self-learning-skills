from __future__ import annotations

import importlib.util
import hashlib
import hmac
import json
import os
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "self-learning"
    / "scripts"
    / "learning_cycle.py"
)
spec = importlib.util.spec_from_file_location("learning_cycle", MODULE_PATH)
assert spec and spec.loader
learning = importlib.util.module_from_spec(spec)
spec.loader.exec_module(learning)


class LearningCycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / ".agent-learning"
        learning.initialize(self.root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _update_config(self, **updates) -> None:
        config_path = self.root / "config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config.update(updates)
        learning.atomic_write_json(config_path, config)

    def _enable_local_manual_approval(self) -> None:
        self._update_config(approval_mode="local-manual")

    def _experience(self) -> dict:
        return learning.record_experience(
            self.root,
            task_id="task-1",
            outcome="pass",
            summary="The targeted test passed after fixing the cache invalidation order.",
            evidence=["pytest tests/test_cache.py::test_refresh -> 1 passed"],
            failure_pattern="stale cache produced phantom results",
            dead_ends=["Restarting the caller did not invalidate the server cache"],
        )

    def _candidate(self, *, risk: str = "low", protected_domains=None) -> dict:
        event = self._experience()
        return learning.create_candidate(
            self.root,
            name="refresh-cache-safely",
            source_event_ids=[event["event_id"]],
            failure_pattern="stale cache produced phantom results",
            verification="Targeted regression test passed three times from a clean process",
            applicability_boundary="Only this project's development cache; never production writes",
            risk=risk,
            protected_domains=protected_domains or [],
        )

    def _triple_review(self, candidate_id: str) -> None:
        for kind, reviewer in (
            ("evidence", "reviewer-evidence"),
            ("evaluation", "reviewer-evaluation"),
            ("safety", "reviewer-safety"),
        ):
            learning.submit_review(
                self.root,
                candidate_id=candidate_id,
                kind=kind,
                verdict="pass",
                reviewer=reviewer,
                notes=f"Independent {kind} review passed against the candidate evidence.",
                independent=True,
                evidence=[f"review/{kind}.json"],
            )

    def test_initialize_and_hash_chain(self) -> None:
        self._experience()
        result = learning.verify_ledger(self.root)
        self.assertTrue(result["valid"])
        self.assertEqual(result["events"], 1)
        self.assertEqual(len(result["head_hash"]), 64)

    def test_tampered_ledger_is_rejected(self) -> None:
        self._experience()
        ledger = self.root / "ledger.jsonl"
        text = ledger.read_text(encoding="utf-8").replace("phantom", "invented", 1)
        ledger.write_text(text, encoding="utf-8")
        with self.assertRaises(learning.LearningError):
            learning.verify_ledger(self.root)

    def test_possible_secret_is_rejected(self) -> None:
        with self.assertRaises(learning.LearningError):
            learning.record_experience(
                self.root,
                task_id="secret-task",
                outcome="pass",
                summary="Used literal credential sk-1234567890abcdefghijklmnop",
                evidence=["command exited 0"],
            )

    def test_passing_experience_requires_evidence(self) -> None:
        with self.assertRaises(learning.LearningError):
            learning.record_experience(
                self.root,
                task_id="task-no-proof",
                outcome="pass",
                summary="It looked fine.",
                evidence=[],
            )

    def test_candidate_requires_known_source_event(self) -> None:
        with self.assertRaises(learning.LearningError):
            learning.create_candidate(
                self.root,
                name="missing-source",
                source_event_ids=["does-not-exist"],
                failure_pattern="missing evidence",
                verification="test passed",
                applicability_boundary="project only",
            )

    def test_probation_requires_three_distinct_independent_reviews(self) -> None:
        candidate = self._candidate()
        for kind in learning.REVIEW_KINDS:
            learning.submit_review(
                self.root,
                candidate_id=candidate["candidate_id"],
                kind=kind,
                verdict="pass",
                reviewer="same-reviewer",
                notes="Review passed.",
                independent=True,
            )
        with self.assertRaises(learning.LearningError):
            learning.promote_candidate(self.root, candidate_id=candidate["candidate_id"])

    def test_owner_approved_candidate_activates_after_successful_probation(self) -> None:
        self._enable_local_manual_approval()
        candidate = self._candidate()
        candidate_id = candidate["candidate_id"]
        self._triple_review(candidate_id)
        promoted = learning.promote_candidate(self.root, candidate_id=candidate_id)
        self.assertEqual(promoted["state"], "probationary")
        for index in range(3):
            current = learning.record_usage(
                self.root,
                candidate_id=candidate_id,
                outcome="pass",
                evidence=[f"eval/probation-{index}.json"],
            )
        self.assertEqual(current["state"], "probationary")
        current = learning.approve_candidate(
            self.root,
            candidate_id=candidate_id,
            reviewer="owner",
            authority_ref="local-owner-terminal",
            notes="Approved for this project scope.",
        )
        self.assertEqual(current["state"], "active")
        self.assertAlmostEqual(current["reliability"], 0.8)

    def test_default_governance_holds_unapproved_candidate_in_probation(self) -> None:
        candidate = self._candidate()
        candidate_id = candidate["candidate_id"]
        self._triple_review(candidate_id)
        learning.promote_candidate(self.root, candidate_id=candidate_id)
        for index in range(3):
            current = learning.record_usage(
                self.root,
                candidate_id=candidate_id,
                outcome="pass",
                evidence=[f"eval/probation-{index}.json"],
            )
        self.assertEqual(current["state"], "probationary")
        self.assertIn("owner approval", current["history"][-1]["transition_reason"])

    def test_opt_in_low_risk_auto_activation(self) -> None:
        self._update_config(
            require_owner_approval_for_activation=False,
            auto_activate_low_risk=True,
        )

        candidate = self._candidate()
        candidate_id = candidate["candidate_id"]
        self._triple_review(candidate_id)
        learning.promote_candidate(self.root, candidate_id=candidate_id)
        for index in range(3):
            current = learning.record_usage(
                self.root,
                candidate_id=candidate_id,
                outcome="pass",
                evidence=[f"eval/auto-{index}.json"],
            )
        self.assertEqual(current["state"], "active")

    def test_protected_domain_never_auto_activates_without_owner(self) -> None:
        self._update_config(
            require_owner_approval_for_activation=False,
            auto_activate_low_risk=True,
        )

        candidate = self._candidate(protected_domains=["permissions"])
        candidate_id = candidate["candidate_id"]
        self._triple_review(candidate_id)
        learning.promote_candidate(self.root, candidate_id=candidate_id)
        for index in range(3):
            current = learning.record_usage(
                self.root,
                candidate_id=candidate_id,
                outcome="pass",
                evidence=[f"eval/protected-{index}.json"],
            )
        self.assertEqual(current["state"], "probationary")
        self.assertIn("protected-domain", current["history"][-1]["transition_reason"])

    def test_failure_burst_archives_candidate(self) -> None:
        candidate = self._candidate()
        candidate_id = candidate["candidate_id"]
        self._triple_review(candidate_id)
        learning.promote_candidate(self.root, candidate_id=candidate_id)
        for index in range(3):
            current = learning.record_usage(
                self.root,
                candidate_id=candidate_id,
                outcome="fail",
                evidence=[f"eval/failure-{index}.json"],
            )
        self.assertEqual(current["state"], "archived")

    def test_revision_invalidates_reviews_and_approval(self) -> None:
        self._enable_local_manual_approval()
        candidate = self._candidate()
        candidate_id = candidate["candidate_id"]
        self._triple_review(candidate_id)
        learning.promote_candidate(self.root, candidate_id=candidate_id)
        learning.approve_candidate(
            self.root,
            candidate_id=candidate_id,
            reviewer="owner",
            authority_ref="local-owner-terminal",
        )
        revised = learning.revise_candidate(self.root, candidate_id=candidate_id, reason="Boundary was too broad")
        self.assertEqual(revised["version"], 2)
        self.assertEqual(revised["state"], "quarantined")
        self.assertEqual(revised["reviews"], {})
        self.assertFalse(revised["owner_approved"])

    def test_audit_passes_for_valid_workspace(self) -> None:
        candidate = self._candidate()
        self._triple_review(candidate["candidate_id"])
        learning.promote_candidate(self.root, candidate_id=candidate["candidate_id"])
        result = learning.audit_workspace(self.root)
        self.assertTrue(result["valid"])

    def test_host_signed_approval_receipt_is_verified(self) -> None:
        candidate = self._candidate()
        self._triple_review(candidate["candidate_id"])
        learning.promote_candidate(self.root, candidate_id=candidate["candidate_id"])
        request = learning.approval_request(self.root, candidate_id=candidate["candidate_id"])
        receipt = {
            **request,
            "approver": "teamon-owner-control",
            "authority_ref": "memory-review/receipt-42",
            "approved_at": "2026-08-31T12:00:00Z",
        }
        key = "test-only-owner-key-that-is-32-bytes-minimum"
        receipt["signature"] = hmac.new(
            key.encode("utf-8"),
            learning.canonical_json(receipt).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        receipt_path = Path(self.temp.name) / "approval.json"
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        old = os.environ.get("SELF_LEARNING_APPROVAL_KEY")
        os.environ["SELF_LEARNING_APPROVAL_KEY"] = key
        try:
            approved = learning.approve_candidate(
                self.root,
                candidate_id=candidate["candidate_id"],
                receipt_path=receipt_path,
            )
        finally:
            if old is None:
                os.environ.pop("SELF_LEARNING_APPROVAL_KEY", None)
            else:
                os.environ["SELF_LEARNING_APPROVAL_KEY"] = old
        self.assertTrue(approved["owner_approved"])
        self.assertEqual(approved["owner_approval"]["mode"], "host-receipt")

    def test_invalid_host_approval_signature_is_rejected(self) -> None:
        candidate = self._candidate()
        self._triple_review(candidate["candidate_id"])
        learning.promote_candidate(self.root, candidate_id=candidate["candidate_id"])
        request = learning.approval_request(self.root, candidate_id=candidate["candidate_id"])
        receipt = {
            **request,
            "approver": "fake-owner",
            "authority_ref": "fake/receipt",
            "approved_at": "2026-08-31T12:00:00Z",
            "signature": "0" * 64,
        }
        receipt_path = Path(self.temp.name) / "bad-approval.json"
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        old = os.environ.get("SELF_LEARNING_APPROVAL_KEY")
        os.environ["SELF_LEARNING_APPROVAL_KEY"] = "different-test-key-that-is-at-least-32-bytes"
        try:
            with self.assertRaises(learning.LearningError):
                learning.approve_candidate(
                    self.root,
                    candidate_id=candidate["candidate_id"],
                    receipt_path=receipt_path,
                )
        finally:
            if old is None:
                os.environ.pop("SELF_LEARNING_APPROVAL_KEY", None)
            else:
                os.environ["SELF_LEARNING_APPROVAL_KEY"] = old

    def test_candidate_id_path_traversal_is_rejected(self) -> None:
        with self.assertRaises(learning.LearningError):
            learning.load_candidate(self.root, "../../outside")

    def test_review_is_bound_to_exact_artifact_hash(self) -> None:
        skill_dir = Path(self.temp.name) / "project" / "skills" / "bound-skill"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            "---\nname: bound-skill\ndescription: Use this skill when testing exact binding.\n---\n# v1\n",
            encoding="utf-8",
        )
        event = self._experience()
        candidate = learning.create_candidate(
            self.root,
            name="bound-skill",
            source_event_ids=[event["event_id"]],
            failure_pattern="artifact drift after review",
            verification="fixture exists and validator reads it",
            applicability_boundary="test fixture only",
            skill_path=str(skill_dir),
        )
        learning.submit_review(
            self.root,
            candidate_id=candidate["candidate_id"],
            kind="evidence",
            verdict="pass",
            reviewer="evidence-reviewer",
            notes="Reviewed v1.",
            independent=True,
        )
        skill_file.write_text(
            "---\nname: bound-skill\ndescription: Use this skill when testing exact binding.\n---\n# silently changed v2\n",
            encoding="utf-8",
        )
        with self.assertRaises(learning.LearningError):
            learning.submit_review(
                self.root,
                candidate_id=candidate["candidate_id"],
                kind="evaluation",
                verdict="pass",
                reviewer="evaluation-reviewer",
                notes="Must not review an unsealed change.",
                independent=True,
            )

    def test_snapshot_only_approval_cannot_activate_without_ledger_event(self) -> None:
        candidate = self._candidate()
        candidate_id = candidate["candidate_id"]
        self._triple_review(candidate_id)
        candidate = learning.promote_candidate(self.root, candidate_id=candidate_id)
        candidate["owner_approved"] = True
        candidate["owner_approval"] = {
            **learning.approval_request(self.root, candidate_id=candidate_id),
            "approver": "forged",
            "authority_ref": "forged/receipt",
            "approved_at": "2026-08-31T12:00:00Z",
            "mode": "local-manual",
        }
        learning.save_candidate(self.root, candidate)
        for index in range(3):
            current = learning.record_usage(
                self.root,
                candidate_id=candidate_id,
                outcome="pass",
                evidence=[f"eval/forged-{index}.json"],
            )
        self.assertEqual(current["state"], "probationary")
        self.assertIn("owner approval", current["history"][-1]["transition_reason"])

    def test_curriculum_queue_ranks_repeated_failure_pattern(self) -> None:
        first = learning.record_experience(
            self.root,
            task_id="deploy-1",
            outcome="fail",
            summary="Deploy failed before readiness check.",
            evidence=["deploy receipt: readiness timeout"],
            failure_pattern="deployment starts before dependency readiness",
            dead_ends=["Increasing a client timeout did not make the dependency ready"],
        )
        learning.record_experience(
            self.root,
            task_id="deploy-2",
            outcome="partial",
            summary="Retry reproduced the same ordering failure.",
            evidence=["replay receipt: same readiness timeout"],
            failure_pattern="deployment starts before dependency readiness",
        )
        queue = learning.curriculum_queue(self.root)
        self.assertEqual(queue[0]["failure_pattern"], "deployment starts before dependency readiness")
        self.assertEqual(queue[0]["recurrence"], 2)
        self.assertIn(first["event_id"], queue[0]["event_ids"])

    def test_curriculum_queue_points_to_existing_candidate_instead_of_duplicate(self) -> None:
        candidate = self._candidate()
        queue = learning.curriculum_queue(self.root)
        matching = [
            item
            for item in queue
            if item.get("failure_pattern") == "stale cache produced phantom results"
        ][0]
        self.assertEqual(matching["covered_by"][0]["candidate_id"], candidate["candidate_id"])
        self.assertIn("do not duplicate", matching["recommended_action"])

    def test_next_actions_reports_missing_reviews(self) -> None:
        candidate = self._candidate()
        result = learning.next_actions(self.root)
        action = [
            item for item in result["candidate_actions"] if item["candidate_id"] == candidate["candidate_id"]
        ][0]
        self.assertEqual(action["action"], "complete-triple-review")
        self.assertIn("missing evidence review", action["reason"])

    def test_revise_reseals_changed_artifact(self) -> None:
        skill_dir = Path(self.temp.name) / "project" / "skills" / "resealed-skill"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            "---\nname: resealed-skill\ndescription: Use this skill when testing resealing.\n---\n# v1\n",
            encoding="utf-8",
        )
        event = self._experience()
        candidate = learning.create_candidate(
            self.root,
            name="resealed-skill",
            source_event_ids=[event["event_id"]],
            failure_pattern="reviewed artifact changes",
            verification="fixture validator passes",
            applicability_boundary="test fixture only",
            skill_path=str(skill_dir),
        )
        old_hash = candidate["artifact_hash"]
        skill_file.write_text(
            "---\nname: resealed-skill\ndescription: Use this skill when testing resealing.\n---\n# v2\n",
            encoding="utf-8",
        )
        revised = learning.revise_candidate(
            self.root,
            candidate_id=candidate["candidate_id"],
            reason="Changed the exact procedure",
        )
        self.assertEqual(revised["version"], 2)
        self.assertNotEqual(revised["artifact_hash"], old_hash)
        learning.submit_review(
            self.root,
            candidate_id=candidate["candidate_id"],
            kind="evidence",
            verdict="pass",
            reviewer="new-evidence-reviewer",
            notes="Reviewed resealed v2.",
            independent=True,
        )

    def test_audit_detects_artifact_changed_after_review(self) -> None:
        skill_dir = Path(self.temp.name) / "project" / "skills" / "audit-bound-skill"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            "---\nname: audit-bound-skill\ndescription: Use this skill when auditing artifact drift.\n---\n# v1\n",
            encoding="utf-8",
        )
        event = self._experience()
        candidate = learning.create_candidate(
            self.root,
            name="audit-bound-skill",
            source_event_ids=[event["event_id"]],
            failure_pattern="artifact drift",
            verification="fixture exists",
            applicability_boundary="test fixture only",
            skill_path=str(skill_dir),
        )
        skill_file.write_text(
            "---\nname: audit-bound-skill\ndescription: Use this skill when auditing artifact drift.\n---\n# changed\n",
            encoding="utf-8",
        )
        result = learning.audit_workspace(self.root)
        self.assertFalse(result["valid"])
        self.assertTrue(any(candidate["candidate_id"] in issue for issue in result["issues"]))

    def test_skill_validation(self) -> None:
        skill_dir = Path(self.temp.name) / "skills" / "valid-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            """---
name: valid-skill
description: Use this skill when a validated workflow must be reused.
---
# Valid skill

**Failure pattern:** repeated wrong command.
**Verified by:** the regression test passed.

## Applicability boundary
Project-local only.

## Procedure
1. Run the validated command.

## What didn't work
- The old command failed.

## Rollback
Archive this revision.
""",
            encoding="utf-8",
        )
        result = learning.validate_skill(skill_dir, harvested=True)
        self.assertTrue(result["valid"], result)

    def test_skill_validation_detects_name_mismatch(self) -> None:
        skill_dir = Path(self.temp.name) / "skills" / "right-name"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            """---
name: wrong-name
description: Use this skill when testing validation.
---
# Wrong
""",
            encoding="utf-8",
        )
        result = learning.validate_skill(skill_dir)
        self.assertFalse(result["valid"])
        self.assertTrue(any("parent directory" in item for item in result["errors"]))

    def test_skill_validation_scans_reference_files_for_secrets(self) -> None:
        skill_dir = Path(self.temp.name) / "skills" / "secret-reference"
        (skill_dir / "references").mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            """---
name: secret-reference
description: Use this skill when testing package-wide secret scanning.
---
# Safe root
""",
            encoding="utf-8",
        )
        (skill_dir / "references" / "unsafe.md").write_text(
            "credential sk-1234567890abcdefghijklmnop",
            encoding="utf-8",
        )
        result = learning.validate_skill(skill_dir)
        self.assertFalse(result["valid"])
        self.assertTrue(any("references/unsafe.md" in item for item in result["errors"]))

    def test_candidate_artifact_outside_project_root_is_rejected(self) -> None:
        event = self._experience()
        with tempfile.TemporaryDirectory() as outside:
            outside_skill = Path(outside) / "outside-skill"
            outside_skill.mkdir()
            (outside_skill / "SKILL.md").write_text(
                "---\nname: outside-skill\ndescription: Use this skill when testing paths.\n---\n",
                encoding="utf-8",
            )
            with self.assertRaises(learning.LearningError):
                learning.create_candidate(
                    self.root,
                    name="outside-skill",
                    source_event_ids=[event["event_id"]],
                    failure_pattern="absolute path leakage",
                    verification="fixture exists",
                    applicability_boundary="test only",
                    skill_path=str(outside_skill),
                )

    def test_init_refuses_to_rewrite_existing_governance(self) -> None:
        with self.assertRaises(learning.LearningError):
            learning.initialize(self.root, {"auto_activate_low_risk": True})

    def test_record_rejects_unknown_source_trust(self) -> None:
        with self.assertRaises(learning.LearningError):
            learning.record_experience(
                self.root,
                task_id="trust-test",
                outcome="fail",
                summary="Unknown trust label.",
                evidence=["failure receipt"],
                source_trust="magical",
            )

    def test_host_approval_rejects_short_hmac_key(self) -> None:
        candidate = self._candidate()
        self._triple_review(candidate["candidate_id"])
        learning.promote_candidate(self.root, candidate_id=candidate["candidate_id"])
        request = learning.approval_request(self.root, candidate_id=candidate["candidate_id"])
        receipt = {
            **request,
            "approver": "owner",
            "authority_ref": "host/receipt",
            "approved_at": "2026-08-31T12:00:00Z",
        }
        short_key = "too-short"
        receipt["signature"] = hmac.new(
            short_key.encode("utf-8"),
            learning.canonical_json(receipt).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        receipt_path = Path(self.temp.name) / "short-key-approval.json"
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        old = os.environ.get("SELF_LEARNING_APPROVAL_KEY")
        os.environ["SELF_LEARNING_APPROVAL_KEY"] = short_key
        try:
            with self.assertRaises(learning.LearningError):
                learning.approve_candidate(
                    self.root,
                    candidate_id=candidate["candidate_id"],
                    receipt_path=receipt_path,
                )
        finally:
            if old is None:
                os.environ.pop("SELF_LEARNING_APPROVAL_KEY", None)
            else:
                os.environ["SELF_LEARNING_APPROVAL_KEY"] = old


if __name__ == "__main__":
    unittest.main()
