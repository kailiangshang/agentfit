"""Pydantic 结构校验模型：AgentTeams 结果信封的严格 schema。

替代提示词约定的"希望模型守格式"：解析后经 Pydantic 校验，失败时
携带具体校验错误自动重试（pydantic-ai 模式），同时把模型的
指令遵循能力作为可观测信号记录。
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator


class StepSchema(BaseModel):
    layer: str = Field(pattern=r"^(L1|L2|L3|L4)$")
    element_id: str = Field(min_length=1)
    action: str = ""
    ok: bool = True
    error: str | None = None
    output: Any = None
    expected_output: Any = None
    downstream: list[int] = Field(default_factory=list)

    @field_validator("downstream")
    @classmethod
    def non_negative(cls, v: list[int]) -> list[int]:
        if any(i < 0 for i in v):
            raise ValueError("downstream indices must be non-negative")
        return v


class ResultEnvelope(BaseModel):
    """agentfit.agentteams-result 的完整结构合同。"""
    schema_name: str = Field(alias="schema", pattern=r"^agentfit\.agentteams-result$")
    task_id: str = Field(min_length=1)
    candidate_ref: str = Field(min_length=1)
    sample_ref: dict = Field()
    run_index: int = Field(ge=0)
    runtime_ref: str = Field(min_length=1)
    status: str = Field(pattern=r"^(completed|failed|error)$")
    steps: list[StepSchema] = Field(default_factory=list)
    cost_usd: float = Field(default=0.0, ge=0)
    error_code: str | None = None
    error_scope: str | None = None

    model_config = {"populate_by_name": True}


def validate_envelope(payload: dict) -> tuple[ResultEnvelope | None, str | None]:
    """校验结果信封。返回 (envelope, None) 或 (None, 具体错误描述)。"""
    try:
        return ResultEnvelope(**payload), None
    except ValidationError as exc:
        details = []
        for error in exc.errors()[:5]:
            loc = ".".join(str(l) for l in error["loc"])
            details.append(f"{loc}: {error['msg']}")
        return None, "; ".join(details)


def retry_message_with_errors(worker_user_id: str, task: dict,
                              validation_errors: str) -> str:
    """带具体校验错误的重试消息——不是笼统'格式错了'，而是告诉模型哪里错了。"""
    import json
    document = json.dumps(task, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return (
        f"{worker_user_id} Your previous result envelope failed schema validation.\n"
        f"SPECIFIC ERRORS (fix these exactly):\n{validation_errors}\n\n"
        "Return ONLY a corrected JSON envelope with schema=agentfit.agentteams-result. "
        "Each step needs layer (L1|L2|L3|L4), element_id (non-empty string), "
        "action (string), ok (boolean). The envelope needs task_id, candidate_ref, "
        "sample_ref, run_index, runtime_ref, status (completed|failed|error).\n"
        f"AGENTFIT_TASK_BEGIN\n{document}\nAGENTFIT_TASK_END"
    )
