import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_GUIDE = REPO_ROOT / "runtime" / "agentteams" / "README.md"
SOLUTION = REPO_ROOT / "docs" / "agentfit-solution.md"
HOME_DEMO = REPO_ROOT / "docs" / "guides" / "home-demo-runbook.md"


class RuntimeDocumentationContractTest(unittest.TestCase):
    def test_runtime_guide_is_the_single_m0_m1_entrypoint(self):
        text = RUNTIME_GUIDE.read_text(encoding="utf-8")

        self.assertIn(
            "本目录是 AgentFit 在 AgentTeams 上启动 M0/M1 的唯一运行入口",
            text,
        )
        required = (
            "AgentTeams 官方预构建镜像",
            "AgentFit 源码",
            "v1.1.2",
            "runtime/agentteams/preflight.py",
            "runtime/agentteams/install-prebuilt.sh --check",
            "runtime/agentteams/install-prebuilt.sh",
            ".local-demo/agentteams/private.env",
            ".local-demo/agentteams/platform",
            "M0",
            "M1",
            "READY",
            "IN_PROGRESS",
            "tag 与 digest",
            "CLI 仍报告 `dev`",
            "私密安装日志",
            "runtime/agentteams/m1/agentfit-retail-m1.yaml",
            "runtime/agentteams/apply-manifest.sh",
            "agt",
            "hiclaw",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

        self.assertNotIn("docker build", text.lower())
        self.assertNotRegex(text, re.compile(r"(?:sk|key)-[A-Za-z0-9_-]{12,}"))

    def test_canonical_solution_records_m0_ready_and_m1_in_progress(self):
        text = SOLUTION.read_text(encoding="utf-8")

        self.assertIn("M0：`READY`", text)
        self.assertIn("M1：`IN_PROGRESS`", text)
        self.assertIn("M2–M4：`NOT_STARTED`", text)
        self.assertIn("Team `Active`、1 个 Leader 和 4 个 Worker", text)
        self.assertIn("CLI 版本字段仍报告 `dev`", text)
        self.assertIn("官方预构建镜像", text)
        self.assertIn("不执行镜像编译", text)
        self.assertNotIn("在此之前不得写成已批准测试项目", text)

    def test_home_demo_defers_to_runtime_guide_and_preserves_evidence_boundary(self):
        text = HOME_DEMO.read_text(encoding="utf-8")

        self.assertIn("../../runtime/agentteams/README.md", text)
        self.assertIn("M0 已完成并为 `READY`", text)
        self.assertIn(".local-demo/agentteams/evidence", text)
        self.assertIn("M1 已进入 `IN_PROGRESS`", text)
        self.assertIn("runtime/agentteams/m1/agentfit-retail-m1.yaml", text)
        self.assertIn("preflight-only", text)
        self.assertIn("不是 AgentFit Candidate", text)


if __name__ == "__main__":
    unittest.main()
