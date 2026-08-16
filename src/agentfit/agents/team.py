"""六角色装配：把角色运行时挂到总线（元层 L4 拓扑的运行时形态）。

分工与确定性边界见 docs/agentfit-implementation.md §一：
- Steward/Attributor/Architect：认知角色（内核确定性实现，LLM 槽位接口留待生产接入）
- Orchestrator/Validator/Auditor：确定性官员
"""
from __future__ import annotations

from ..bus.messages import MessageBus, MsgType, ResultMsg
from ..core.attribution import attribute_loss
from ..core.transaction import ValidationError
from ..models.loss import Sample
from ..models.solution import Solution
from ..solution import validator as solution_validator
from .base import make_agent
from .orchestrator import Orchestrator


def build_team(orchestrator: Orchestrator, bus: MessageBus | None = None) -> dict[str, object]:
    """注册全部角色到总线，返回角色表。Orchestrator 持有循环，其余角色各守其职。"""
    bus = bus or orchestrator.bus

    steward = make_agent("steward", (MsgType.INTAKE, MsgType.CLARIFY, MsgType.EXPLAIN),
                         _steward_intake, llm_slots=["intake", "clarify", "explain"])

    attributor = make_agent("attributor", (MsgType.ATTRIBUTE,),
                            _make_attributor_handler(orchestrator), llm_slots=["counterfactual"])

    architect = make_agent("architect", (MsgType.BOOTSTRAP, MsgType.PROPOSE),
                           lambda msg: _architect_dispatch(msg, orchestrator), llm_slots=["bootstrap", "proposal"])

    validator = make_agent("validator", (MsgType.VALIDATE_STRUCT, MsgType.REGRESSION),
                           _make_validator_handler(orchestrator))

    auditor = make_agent("auditor", (MsgType.LOG_APPEND,), _auditor_log)

    for agent in (steward, attributor, architect, validator, auditor):
        bus.register(agent.name, agent.handled_types, agent.handle)
    return {"steward": steward, "orchestrator": orchestrator, "attributor": attributor,
            "architect": architect, "validator": validator, "auditor": auditor}


# ---- Steward：材料操作化（确定性内核版；生产接 LLM 槽位） ----
def _steward_intake(msg):
    payload = msg.payload
    samples = [Sample(**spec) for spec in payload.get("samples", [])]
    if not samples:
        return ResultMsg(task_id=msg.task_id, status="escalated",
                         output=[], evidence={"reason": "样本不足，需澄清"})
    return samples


# ---- Attributor：单失败样本归因 ----
def _make_attributor_handler(orch: Orchestrator):
    def handler(msg):
        payload = msg.payload
        return attribute_loss(payload["sample"], payload["trace"], orch.solution)
    return handler


# ---- Architect：bootstrap / 建议生成 ----
def _architect_dispatch(msg, orch: Orchestrator):
    if msg.type == MsgType.BOOTSTRAP:
        return orch.solution          # 初始方案由场景构建器给出（Simple First）
    from ..core.aggregation import aggregate
    from ..core.proposals import propose_updates
    agg = aggregate(msg.payload.get("loss_traces", []))
    return propose_updates(agg, orch.pool.by_id(), orch.solution)


# ---- Validator：结构验证（裁决权，纯确定性） ----
def _make_validator_handler(orch: Orchestrator):
    def handler(msg):
        if msg.type == MsgType.VALIDATE_STRUCT:
            solution: Solution = msg.payload.get("solution", orch.solution)
            errors = solution_validator.validate_existence_dependencies(solution)
            errors += solution_validator.validate_same_layer_constraints(solution)
            return ResultMsg(task_id=msg.task_id, status="ok" if not errors else "failed",
                             output=errors)
        return ResultMsg(task_id=msg.task_id, status="ok", output=None)
    return handler


# ---- Auditor：证据落链（只记录不决策） ----
def _auditor_log(msg):
    return ResultMsg(task_id=msg.task_id, status="ok",
                     evidence={"recorded": True, "type": msg.type.value})
