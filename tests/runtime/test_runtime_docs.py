import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_GUIDE = REPO_ROOT / "runtime" / "agentteams" / "README.md"
SOLUTION = REPO_ROOT / "docs" / "agentfit-solution.md"
HOME_DEMO = REPO_ROOT / "docs" / "guides" / "home-demo-runbook.md"


class RuntimeDocumentationContractTest(unittest.TestCase):
    def test_runtime_guide_is_the_single_m0_entrypoint(self):
        text = RUNTIME_GUIDE.read_text(encoding="utf-8")

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
            "IN_PROGRESS",
            "NOT_STARTED",
            "agt",
            "hiclaw",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

        self.assertNotIn("docker build", text.lower())
        self.assertNotRegex(text, re.compile(r"(?:sk|key)-[A-Za-z0-9_-]{12,}"))

    def test_canonical_solution_records_authorized_but_not_completed_state(self):
        text = SOLUTION.read_text(encoding="utf-8")

        self.assertIn("M0：`IN_PROGRESS`", text)
        self.assertIn("M1–M4：`NOT_STARTED`", text)
        self.assertIn("官方预构建镜像", text)
        self.assertIn("不执行镜像编译", text)
        self.assertNotIn("在此之前不得写成已批准测试项目", text)

    def test_home_demo_defers_to_runtime_guide_and_preserves_evidence_boundary(self):
        text = HOME_DEMO.read_text(encoding="utf-8")

        self.assertIn("../../runtime/agentteams/README.md", text)
        self.assertIn("M0 已获准启动，但仍为 `IN_PROGRESS`", text)
        self.assertIn("preflight-only", text)
        self.assertIn("不是 AgentFit Candidate", text)


if __name__ == "__main__":
    unittest.main()
