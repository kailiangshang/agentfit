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
        ):
            with self.subTest(term=term):
                self.assertIn(term, required)

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
        self.assertNotIn("六层 ML 映射", source)


if __name__ == "__main__":
    unittest.main()
