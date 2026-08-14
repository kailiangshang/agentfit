import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
WRAPPER = REPO_ROOT / "runtime" / "agentteams" / "install-prebuilt.sh"


class InstallPrebuiltTest(unittest.TestCase):
    def setUp(self):
        ignored_root = REPO_ROOT / ".local-demo" / "agentteams" / "tests"
        ignored_root.mkdir(parents=True, exist_ok=True)
        self.tempdir = tempfile.TemporaryDirectory(dir=ignored_root)
        self.env_file = Path(self.tempdir.name) / "private.env"

    def tearDown(self):
        self.tempdir.cleanup()

    def write_env(self, *, mode=0o600, **overrides):
        values = {
            "AGENTTEAMS_LLM_API_KEY": "fixture-secret-key",
            "AGENTTEAMS_OPENAI_BASE_URL": "https://litellm.example/v1",
            "AGENTTEAMS_DEFAULT_MODEL": "fixture-model",
        }
        values.update(overrides)
        self.env_file.write_text(
            "".join(f"{name}={value!r}\n" for name, value in values.items()),
            encoding="utf-8",
        )
        self.env_file.chmod(mode)

    def run_wrapper(self, *args, extra_env=None):
        environment = os.environ.copy()
        for name in tuple(environment):
            if name.startswith("AGENTTEAMS_INSTALL_") or name in {
                "AGENTTEAMS_VERSION",
                "AGENTTEAMS_LLM_API_KEY",
                "AGENTTEAMS_OPENAI_BASE_URL",
                "AGENTTEAMS_DEFAULT_MODEL",
            }:
                environment.pop(name)
        if extra_env:
            environment.update(extra_env)
        return subprocess.run(
            [str(WRAPPER), "--env-file", str(self.env_file), *args],
            cwd=REPO_ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_check_accepts_private_config_without_disclosing_values(self):
        self.write_env()

        result = self.run_wrapper("--check")

        self.assertEqual(0, result.returncode, result.stderr)
        combined = result.stdout + result.stderr
        self.assertIn("version=v1.1.2", combined)
        self.assertIn("image_source=official-prebuilt", combined)
        self.assertIn("data_volume=agentfit-agentteams-data", combined)
        self.assertIn("dashboard=disabled", combined)
        self.assertIn("upgrade_mode=keep-all", combined)
        self.assertIn("api_key=configured", combined)
        self.assertNotIn("fixture-secret-key", combined)
        self.assertNotIn("https://litellm.example/v1", combined)
        self.assertNotIn("fixture-model", combined)

    def test_missing_private_file_is_rejected(self):
        result = self.run_wrapper("--check")

        self.assertNotEqual(0, result.returncode)
        self.assertIn("private env file does not exist", result.stderr)

    def test_group_readable_private_file_is_rejected(self):
        self.write_env(mode=0o640)

        result = self.run_wrapper("--check")

        self.assertNotEqual(0, result.returncode)
        self.assertIn("mode 0600", result.stderr)

    def test_missing_required_variable_is_rejected(self):
        self.write_env(AGENTTEAMS_DEFAULT_MODEL="")

        result = self.run_wrapper("--check")

        self.assertNotEqual(0, result.returncode)
        self.assertIn("AGENTTEAMS_DEFAULT_MODEL is required", result.stderr)

    def test_placeholder_value_is_rejected(self):
        self.write_env(AGENTTEAMS_LLM_API_KEY="<litellm-api-key>")

        result = self.run_wrapper("--check")

        self.assertNotEqual(0, result.returncode)
        self.assertIn("AGENTTEAMS_LLM_API_KEY still contains a placeholder", result.stderr)

    def test_external_image_override_is_rejected(self):
        self.write_env()

        result = self.run_wrapper(
            "--check",
            extra_env={"AGENTTEAMS_INSTALL_MANAGER_IMAGE": "local/manager:test"},
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("image overrides are forbidden", result.stderr)

    def test_non_pinned_version_is_rejected(self):
        self.write_env()

        result = self.run_wrapper(
            "--check", extra_env={"AGENTTEAMS_VERSION": "v1.2.0-beta.1"}
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("only v1.1.2 is allowed", result.stderr)


if __name__ == "__main__":
    unittest.main()
