"""六角色装配：把角色运行时挂到总线（元层 L4 拓扑的运行时形态）。

分工与确定性边界见 docs/agentfit-implementation.md §一：
- Steward/Attributor/Architect：认知角色（内核确定性实现，LLM 槽位接口留待生产接入）
- Orchestrator/Validator/Auditor：确定性官员
"""
from __future__ import annotations

from ..bus.messages import MessageBus, MsgType, ResultMsg
from ..skills.registry import SkillRegistry
from .architect import make_handler as make_architect_handler
from .attributor import make_handler as make_attributor_handler
from .base import make_agent
from .orchestrator import Orchestrator
from .steward import handle as steward_handle
from .validator import make_handler as make_validator_handler


def build_team(orchestrator: Orchestrator, bus: MessageBus | None = None,
               registry: SkillRegistry | None = None) -> dict[str, object]:
    """注册全部角色到总线，返回角色表。Orchestrator 持有循环，其余角色各守其职。"""
    bus = bus or orchestrator.bus
    registry = registry or SkillRegistry()

    steward = make_agent("steward", (MsgType.INTAKE, MsgType.CLARIFY, MsgType.EXPLAIN),
                         steward_handle,
                         skills=registry.require("intake", "clarify", "explain"),
                         llm_slots=["intake", "clarify", "explain"])

    attributor = make_agent("attributor", (MsgType.ATTRIBUTE,),
                            make_attributor_handler(orchestrator),
                            skills=registry.require("attribution"),
                            llm_slots=["counterfactual"])

    architect = make_agent("architect", (MsgType.BOOTSTRAP, MsgType.PROPOSE),
                           make_architect_handler(orchestrator),
                           skills=registry.require("bootstrap", "aggregation", "proposal", "cascade"),
                           llm_slots=["bootstrap", "proposal"])

    validator = make_agent("validator", (MsgType.VALIDATE_STRUCT, MsgType.REGRESSION),
                           make_validator_handler(orchestrator),
                           skills=registry.require("validation", "regression"))

    auditor = make_agent("auditor", (MsgType.LOG_APPEND,), _auditor_log,
                         skills=registry.require("lambda_audit"))

    for agent in (steward, attributor, architect, validator, auditor):
        bus.register(agent.name, agent.handled_types, agent.handle)
    return {"steward": steward, "orchestrator": orchestrator, "attributor": attributor,
            "architect": architect, "validator": validator, "auditor": auditor}
# ---- Auditor：证据落链（只记录不决策） ----
def _auditor_log(msg):
    return ResultMsg(task_id=msg.task_id, status="ok",
                     evidence={"recorded": True, "type": msg.type.value})
