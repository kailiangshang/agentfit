"""Canonical project inputs shared by compilation, training and delivery."""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

from .sample import canonical_hash
from .solution import CapabilityTool, HumanGate, SolidAtom


@dataclass(frozen=True)
class CapabilityInventory:
    """Human-provided L1/L2 capabilities; candidates may not invent entries."""

    atoms: tuple[SolidAtom, ...]
    tools: tuple[CapabilityTool, ...]
    content_hash: str

    @classmethod
    def create(cls, *, atoms: tuple[SolidAtom, ...] | list[SolidAtom],
               tools: tuple[CapabilityTool, ...] | list[CapabilityTool]) -> "CapabilityInventory":
        body = {
            "atoms": tuple(copy.deepcopy(tuple(atoms))),
            "tools": tuple(copy.deepcopy(tuple(tools))),
        }
        return cls(**body, content_hash=canonical_hash(body))

    def __post_init__(self) -> None:
        self.assert_integrity()

    def assert_integrity(self) -> None:
        if not self.atoms:
            raise ValueError("capability inventory requires at least one L1 atom")
        atom_ids = [atom.id for atom in self.atoms]
        if any(not atom.id or not atom.type for atom in self.atoms):
            raise ValueError("every L1 atom requires an id and semantic type")
        if len(atom_ids) != len(set(atom_ids)):
            raise ValueError("capability inventory L1 atom ids must be unique")

        tool_ids = [tool.id for tool in self.tools]
        if not self.tools or any(not tool.id or not tool.wraps for tool in self.tools):
            raise ValueError("every L2 tool requires an id and wrapped L1 atoms")
        if len(tool_ids) != len(set(tool_ids)):
            raise ValueError("capability inventory L2 tool ids must be unique")
        known_atoms = set(atom_ids)
        for tool in self.tools:
            unknown = sorted(set(tool.wraps) - known_atoms)
            if unknown:
                raise ValueError(
                    f"L2 tool {tool.id} wraps unknown L1 atom: {unknown[0]}"
                )

        expected = canonical_hash({"atoms": self.atoms, "tools": self.tools})
        if self.content_hash != expected:
            raise ValueError("capability inventory content_hash does not match content")


def capability_inventory_from_dict(data: dict[str, Any]) -> CapabilityInventory:
    """Restore and verify a persisted capability inventory."""
    if not isinstance(data, dict):
        raise TypeError("capability inventory must be an object")
    atoms = tuple(SolidAtom(**item) for item in data.get("atoms", []))
    tools = []
    for item in data.get("tools", []):
        payload = dict(item)
        gate = payload.get("human_gate")
        payload["human_gate"] = HumanGate(**gate) if gate else None
        tools.append(CapabilityTool(**payload))
    content_hash = data.get("content_hash")
    if not isinstance(content_hash, str):
        raise ValueError("capability inventory content_hash is required")
    return CapabilityInventory(tuple(atoms), tuple(tools), content_hash)
