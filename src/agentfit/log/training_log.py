"""哈希链训练日志（可审计的机制保证）。每条 entry 的 hash = sha256(prev_hash + content)。"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class EpochEntry:
    epoch: int
    solution_version: int
    pass_rate: float
    loss_distribution: dict[str, int] = field(default_factory=dict)
    updates_applied: list[dict] = field(default_factory=list)
    regularization: dict[str, float] = field(default_factory=dict)
    behavioral: dict[str, float] = field(default_factory=dict)
    regression: dict[str, int] = field(default_factory=dict)
    lambda_values: dict[str, float] = field(default_factory=dict)
    cost_usd: float = 0.0
    rolled_back: bool = False
    note: str = ""


def _canonical(entry: EpochEntry) -> str:
    return json.dumps(asdict(entry), sort_keys=True, ensure_ascii=False, default=str)


class TrainingLog:
    def __init__(self) -> None:
        self.entries: list[dict] = []
        self._prev_hash = "GENESIS"

    def append(self, entry: EpochEntry) -> str:
        content = _canonical(entry)
        digest = hashlib.sha256((self._prev_hash + content).encode("utf-8")).hexdigest()
        record = {"entry": json.loads(content), "hash": digest, "previous_hash": self._prev_hash}
        self.entries.append(record)
        self._prev_hash = digest
        return digest

    def verify(self) -> bool:
        """全链校验：任何条目被篡改则 False。"""
        prev = "GENESIS"
        for record in self.entries:
            expect = hashlib.sha256((prev + json.dumps(record["entry"], sort_keys=True, ensure_ascii=False, default=str)).encode("utf-8")).hexdigest()
            if record["previous_hash"] != prev or record["hash"] != expect:
                return False
            prev = record["hash"]
        return True

    def pass_rate_series(self) -> list[float]:
        return [r["entry"]["pass_rate"] for r in self.entries if not r["entry"]["rolled_back"]]

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.entries, ensure_ascii=False, indent=1), encoding="utf-8")
