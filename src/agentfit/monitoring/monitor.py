"""监控（简版）：训练后健康检查。drift 检测 + 部署监控规则导出。"""
from __future__ import annotations

from ..models.sample import TaskSample

DRIFT_ALERT_RATIO = 0.15   # 分布偏移 > 15% → 建议重训练（test-scenario.md §四）


def feature_distribution(samples: list[TaskSample]) -> dict[str, float]:
    """布尔特征 → 出现比例。"""
    if any(not isinstance(item, TaskSample) for item in samples):
        raise TypeError("monitoring accepts canonical TaskSample objects only")
    dist: dict[str, int] = {}
    for s in samples:
        for k, v in s.input_data.items():
            if isinstance(v, bool) and v:
                dist[k] = dist.get(k, 0) + 1
    n = max(1, len(samples))
    return {k: c / n for k, c in dist.items()}


def detect_drift(baseline_samples: list[TaskSample], recent_samples: list[TaskSample]) -> dict:
    """简版漂移检测：逐特征占比差的总平均 > 15% 告警。"""
    a, b = feature_distribution(baseline_samples), feature_distribution(recent_samples)
    keys = set(a) | set(b)
    diffs = {k: abs(a.get(k, 0.0) - b.get(k, 0.0)) for k in keys}
    avg_drift = sum(diffs.values()) / max(1, len(diffs))
    return {"avg_drift": round(avg_drift, 4), "alert": avg_drift > DRIFT_ALERT_RATIO,
            "per_feature": {k: round(v, 3) for k, v in sorted(diffs.items(), key=lambda kv: -kv[1])[:5]}}


def check_training_health(summary: dict, budget_usd: float) -> list[str]:
    """训练收尾健康检查（monitor 官员职责的简版）。"""
    alerts: list[str] = []
    if not summary.get("log_chain_valid", False):
        alerts.append("哈希链校验失败：日志可能被篡改")
    if summary.get("budget_exceeded"):
        alerts.append("预算超限熔断")
    if summary.get("final_pass_rate") is not None and summary["final_pass_rate"] < 0.8:
        alerts.append("最终通过率 < 80%：检查交付边界")
    if summary.get("total_cost_usd", 0) > budget_usd * 0.8:
        alerts.append("成本接近预算上限（>80%）")
    return alerts
