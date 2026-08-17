"""Evidence-based automation boundary analysis."""
from __future__ import annotations

import json
from pathlib import Path

from ..store.run_store import RunStore


def analyze_boundary(run_dir: str | Path) -> dict:
    """Classify Samples from completed Episodes, with a legacy-run fallback."""
    store = RunStore(run_dir)
    samples_doc = store.load_json("samples.json") if (store.root / "samples.json").is_file() else {}
    samples = samples_doc.get("samples", [])
    by_id = {sample["id"]: sample for sample in samples}
    episode_paths = sorted((store.root / "episodes").glob("*.json"))

    if episode_paths:
        outcomes: dict[str, list[str]] = {}
        for path in episode_paths:
            episode = json.loads(path.read_text(encoding="utf-8"))
            sample_id = episode["identity"]["sample_ref"]["sample_id"]
            outcomes.setdefault(sample_id, []).append(episode["result"])
        human_required = sorted(
            sample_id for sample_id, sample in by_id.items()
            if sample.get("requires_human", False)
        )
        automated = sorted(
            sample_id for sample_id, results in outcomes.items()
            if sample_id not in human_required and "PASS" in results
        )
        failed = sorted(
            sample_id for sample_id, results in outcomes.items()
            if sample_id not in human_required and "PASS" not in results
        )
        untested = sorted(set(by_id) - set(outcomes))
        evidence_source = "episodes"
    else:
        human_required, eval_errors = [], []
        for epoch in store.epochs():
            loss_dir = store.root / "loss_traces" / f"epoch_{epoch:03d}"
            for path in loss_dir.glob("*.json") if loss_dir.is_dir() else ():
                trace = json.loads(path.read_text(encoding="utf-8"))
                if trace.get("root_cause_layer") == "human":
                    human_required.append(trace["sample_id"])
                elif trace.get("root_cause_layer") == "eval_error":
                    eval_errors.append(trace["sample_id"])
        human_required = sorted(set(human_required) | {
            sample_id for sample_id, sample in by_id.items()
            if sample.get("requires_human", False)
        })
        failed = sorted(set(eval_errors))
        automated = sorted(set(by_id) - set(human_required) - set(failed))
        untested = []
        evidence_source = "legacy_epoch_fallback"

    coverage = len(automated) / max(1, len(by_id))
    delivery = (
        "全自动" if coverage >= 0.95 and not human_required else
        "部分自动" if coverage >= 0.7 else
        "降级" if coverage >= 0.5 else "保留人工"
    )
    return {
        "automated": len(automated),
        "automated_sample_ids": automated,
        "human_required": human_required,
        "failed": failed,
        "untested": untested,
        "coverage": round(coverage, 3),
        "recommended_delivery": delivery,
        "evidence_source": evidence_source,
    }


def write_boundary(run_dir: str | Path) -> Path:
    root = Path(run_dir)
    path = root / "boundary.json"
    path.write_text(
        json.dumps(analyze_boundary(root), ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    return path
