import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
WRAPPER = REPO_ROOT / "runtime" / "agentteams" / "apply-manifest.sh"
MANIFEST = REPO_ROOT / "runtime" / "agentteams" / "m1" / "agentfit-retail-m1.yaml"


class ApplyManifestTest(unittest.TestCase):
    def setUp(self):
        ignored_root = REPO_ROOT / ".local-demo" / "agentteams" / "tests"
        ignored_root.mkdir(parents=True, exist_ok=True)
        self.tempdir = tempfile.TemporaryDirectory(dir=ignored_root)
        self.external_cwd = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.log_file = self.root / "apply.log"
        self.fake_bin = self.root / "bin"
        self.fake_bin.mkdir()
        fake_docker = self.fake_bin / "docker"
        fake_docker.write_text(
            "#!/bin/sh\n"
            "if [ \"$1\" = ps ]; then\n"
            "  printf '%s\\n' agentteams-controller\n"
            "elif [ \"$1\" = exec ] && [ \"$3\" = sh ]; then\n"
            "  printf '%s\\n' /usr/local/bin/hiclaw\n"
            "elif [ \"$1\" = cp ]; then\n"
            "  exit 0\n"
            "elif [ \"$1\" = exec ] && [ \"$4\" = apply ]; then\n"
            "  printf '%s\\n' 'Initial password: fixture-human-password'\n"
            "else\n"
            "  printf '%s\\n' \"unexpected docker args: $*\" >&2\n"
            "  exit 64\n"
            "fi\n",
            encoding="utf-8",
        )
        fake_docker.chmod(0o700)

    def tearDown(self):
        self.external_cwd.cleanup()
        self.tempdir.cleanup()

    def test_detects_hiclaw_and_keeps_apply_output_private(self):
        environment = os.environ.copy()
        environment["PATH"] = f"{self.fake_bin}:{environment['PATH']}"

        result = subprocess.run(
            [
                "/bin/bash",
                str(WRAPPER),
                "--file",
                str(MANIFEST),
                "--log-file",
                str(self.log_file),
            ],
            cwd=REPO_ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(0, result.returncode, result.stderr)
        combined = result.stdout + result.stderr
        self.assertIn("cli=hiclaw", combined)
        self.assertIn("apply=accepted", combined)
        self.assertNotIn("fixture-human-password", combined)
        self.assertIn(
            "fixture-human-password", self.log_file.read_text(encoding="utf-8")
        )
        self.assertEqual(0o600, self.log_file.stat().st_mode & 0o777)
        ignored = subprocess.run(
            ["git", "check-ignore", "-q", str(self.log_file)],
            cwd=REPO_ROOT,
            check=False,
        )
        self.assertEqual(0, ignored.returncode)

    def test_relative_log_is_anchored_to_repository_root(self):
        environment = os.environ.copy()
        environment["PATH"] = f"{self.fake_bin}:{environment['PATH']}"
        relative_log = self.log_file.relative_to(REPO_ROOT)

        result = subprocess.run(
            [
                "/bin/bash",
                str(WRAPPER),
                "--file",
                str(MANIFEST),
                "--log-file",
                str(relative_log),
            ],
            cwd=self.external_cwd.name,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue(self.log_file.is_file())
        self.assertEqual(0o600, self.log_file.stat().st_mode & 0o777)
        self.assertFalse((Path(self.external_cwd.name) / relative_log).exists())


if __name__ == "__main__":
    unittest.main()
