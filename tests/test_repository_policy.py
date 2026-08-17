"""Repository-level governance for the single-canonical architecture."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
FROZEN_SUBMISSION = REPO / "competition" / "2026-08-16" / "submission"
FROZEN_TREE_DIGEST = "b63a2210ce0d395d550e6981dedd92792ef9fe8b4e4e66e5dd7016efa0a1abfa"
LEGACY_ARCHITECTURE_DOCS = {
    "agentfit-skeleton.md",
    "agentfit-solution.md",
    "agentfit-implementation.md",
}


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


def test_active_docs_do_not_carry_iteration_names() -> None:
    violations: list[str] = []
    patterns = (
        re.compile(r"(?i)\bv\d+(?:[._-]\d+)*(?:-final)?\b"),
        re.compile(r"(?i)\bfinal\b"),
        re.compile(r"定稿不改|旧版本保留|可版本化重训练"),
    )
    for path in sorted((REPO / "docs").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), 1):
            active_text = re.sub(
                r"(?i)\bAgentTeams\s+v\d+(?:[._-]\d+)*\b", "AgentTeams", line,
            )
            if any(pattern.search(active_text) for pattern in patterns):
                violations.append(f"{path.relative_to(REPO)}:{line_no}: {line.strip()}")
    assert violations == [], "活跃文档仍携带迭代名称:\n" + "\n".join(violations)


def test_active_artifact_filenames_are_stable() -> None:
    pattern = re.compile(r"(?i)(?:^|[-_.])(v\d+(?:[._-]\d+)*|draft|final|stage[-_]?\d*)(?:$|[-_.])")
    violations = []
    for root_name in ("src", "docs", "bridges", "examples"):
        root = REPO / root_name
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            if pattern.search(path.stem):
                violations.append(path.relative_to(REPO).as_posix())
    assert violations == [], "活构件文件名携带迭代标签:\n" + "\n".join(violations)


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
    for command in ("agentfit train", "agentfit validate", "agentfit report", "agentfit export"):
        assert command in scenario
    assert (REPO / "examples" / "telecom-case.json").is_file()
    for artifact in ("sample_sets.json", "summary.json", "boundary.json",
                     "delivery_decision.json",
                     "solution_package/package.json", "evidence_package/manifest.json"):
        assert artifact in scenario


def test_open_source_maintenance_contracts_exist() -> None:
    assert (REPO / "CONTRIBUTING.md").is_file()
    assert (REPO / "SECURITY.md").is_file()
