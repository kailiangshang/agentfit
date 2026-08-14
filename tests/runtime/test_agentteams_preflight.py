import json
import tempfile
import unittest
from pathlib import Path

from runtime.agentteams import preflight as preflight_module
from runtime.agentteams.preflight import (
    CommandResult,
    HostResources,
    OFFICIAL_IMAGES,
    _detect_memory_bytes,
    run_preflight,
)


class FakeRunner:
    def __init__(self, results):
        self.results = results
        self.calls = []

    def run(self, argv, timeout=30):
        key = tuple(argv)
        self.calls.append(key)
        return self.results.get(key, CommandResult(127, "", "unexpected command"))


class AgentTeamsPreflightTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name) / "AgentTeams"
        self.repo.mkdir()
        (self.repo / ".git").mkdir()
        self.version = "v1.1.2"
        self.resources = HostResources(
            cpu_count=8,
            memory_bytes=16 * 1024**3,
            disk_free_bytes=100 * 1024**3,
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def healthy_results(self):
        results = {
            ("docker", "--version"): CommandResult(0, "Docker version 29.2.1", ""),
            ("docker", "info", "--format", "{{.ServerVersion}}"): CommandResult(
                0, "29.2.1", ""
            ),
            ("docker", "compose", "version"): CommandResult(
                0, "Docker Compose version v5.0.2", ""
            ),
            (
                "git",
                "-C",
                str(self.repo.resolve()),
                "rev-parse",
                "--verify",
                f"refs/tags/{self.version}",
            ): CommandResult(0, "deadbeef", ""),
        }
        for image in OFFICIAL_IMAGES.values():
            results[("docker", "manifest", "inspect", f"{image}:{self.version}")] = (
                CommandResult(0, "{}", "")
            )
        return results

    def test_healthy_environment_is_ready(self):
        report = run_preflight(
            repo=self.repo,
            version=self.version,
            runner=FakeRunner(self.healthy_results()),
            resources=self.resources,
            environ={
                "AGENTTEAMS_LLM_API_KEY": "super-secret-key",
                "AGENTTEAMS_OPENAI_BASE_URL": "https://litellm.example/v1",
                "AGENTTEAMS_DEFAULT_MODEL": "model-a",
            },
        )

        self.assertTrue(report.ready)
        self.assertTrue(all(check.ok for check in report.checks))

        rendered = json.dumps(report.to_dict(), ensure_ascii=False)
        self.assertNotIn("super-secret-key", rendered)
        self.assertNotIn("https://litellm.example/v1", rendered)
        self.assertNotIn("model-a", rendered)
        self.assertIn('"detail": "configured"', rendered)

    def test_missing_docker_daemon_fails_readiness(self):
        results = self.healthy_results()
        results[("docker", "info", "--format", "{{.ServerVersion}}")] = CommandResult(
            1, "", "Cannot connect to the Docker daemon"
        )

        report = run_preflight(
            repo=self.repo,
            version=self.version,
            runner=FakeRunner(results),
            resources=self.resources,
            environ=self.configured_environment(),
        )

        check = report.by_name("docker.daemon")
        self.assertFalse(report.ready)
        self.assertFalse(check.ok)
        self.assertIn("unavailable", check.detail)

    def test_missing_pinned_tag_fails_readiness(self):
        results = self.healthy_results()
        tag_command = (
            "git",
            "-C",
            str(self.repo.resolve()),
            "rev-parse",
            "--verify",
            f"refs/tags/{self.version}",
        )
        results[tag_command] = CommandResult(128, "", "unknown revision")

        report = run_preflight(
            repo=self.repo,
            version=self.version,
            runner=FakeRunner(results),
            resources=self.resources,
            environ=self.configured_environment(),
        )

        self.assertFalse(report.by_name("agentteams.tag").ok)
        self.assertEqual("missing v1.1.2", report.by_name("agentteams.tag").detail)

    def test_insufficient_resources_report_each_failed_gate(self):
        report = run_preflight(
            repo=self.repo,
            version=self.version,
            runner=FakeRunner(self.healthy_results()),
            resources=HostResources(
                cpu_count=2,
                memory_bytes=4 * 1024**3,
                disk_free_bytes=10 * 1024**3,
            ),
            environ=self.configured_environment(),
        )

        self.assertFalse(report.ready)
        self.assertFalse(report.by_name("host.cpu").ok)
        self.assertFalse(report.by_name("host.memory").ok)
        self.assertFalse(report.by_name("host.disk").ok)

    def test_missing_private_model_configuration_is_explicit(self):
        report = run_preflight(
            repo=self.repo,
            version=self.version,
            runner=FakeRunner(self.healthy_results()),
            resources=self.resources,
            environ={},
        )

        self.assertFalse(report.ready)
        self.assertEqual("missing", report.by_name("config.api_key").detail)
        self.assertEqual("missing", report.by_name("config.base_url").detail)
        self.assertEqual("missing", report.by_name("config.default_model").detail)

    @staticmethod
    def configured_environment():
        return {
            "AGENTTEAMS_LLM_API_KEY": "key",
            "AGENTTEAMS_OPENAI_BASE_URL": "https://example.invalid/v1",
            "AGENTTEAMS_DEFAULT_MODEL": "model",
        }


class MemoryDetectionTest(unittest.TestCase):
    def test_proc_meminfo_is_preferred_when_present(self):
        with tempfile.TemporaryDirectory() as td:
            meminfo = Path(td) / "meminfo"
            meminfo.write_text("MemTotal:       16384000 kB\n", encoding="utf-8")
            self.assertEqual(16384000 * 1024, _detect_memory_bytes(meminfo))

    def test_darwin_sysctl_is_used_when_meminfo_is_missing(self):
        original_platform = preflight_module.sys.platform
        original_run = preflight_module.SubprocessRunner.run
        try:
            preflight_module.sys.platform = "darwin"
            preflight_module.SubprocessRunner.run = lambda self, argv, timeout=30: CommandResult(
                0, str(8 * 1024**3), ""
            )
            self.assertEqual(8 * 1024**3, _detect_memory_bytes(Path("/nonexistent-meminfo")))
        finally:
            preflight_module.sys.platform = original_platform
            preflight_module.SubprocessRunner.run = original_run

    def test_unknown_platform_reports_zero(self):
        original_platform = preflight_module.sys.platform
        try:
            preflight_module.sys.platform = "linux"
            self.assertEqual(0, _detect_memory_bytes(Path("/nonexistent-meminfo")))
        finally:
            preflight_module.sys.platform = original_platform


if __name__ == "__main__":
    unittest.main()
