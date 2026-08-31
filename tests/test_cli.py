from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "self-learning"
    / "scripts"
    / "learning_cycle.py"
)


class LearningCycleCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name) / "project"
        self.project.mkdir()
        self.root = self.project / ".agent-learning"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_cli(self, *args: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=self.project,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != expected:
            self.fail(
                f"expected return code {expected}, got {result.returncode}\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )
        return result

    def test_full_cli_auto_activation_lifecycle(self) -> None:
        overrides = json.dumps(
            {
                "require_owner_approval_for_activation": False,
                "auto_activate_low_risk": True,
            }
        )
        self.run_cli("init", "--root", str(self.root), "--config-json", overrides)
        record = json.loads(
            self.run_cli(
                "record",
                "--root",
                str(self.root),
                "--task-id",
                "cli-task-1",
                "--outcome",
                "pass",
                "--summary",
                "CLI fixture passed",
                "--evidence",
                "fixture/receipt.json",
                "--failure-pattern",
                "fixture executes in the wrong order",
                "--dead-end",
                "retrying without reordering reproduced the failure",
            ).stdout
        )
        candidate = json.loads(
            self.run_cli(
                "candidate",
                "--root",
                str(self.root),
                "--name",
                "fix-cli-order",
                "--source-event",
                record["event_id"],
                "--failure-pattern",
                "fixture executes in the wrong order",
                "--verification",
                "fixture passed after ordering correction",
                "--boundary",
                "CLI test fixture only",
                "--risk",
                "low",
                "--scope",
                "project",
            ).stdout
        )
        candidate_id = candidate["candidate_id"]
        for kind, reviewer in (
            ("evidence", "cli-evidence-reviewer"),
            ("evaluation", "cli-evaluation-reviewer"),
            ("safety", "cli-safety-reviewer"),
        ):
            self.run_cli(
                "review",
                "--root",
                str(self.root),
                "--candidate",
                candidate_id,
                "--kind",
                kind,
                "--verdict",
                "pass",
                "--reviewer",
                reviewer,
                "--notes",
                f"{kind} CLI review passed",
                "--independent",
            )
        self.run_cli("promote", "--root", str(self.root), "--candidate", candidate_id)
        current = None
        for index in range(3):
            current = json.loads(
                self.run_cli(
                    "usage",
                    "--root",
                    str(self.root),
                    "--candidate",
                    candidate_id,
                    "--outcome",
                    "pass",
                    "--evidence",
                    f"evals/cli-{index}.json",
                ).stdout
            )
        assert current is not None
        self.assertEqual(current["state"], "active")
        audit = json.loads(self.run_cli("audit", "--root", str(self.root)).stdout)
        self.assertTrue(audit["valid"])

    def test_cli_rejects_secret_and_returns_error_code_two(self) -> None:
        self.run_cli("init", "--root", str(self.root))
        result = self.run_cli(
            "record",
            "--root",
            str(self.root),
            "--task-id",
            "secret-cli",
            "--outcome",
            "pass",
            "--summary",
            "credential sk-1234567890abcdefghijklmnop",
            "--evidence",
            "fixture passed",
            expected=2,
        )
        self.assertIn("possible secret", result.stderr.lower())

    def test_cli_next_and_queue_are_machine_readable(self) -> None:
        self.run_cli("init", "--root", str(self.root))
        self.run_cli(
            "record",
            "--root",
            str(self.root),
            "--task-id",
            "queue-cli",
            "--outcome",
            "fail",
            "--summary",
            "Queue fixture failed",
            "--evidence",
            "fixture/failure.json",
            "--failure-pattern",
            "queue fixture lacks a prerequisite",
        )
        queue = json.loads(self.run_cli("queue", "--root", str(self.root)).stdout)
        next_result = json.loads(self.run_cli("next", "--root", str(self.root)).stdout)
        self.assertEqual(queue[0]["failure_pattern"], "queue fixture lacks a prerequisite")
        self.assertIn("curriculum_opportunities", next_result)


if __name__ == "__main__":
    unittest.main()
