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


def test_no_platform_dependency_inside_library():
    violations = []
    for py in SRC.rglob("*.py"):
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


def test_architecture_level_complete():
    """架构正本的全量结构清单——子模块可逐步增强，但边界不能缺失。"""
    required_modules = [
        "agentfit.bus.messages", "agentfit.agents.base", "agentfit.agents.orchestrator",
        "agentfit.agents.team", "agentfit.agents.auditor", "agentfit.agents.steward",
        "agentfit.agents.attributor", "agentfit.agents.architect", "agentfit.agents.validator",
        "agentfit.models.solution", "agentfit.models.loss", "agentfit.models.config",
        "agentfit.models.sample", "agentfit.models.manifest",
        "agentfit.core.attribution", "agentfit.core.transaction", "agentfit.core.regularization",
        "agentfit.core.aggregation", "agentfit.core.proposals", "agentfit.core.regression",
        "agentfit.data.sample_pool", "agentfit.data.clustering",
        "agentfit.executors.base", "agentfit.executors.simulator",
        "agentfit.solution.validator", "agentfit.solution.builder",
        "agentfit.log.training_log", "agentfit.log.report",
        "agentfit.store.run_store", "agentfit.dashboard.generate",
        "agentfit.monitoring.monitor", "agentfit.delivery.package", "agentfit.delivery.boundary",
        "agentfit.skills.registry", "agentfit.gates.human", "agentfit.adapters.protocols",
        "agentfit.cli",
    ]
    import importlib
    for mod in required_modules:
        importlib.import_module(mod)   # 缺一个就 ImportError → 测试失败


def test_platform_neutral_adapter_protocols_are_reserved():
    import importlib

    protocols = importlib.import_module("agentfit.adapters.protocols")
    for name in ("CognitiveAdapter", "RetrievalAdapter", "SandboxAdapter"):
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
