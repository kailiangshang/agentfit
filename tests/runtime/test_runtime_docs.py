import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_GUIDE = REPO_ROOT / "runtime" / "agentteams" / "README.md"
SOLUTION = REPO_ROOT / "docs" / "agentfit-solution.md"
HOME_DEMO = REPO_ROOT / "docs" / "guides" / "home-demo-runbook.md"
DOCS_INDEX = REPO_ROOT / "docs" / "README.md"


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
            "v1.2.0-beta.1",
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
            "CLI 报告 `dev`",
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

    def test_runtime_guide_supports_direct_deepseek_without_a_litellm_server(self):
        text = RUNTIME_GUIDE.read_text(encoding="utf-8")

        required = (
            "不需要部署 LiteLLM Server",
            "https://api.deepseek.com/v1",
            "deepseek-chat",
            "runtime/agentteams/m1/render_model_manifest.py",
            ".local-demo/agentteams/m1/agentfit-retail-m1.deepseek.yaml",
            "--reuse-existing-human",
            "AGENTFIT_TEAM_MANIFEST",
            '--file "$AGENTFIT_TEAM_MANIFEST"',
            '--manifest-file "$AGENTFIT_TEAM_MANIFEST"',
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_runtime_guide_does_not_retroactively_bind_post_run_package(self):
        text = RUNTIME_GUIDE.read_text(encoding="utf-8")

        self.assertIn("初始实例化快照", text)
        self.assertIn("不能绑定到 Round 1/2", text)
        self.assertIn("新一轮运行前", text)

    def test_home_guide_explains_deepseek_for_agentteams_and_tau_benchmark(self):
        text = HOME_DEMO.read_text(encoding="utf-8")

        required = (
            "只有 Docker + DeepSeek API",
            "DEEPSEEK_API_KEY",
            "deepseek/deepseek-chat",
            "LiteLLM Python 客户端",
            "不需要 LiteLLM Server",
            "render_model_manifest.py",
            "不得越过 Human freeze",
            "AGENTFIT_TEAM_MANIFEST",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_home_guide_prioritizes_a_final_package_replay_before_candidate_work(self):
        text = HOME_DEMO.read_text(encoding="utf-8")

        required = (
            "回家后的第一目标",
            "最终加固包重放",
            "run_bound_send_metadata",
            "structured_matrix_mentions",
            "先不启动 Candidate",
            "办公室 `.local-demo`",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_canonical_solution_records_m0_ready_and_m1_in_progress(self):
        text = SOLUTION.read_text(encoding="utf-8")

        self.assertIn("M0：`READY`", text)
        self.assertIn("M1：`IN_PROGRESS`", text)
        self.assertIn("M2–M4：`NOT_STARTED`", text)
        for v4_term in (
            "强层级映射纪律",
            "场景内持续学习",
            "RegressionPool",
            "实体污染与语义复用",
            "四层资产",
        ):
            with self.subTest(v4_term=v4_term):
                self.assertIn(v4_term, text)
        self.assertIn("Team `Active`、1 个 Leader 和 4 个 Worker", text)
        self.assertIn("CLI 版本字段仍报告 `dev`", text)
        self.assertIn("官方预构建镜像", text)
        self.assertIn("不执行镜像编译", text)
        self.assertIn("两轮 ProjectCase preparation", text)
        self.assertIn("task 0、2、13", text)
        self.assertIn("尚未运行 Candidate", text)
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
        self.assertIn("两轮 ProjectCase preparation", text)
        self.assertIn("task 0、2、13", text)
        self.assertIn("尚未运行 Candidate", text)

    def test_docs_index_records_current_projectcase_preparation_boundary(self):
        text = DOCS_INDEX.read_text(encoding="utf-8")

        self.assertIn("M0 已完成并为 `READY`", text)
        self.assertIn("M1 仍为 `IN_PROGRESS`", text)
        self.assertIn("两轮 ProjectCase preparation", text)
        self.assertIn("task 0、2、13", text)
        self.assertIn("尚未运行 Candidate", text)
        self.assertIn(
            "research/home-demo/retail-m1/dossier/15-agentteams-m1-multiscenario-run.md",
            text,
        )


if __name__ == "__main__":
    unittest.main()
