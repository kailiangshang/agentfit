#!/usr/bin/env python3
"""Contract tests for the AgentFit preliminary submission package."""

from __future__ import annotations

import base64
import importlib.util
import json
import re
import tempfile
import unittest
import zipfile
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches
from pypdf import PdfWriter


ROOT = Path(__file__).resolve().parent
SLIDES_DIR = ROOT / "slides"
INTRODUCTION = ROOT / "work-introduction-draft.md"
VALIDATOR = ROOT / "validate_presentation.py"
PPTX = ROOT / "agentfit-preliminary-draft.pptx"
REPO_ROOT = ROOT.parents[2]
SOLUTION = REPO_ROOT / "docs" / "agentfit-solution.md"
PROJECT_CASE = REPO_ROOT / "docs" / "internal" / "contracts" / "project-case-template.md"
LANDING = ROOT.parent / "design" / "agentteams-landing-design.md"
PRESENTATION_DESIGN = ROOT.parent / "design" / "presentation-redesign.md"
OFFICIAL_CASE_MD = ROOT.parent / "research" / "official-case-simulation.md"
OFFICIAL_CASE_JSON = ROOT.parent / "research" / "official-case-simulation.json"
IDENTITIES = ROOT / "agent-identity.md"
SKILLS = ROOT / "skill-catalog.md"
RISKS = ROOT / "risk-and-human-gates.md"
README = ROOT.parent / "README.md"
READINESS = ROOT.parent / "planning" / "readiness-board.md"

EVALUATION_IDENTITY = "CandidateVersion × SampleVersion × RunIndex"
MANIFEST_PURPOSES = (
    "adaptation",
    "validation",
    "sealed_holdout",
    "stress_and_failure",
)
ACTIVE_SEMANTIC_SOURCES = (
    SOLUTION,
    PROJECT_CASE,
    LANDING,
    PRESENTATION_DESIGN,
    OFFICIAL_CASE_MD,
    OFFICIAL_CASE_JSON,
    IDENTITIES,
    SKILLS,
    RISKS,
    ROOT / "ppt-outline.md",
    INTRODUCTION,
)


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


