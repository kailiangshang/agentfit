#!/usr/bin/env python3
"""
AgentFit airline batch runner。
关键: 注入从 retail 提炼的 Skill (SK-GEN-001/002)，验证跨场景复用。

Usage: python3 batch_runner.py <task_ids> [batch_name]
"""

import json
import re
import subprocess
import sys
import time
from pathlib import Path
from collections import Counter

RUN_ROOT = Path(__file__).resolve().parent
TAU3_DATA = Path("/Users/kaiiangs/Desktop/open-source-project/agentfit-labs/tau2-bench/data/tau2/domains/airline")
TOOL_PATH = RUN_ROOT / "airline_tools_db.py"
POLICY_PATH = RUN_ROOT / "source/policy.md"
TASKS_PATH = RUN_ROOT / "source/tasks.json"
BATCH_DIR = RUN_ROOT / "batch-runs"
BATCH_DIR.mkdir(exist_ok=True)


def load_tasks():
    return json.loads(TASKS_PATH.read_text())


def build_prompt(task, policy, tool_path):
    scenario = task["user_scenario"]["instructions"]
    scenario_text = f"""{scenario.get('task_instructions', '')}
{scenario.get('known_info', '')}
Reason: {scenario.get('reason_for_call', '')}"""

    return f"""你是 airline 客服 agent。严格按以下 policy 处理用户请求。

POLICY（airline agent policy）：
{policy}

策略知识（从 retail 场景提炼，验证跨场景复用）:

1. 首选路径阻塞处理 [SK-GEN-001]:
   当用户首选的操作(book/cancel/update)无法满足时(如航班满员、时间冲突):
   - 不要直接放弃或编造信息
   - 回溯到用户目标层面: 用户要的可能是"到达目的地"而非"特定航班"
   - 检查替代操作能否满足用户目标
   - 告诉用户首选不可用,提出替代方案,询问是否接受

2. 用户意图优先级 [SK-GEN-002]:
   当用户表达了条件偏好或fallback指令:
   - 严格遵守用户指定的优先级
   - 先检查首选是否可行,首选不可行才走fallback
   - 绝不自行假设或替代用户的决策

工具调用方式: python3 {tool_path} <tool_name> '<json_args>'

可用工具:
- find_user(通用): 支持 user_id 或 name 查找
- get_user_details: 查用户详情
- get_reservation_details: 查预订详情
- search_direct_flight: 搜索直飞航班
- book_reservation: 预订
- cancel_reservation: 取消预订
- update_reservation_flights: 改签
- update_reservation_baggages: 改行李
- update_reservation_passengers: 改乘客
- calculate: 计算
- transfer_to_human_agents: 转人工

规则:
- 每次只调一个工具
- 不要停下来等待用户回复! 假设用户已确认(yes),直接继续执行下一步
- 所有操作必须在本次对话中用工具调用完成,不要只输出文本建议
- 如果policy要求用户确认,假设用户已确认并立即执行
- 如果需要多轮协商,按最理想路径一次性执行
- 不要编造信息
- 最后必须调用最终操作工具,不能停在文本回复

用户场景:
{scenario_text}

执行完整流程,每一步报告工具调用和结果。
最后用一行总结: EXEC_RESULT: <关键操作和参数>"""


