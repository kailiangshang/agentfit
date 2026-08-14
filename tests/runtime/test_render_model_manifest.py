import hashlib
import json
import subprocess
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "runtime" / "agentteams" / "m1" / "render_model_manifest.py"
CANONICAL = REPO_ROOT / "runtime" / "agentteams" / "m1" / "agentfit-retail-m1.yaml"


class RenderModelManifestTest(unittest.TestCase):
    def setUp(self):
        ignored_root = REPO_ROOT / ".local-demo" / "agentteams" / "tests"
        ignored_root.mkdir(parents=True, exist_ok=True)
        self.tempdir = tempfile.TemporaryDirectory(dir=ignored_root)
        self.root = Path(self.tempdir.name)
        self.output = self.root / "agentfit-retail-m1.deepseek.yaml"

    def tearDown(self):
        self.tempdir.cleanup()

    def run_renderer(self, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "python3",
                str(SCRIPT),
                "--input-file",
                str(CANONICAL),
                "--output-file",
                str(self.output),
                "--model",
                "deepseek-chat",
                *extra,
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_renders_all_team_models_without_mutating_canonical_contract(self):
        source_before = CANONICAL.read_bytes()
        original = list(yaml.safe_load_all(source_before.decode("utf-8")))

        result = self.run_renderer()

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(source_before, CANONICAL.read_bytes())
        rendered = list(yaml.safe_load_all(self.output.read_text(encoding="utf-8")))
        original_team = next(item for item in original if item["kind"] == "Team")
        rendered_team = next(item for item in rendered if item["kind"] == "Team")
        self.assertEqual("deepseek-chat", rendered_team["spec"]["leader"]["model"])
        self.assertEqual(
            {"deepseek-chat"},
            {worker["model"] for worker in rendered_team["spec"]["workers"]},
        )

        expected_team = deepcopy(original_team)
        expected_team["spec"]["leader"]["model"] = "deepseek-chat"
        for worker in expected_team["spec"]["workers"]:
            worker["model"] = "deepseek-chat"
        self.assertEqual(expected_team, rendered_team)
        self.assertEqual(
            [item for item in original if item["kind"] != "Team"],
            [item for item in rendered if item["kind"] != "Team"],
        )
        self.assertEqual(0o600, self.output.stat().st_mode & 0o777)

    def test_writes_private_hash_provenance_without_credentials(self):
        result = self.run_renderer()

        self.assertEqual(0, result.returncode, result.stderr)
        provenance_path = self.output.with_suffix(self.output.suffix + ".provenance.json")
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
        self.assertEqual("agentfit.model-manifest-render/v1", provenance["schema_version"])
        self.assertEqual("deepseek-chat", provenance["model"])
        self.assertEqual(
            hashlib.sha256(CANONICAL.read_bytes()).hexdigest(),
            provenance["source_manifest_sha256"],
        )
        self.assertEqual(
            hashlib.sha256(self.output.read_bytes()).hexdigest(),
            provenance["rendered_manifest_sha256"],
        )
        self.assertEqual(5, provenance["changed_member_count"])
        self.assertNotRegex(
            provenance_path.read_text(encoding="utf-8"),
            r"(?i)(api[_-]?key|password|bearer)\s*[:=]",
        )
        self.assertEqual(0o600, provenance_path.stat().st_mode & 0o777)

    def test_rejects_output_outside_ignored_local_demo(self):
        with tempfile.TemporaryDirectory() as outside:
            output = Path(outside) / "deepseek.yaml"
            result = subprocess.run(
                [
                    "python3",
                    str(SCRIPT),
                    "--input-file",
                    str(CANONICAL),
                    "--output-file",
                    str(output),
                    "--model",
                    "deepseek-chat",
                ],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertNotEqual(0, result.returncode)
        self.assertIn(".local-demo", result.stderr)

    def test_rejects_placeholder_or_malformed_model_id(self):
        for model in ("<deepseek-model>", "deepseek chat", ""):
            with self.subTest(model=model):
                result = subprocess.run(
                    [
                        "python3",
                        str(SCRIPT),
                        "--input-file",
                        str(CANONICAL),
                        "--output-file",
                        str(self.output),
                        "--model",
                        model,
                    ],
                    cwd=REPO_ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertNotEqual(0, result.returncode)
                self.assertIn("model", result.stderr.lower())

    def test_rejects_an_input_manifest_containing_a_credential_assignment(self):
        unsafe = self.root / "unsafe-input.yaml"
        unsafe.write_text(
            CANONICAL.read_text(encoding="utf-8").replace(
                "description: AgentFit M1 meta-team",
                "api_key: do-not-accept-this-secret-value\n  description: AgentFit M1 meta-team",
                1,
            ),
            encoding="utf-8",
        )
        result = subprocess.run(
            [
                "python3",
                str(SCRIPT),
                "--input-file",
                str(unsafe),
                "--output-file",
                str(self.output),
                "--model",
                "deepseek-chat",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("credential", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
