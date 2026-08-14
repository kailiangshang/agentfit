import json
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
REPORT = (
    REPO_ROOT
    / "docs"
    / "research"
    / "home-demo"
    / "retail-m1"
    / "dossier"
    / "15-agentteams-m1-multiscenario-run.md"
)
COMPARISON = (
    REPO_ROOT
    / "docs"
    / "research"
    / "home-demo"
    / "retail-m1"
    / "batch-runs"
    / "agentteams-m1-round-comparison.json"
)
RUNTIME_README = REPO_ROOT / "runtime" / "agentteams" / "README.md"


class M1MultiscenarioReportTest(unittest.TestCase):
    def test_report_covers_package_trace_paths_cost_and_boundaries(self):
        text = REPORT.read_text(encoding="utf-8")
        for phrase in (
            "可部署 AgentFit 包",
            "Trace 与迭代对照",
            "求解路径",
            "适配路径",
            "成本与时延",
            "失败分支",
            "M1 IN_PROGRESS",
            "没有 Candidate",
            "answer payload",
            "未保存 pre-run package provenance",
            "structured_matrix_mentions_from_raw",
            "legacy_task_meta_and_matrix_assignment",
        ):
            self.assertIn(phrase, text)
        self.assertNotRegex(
            text,
            re.compile(r"(?i)(?:password|bearer|api[_-]?key)\s*[:=]\s*\S{8,}"),
        )

    def test_comparison_preserves_observed_metrics_and_evidence_scope(self):
        value = json.loads(COMPARISON.read_text(encoding="utf-8"))
        self.assertEqual("M1_PROJECTCASE_PREPARATION", value["evidence_scope"])
        self.assertEqual(2, len(value["rounds"]))
        round_1, round_2 = value["rounds"]
        self.assertEqual(140, round_1["message_event_count"])
        self.assertEqual(155, round_2["message_event_count"])
        self.assertEqual(0, round_2["answer_payload_match_count"])
        self.assertIn("answer_match_scope", round_2)
        self.assertIn("terminal_prefix_binding", round_2)
        self.assertEqual(
            "exact canonical non-empty JSON containers of length >= 40 in dossier JSON",
            round_2["answer_match_scope"],
        )
        self.assertEqual("legacy_cli_only", round_2["terminal_prefix_binding"])
        self.assertEqual(
            "structured_matrix_mentions_from_raw",
            round_2["assignment_binding"],
        )
        self.assertEqual(
            "legacy_task_meta_and_matrix_assignment",
            round_2["dossier_identity_binding"],
        )
        self.assertEqual(
            ["business_engineer", "governance_auditor"],
            round_2["observed_worker_path"],
        )
        self.assertEqual("cumulative_runtime", value["usage"]["scope"])
        self.assertFalse(value["claims"]["candidate_run_completed"])

    def test_runtime_readme_exposes_reproducible_m1_commands(self):
        text = RUNTIME_README.read_text(encoding="utf-8")
        for command in (
            "prepare_projectcase.py",
            "usage-snapshot",
            "matrix_run.py send",
            "matrix_run.py export-once",
            "validate_run.py",
            "export_dossier.py",
            "--manifest-file",
            "provenance.json",
            "--reuse-existing-human",
        ):
            self.assertIn(command, text)


if __name__ == "__main__":
    unittest.main()
