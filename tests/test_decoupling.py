"""架构守护测试：解耦约束 + 架构级全量（防推倒重来的机制保证）。

1. src/agentfit 内禁止 import agentteams / tau2（桥接只允许在 bridges/）
2. 架构正本声明的全部结构模块必须存在且可导入（架构级全量）
3. 11 个 Skill 定义文件存在且使用稳定名称（演化由 Git 记录）
"""
from __future__ import annotations

import ast
from pathlib import Path

import agentfit

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src" / "agentfit"
FORBIDDEN = ("agentteams", "tau2", "tau2bench")


def test_core_does_not_import_plugins():
    """薄核心原则：src/agentfit 不得静态 import plugins/（插件通过接口注入）。

    动态加载（importlib）是允许的——orchestrator 的 _invoke_plugin 用的就是动态加载。
    """
    # 组合根例外：cli.py 是唯一同时引核心和插件的文件
    COMPOSITION_ROOT = "cli.py"
    violations = []
    for py in SRC.rglob("*.py"):
        if py.name == COMPOSITION_ROOT:
            continue
        content = py.read_text(encoding="utf-8")
        for i, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            if (stripped.startswith("from plugins.") or stripped.startswith("import plugins.")
                    and "importlib" not in stripped):
                violations.append(f"{py.relative_to(REPO)}:{i} {stripped[:60]}")
    assert not violations, (
        "核心不得静态 import plugins（薄核心原则）：\n" + "\n".join(violations)
    )


def test_core_does_not_import_platform_dependency_inside_library():
    violations = []
    for py in SRC.rglob("*.py"):
        relative = py.relative_to(SRC).as_posix().lower()
        if any(name in relative for name in FORBIDDEN):
            violations.append(f"{py.relative_to(REPO)} is platform-specific")
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            else:
                continue
            for name in names:
                root = name.split(".")[0].lower()
                if any(f in root for f in FORBIDDEN):
                    violations.append(f"{py.relative_to(REPO)} imports {name}")
    assert not violations, f"库内出现平台强依赖：\n{chr(10).join(violations)}"


def test_task_sample_is_the_only_active_sample_model() -> None:
    violations = []
    excluded = {
        SRC / "models" / "loss.py",
        SRC / "models" / "sample.py",
    }
    for root in (SRC, REPO / "bridges"):
        for path in root.rglob("*.py"):
            if path in excluded:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and any(
                    alias.name == "Sample" for alias in node.names
                ):
                    violations.append(str(path.relative_to(REPO)))
    assert not violations, "活跃运行路径仍导入 legacy Sample:\n" + "\n".join(
        sorted(set(violations))
    )
    loss_source = (SRC / "models" / "loss.py").read_text(encoding="utf-8")
    sample_source = (SRC / "models" / "sample.py").read_text(encoding="utf-8")
    store_source = (SRC / "store" / "run_store.py").read_text(encoding="utf-8")
    assert "class Sample:" not in loss_source
    assert "task_sample_from_legacy" not in sample_source
    assert "def save_samples(" not in store_source
    for path in SRC.rglob("*.py"):
        assert "legacy_group" not in path.read_text(encoding="utf-8"), path.relative_to(REPO)


def test_architecture_level_complete():
    """架构正本的全量结构清单——子模块可逐步增强，但边界不能缺失。"""
    required_modules = [
        "agentfit.bus.messages", "agentfit.agents.base", "agentfit.agents.orchestrator",
        "agentfit.agents.team", "agentfit.agents.auditor", "agentfit.agents.steward",
        "agentfit.agents.attributor", "agentfit.agents.architect", "agentfit.agents.validator",
        "agentfit.models.solution", "agentfit.models.loss", "agentfit.models.config",
        "agentfit.models.sample", "agentfit.models.manifest",
        "agentfit.models.evidence",
        "agentfit.core.attribution", "agentfit.core.transaction", "agentfit.core.regularization",
        "agentfit.core.aggregation", "agentfit.core.proposals", "agentfit.core.regression",
        "agentfit.data.sample_pool", "agentfit.data.clustering",
        "agentfit.executors.base", "agentfit.executors.simulator",
        "agentfit.solution.validator", "agentfit.solution.builder",
        "agentfit.log.training_log", "plugins.report",
        "agentfit.store.run_store", "plugins.dashboard.generate",
        "agentfit.monitoring.monitor", "plugins.solution_package", "plugins.boundary",
        "agentfit.skills.registry", "agentfit.gates.human", "agentfit.adapters.protocols",
        "agentfit.cli",
    ]
    import importlib
    for mod in required_modules:
        importlib.import_module(mod)   # 缺一个就 ImportError → 测试失败


def test_platform_neutral_adapter_protocols_are_reserved():
    import importlib

    protocols = importlib.import_module("agentfit.adapters.protocols")
    for name in (
        "CognitiveAdapter", "RetrievalAdapter", "SandboxAdapter",
        "ExternalEvidenceProjector",
    ):
        contract = getattr(protocols, name)
        assert getattr(contract, "_is_protocol", False), f"{name} 必须是平台无关 Protocol"


def test_skills_are_stable_files():
    skills = sorted((SRC / "skills").glob("*.md"))
    assert len(skills) == 11, f"应有 11 个 Skill 定义，实际 {len(skills)}"
    for skill in skills:
        content = skill.read_text(encoding="utf-8")
        assert "## 步骤" in content, f"{skill.name} 缺步骤"
        assert "## 版本" not in content and "可版本化" not in content, f"{skill.name} 不应自带迭代版本"


def test_bridges_exist_outside_library():
    for bridge in ("bridges/agentteams/export_solution.py",
                   "bridges/agentteams/import_results.py",
                   "bridges/tau2bench/run_bench.py"):
        assert (REPO / bridge).exists(), f"缺桥接脚本 {bridge}"
