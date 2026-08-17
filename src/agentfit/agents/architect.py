"""Architect role: bootstrap candidates and propose evidence-backed changes."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..bus.messages import MsgType, TaskMsg
from ..core.aggregation import aggregate
from ..core.proposals import propose_updates

if TYPE_CHECKING:
    from .orchestrator import Orchestrator


def make_handler(orchestrator: "Orchestrator"):
    def handle(msg: TaskMsg):
        if msg.type == MsgType.BOOTSTRAP:
            return orchestrator.solution
        aggregated = aggregate(msg.payload.get("loss_traces", []))
        return propose_updates(aggregated, orchestrator.pool.by_id(), orchestrator.solution)
    return handle
