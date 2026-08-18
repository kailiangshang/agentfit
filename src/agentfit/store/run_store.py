"""RunStore：训练或外部评价的一次不可变证据目录。

目录结构（对应 docs/test-scenario.md §六交付树）：
  <run_dir>/
    run.json                  # 运行元信息（场景/配置/起止/最终状态）
    task_samples.json         # 唯一 TaskSample 正本
    epochs/epoch_NNN.json     # 每轮：通过率/损失分布/更新/正则/回归/λ/成本
    loss_traces/epoch_NNN/<sample_id>.json   # 失败样本归因明细
    solution_versions/vNNN.json              # 每个版本四层全量快照
    messages/epoch_NNN.json   # 总线消息因果链
    summary.json              # 与 run_kind 对应的可重算汇总

外部评价另用 candidate_manifest.json、external_evidence/、Trace 和 Episode，
不得伪造训练 Epoch、Solution snapshot 或 G3。Dashboard / 报告 / 审计共同读取。
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

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

    def save_sample_manifests(self, collection: Any) -> Path:
        path = self.root / "sample_sets.json"
        _write(path, collection)
        return path

    def save_task_samples(self, samples: list[Any]) -> Path:
        path = self.root / "task_samples.json"
        _write(path, {"total": len(samples), "samples": samples})
        return path

    def save_source_observations(self, observations: list[Any]) -> Path:
        path = self.root / "source_observations.json"
        _write(path, {"total": len(observations), "observations": observations})
        return path

    def save_capability_inventory(self, inventory: Any) -> Path:
        path = self.root / "capability_inventory.json"
        _write(path, inventory)
        return path

    def save_objective(self, objective: Any) -> Path:
        path = self.root / "objective.json"
        _write(path, objective)
        return path

    def save_acceptance(self, acceptance: Any) -> Path:
        path = self.root / "acceptance.json"
        _write(path, acceptance)
        return path

    def save_source_results(self, results: Any) -> Path:
        path = self.root / "source_results.json"
        _write(path, results)
        return path

    def save_source_results_bytes(self, results: bytes) -> Path:
        """Preserve the uploaded bytes so its SHA-256 remains independently checkable."""
        path = self.root / "source_results.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(results)
        return path

    def save_candidate_manifest(self, manifest: Any) -> Path:
        path = self.root / "candidate_manifest.json"
        _write(path, manifest)
        return path

    def save_training_candidate_manifest(self, manifest: Any) -> Path:
        path = self.root / "candidate_manifests" / f"{manifest.content_hash}.json"
        _write(path, manifest)
        return path

    def save_external_evidence(self, record: Any) -> Path:
        path = self.root / "external_evidence" / f"record_{record.source_index:06d}.json"
        _write(path, record)
        return path

    def save_episode(self, episode: Any) -> Path:
        path = self.root / "episodes" / f"{episode.identity.key}.json"
        _write(path, episode)
        return path

    def save_trace(self, identity: Any, trace: Any) -> Path:
        path = self.root / "traces" / f"{identity.key}.json"
        _write(path, trace)
        return path

    def save_training_trace(self, epoch: int, phase: str, identity: Any, trace: Any) -> Path:
        path = (
            self.root / "training_traces" / phase / f"epoch_{epoch:03d}"
            / f"{identity.key}.json"
        )
        _write(path, trace)
        return path

    def save_training_episode(self, epoch: int, phase: str, episode: Any) -> Path:
        path = (
            self.root / "training_episodes" / phase / f"epoch_{epoch:03d}"
            / f"{episode.identity.key}.json"
        )
        _write(path, episode)
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

    def save_delivery_decision(self, decision: dict) -> Path:
        path = self.root / "delivery_decision.json"
        _write(path, decision)
        return path

    # ---- 读（dashboard/报告用） ----
    def load_json(self, rel: str) -> Any:
        return json.loads((self.root / rel).read_text(encoding="utf-8"))

    def epochs(self) -> list[int]:
        d = self.root / "epochs"
        return sorted(int(p.stem.split("_")[1]) for p in d.glob("epoch_*.json")) if d.is_dir() else []

    def solution_versions(self) -> list[int]:
        d = self.root / "solution_versions"
        return sorted(int(p.stem[1:]) for p in d.glob("v*.json")) if d.is_dir() else []

    def external_evidence_indices(self) -> list[int]:
        directory = self.root / "external_evidence"
        if not directory.is_dir():
            return []
        return sorted(int(path.stem.split("_")[1]) for path in directory.glob("record_*.json"))

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
        payload: dict[str, Any] = {"run": None, "task_samples": None,
                                   "source_observations": None, "sample_sets": None,
                                   "capability_inventory": None,
                                   "objective": None, "acceptance": None,
                                   "candidate_manifest": None, "external_evidence": [],
                                   "training_evidence": [], "evaluation_evidence": [],
                                   "epochs": [],
                                   "loss_traces": {}, "solutions": {}, "messages": {}, "summary": None}
        if (self.root / "run.json").exists():
            payload["run"] = self.load_json("run.json")
        if (self.root / "task_samples.json").exists():
            payload["task_samples"] = self.load_json("task_samples.json")
        if (self.root / "source_observations.json").exists():
            payload["source_observations"] = self.load_json("source_observations.json")
        if (self.root / "capability_inventory.json").exists():
            payload["capability_inventory"] = self.load_json("capability_inventory.json")
        if (self.root / "objective.json").exists():
            payload["objective"] = self.load_json("objective.json")
        if (self.root / "acceptance.json").exists():
            payload["acceptance"] = self.load_json("acceptance.json")
        if (self.root / "sample_sets.json").exists():
            payload["sample_sets"] = self.load_json("sample_sets.json")
        if (self.root / "candidate_manifest.json").exists():
            payload["candidate_manifest"] = self.load_json("candidate_manifest.json")
        for index in self.external_evidence_indices():
            payload["external_evidence"].append(
                self.load_json(f"external_evidence/record_{index:06d}.json")
            )
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
        purpose_by_sample_ref = {
            (ref.get("sample_id"), ref.get("content_hash")): manifest.get("purpose", "")
            for manifest in (payload.get("sample_sets") or {}).get("manifests", [])
            for ref in manifest.get("sample_refs", [])
        }
        training_root = self.root / "training_episodes"
        if training_root.is_dir():
            for episode_path in sorted(training_root.rglob("*.json")):
                episode = json.loads(episode_path.read_text(encoding="utf-8"))
                trace = self.load_json(episode["trace_ref"])
                relative = episode_path.relative_to(training_root)
                payload["training_evidence"].append({
                    "phase": relative.parts[0],
                    "epoch": int(relative.parts[1].split("_")[1]),
                    **_dashboard_episode_record(episode, trace),
                })
        evaluation_root = self.root / "episodes"
        if evaluation_root.is_dir():
            for episode_path in sorted(evaluation_root.glob("*.json")):
                episode = json.loads(episode_path.read_text(encoding="utf-8"))
                trace = self.load_json(episode["trace_ref"])
                sample_ref = episode["identity"]["sample_ref"]
                payload["evaluation_evidence"].append({
                    "purpose": purpose_by_sample_ref.get(
                        (sample_ref.get("sample_id"), sample_ref.get("content_hash")), "",
                    ),
                    **_dashboard_episode_record(episode, trace),
                })
        if (self.root / "summary.json").exists():
            payload["summary"] = self.load_json("summary.json")
        return payload


def _dashboard_episode_record(episode: dict[str, Any], trace: dict[str, Any]) -> dict[str, Any]:
    identity = episode["identity"]
    return {
        "sample_id": identity["sample_ref"]["sample_id"],
        "candidate_ref": identity["candidate_ref"],
        "run_index": identity["run_index"],
        "result": episode["result"],
        "error_code": trace.get("error_code"),
        "route": [
            step["element_id"]
            for step in trace.get("steps", [])
            if step.get("layer") == "L2" and step.get("ok") is True
        ],
    }
