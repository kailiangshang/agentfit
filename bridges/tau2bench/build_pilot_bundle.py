#!/usr/bin/env python3
"""从 τ²-bench telecom small=20 生成 pilot G0 冻结 bundle（阶段 B/C 用）。

- 四个互不重叠的 pilot manifest（确定性按下标分割，冻结前公开）
- 每个根因映射到语义原子/工具（能力清单覆盖全部 20 题根因）
- --smoke 模式：adaptation 收敛为预指定的 5 题（阶段 B 协议验证用，
  freeze 记录注明派生自同一 pilot G0）
"""
from __future__ import annotations

import argparse
import datetime
import json
from pathlib import Path

# 根因 → (feature, 原子id, 原子类型, 描述, 工具id, 工具描述, 需人工门禁)
ROOT_CAUSE_MAP = {
    "user_abroad_roaming_enabled_off": ("roaming_off_abroad", "toggle_roaming", "write", "开关漫游状态", "safe_toggle_roaming", "安全开关漫游", False),
    "user_abroad_roaming_disabled_on": ("roaming_on_abroad", "toggle_roaming", "write", "开关漫游状态", "safe_toggle_roaming", "安全开关漫游", False),
    "user_abroad_roaming_disabled_off": ("roaming_on_abroad", "toggle_roaming", "write", "开关漫游状态", "safe_toggle_roaming", "安全开关漫游", False),
    "data_mode_off": ("data_mode_off", "toggle_data_mode", "write", "切换移动数据开关", "safe_toggle_data_mode", "安全切换移动数据", False),
    "data_saver_mode_on": ("data_saver", "disable_data_saver", "write", "关闭省流模式", "safe_disable_data_saver", "安全关闭省流模式", False),
    "bad_network_preference": ("bad_network", "reset_network_preference", "write", "重置网络偏好设置", "safe_reset_network_preference", "安全重置网络偏好", False),
    "bad_vpn": ("bad_vpn", "reset_vpn", "write", "重置 VPN 配置", "safe_reset_vpn", "安全重置 VPN", False),
    "data_usage_exceeded": ("data_exceeded", "top_up_data", "write", "流量加油包办理", "safe_top_up_data", "安全办理流量加油包", True),
    "airplane_mode_on": ("airplane", "reset_airplane_mode", "write", "关闭飞行模式", "safe_reset_airplane_mode", "安全重置飞行模式", False),
    "unseat_sim_card": ("sim_unseated", "reseat_sim", "write", "重新插拔 SIM 卡", "safe_reseat_sim", "安全重插 SIM", False),
    "lock_sim_card_pin": ("sim_locked", "escalate_human", "human", "升级人工处理", "safe_escalate_human", "升级人工（SIM PIN 解锁需 PUK）", False),
    "break_apn_settings": ("apn_broken", "reset_apn", "write", "重置 APN 接入点", "safe_reset_apn", "安全重置 APN", False),
    "overdue_bill_suspension": ("bill_overdue", "process_bill_payment", "write", "处理欠费缴纳", "safe_process_bill_payment", "安全处理缴费（金额门禁）", True),
    "contract_end_suspension": ("contract_ended", "escalate_human", "human", "升级人工处理", "safe_escalate_human", "升级人工（合同变更需商务确认）", False),
    "bad_wifi_calling": ("wifi_calling_bad", "reset_wifi_calling", "write", "重置 WiFi 通话配置", "safe_reset_wifi_calling", "安全重置 WiFi 通话", False),
    "break_apn_mms_setting": ("mms_broken", "reset_apn", "write", "重置 APN 接入点", "safe_reset_apn", "安全重置 APN", False),
    "break_app_sms_permission": ("app_sms_denied", "fix_app_permissions", "write", "修复应用权限", "safe_fix_app_permissions", "安全修复应用权限", False),
    "break_app_storage_permission": ("app_storage_denied", "fix_app_permissions", "write", "修复应用权限", "safe_fix_app_permissions", "安全修复应用权限", False),
    "break_app_both_permissions": ("app_both_denied", "fix_app_permissions", "write", "修复应用权限", "safe_fix_app_permissions", "安全修复应用权限", False),
}

# 确定性四集合分割（下标 → purpose；冻结前公开，写入 bundle 注释性字段）
PILOT_SPLIT = {
    "adaptation": [0, 3, 4, 5, 8, 9, 11, 16],
    "validation": [1, 6, 12, 17],
    "sealed_holdout": [7, 10, 14, 18],
    "stress_and_failure": [2, 13, 15, 19],
}
# 阶段 B 预指定的 smoke 5 题（来自 adaptation）
SMOKE_ADAPTATION = [0, 4, 5, 8, 9]


