"""Repository-level governance for the single-canonical architecture."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
FROZEN_SUBMISSION = REPO / "competition" / "2026-08-16" / "submission"
FROZEN_TREE_DIGEST = "b63a2210ce0d395d550e6981dedd92792ef9fe8b4e4e66e5dd7016efa0a1abfa"
LEGACY_ARCHITECTURE_DOCS = {
    "agentfit-skeleton.md",
    "agentfit-solution.md",
    "agentfit-implementation.md",
}
ITERATION_PATH_PATTERN = re.compile(
    r"(?i)(?:^|[-_.])(v\d+(?:[._-]\d+)*|draft|final|stage[-_]?\d*)(?:$|[-_.])"
)


def _contains_active_iteration_name(line: str) -> bool:
    """Reject AgentFit iteration labels without rejecting dependency identities."""
    active_text = re.sub(r"https?://[^\s`'\"<>]+", "", line)
    active_text = re.sub(
        r"(?i)\bAgentTeams\s+v\d+(?:[._-]\d+)*\b", "AgentTeams", active_text,
    )
    active_text = re.sub(
        r"(?i)\bDeepSeek-V4(?:-(?:Flash|Pro|Max))?\b", "DeepSeek", active_text,
    )
    active_text = re.sub(
        r"(?i)(\bLiteLLM\b[\s:`]*)/v1/models(?=$|[\s`'\"\])，。；、|])",
        r"\1/api/models",
        active_text,
    )
    active_text = re.sub(r"(?i)--[a-z0-9][a-z0-9-]*", "", active_text)
    patterns = (
        re.compile(r"(?i)\bv\d+(?:[._-]\d+)*(?:-final)?\b"),
        re.compile(r"(?i)\bfinal\b"),
        re.compile(r"定稿不改|旧版本保留|可版本化重训练"),
    )
    return any(pattern.search(active_text) for pattern in patterns)


def _contains_active_iteration_path(path: Path) -> bool:
    """Reject iteration labels in every directory or file component."""
    return any(ITERATION_PATH_PATTERN.search(Path(part).stem) for part in path.parts)


def _is_immutable_evidence_path(path: Path) -> bool:
    return (
        path.parts[:3] == ("competition", "2026-08-16", "submission")
        or path.parts[:1] == ("runs",)
    )


def _tracked_active_artifact_paths() -> list[Path]:
    """Return repository-wide tracked paths, excluding immutable evidence archives."""
    result = subprocess.run(
        ("git", "ls-files", "-z"),
        cwd=REPO,
        check=True,
        capture_output=True,
    )
    paths = [Path(raw.decode()) for raw in result.stdout.split(b"\0") if raw]
    return [path for path in paths if not _is_immutable_evidence_path(path)]


def _active_doc_iteration_violations(root: Path) -> list[str]:
    violations: list[str] = []
    for path in sorted(root.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), 1):
            if _contains_active_iteration_name(line):
                violations.append(f"{path.relative_to(root)}:{line_no}: {line.strip()}")
    return violations


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(
        p for p in root.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.suffix not in {".pyc", ".pyo"}
    ):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def test_tree_digest_ignores_generated_caches(tmp_path: Path) -> None:
    (tmp_path / "artifact.txt").write_text("canonical", encoding="utf-8")
    expected = _tree_digest(tmp_path)
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    (cache / "artifact.cpython-312.pyc").write_bytes(b"generated")
    assert _tree_digest(tmp_path) == expected


def test_preliminary_submission_is_frozen() -> None:
    assert _tree_digest(FROZEN_SUBMISSION) == FROZEN_TREE_DIGEST


def test_architecture_has_one_canonical_document() -> None:
    assert (REPO / "docs" / "architecture.md").is_file()
    leftovers = sorted(
        path.name for path in (REPO / "docs").glob("*.md")
        if path.name in LEGACY_ARCHITECTURE_DOCS
    )
    assert leftovers == [], f"重叠架构文档必须合并后删除: {leftovers}"


def test_active_doc_policy_scans_nested_markdown(tmp_path: Path) -> None:
    nested = tmp_path / "architecture"
    nested.mkdir()
    (nested / "overview.md").write_text("AgentFit v3\n", encoding="utf-8")

    violations = _active_doc_iteration_violations(tmp_path)

    assert len(violations) == 1
    assert "architecture/overview.md:1" in violations[0]


def test_active_docs_do_not_carry_iteration_names() -> None:
    violations = _active_doc_iteration_violations(REPO / "docs")
    assert violations == [], "活跃文档仍携带迭代名称:\n" + "\n".join(violations)


def test_iteration_name_policy_distinguishes_dependency_identities() -> None:
    for line in (
        "DeepSeek-V4-Flash 使用说明",
        "model_id=deepseek-v4-flash",
        "DeepSeek-V4-Pro-Max 官方成绩",
        "AgentTeams v1.1.2 平台合同",
        "tau2-bench@1.0.1 数据快照",
        "LiteLLM `/v1/models` model discovery",
        "DeepSeek API https://api.deepseek.com/v1",
    ):
        assert not _contains_active_iteration_name(line)
    for line in (
        "GET /v1/models",
        "OtherGateway /v1/models",
        "LiteLLM /v1/models/preview",
        "LiteLLM /v1/models?preview=1",
        "LiteLLM /v1/models#preview",
        "LiteLLM /v1/models%2Fpreview",
        "LiteLLM /v1/models;preview=1",
        "LiteLLM docs: OtherGateway /v1/models",
        "AgentFit v2",
        "architecture-v3",
        "docs/architecture/v3/overview.md",
        "AgentFit/v2/README.md",
        "AgentFit/v1/models",
        "final architecture",
        "旧版本保留",
    ):
        assert _contains_active_iteration_name(line)


def test_iteration_path_policy_rejects_versioned_active_directories() -> None:
    for relative_path in (
        "docs/architecture/v3/overview.md",
        "AgentFit/v2/README.md",
        "src/agentfit/architecture-v3.py",
    ):
        assert _contains_active_iteration_path(Path(relative_path))
    for relative_path in (
        "docs/architecture.md",
        "src/agentfit/models.py",
    ):
        assert not _contains_active_iteration_path(Path(relative_path))


def test_path_policy_only_exempts_known_evidence_archives() -> None:
    assert _is_immutable_evidence_path(
        Path("competition/2026-08-16/submission/slides/01-cover.html")
    )
    assert _is_immutable_evidence_path(Path("runs/evaluation-v001.json"))
    assert not _is_immutable_evidence_path(
        Path("competition/2027-01-01/submission-v2/README.md")
    )


def test_active_artifact_paths_are_stable() -> None:
    violations = [
        path.as_posix()
        for path in _tracked_active_artifact_paths()
        if _contains_active_iteration_path(path)
    ]
    assert violations == [], "活构件路径携带迭代标签:\n" + "\n".join(violations)


def test_skills_are_stable_canonical_files() -> None:
    skills = sorted((REPO / "src" / "agentfit" / "skills").glob("*.md"))
    assert len(skills) == 11
    violations = []
    for path in skills:
        text = path.read_text(encoding="utf-8")
        if "## 步骤" not in text:
            violations.append(f"{path.name}: 缺步骤")
        if "## 版本" in text or "可版本化" in text:
            violations.append(f"{path.name}: Skill 演化必须交给 Git")
    assert violations == [], "\n".join(violations)


def test_agentteams_bridge_uses_stable_deployment_names() -> None:
    apply_text = (REPO / "bridges" / "agentteams" / "apply_team.py").read_text(encoding="utf-8")
    export_text = (REPO / "bridges" / "agentteams" / "export_solution.py").read_text(encoding="utf-8")
    assert "team-agentfit-v" not in apply_text
    assert not re.search(r'"project"\s*:\s*f?"[^"\n]*-v\{', export_text)


def test_active_sources_only_reference_canonical_architecture() -> None:
    violations = []
    for root in (REPO / "src", REPO / "docs"):
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix not in {".py", ".md"}:
                continue
            text = path.read_text(encoding="utf-8")
            for legacy in LEGACY_ARCHITECTURE_DOCS:
                if legacy in text:
                    violations.append(f"{path.relative_to(REPO)} references {legacy}")
    assert violations == [], "已删除架构副本仍被引用:\n" + "\n".join(violations)


def test_documented_cli_and_example_are_executable_contracts() -> None:
    scenario = (REPO / "docs" / "test-scenario.md").read_text(encoding="utf-8")
    assert "python -m agentfit.train" not in scenario
    for command in (
        "agentfit compile", "agentfit train", "agentfit validate",
        "agentfit report", "agentfit export",
    ):
        assert command in scenario
    assert "AGENTFIT_G3_SIGNING_KEY" in scenario
    assert (REPO / "examples" / "telecom-materials.json").is_file()
    assert not (REPO / "examples" / "telecom-case.json").exists(), (
        "compiled cases are generated output, not a second tracked source"
    )
    assert "├── samples.json" not in scenario
    assert "external_evaluation" in scenario
    assert "不得执行 `agentfit export`" in scenario
    for artifact in ("sample_sets.json", "summary.json", "boundary.json",
                     "delivery_decision.json",
                     "solution_package/package.json", "evidence_package/manifest.json"):
        assert artifact in scenario


def test_external_evaluation_docs_match_the_separate_evidence_contract() -> None:
    architecture = (REPO / "docs" / "architecture.md").read_text(encoding="utf-8")
    scenario = (REPO / "docs" / "test-scenario.md").read_text(encoding="utf-8")
    plan = (REPO / "docs" / "development-plan.md").read_text(encoding="utf-8")

    for term in ("CandidateManifest", "ExternalEvidenceRecord"):
        assert term in architecture
    for artifact in (
        "candidate_manifest.json", "external_evidence/", "evaluation_report.md",
    ):
        assert artifact in scenario
    assert "外部评价不生成训练 Epoch" in scenario
    assert "epoch 哈希链；它不要求伪造" not in scenario
    assert "逐条外部证据链" in plan


def test_active_docs_match_the_current_acceptance_and_ci_state() -> None:
    architecture = (REPO / "docs" / "architecture.md").read_text(encoding="utf-8")
    plan = (REPO / "docs" / "development-plan.md").read_text(encoding="utf-8")
    readme = (REPO / "docs" / "README.md").read_text(encoding="utf-8")
    scenario = (REPO / "docs" / "test-scenario.md").read_text(encoding="utf-8")

    assert "还没有 `ObjectiveSpec`" not in plan
    assert "ObjectiveSpec 与 AcceptanceResult" in plan
    assert "CI 工作流尚未接入" in architecture
    assert "CI 扫描活构件" not in architecture
    for artifact in ("objective.json", "acceptance.json"):
        assert artifact in scenario
    for document in (readme, scenario):
        assert "当前严格示例会被 G3 拒绝导出" in document


def test_active_docs_keep_four_layer_semantics_separate_from_runtime_bindings() -> None:
    architecture = (REPO / "docs" / "architecture.md").read_text(encoding="utf-8")
    plan = (REPO / "docs" / "development-plan.md").read_text(encoding="utf-8")
    readme = (REPO / "docs" / "README.md").read_text(encoding="utf-8")
    scenario = (REPO / "docs" / "test-scenario.md").read_text(encoding="utf-8")

    for document in (architecture, plan, readme, scenario):
        assert "RuntimeManifest" not in document
    assert "MCP、Memory 与对象层自动部署" not in architecture
    assert "横向同层禁止互调" not in readme
    assert "L4 只允许通过显式 TopologyEdge 通信" in architecture
    assert "MCP、原生函数、HTTP 或脚本" in architecture
    assert "运行环境错误不得归因到 L1–L4" in architecture
    assert "AgentTeamsSandboxExecutor" in scenario
    assert "import_results_to_runstore" in scenario
    assert "capability_contracts" in architecture


def test_telecom_materials_compile_to_four_traceable_sets() -> None:
    from agentfit.materials.compiler import compile_material_bundle

    materials = json.loads(
        (REPO / "examples" / "telecom-materials.json").read_text(encoding="utf-8")
    )
    compiled = compile_material_bundle(materials)
    assert len(compiled.observations) >= 1
    assert len(compiled.task_samples) == 12
    assert all(task.observation_refs for task in compiled.task_samples)
    compiled.sample_sets.assert_ready_for_candidate_generation()
    assert {
        manifest.purpose.value: len(manifest.sample_refs)
        for manifest in compiled.sample_sets.manifests
    } == {
        "adaptation": 3,
        "validation": 3,
        "sealed_holdout": 3,
        "stress_and_failure": 3,
    }
    assert {
        criterion.min_pass_rate for criterion in compiled.objective_spec.criteria
    } == {1.0}


def test_open_source_maintenance_contracts_exist() -> None:
    assert (REPO / "CONTRIBUTING.md").is_file()
    assert (REPO / "SECURITY.md").is_file()
    assert "Changes to TaskSample" in (REPO / "CONTRIBUTING.md").read_text(encoding="utf-8")


def test_benchmark_plan_blocks_unlicensed_sources_and_clusters_trials() -> None:
    benchmark = (REPO / "docs" / "benchmark-evaluation.md").read_text(encoding="utf-8")

    assert "DeepSeek 官网已经正式发布 `deepseek-v4-flash`" in benchmark
    assert "**官方外部参照**" in benchmark
    assert "Published Reference 只作为单独一列" in benchmark
    assert "不参加显著性检验" in benchmark
    assert "`BLOCKED_LICENSE`" in benchmark
    assert "禁止 clone、运行、vendor 或调用公共服务" in benchmark
    assert "仓库未声明顶层 license；可使用公共服务" not in benchmark
    assert "先在每个 SampleRef 内汇总同一 arm 的重复 trial" in benchmark
    assert "paired bootstrap 以 SampleRef 为重采样 cluster" in benchmark
    assert "McNemar 使用 sample-level paired outcome" in benchmark
    assert "trial 不能作为独立样本扩大统计样本量" in benchmark


def test_benchmark_execution_scope_is_tau2_telecom_then_retail() -> None:
    benchmark = (REPO / "docs" / "benchmark-evaluation.md").read_text(encoding="utf-8")
    plan = (REPO / "docs" / "development-plan.md").read_text(encoding="utf-8")

    for document in (benchmark, plan):
        assert "当前只建设一个 benchmark adapter：`τ²-bench`" in document
        assert "telecom 5 题协议与证据 smoke" in document
        assert "telecom 20 题完整维护闭环" in document
        assert "telecom 74 个 train 样本扩大与优化" in document
        assert "telecom 40 个 official test 封存验收" in document
        assert "retail 小规模复用验证" in document
        assert "不排期、不开发 Adapter" in document

    route = (
        "telecom 5 题协议与证据 smoke",
        "telecom 20 题完整维护闭环",
        "telecom 74 个 train 样本扩大与优化",
        "telecom 40 个 official test 封存验收",
        "retail 小规模复用验证",
    )
    for document in (benchmark, plan):
        positions = [document.index(label) for label in route]
        assert positions == sorted(positions)

    stage_titles = (
        "### 阶段 B：telecom 5 题协议与证据 smoke",
        "### 阶段 C：telecom 20 题完整维护闭环",
        "### 阶段 D：telecom 74 个 train 样本扩大与优化",
        "### 阶段 E：telecom 40 个 official test 封存验收",
        "### 阶段 F：retail 小规模复用验证",
    )
    stage_positions = [benchmark.index(title) for title in stage_titles]
    assert stage_positions == sorted(stage_positions)
    assert "pilot G0" in benchmark
    assert "候选生成前" in benchmark
    assert "四个互不重叠的 pilot manifest" in benchmark
    assert "telecom CandidateRef 的完整 L1–L4" in benchmark
    assert "资产复用账本" in benchmark
    assert "完整 L1–L4" in plan
    assert "资产复用账本" in plan
    assert "### 2.1 数据集总览" not in benchmark
    assert "阶段 F：外部适用性扩展" not in benchmark
    assert "主实验稳定后再扩展 Terminal-Bench" not in benchmark
    assert "外部 benchmark bridge" not in benchmark
    assert not re.search(r"^### 阶段.*full", benchmark, re.MULTILINE)


def test_current_execution_uses_user_owned_deepseek_official_api() -> None:
    benchmark = (REPO / "docs" / "benchmark-evaluation.md").read_text(encoding="utf-8")
    plan = (REPO / "docs" / "development-plan.md").read_text(encoding="utf-8")
    scenario = (REPO / "docs" / "test-scenario.md").read_text(encoding="utf-8")

    for document in (benchmark, plan, scenario):
        assert "deepseek-v4-flash" in document
    assert "用户自有的 DeepSeek 官网 API" in benchmark
    assert "https://api.deepseek.com/v1" in benchmark
    assert "https://api.deepseek.com/v1" in scenario
    assert "DEEPSEEK_API_KEY" in benchmark
    assert "DEEPSEEK_API_KEY" in scenario
    assert "不使用 LiteLLM 网关、代理或路由" in benchmark
    assert benchmark.count("LiteLLM") == 1
    assert "LiteLLM" not in plan
    assert "LiteLLM" not in scenario


def test_deepseek_official_api_runtime_is_blocked_until_preflight() -> None:
    scenario = (REPO / "docs" / "test-scenario.md").read_text(encoding="utf-8")

    assert "BLOCKED_NOT_VERIFIED" in scenario
    assert "DeepSeek 官网 API 直连尚未完成预检" in scenario


def test_agentteams_live_validation_is_archival_not_a_current_runbook() -> None:
    live_validation = (
        REPO / "docs" / "agentteams-live-validation.md"
    ).read_text(encoding="utf-8")
    docs_index = (REPO / "docs" / "README.md").read_text(encoding="utf-8")

    assert "2026-08-18 历史证据" in live_validation
    assert "ARCHIVAL_EVIDENCE" in live_validation
    assert "不作为当前运行入口" in live_validation
    assert "`deepseek/deepseek-chat`" in live_validation
    assert "--model deepseek/deepseek-chat" not in live_validation
    assert "BLOCKED_NOT_VERIFIED" in live_validation
    assert "AgentTeams 历史联动证据" in docs_index
    assert "证据边界；当前复现入口阻断" in docs_index
