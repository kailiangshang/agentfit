"""Attributor role: attribute one failed sample without proposing changes."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..bus.messages import TaskMsg
from ..core.attribution import attribute_loss

if TYPE_CHECKING:
    from .orchestrator import Orchestrator


def make_handler(orchestrator: "Orchestrator"):
    def handle(msg: TaskMsg):
        return attribute_loss(
            msg.payload["sample"], msg.payload["trace"], orchestrator.solution,
        )
    return handle