def build(tasks_path: Path, smoke: bool) -> dict:
    data = json.loads(tasks_path.read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else data.get("tasks", [])
    assert len(items) == 20, f"expected small=20, got {len(items)}"

    atoms, tools = {}, {}
    for cause, (feature, atom_id, atom_type, atom_desc, tool_id, tool_desc, gate) in ROOT_CAUSE_MAP.items():
        if atom_id not in atoms:
            atoms[atom_id] = {"id": atom_id, "type": atom_type, "description": atom_desc,
                              "domain": "telecom_network_api", "frozen": True}  # L1 基础设施
        if tool_id not in tools:
            tool = {"id": tool_id, "wraps": [atom_id], "description": tool_desc,
                    "capability_type": "review_routing" if gate else "safe_wrapper"}
            if gate:
                tool["human_gate"] = {"condition": "amount > 0", "reviewer": "finance_team", "on_timeout": "block"}
            tools[tool_id] = tool

    runbook = {feature: f"When {feature} is the diagnosed root cause, use the approved {tool_id} capability."
               for cause, (feature, _, _, _, tool_id, _, _) in ROOT_CAUSE_MAP.items()}
    materials = [
        {"id": "telecom-pilot-runbook", "kind": "procedure", "content": runbook,
         "metadata": {"source": "tau2-bench telecom tasks_small projection"}},
        {"id": "telecom-pilot-evaluation-policy", "kind": "policy",
         "content": {"pass": "executed actions match the expected semantic action for the diagnosed root cause",
                     "fail": "wrong or missing action"},
         "metadata": {"source": "tau2-bench telecom evaluation semantics (semantic projection)"}},
    ]

    purpose_of = {}
    for purpose, indices in PILOT_SPLIT.items():
        for idx in indices:
            purpose_of[idx] = purpose

    tasks = []
    for idx, item in enumerate(items):
        causes = item["id"].split("]")[1].split("[PERSONA")[0].split("|")
        features = {}
        actions = []
        for cause in causes:
            feature, _, _, _, tool_id, _, _ = ROOT_CAUSE_MAP[cause]
            features[feature] = True
            if tool_id not in [a["tool"] for a in actions]:
                actions.append({"tool": tool_id, "params": {}})
        persona = item["id"].split("[PERSONA")[1].rstrip("]") if "[PERSONA" in item["id"] else "None"
        tasks.append({
            "id": f"tau2-small-{idx:02d}",
            "purpose": purpose_of[idx],
            "observation_ids": ["telecom-pilot-runbook", "telecom-pilot-evaluation-policy"],
            "input_data": features,
            "expected": {"actions": actions, "outcome": {}},
            "requires_human": any(t["tool"] == "safe_escalate_human" for t in actions),
            "complexity": "compound" if len(causes) > 1 else "simple",
            "metadata": {"tau2_task_id": item["id"], "persona": persona},
        })

    if smoke:
        keep = {f"tau2-small-{i:02d}" for i in SMOKE_ADAPTATION}
        tasks = [t for t in tasks if t["purpose"] != "adaptation" or t["id"] in keep]

    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    return {
        "scenario": "telecom-pilot-smoke" if smoke else "telecom-pilot",
        "materials": materials,
        "capabilities": {"atoms": list(atoms.values()), "tools": list(tools.values())},
        "objective": {"criteria": [
            {"purpose": p, "min_pass_rate": 0.6, "max_errors": 2, "max_cost_usd": 2.0, "max_risk_events": 0}
            for p in ("adaptation", "validation", "sealed_holdout", "stress_and_failure")
        ], "max_total_evaluation_cost_usd": 8.0},
        "tasks": tasks,
        "freeze": {"reviewer": "human-owner", "approved": True, "decided_at": now,
                   "reason": ("pilot G0 (stage-B smoke derivation): four non-overlapping sets from "
                              "tau2 telecom small=20, deterministic index split, smoke adaptation="
                              + ",".join(f"tau2-small-{i:02d}" for i in SMOKE_ADAPTATION))},
        "training": {"batch_size": 5 if smoke else 4, "max_epochs": 3},
        "taxonomy": {
            "customs": [{"name": "telecom_network_api", "layer": "L1_domain", "parent": "external_system",
                         "label": "电信网管接口", "description": "运营商网元操作与查询接口族"}],
            "selected_l1_domains": [], "selected_l2_capability_types": [],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", default="../tau2-bench/data/tau2/domains/telecom/tasks_small.json")
    parser.add_argument("--output", required=True)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    bundle = build(Path(args.tasks), smoke=args.smoke)
    Path(args.output).write_text(json.dumps(bundle, ensure_ascii=False, indent=1), encoding="utf-8")
    purposes = {}
    for t in bundle["tasks"]:
        purposes[t["purpose"]] = purposes.get(t["purpose"], 0) + 1
    print(json.dumps({"output": args.output, "tasks": len(bundle["tasks"]),
                      "by_purpose": purposes, "smoke": args.smoke}, ensure_ascii=False))


if __name__ == "__main__":
    main()