def _section(text: str, heading: str) -> str:
    match = re.search(
        rf"^{re.escape(heading)}\s*$\n(?P<body>.*?)(?=^##\s|\Z)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    if not match:
        raise AssertionError(f"missing section: {heading}")
    return match.group("body")


def _add_transition_and_media(pptx_path: Path) -> None:
    rewritten = pptx_path.with_suffix(".rewritten.pptx")
    with zipfile.ZipFile(pptx_path) as source, zipfile.ZipFile(
        rewritten, "w"
    ) as target:
        for item in source.infolist():
            payload = source.read(item.filename)
            if item.filename == "ppt/slides/slide1.xml":
                payload = payload.replace(
                    b"</p:sld>", b"<p:transition/></p:sld>"
                )
            target.writestr(item, payload)
        target.writestr("ppt/media/demo.mp4", b"design-test-media")
    rewritten.replace(pptx_path)


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
        self.assertTrue(
            hasattr(validator, "EXPECTED_PAGE_TITLES"),
            "validator must encode the title expected on every page",
        )
        self.assertTrue(
            hasattr(validator, "SLIDE_REQUIRED_TERMS"),
            "validator must encode affected-slide terms per page",
        )
        if hasattr(validator, "EXPECTED_PAGE_TITLES"):
            self.assertEqual(17, len(validator.EXPECTED_PAGE_TITLES))
        if hasattr(validator, "SLIDE_REQUIRED_TERMS"):
            self.assertEqual(
                "AgentFit 先定义样本，再编译任务和方案",
                validator.SLIDE_REQUIRED_TERMS[4][0],
            )
            self.assertIn(
                "候选冻结后，仅 GovernanceAuditor 消费 sealed-holdout 结果",
                validator.SLIDE_REQUIRED_TERMS[7],
            )
            self.assertIn(
                "候选前冻结 Sample/Task · 候选后批准 TrialSpec",
                validator.SLIDE_REQUIRED_TERMS[7],
            )
            self.assertIn("L1 样本语义", validator.SLIDE_REQUIRED_TERMS.get(13, ()))
            self.assertIn("L7 跨项目学习", validator.SLIDE_REQUIRED_TERMS.get(13, ()))

    def test_sample_and_task_freeze_precedes_candidate_generation(self) -> None:
        solution_flow = _section(
            SOLUTION.read_text(encoding="utf-8"), "### 7.3 通信、状态与责任"
        )
        self.assertIn(
            "SampleSemanticSpec + four distinct SampleSetManifests(adaptation, validation, sealed_holdout, stress_and_failure)",
            solution_flow,
        )

        landing_text = LANDING.read_text(encoding="utf-8")
        flow = _section(landing_text, "## 5. 最小闭环")
        ordered_steps = (
            "adaptation、validation、sealed_holdout、stress_and_failure 四份互异且不可变的 SampleSetManifest",
            "Human 批准并冻结 SampleSemanticSpec、TaskSemanticSpec 与四份 SampleSetManifest",
            "AgentArchitect 生成 Capability Registry、AlignmentReport 和 CandidateGraphSet",
            "Human 单独批准 TrialSpec、权限和预算",
        )
        positions = []
        for step in ordered_steps:
            with self.subTest(step=step):
                self.assertIn(step, flow)
            positions.append(flow.find(step))
        self.assertEqual(sorted(positions), positions)

        self.assertIn(
            "| BusinessEngineer | 独立 Worker | Worker 配置、Sample/Task 编译 Skill、`SampleSemanticSpec`、`SampleSetManifest`、`TaskSemanticSpec` |",
            landing_text,
        )

        identity_flow = _section(
            IDENTITIES.read_text(encoding="utf-8"), "## 责任链协作流程"
        )
        identity_steps = (
            "业务架构师(定义 Sample/Task 契约与四份 manifest)",
            "Human(批准并冻结 Sample/Task 契约与四份 manifest)",
            "方案架构师(生成候选)",
            "Human(单独批准 TrialSpec、权限和预算)",
        )
        identity_positions = []
        for step in identity_steps:
            with self.subTest(identity_step=step):
                self.assertIn(step, identity_flow)
            identity_positions.append(identity_flow.find(step))
        self.assertEqual(sorted(identity_positions), identity_positions)

        skill_text = SKILLS.read_text(encoding="utf-8")
        self.assertIn(
            "Sample/Task 契约与四份 SampleSetManifest 获 Human 批准并冻结后触发",
            skill_text,
        )
        risk_text = RISKS.read_text(encoding="utf-8")
        self.assertIn("候选生成前", risk_text)
        self.assertIn("候选生成后,统一试验前", risk_text)

    def test_evaluation_identity_is_exact_in_active_sources(self) -> None:
        identity_sources = (
            SOLUTION,
            PROJECT_CASE,
            LANDING,
            OFFICIAL_CASE_MD,
            OFFICIAL_CASE_JSON,
            IDENTITIES,
            SKILLS,
        )
        for path in identity_sources:
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name, identity=EVALUATION_IDENTITY):
                self.assertIn(EVALUATION_IDENTITY, text)

        weakened_patterns = (
            r"CandidateVersion × TaskSample(?: × RunIndex)?",
            r"Candidate × TaskSample(?: × RunIndex)?",
            r"Candidate × Sample(?: Trace)?",
            r"CandidateVersion × SampleVersion(?! × RunIndex)",
        )
        for path in ACTIVE_SEMANTIC_SOURCES:
            text = path.read_text(encoding="utf-8")
            for pattern in weakened_patterns:
                with self.subTest(path=path.name, weakened=pattern):
                    self.assertIsNone(re.search(pattern, text))
            for stale in ("same input", "同一输入", "相同输入", "统一输入"):
                with self.subTest(path=path.name, stale=stale):
                    self.assertNotIn(stale, text)

        execution_trace = _section(
            SOLUTION.read_text(encoding="utf-8"), "### 9.2 ExecutionTrace"
        )
        self.assertIn("sample_version, run_index, episode_and_step", execution_trace)

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

        sample_spec = payload["sample_semantic_spec"]
        for field in ("sample_spec_id", "version", "task_spec_ref"):
            with self.subTest(sample_spec_field=field):
                self.assertIn(field, sample_spec)
                self.assertTrue(sample_spec.get(field))
        self.assertEqual("not_instantiated", sample_spec.get("status"))
        sample_spec_ref = (
            f"{sample_spec.get('sample_spec_id')}@{sample_spec.get('version')}"
        )

        manifest_contract = payload["sample_set_manifests"]
        self.assertEqual("not_instantiated", manifest_contract["status"])
        descriptors = manifest_contract.get("descriptors", {})
        self.assertEqual(set(MANIFEST_PURPOSES), set(descriptors))
        for purpose in MANIFEST_PURPOSES:
            descriptor = descriptors.get(purpose, {})
            with self.subTest(manifest=purpose):
                self.assertEqual("not_instantiated", descriptor.get("status"))
                self.assertEqual(purpose, descriptor.get("purpose"))
                self.assertEqual(sample_spec_ref, descriptor.get("sample_spec_ref"))
                self.assertIn("version", descriptor)
                self.assertIsNone(descriptor.get("version"))
                self.assertIn("content_hash", descriptor)
                self.assertIsNone(descriptor.get("content_hash"))
                self.assertTrue(descriptor.get("access_policy"))

        task_contract = payload["task_semantic_spec"]
        self.assertEqual(sample_spec_ref, task_contract.get("sample_spec_ref"))
        sample_distribution = task_contract.get("sample_distribution", {})
        self.assertEqual(
            "not_instantiated", sample_distribution.get("status")
        )
        self.assertEqual(
            list(MANIFEST_PURPOSES),
            sample_distribution.get("manifest_purposes"),
        )

        episode_mapping = payload.get("episode_run_mapping", {})
        self.assertEqual("not_instantiated", episode_mapping.get("status"))
        self.assertEqual(
            EVALUATION_IDENTITY, episode_mapping.get("evaluation_unit")
        )
        for field in (
            "candidate_version",
            "sample_version",
            "run_index",
            "episode_semantics",
            "trace_semantics",
        ):
            with self.subTest(episode_mapping_field=field):
                self.assertIn(field, episode_mapping)

        case_text = OFFICIAL_CASE_MD.read_text(encoding="utf-8")
        paper_trace = "\n".join(payload["paper_trace"])
        self.assertNotIn("生成 SampleSetManifest", paper_trace)
        self.assertNotIn("生成 SampleSetManifest", case_text)
        self.assertIn("不实例化任何样本成员或 SampleSetManifest", case_text)

    def test_affected_slides_have_exact_source_phrases(self) -> None:
        required_by_slide = {
            "04-compiler.html": (
                "AgentFit 先定义样本，再编译任务和方案",
            ),
            "06-software-dev.html": (
                "同一冻结 SampleSetManifest",
                "同一版本化 TaskSample",
            ),
            "07-trialspec.html": (
                "候选冻结后，仅 GovernanceAuditor 消费 sealed-holdout 结果",
                "候选前冻结 Sample/Task · 候选后批准 TrialSpec",
            ),
            "13-a1-ml-mapping.html": (
                "L1 样本语义",
                "L7 跨项目学习",
            ),
        }
        for filename, terms in required_by_slide.items():
            text = (SLIDES_DIR / filename).read_text(encoding="utf-8")
            for term in terms:
                with self.subTest(slide=filename, term=term):
                    self.assertIn(term, text)

    def test_validator_checks_affected_terms_on_their_pptx_slides(self) -> None:
        validator = _load_validator()
        with tempfile.TemporaryDirectory(prefix="agentfit-slide-guard-") as temp_dir:
            path = Path(temp_dir) / "misplaced-terms.pptx"
            presentation = Presentation(PPTX)
            replacements = {
                4: (
                    "AgentFit 先定义样本，再编译任务和方案",
                    "AgentFit 先量体，再裁衣，最后试穿",
                ),
                7: (
                    "候选冻结后，仅 GovernanceAuditor 消费 sealed-holdout 结果",
                    "同一项目档案 · 每个样本可重放 · 每次执行有 Episode · 每次决策有 Trace",
                ),
                13: (
                    "L1 样本语义",
                    "L1 任务语义",
                ),
            }
            for slide_number, (required, stale) in replacements.items():
                for shape in presentation.slides[slide_number - 1].shapes:
                    if getattr(shape, "has_text_frame", False) and required in shape.text:
                        shape.text = shape.text.replace(required, stale)
                textbox = presentation.slides[0].shapes.add_textbox(
                    Inches(0.1), Inches(0.1), Inches(10), Inches(0.3)
                )
                textbox.text = required
            presentation.save(path)

            errors = validator.validate(path)

        self.assertIn(
            "PPTX slide 4 is missing required term: AgentFit 先定义样本，再编译任务和方案",
            errors,
        )
        self.assertIn(
            "PPTX slide 7 is missing required term: 候选冻结后，仅 GovernanceAuditor 消费 sealed-holdout 结果",
            errors,
        )
        self.assertIn(
            "PPTX slide 13 is missing required term: L1 样本语义",
            errors,
        )

    def test_validator_rejects_blank_pdf_pages_even_when_count_matches(self) -> None:
        validator = _load_validator()
        with tempfile.TemporaryDirectory(prefix="agentfit-pdf-guard-") as temp_dir:
            pdf_path = Path(temp_dir) / "blank-17-pages.pdf"
            writer = PdfWriter()
            for _ in range(17):
                writer.add_blank_page(width=1280, height=720)
            with pdf_path.open("wb") as stream:
                writer.write(stream)

            errors = validator.validate(PPTX, pdf_path)

        self.assertIn(
            "PDF page 4 is missing expected title: AgentFit 先定义样本，再编译任务和方案",
            errors,
        )

    def test_validator_rejects_raster_media_transitions_and_invisible_text(self) -> None:
        validator = _load_validator()
        with tempfile.TemporaryDirectory(prefix="agentfit-native-guard-") as temp_dir:
            temp = Path(temp_dir)
            pptx_path = temp / "non-native.pptx"
            png_path = temp / "pixel.png"
            png_path.write_bytes(
                base64.b64decode(
                    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
                )
            )

            presentation = Presentation()
            slide = presentation.slides.add_slide(presentation.slide_layouts[6])
            slide.shapes.add_picture(
                str(png_path),
                0,
                0,
                width=presentation.slide_width,
                height=presentation.slide_height,
            )
            textbox = slide.shapes.add_textbox(
                presentation.slide_width + Inches(1),
                presentation.slide_height + Inches(1),
                Inches(1),
                Inches(1),
            )
            textbox.text = "only invisible native text"
            presentation.save(pptx_path)
            _add_transition_and_media(pptx_path)

            errors = validator.validate(pptx_path)

        self.assertIn("PPTX slide 1 contains a picture/raster shape", errors)
        self.assertIn("PPTX package contains embedded media: ppt/media/demo.mp4", errors)
        self.assertIn("PPTX slide 1 contains a transition", errors)
        self.assertIn(
            "PPTX slide 1 has no visible native text/content shape", errors
        )

    def test_readiness_describes_pptx_geometry_and_pdf_text_truthfully(self) -> None:
        expected = (
            "PPTX 的 17 页结构、内容与几何验证通过，"
            "PDF 的 17 页页数与逐页文本验证通过"
        )
        for path in (README, READINESS):
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                self.assertIn(expected, text)
                self.assertNotIn("PPTX/PDF 的结构、内容与几何", text)
                self.assertNotIn("PPTX/PDF 的结构、内容与几何验证", text)
                self.assertIn("完整 17 页 PPTX/PDF 的逐页视觉复核仍待完成", text)

        solution_text = SOLUTION.read_text(encoding="utf-8")
        self.assertIn(
            "| 初赛材料 | `IN_PROGRESS` |",
            solution_text,
        )
        self.assertIn(
            "完整 17 页 PPTX/PDF 的逐页视觉复核仍待完成",
            solution_text,
        )
        self.assertNotIn("| 初赛材料 | `READY` |", solution_text)
        self.assertIn("488 个非空白字符", solution_text)
        self.assertNotIn("468 个非空白字符", solution_text)

    def test_introduction_guidance_uses_approved_limit_and_measured_count(self) -> None:
        design_text = PRESENTATION_DESIGN.read_text(encoding="utf-8")
        self.assertNotIn("420–470", design_text)
        self.assertIn("不超过 500", design_text)
        self.assertIn("实测 488", design_text)

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
