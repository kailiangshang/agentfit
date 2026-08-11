#!/usr/bin/env python3
"""Contract tests for the AgentFit preliminary submission package."""

from __future__ import annotations

import importlib.util
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SLIDES_DIR = ROOT / "slides"
INTRODUCTION = ROOT / "work-introduction-draft.md"
VALIDATOR = ROOT / "validate_presentation.py"
REPO_ROOT = ROOT.parents[2]
SOLUTION = REPO_ROOT / "docs" / "agentfit-solution.md"
PROJECT_CASE = REPO_ROOT / "docs" / "internal" / "contracts" / "project-case-template.md"
LANDING = ROOT.parent / "design" / "agentteams-landing-design.md"
OFFICIAL_CASE_MD = ROOT.parent / "research" / "official-case-simulation.md"
OFFICIAL_CASE_JSON = ROOT.parent / "research" / "official-case-simulation.json"
IDENTITIES = ROOT / "agent-identity.md"
SKILLS = ROOT / "skill-catalog.md"
RISKS = ROOT / "risk-and-human-gates.md"


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_presentation", VALIDATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to import {VALIDATOR}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _submission_introduction(text: str) -> str:
    match = re.search(
        r"^## 500 字以内作品简介\s*$\n(?P<body>.*?)(?=^##\s|\Z)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    if not match:
        raise AssertionError("missing '500 字以内作品简介' section")
    return match.group("body").strip()


class SubmissionContractTest(unittest.TestCase):
    def test_deck_has_twelve_main_slides_and_five_appendices(self) -> None:
        slides = sorted(SLIDES_DIR.glob("[0-9][0-9]-*.html"))
        self.assertEqual(17, len(slides))
        self.assertEqual(
            [f"{index:02d}" for index in range(1, 18)],
            [path.name[:2] for path in slides],
        )

    def test_introduction_fits_platform_limit_and_reports_current_state(self) -> None:
        introduction = _submission_introduction(
            INTRODUCTION.read_text(encoding="utf-8")
        )
        character_count = len(re.sub(r"\s+", "", introduction))
        self.assertLessEqual(character_count, 500)
        self.assertIn("AgentFit", introduction)
        self.assertIn("AgentTeams", introduction)
        self.assertIn("拒绝自动化", introduction)
        self.assertIn("真实运行证据仍待补", introduction)
        self.assertNotIn("正在实施", introduction)

    def test_html_sources_exclude_disproved_or_stale_claims(self) -> None:
        source = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted(SLIDES_DIR.glob("*.html"))
        )
        forbidden = (
            "ImageNet 75%",
            "90%+",
            "超越人工设计 1.2%",
            "methodology §13",
            "已验证 Meta-learning",
            "首个真实项目案例与五元 Agent 在 AgentTeams 上的闭环正在实施",
        )
        for term in forbidden:
            with self.subTest(term=term):
                self.assertNotIn(term, source)

    def test_validator_encodes_frozen_seventeen_page_contract(self) -> None:
        validator = _load_validator()
        self.assertEqual(17, validator.EXPECTED_SLIDES)
        required = set(validator.REQUIRED_TERMS)
        for term in (
            "Agent Architecture Search",
            "Human",
            "Skill",
            "MCP",
            "上下文",
            "验证",
            "安全",
            "开放",
            "未实现",
            "Sample",
            "TaskSample",
            "Episode",
            "七层 ML 映射",
            "同一冻结样本集",
        ):
            with self.subTest(term=term):
                self.assertIn(term, required)
        self.assertIn("六层 ML 映射", validator.FORBIDDEN_TERMS)

    def test_sample_semantics_propagates_to_active_sources(self) -> None:
        required_by_file = {
            SOLUTION: ("SampleSemanticSpec", "SampleSetManifest", "TaskSample", "Episode"),
            PROJECT_CASE: ("sample_semantic_spec", "sample_set_manifests", "sealed_holdout"),
            LANDING: ("SampleSemanticSpec", "SampleSetManifest", "SampleEvaluation"),
            OFFICIAL_CASE_MD: ("SourceObservation", "TaskSample", "Episode"),
            IDENTITIES: ("SampleSemanticSpec", "SampleSetManifest"),
            SKILLS: ("SampleSemanticSpec", "SampleSetManifest"),
            RISKS: ("SampleSetManifest", "content_hash"),
        }
        for path, terms in required_by_file.items():
            text = path.read_text(encoding="utf-8")
            for term in terms:
                with self.subTest(path=path.name, term=term):
                    self.assertIn(term, text)

        solution_text = SOLUTION.read_text(encoding="utf-8")
        self.assertIn(
            "Sample 是在特定任务契约下，可以被独立冻结、重放、执行和评价的最小业务语义单元。",
            solution_text,
        )
        for contract in (
            "SourceObservation = 原始业务观察",
            "TaskSample = 当前任务契约下可独立冻结、重放、执行和评价的最小单位",
            "Episode = 固定候选在固定 TaskSample 上的一次完整执行",
            "EvaluationUnit = CandidateVersion × SampleVersion × RunIndex",
        ):
            with self.subTest(contract=contract):
                self.assertIn(contract, solution_text)

        project_case_text = PROJECT_CASE.read_text(encoding="utf-8")
        manifest_match = re.search(
            r"^## sample_set_manifests\s*$\n(?P<body>.*?)(?=^##\s|\Z)",
            project_case_text,
            flags=re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(manifest_match)
        manifest_text = manifest_match.group("body") if manifest_match else ""
        for purpose in (
            "adaptation",
            "validation",
            "sealed_holdout",
            "stress_and_failure",
        ):
            contract_line = (
                f"{purpose}: SampleSetManifest(version, content_hash, access_policy)"
            )
            with self.subTest(manifest_contract=contract_line):
                self.assertIn(contract_line, manifest_text)

        identity_and_skill_text = "\n".join(
            path.read_text(encoding="utf-8") for path in (IDENTITIES, SKILLS)
        )
        identity_text = IDENTITIES.read_text(encoding="utf-8")
        outcome_consumers = re.findall(
            r"^sealed_holdout_outcome_consumer:\s*(.+)$",
            identity_text,
            flags=re.MULTILINE,
        )
        self.assertEqual(["GovernanceAuditor only"], outcome_consumers)
        self.assertIn(
            "sealed_holdout_outcome_consumer: GovernanceAuditor only", identity_text
        )
        self.assertIn(
            "sealed_holdout_access_timing: after_candidate_freeze", identity_text
        )
        self.assertRegex(
            identity_and_skill_text,
            r"GovernanceAuditor.{0,200}sealed holdout.{0,100}(?:after|候选冻结|freeze)",
        )
        self.assertRegex(
            identity_and_skill_text,
            r"(?:AgentArchitect|候选).{0,250}(?:never|不得|不能).{0,100}sealed[- ]holdout",
        )
        self.assertRegex(
            identity_and_skill_text,
            r"(?:ValidationEngineer|执行).{0,250}(?:adaptation/validation/failure only|不得|不能).{0,100}(?:holdout|sealed)",
        )

    def test_sample_case_json_uses_machine_readable_contracts(self) -> None:
        payload = json.loads(OFFICIAL_CASE_JSON.read_text(encoding="utf-8"))
        self.assertIn("sample_semantic_spec", payload)
        self.assertIn("sample_mapping_examples", payload)
        self.assertEqual(
            "design_simulation_not_runtime_evidence", payload["evidence_status"]
        )

    def test_slides_make_sample_unit_and_episode_explicit(self) -> None:
        source = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted(SLIDES_DIR.glob("*.html"))
        )
        for term in ("七层 ML 映射", "同一冻结样本集", "TaskSample", "Episode"):
            with self.subTest(term=term):
                self.assertIn(term, source)
        layer_positions = []
        for index, layer in enumerate(
            (
                "L1 样本语义",
                "L2 任务语义",
                "L3 能力语义",
                "L4 候选表示",
                "L5 内循环",
                "L6 外循环",
                "L7 跨项目学习",
            ),
            start=1,
        ):
            position = source.find(layer)
            with self.subTest(layer=layer):
                self.assertNotEqual(-1, position)
            layer_positions.append(position)
        self.assertEqual(sorted(layer_positions), layer_positions)
        self.assertNotIn("六层 ML 映射", source)


if __name__ == "__main__":
    unittest.main()
