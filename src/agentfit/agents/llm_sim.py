"""LLM Simulator.

Deterministic simulation of LLM responses for reproducible testing.
Each scenario registers prompt handlers; the simulator dispatches by prompt_key.

In production, this would be replaced by real LLM API calls.
The simulator allows AgentFit's evaluation methodology to be tested
without API dependencies.
"""

from __future__ import annotations

from typing import Any, Callable


class LLMSimulator:
    def __init__(self):
        self._handlers: dict[str, Callable] = {}
        self._default: Callable | None = None

    def register(self, prompt_key: str, handler: Callable) -> None:
        self._handlers[prompt_key] = handler

    def register_default(self, handler: Callable) -> None:
        self._default = handler

    def generate(
        self,
        prompt_key: str,
        context: dict[str, Any] | None = None,
        memory: dict[str, Any] | None = None,
        config: dict[str, Any] | None = None,
    ) -> Any:
        handler = self._handlers.get(prompt_key)
        if handler is None and self._default:
            handler = self._default
        if handler is None:
            return {"output": "simulated", "done": True}
        return handler(context or {}, memory or {}, config or {})
