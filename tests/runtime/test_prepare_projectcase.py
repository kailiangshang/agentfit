import json
import hashlib
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

from runtime.agentteams.m1.prepare_projectcase import select_samples


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "runtime" / "agentteams" / "m1" / "prepare_projectcase.py"


class PrepareProjectCaseTest(unittest.TestCase):
    def test_builds_sanitized_batch_and_request_without_evaluation_answers(self):
        tasks = [
            {
                "id": task_id,
                "description": {"purpose": None},
                "user_scenario": {
                    "instructions": {
                        "task_instructions": hidden,
                        "domain": "retail",
                        "reason_for_call": reason,
                        "known_info": "known",
                        "unknown_info": None,
                    }
                },
                "initial_state": None,
                "evaluation_criteria": [f"SECRET-ANSWER-{task_id}"],
            }
            for task_id, hidden, reason in (
                ("0", "hidden-0", "exchange"),
                ("2", ".", "return"),
                ("13", "hidden preference", "cancel"),
            )
        ]

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            tasks_file = root / "tasks.json"
            policy_file = root / "policy.md"
            manifest_file = root / "manifest.yaml"
            output_dir = root / "output"
            tasks_file.write_text(json.dumps(tasks), encoding="utf-8")
            policy_file.write_text("# Official policy\n", encoding="utf-8")
            manifest_file.write_text("kind: Team\nmetadata:\n  name: fixture\n", encoding="utf-8")

            result = subprocess.run(
                [
                    "python3",
                    str(SCRIPT),
                    "--tasks-file",
                    str(tasks_file),
                    "--policy-file",
                    str(policy_file),
                    "--task-id",
                    "0",
                    "--task-id",
                    "2",
                    "--task-id",
                    "13",
                    "--run-id",
                    "retail-r2-batch-0-2-13",
                    "--manifest-file",
                    str(manifest_file),
                    "--source-version",
                    "tau2-bench/v1.0.1",
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(0, result.returncode, result.stderr)
            samples_path = output_dir / "samples.json"
            request_path = output_dir / "request.md"
            provenance_path = output_dir / "provenance.json"
            samples_text = samples_path.read_text(encoding="utf-8")
            request_text = request_path.read_text(encoding="utf-8")
            samples = json.loads(samples_text)
            provenance = json.loads(provenance_path.read_text(encoding="utf-8"))

            self.assertEqual(["0", "2", "13"], samples["task_ids"])
            self.assertEqual(3, len(samples["samples"]))
            self.assertEqual("tau2-bench/v1.0.1", samples["source_version"])
            self.assertNotIn("evaluation_criteria", samples_text)
            self.assertNotIn("SECRET-ANSWER", samples_text + request_text)
            self.assertTrue(all(
                sample["exposure_policy"]["future_candidate_direct_input"] == []
                for sample in samples["samples"]
            ))
            self.assertTrue(all(
                "user_scenario.instructions" in sample["exposure_policy"]["user_simulator_only"]
                for sample in samples["samples"]
            ))
            self.assertIn("all four SampleSetManifest contracts", request_text)
            self.assertIn("before any Human freeze request", request_text)
            self.assertIn("not_instantiated", request_text)
            terminal_prefix = provenance["terminal_prefix"]
            self.assertRegex(
                terminal_prefix,
                re.compile(r"^AGENTFIT-retail-r2-batch-0-2-13-[0-9a-f]{32}$"),
            )
            self.assertIn(terminal_prefix, request_text)
            self.assertEqual(
                hashlib.sha256(tasks_file.read_bytes()).hexdigest(),
                samples["source_tasks_sha256"],
            )
            self.assertEqual(
                hashlib.sha256(manifest_file.read_bytes()).hexdigest(),
                provenance["files"]["agentteams_manifest"]["sha256"],
            )
            self.assertEqual("pre_run", provenance["capture_timing"])
            self.assertEqual(0o600, samples_path.stat().st_mode & 0o777)
            self.assertEqual(0o600, request_path.stat().st_mode & 0o777)
            self.assertEqual(0o600, provenance_path.stat().st_mode & 0o777)

    def test_rejects_source_schema_drift_and_nested_answer_fields(self):
        safe = {
            "id": "0",
            "description": {"purpose": "exchange"},
            "user_scenario": {
                "instructions": {
                    "task_instructions": "ask for an exchange",
                    "domain": "retail",
                    "reason_for_call": "exchange",
                    "known_info": "known",
                    "unknown_info": None,
                },
                "persona": None,
            },
            "initial_state": None,
            "evaluation_criteria": {"actions": []},
        }
        with self.subTest("unknown top-level field"):
            drifted = {**safe, "expected_answer": "must not pass"}
            with self.assertRaisesRegex(ValueError, "source schema drift"):
                select_samples([drifted], ["0"], "tau2-bench/v1.0.1")

        with self.subTest("nested answer field"):
            drifted = json.loads(json.dumps(safe))
            drifted["description"]["expected_answer"] = "must not pass"
            with self.assertRaisesRegex(ValueError, "source schema drift"):
                select_samples([drifted], ["0"], "tau2-bench/v1.0.1")

        with self.subTest("unsupported source version"):
            with self.assertRaisesRegex(ValueError, "unsupported source version"):
                select_samples([safe], ["0"], "tau2-bench/v9.9.9")


if __name__ == "__main__":
    unittest.main()
