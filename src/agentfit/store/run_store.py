"""RunStore：一次训练运行的标准产物目录（数据基座）。

目录结构（对应 docs/test-scenario.md §六交付树）：
  <run_dir>/
    run.json                  # 运行元信息（场景/配置/起止/最终状态）
    samples.json              # 样本池 + 分组
    epochs/epoch_NNN.json     # 每轮：通过率/损失分布/更新/正则/回归/λ/成本
    loss_traces/epoch_NNN/<sample_id>.json   # 失败样本归因明细
    solution_versions/vNNN.json              # 每个版本四层全量快照
    messages/epoch_NNN.json   # 总线消息因果链
    summary.json              # 收尾汇总（baseline vs final、交付建议）

Dashboard / 报告 / 审计取证三个消费者共同读这里。
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from ..models.loss import Sample
from ..models.solution import Solution


def _dump(obj: Any) -> Any:
    if is_dataclass(obj):
        return _dump(asdict(obj))
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, (list, tuple)):
        return [_dump(o) for o in obj]
    if isinstance(obj, dict):
        return {k: _dump(v) for k, v in obj.items()}
    return obj


def _write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_dump(data), ensure_ascii=False, indent=1), encoding="utf-8")


class RunStore:
    def __init__(self, run_dir: str | Path):
        self.root = Path(run_dir)
        self.root.mkdir(parents=True, exist_ok=True)

    # ---- 写 ----
    def init_run(self, meta: dict) -> None:
        _write(self.root / "run.json", meta)

    def save_samples(self, samples: list[Sample]) -> None:
        _write(self.root / "samples.json", {
            "total": len(samples),
            "groups": {g: [s.id for s in samples if s.group == g] for g in {s.group for s in samples}},
            "samples": samples,
        })

    def save_sample_manifests(self, collection: Any) -> Path:
        path = self.root / "sample_sets.json"
        _write(path, collection)
        return path

    def save_task_samples(self, samples: list[Any]) -> Path:
        path = self.root / "task_samples.json"
        _write(path, {"total": len(samples), "samples": samples})
        return path

    def save_source_results(self, results: Any) -> Path:
        path = self.root / "source_results.json"
        _write(path, results)
        return path

    def save_episode(self, episode: Any) -> Path:
        path = self.root / "episodes" / f"{episode.identity.key}.json"
        _write(path, episode)
        return path

    def save_trace(self, identity: Any, trace: Any) -> Path:
        path = self.root / "traces" / f"{identity.key}.json"
        _write(path, trace)
        return path

    def save_solution_version(self, solution: Solution, note: str = "") -> None:
        path = self.root / "solution_versions" / f"v{solution.version:03d}.json"
        _write(path, {"version": solution.version, "note": note, "solution": solution})

    def save_epoch(self, epoch: int, entry_record: dict, loss_traces: list) -> None:
        _write(self.root / "epochs" / f"epoch_{epoch:03d}.json", entry_record)
        for lt in loss_traces:
            _write(self.root / "loss_traces" / f"epoch_{epoch:03d}" / f"{lt.sample_id}.json", lt)

    def save_messages(self, epoch: int, traffic: list[dict]) -> None:
        _write(self.root / "messages" / f"epoch_{epoch:03d}.json", traffic)

    def save_summary(self, summary: dict) -> None:
        _write(self.root / "summary.json", summary)

    # ---- 读（dashboard/报告用） ----
    def load_json(self, rel: str) -> Any:
        return json.loads((self.root / rel).read_text(encoding="utf-8"))

    def epochs(self) -> list[int]:
        d = self.root / "epochs"
        return sorted(int(p.stem.split("_")[1]) for p in d.glob("epoch_*.json")) if d.is_dir() else []

    def solution_versions(self) -> list[int]:
        d = self.root / "solution_versions"
        return sorted(int(p.stem[1:]) for p in d.glob("v*.json")) if d.is_dir() else []

    def verify_hash_chain(self) -> bool:
        """Recompute the persisted epoch chain; never trust summary metadata."""
        epochs = self.epochs()
        if not epochs:
            return False
        previous = "GENESIS"
        for epoch in epochs:
            record = self.load_json(f"epochs/epoch_{epoch:03d}.json")
            if not isinstance(record, dict) or not isinstance(record.get("entry"), dict):
                return False
            canonical = json.dumps(
                record["entry"], sort_keys=True, ensure_ascii=False, default=str,
            )
            expected = hashlib.sha256((previous + canonical).encode("utf-8")).hexdigest()
            if record.get("previous_hash") != previous or record.get("hash") != expected:
                return False
            previous = expected
        return True

    def dashboard_payload(self) -> dict:
        """一次性聚合全部呈现数据。"""
        payload: dict[str, Any] = {"run": None, "samples": None, "epochs": [],
                                   "loss_traces": {}, "solutions": {}, "messages": {}, "summary": None}
        if (self.root / "run.json").exists():
            payload["run"] = self.load_json("run.json")
        if (self.root / "samples.json").exists():
            payload["samples"] = self.load_json("samples.json")
        for e in self.epochs():
            payload["epochs"].append(self.load_json(f"epochs/epoch_{e:03d}.json"))
            lt_dir = self.root / "loss_traces" / f"epoch_{e:03d}"
            if lt_dir.is_dir():
                payload["loss_traces"][e] = [json.loads(p.read_text(encoding="utf-8"))
                                             for p in sorted(lt_dir.glob("*.json"))]
            msg = self.root / "messages" / f"epoch_{e:03d}.json"
            if msg.exists():
                payload["messages"][e] = self.load_json(f"messages/epoch_{e:03d}.json")
        for v in self.solution_versions():
            payload["solutions"][v] = self.load_json(f"solution_versions/v{v:03d}.json")
        if (self.root / "summary.json").exists():
            payload["summary"] = self.load_json("summary.json")
        return payload