def run_one_task(task_id, task, policy):
    prompt = build_prompt(task, policy, str(TOOL_PATH))
    expected_actions = task["evaluation_criteria"]["actions"]
    expected_tools = [a["name"] for a in expected_actions]

    print(f"\n{'=' * 60}")
    print(f"  Task {task_id} ({len(expected_tools)} expected actions)")
    reason = task['user_scenario']['instructions'].get('reason_for_call', '')[:60]
    print(f"  {reason}")
    print(f"{'=' * 60}")

    start = time.time()
    try:
        result = subprocess.run(
            ["opencode", "run", prompt, "-m", "deepseek/deepseek-chat"],
            capture_output=True, text=True, timeout=300,
            cwd=str(RUN_ROOT.parents[3]),
        )
        elapsed = time.time() - start
        output = result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        elapsed = 300
        output = "TIMEOUT"
    except Exception as e:
        elapsed = time.time() - start
        output = f"ERROR: {e}"

    raw_file = BATCH_DIR / f"task-{task_id}-raw.txt"
    raw_file.write_text(output)

    # 评估: 通用工具名匹配
    unique_expected = list(set(expected_tools))
    found = []
    for exp in unique_expected:
        if exp in output:
            found.append(exp)
            continue
        if exp.startswith("find_user") and "find_user" in output:
            found.append(exp)
            continue
        if exp.startswith("get_user") and "get_user" in output:
            found.append(exp)
            continue
        if exp.startswith("update_reservation") and "update_reservation" in output:
            found.append(exp)
            continue

    missing = [t for t in unique_expected if t not in found]
    match_rate = len(found) / len(unique_expected) if unique_expected else 1.0
    actual_calls = re.findall(r"airline_tools_db\.py\s+(\w+)", output)
    exec_match = re.search(r"EXEC_RESULT:\s*(.+)", output)

    # 链路诊断
    perceive = 1.0
    knowledge = 1.0
    reasoning = 1.0
    act = 1.0
    issues = []
    breakpoint_name = None
    structural = False

    if "error" in output.lower() and ("not found" in output.lower() or "必须先验证" in output):
        perceive = 0.5
        issues.append("工具调用出错或约束拒绝")
        breakpoint_name = "execution_perceive"

    skill_keywords = ["首选", "替代", "fallback", "不可用", "回溯", "替代方案"]
    skill_used = any(kw in output for kw in skill_keywords)
    if missing and not skill_used:
        knowledge = 0.3
        issues.append("失败时未使用策略知识")
        if not breakpoint_name:
            breakpoint_name = "knowledge_guide"
    elif missing and skill_used:
        knowledge = 0.6

    if len(missing) > 0:
        reasoning = 0.4
        issues.append(f"缺少{len(missing)}个期望工具调用")

    if not exec_match:
        act = 0.4
        issues.append("未输出EXEC_RESULT")

    if len(actual_calls) > 15:
        structural = True
        issues.append("工具调用次数过多(>15)")
        breakpoint_name = "structural:context_overload"

    record = {
        "task_id": task_id,
        "expected_actions": len(expected_tools),
        "unique_expected": len(unique_expected),
        "found": len(found),
        "match_rate": match_rate,
        "matched": found,
        "missing": missing,
        "actual_tool_calls": actual_calls,
        "exec_result": exec_match.group(1).strip() if exec_match else None,
        "elapsed": round(elapsed, 1),
        "status": "COMPLETED" if output != "TIMEOUT" else "TIMEOUT",
        "linkage": {
            "execution_perceive": perceive,
            "knowledge_guide": knowledge,
            "reasoning_understand": reasoning,
            "execution_act": act,
            "issues": issues,
            "primary_breakpoint": breakpoint_name,
            "structural_limitation": structural,
        }
    }

    print(f"  match: {len(found)}/{len(unique_expected)} ({match_rate:.0%})")
    print(f"  matched: {found}")
    if missing:
        print(f"  missing: {missing}")
    print(f"  elapsed: {elapsed:.1f}s")
    print(f"  linkage: perceive={perceive:.1f} knowledge={knowledge:.1f} reasoning={reasoning:.1f} act={act:.1f}")
    if breakpoint_name:
        print(f"  breakpoint: {breakpoint_name}")
    if structural:
        print(f"  ⚠ structural limitation!")

    return record


def main():
    task_ids = sys.argv[1].split(",") if len(sys.argv) > 1 else ["5", "9", "2", "4"]
    batch_name = sys.argv[2] if len(sys.argv) > 2 else f"airline-batch-{int(time.time())}"

    tasks = load_tasks()
    policy = POLICY_PATH.read_text()

    print(f"{'=' * 60}")
    print(f"  AgentFit Airline Batch — {batch_name}")
    print(f"  Tasks: {task_ids}")
    print(f"  Model: deepseek/deepseek-chat")
    print(f"  Candidate: C1 + retail Skill (SK-GEN-001/002) 跨场景复用验证")
    print(f"{'=' * 60}")

    all_results = []
    for tid in task_ids:
        tid = tid.strip()
        task = next((t for t in tasks if str(t["id"]) == tid), None)
        if not task:
            print(f"  task {tid} not found, skip")
            continue
        record = run_one_task(tid, task, policy)
        all_results.append(record)

    # Batch 汇总
    print(f"\n{'=' * 60}")
    print(f"  Batch 链路健康度汇总")
    print(f"{'=' * 60}")
    print(f"{'task':>5}  {'perceive':>8}  {'knowledge':>9}  {'reasoning':>9}  {'act':>5}  {'acc':>5}  breakpoint")
    print("-" * 80)
    for r in all_results:
        d = r["linkage"]
        bp = d["primary_breakpoint"] or "—"
        s = "⚠STRUCT" if d["structural_limitation"] else ""
        print(f"{r['task_id']:>5}  {d['execution_perceive']:>8.1f}  {d['knowledge_guide']:>9.1f}  {d['reasoning_understand']:>9.1f}  {d['execution_act']:>5.1f}  {r['match_rate']:>4.0%}  {bp} {s}")

    avg = sum(r["match_rate"] for r in all_results) / len(all_results)
    full = sum(1 for r in all_results if r["match_rate"] == 1.0)
    any_struct = any(r["linkage"]["structural_limitation"] for r in all_results)

    print(f"\n  场景 acc: {avg:.0%}")
    print(f"  全匹配: {full}/{len(all_results)}")
    print(f"  结构性限制: {'YES ⚠' if any_struct else 'NO'}")

    breakpoints = [r["linkage"]["primary_breakpoint"] for r in all_results if r["linkage"]["primary_breakpoint"]]
    bp_counts = Counter(breakpoints)
    if bp_counts:
        print(f"\n  断点分布:")
        for bp, count in bp_counts.most_common():
            print(f"    {bp}: {count}次")

    summary = {
        "batch_name": batch_name,
        "domain": "airline",
        "task_ids": task_ids,
        "skill_injected": ["SK-GEN-001", "SK-GEN-002"],
        "avg_acc": avg,
        "full_match": full,
        "has_structural_limitation": any_struct,
        "breakpoint_distribution": dict(bp_counts),
        "results": all_results,
    }
    summary_file = BATCH_DIR / f"{batch_name}-summary.json"
    summary_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\n  结果已保存: {summary_file.name}")


if __name__ == "__main__":
    main()
