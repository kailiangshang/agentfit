"""Stable contracts that keep model, retrieval, tool, material, preference,
storage and presentation runtimes out of core.

核心只定义接口；插件实现功能。新增功能 = 新增插件，核心不变胖。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


# ---- 认知槽位（Attributor/Architect 的 LLM 调用） ----

@dataclass(frozen=True)
class EvidenceReference:
    uri: str
    content_hash: str
    media_type: str = "application/json"


@dataclass(frozen=True)
class CognitiveRequest:
    slot: str
    payload: dict[str, Any]
    instructions: str = ""
    evidence_refs: tuple[EvidenceReference, ...] = ()
    budget_usd: float | None = None


@dataclass(frozen=True)
class CognitiveResult:
    output: Any
    evidence_refs: tuple[EvidenceReference, ...] = ()
    model_ref: str = ""
    cost_usd: float = 0.0
    trace_ref: str = ""


@runtime_checkable
class CognitiveAdapter(Protocol):
    def invoke(self, request: CognitiveRequest) -> CognitiveResult: ...


# ---- 检索 ----

@dataclass(frozen=True)
class RetrievalQuery:
    text: str
    filters: dict[str, Any] = field(default_factory=dict)
    limit: int = 10


@dataclass(frozen=True)
class RetrievedEvidence:
    reference: EvidenceReference
    content: Any
    score: float


@runtime_checkable
class RetrievalAdapter(Protocol):
    def retrieve(self, query: RetrievalQuery) -> tuple[RetrievedEvidence, ...]: ...


# ---- 沙箱执行 ----

@dataclass(frozen=True)
class SandboxRequest:
    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: float = 30.0


@dataclass(frozen=True)
class SandboxResult:
    status: str
    output: Any = None
    error: str | None = None
    evidence_ref: EvidenceReference | None = None
    cost_usd: float = 0.0


@runtime_checkable
class SandboxAdapter(Protocol):
    def execute(self, request: SandboxRequest) -> SandboxResult: ...


@runtime_checkable
class ExternalEvidenceProjector(Protocol):
    """Bridge callback that deterministically projects raw source evidence."""

    def __call__(self, source_results: dict[str, Any], candidate_ref: str) -> Any: ...


# ---- 材料解析（张伟诉求①：不想手工整理材料） ----

@dataclass(frozen=True)
class MaterialParseResult:
    bundle: dict[str, Any]           # AgentFit bundle 格式
    clarifications: list[dict]       # 需要用户澄清的问题
    confidence: float


@runtime_checkable
class MaterialParser(Protocol):
    """从原始业务材料生成可训练的 bundle。"""

    def parse(self, raw_materials: Any) -> MaterialParseResult: ...


# ---- 偏好管理（张伟诉求③：审批偏好自动沉淀） ----

@dataclass(frozen=True)
class ApprovalDecision:
    approved: bool
    reason: str
    proposal_summaries: tuple[str, ...]
    timestamp: str


@runtime_checkable
class PreferenceStore(Protocol):
    """跨 run 持久化审批偏好，从决策历史自动学习。"""

    def record_decision(self, decision: ApprovalDecision) -> None: ...
    def learned_preferences(self) -> str: ...
    def update_preferences(self, preferences: str) -> None: ...


# ---- 存储后端（张伟诉求⑤：历史可查询不占空间） ----

@dataclass(frozen=True)
class StorageQuery:
    scenario: str | None = None
    since: str | None = None
    version_range: tuple[int, int] | None = None
    change_type: str | None = None


@runtime_checkable
class StorageBackend(Protocol):
    """证据存储与查询。默认实现：本地文件系统 RunStore。"""

    def save_run(self, run_dir: Path) -> None: ...
    def query(self, criteria: StorageQuery) -> list[dict[str, Any]]: ...
    def compact(self, older_than_days: int) -> int: ...


# ---- 呈现（Dashboard / 报告 / 演进图） ----

@runtime_checkable
class Presenter(Protocol):
    """从 RunStore 数据生成人类可读的呈现。"""

    def render(self, run_dir: Path) -> Path: ...


# ---- 进度推送（张伟诉求②：训练时看业务语义） ----

@dataclass(frozen=True)
class ProgressEvent:
    sample_id: str
    business_description: str        # "省流模式导致的网速慢"
    result: str                      # PASS/FAIL/ERROR
    elapsed_seconds: float
    running_summary: str             # "已处理 3/8，通过 2，失败 1"


@runtime_checkable
class ProgressRenderer(Protocol):
    """训练进度的实时呈现。默认实现：终端打印。"""

    def emit(self, event: ProgressEvent) -> None: ...
