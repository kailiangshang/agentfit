#!/usr/bin/env python3
"""
AgentFit batch runner v2 — 整合框架版。
跑一批 task → 收集结果 → 链路诊断 → 输出归因。

Usage: python3 batch_runner.py <task_ids> [batch_name]
Example: python3 batch_runner.py "0,1,5,10" batch1
"""

import json
import re
import subprocess
import sys
import time
from pathlib import Path

RUN_ROOT = Path(__file__).resolve().parent
TAU3_DATA = Path("/Users/kaiiangs/Desktop/open-source-project/agentfit-labs/tau2-bench/data/tau2/domains/retail")
TOOL_PATH = RUN_ROOT / "retail_tools_db.py"
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

    return f"""你是 retail 客服 agent。严格按以下 policy 处理用户请求。

POLICY（retail agent policy）：
{policy}

策略知识（遇到以下情况时参考）:

1. 首选路径阻塞处理:
   当用户首选的操作(exchange/modify)无法满足时(如目标变体不存在):
   - 不要直接放弃或编造信息
   - 回溯到用户目标层面: 用户要的可能是"能用的东西"而非"特定型号"
   - 检查替代操作(return/cancel+重下)能否满足用户目标
   - 告诉用户首选不可用,提出替代方案,询问是否接受

2. 用户意图优先级:
   当用户表达了条件偏好或fallback指令:
   - 严格遵守用户指定的优先级
   - 先检查首选是否存在,首选不存在才走fallback
   - 绝不自行假设或替代用户的决策

3. 多变体匹配方法:
   当需要从多个产品变体中匹配用户需求:
   - 先查看 properties_summary 了解所有可选属性范围
   - 按用户约束缩小候选范围
   - 在候选内做精确匹配
   - 如果无精确匹配,检查用户是否有fallback指令

工具调用方式: python3 {tool_path} <tool_name> '<json_args>'

可用工具:
- find_user(通用): 支持 {{email}} 或 {{first_name,last_name,zip}} 或 {{user_id}}
- get_order_details: 查订单
- get_product_details: 查产品变体(返回含properties_summary)
- get_user_details: 查用户详情
- exchange_delivered_order_items: 换货
- cancel_pending_order: 取消订单
- modify_pending_order: 修改订单
- return_delivered_order: 退货
- transfer_to_human_agents: 转人工

规则:
- 每次只调一个工具
- 不要停下来等待用户回复! 假设用户已确认(yes),直接继续执行下一步
- 所有操作必须在本次对话中用工具调用完成,不要只输出文本建议
- 如果policy要求用户确认,假设用户已确认并立即执行
- exchange 只能调一次,必须把所有要换的物品收集齐再调
- 如果需要多轮协商(如用户有分层fallback),按最理想路径一次性执行
- 不要编造信息
- 最后必须调用最终操作工具(exchange/cancel/return/transfer),不能停在文本回复

用户场景:
{scenario_text}

执行完整流程,每一步报告工具调用和结果及决策理由。
最后用一行总结: EXEC_RESULT: <关键操作和参数>"""


def run_one_task(task_id, task, policy):
    prompt = build_prompt(task, policy, str(TOOL_PATH))
    expected_actions = task["evaluation_criteria"]["actions"]
    expected_tools = [a["name"] for a in expected_actions]

    print(f"\n{'=' * 60}")
    print(f"  Task {task_id} ({len(expected_tools)} expected actions)")
    print(f"  {task['user_scenario']['instructions'].get('reason_for_call', '')[:60]}")
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

    # 保存原始输出
    raw_file = BATCH_DIR / f"task-{task_id}-v2-raw.txt"
    raw_file.write_text(output)

    # 评估: 工具名匹配
    found_tools = []
    for name in set(expected_tools):
        if name in output:
            found_tools.append(name)
    # 也检查通用名 find_user
    if "find_user" in output and "find_user_id_by_name_zip" in expected_tools and "find_user_id_by_name_zip" not in found_tools:
        found_tools.append("find_user_id_by_name_zip")

    unique_expected = list(set(expected_tools))
    match_rate = len(found_tools) / len(unique_expected) if unique_expected else 1.0

    # 提取实际工具调用
    tool_calls = re.findall(r"retail_tools_db\.py\s+(\w+)", output)
    # 也匹配 opencode 实际执行的工具调用
    exec_match = re.search(r"EXEC_RESULT:\s*(.+)", output)

    # 链路诊断
    diagnosis = diagnose_linkage(output, expected_tools, found_tools, tool_calls, task_id)

    record = {
        "task_id": task_id,
        "expected_actions": len(expected_tools),
        "unique_expected_tools": len(unique_expected),
        "found_tools": len(found_tools),
        "match_rate": match_rate,
        "matched": found_tools,
        "missing": [t for t in unique_expected if t not in found_tools],
        "actual_tool_calls": tool_calls,
        "exec_result": exec_match.group(1).strip() if exec_match else None,
        "elapsed": round(elapsed, 1),
        "status": "COMPLETED" if output != "TIMEOUT" else "TIMEOUT",
        "linkage_diagnosis": diagnosis,
    }

    print(f"  match: {len(found_tools)}/{len(unique_expected)} ({match_rate:.0%})")
    print(f"  matched: {found_tools}")
    if record["missing"]:
        print(f"  missing: {record['missing']}")
    print(f"  elapsed: {elapsed:.1f}s")
    diag = diagnosis
    print(f"  linkage: perceive={diag['execution_perceive']:.1f} knowledge={diag['knowledge_guide']:.1f} reasoning={diag['reasoning_understand']:.1f} act={diag['execution_act']:.1f}")
    if diag["primary_breakpoint"]:
        print(f"  breakpoint: {diag['primary_breakpoint']}")
    if diag["structural_limitation"]:
        print(f"  ⚠ structural limitation detected!")

    return record


def diagnose_linkage(output, expected_tools, found_tools, actual_calls, task_id):
    """对输出做链路健康度诊断"""
    perceive = 1.0
    knowledge = 1.0
    reasoning = 1.0
    act = 1.0
    issues = []
    breakpoint = None
    structural = False

    # 执行层·感知: 工具调用成功了吗?
    if "error" in output.lower() and "User not found" in output:
        perceive = 0.3
        issues.append("用户查找失败")
        breakpoint = "execution_perceive"
    elif "error" in output.lower() and "tool" in output.lower():
        perceive = 0.5
        issues.append("工具调用出错")

    # 知识层·指导: agent 用了策略知识吗?
    knowledge_keywords = ["首选", "替代", "fallback", "不可用", "回溯", "退化", "return", "退货"]
    knowledge_used = any(kw in output for kw in knowledge_keywords)
    # 如果有失败但没提到任何策略知识
    missing = [t for t in set(expected_tools) if t not in found_tools]
    if missing and not knowledge_used:
        knowledge = 0.2
        issues.append("失败时未使用任何策略知识")
        if not breakpoint:
            breakpoint = "knowledge_guide"
    elif missing and knowledge_used:
        knowledge = 0.6
        issues.append("使用了策略知识但仍未完全解决")

    # 推理层·理解: 做了正确的推理吗?
    if len(missing) > 0:
        reasoning = 0.4
        issues.append(f"缺少{len(missing)}个期望工具调用")
    if "不知道" in output or "无法" in output or "I cannot" in output:
        reasoning = min(reasoning, 0.3)
        issues.append("agent 表示无法处理")
        if not breakpoint:
            breakpoint = "reasoning_understand"

    # 执行层·动作: 最终执行了吗?
    exec_match = re.search(r"EXEC_RESULT:\s*(.+)", output)
    if not exec_match:
        act = 0.3
        issues.append("未输出EXEC_RESULT总结")
    elif len(missing) > 0:
        act = 0.5

    # 结构性限制检测
    if len(actual_calls) > 12:
        structural = True
        issues.append("工具调用次数过多(>12)——可能上下文过载")
        breakpoint = "structural:context_overload"
    if "遗忘" in output or "忘记" in output or "forgot" in output.lower():
        structural = True
        issues.append("agent 明确表示遗忘——上下文过载信号")
        breakpoint = "structural:context_overload"

    return {
        "execution_perceive": perceive,
        "knowledge_guide": knowledge,
        "reasoning_understand": reasoning,
        "execution_act": act,
        "issues": issues,
        "primary_breakpoint": breakpoint,
        "structural_limitation": structural,
    }


def main():
    task_ids = sys.argv[1].split(",") if len(sys.argv) > 1 else ["0", "1", "5", "10"]
    batch_name = sys.argv[2] if len(sys.argv) > 2 else f"batch-{int(time.time())}"

    tasks = load_tasks()
    policy = POLICY_PATH.read_text()

    print(f"{'=' * 60}")
    print(f"  AgentFit Batch Runner — {batch_name}")
    print(f"  Tasks: {task_ids}")
    print(f"  Model: deepseek/deepseek-chat")
    print(f"  Candidate: C1-single-agent + skill injection + v2 tools")
    print(f"{'=' * 60}")

    all_results = []
    for tid in task_ids:
        tid = tid.strip()
        task = next((t for t in tasks if t["id"] == tid), None)
        if not task:
            print(f"  task {tid} not found, skip")
            continue
        record = run_one_task(tid, task, policy)
        all_results.append(record)

    # Batch 级链路统计
    print(f"\n{'=' * 60}")
    print(f"  Batch 链路健康度汇总")
    print(f"{'=' * 60}")
    print(f"{'task':>5}  {'perceive':>8}  {'knowledge':>9}  {'reasoning':>9}  {'act':>5}  {'match':>5}  breakpoint")
    print("-" * 80)
    for r in all_results:
        d = r["linkage_diagnosis"]
        bp = d["primary_breakpoint"] or "—"
        structural = "⚠STRUCT" if d["structural_limitation"] else ""
        print(f"{r['task_id']:>5}  {d['execution_perceive']:>8.1f}  {d['knowledge_guide']:>9.1f}  {d['reasoning_understand']:>9.1f}  {d['execution_act']:>5.1f}  {r['match_rate']:>4.0%}  {bp} {structural}")

    avg_match = sum(r["match_rate"] for r in all_results) / len(all_results)
    full_match = sum(1 for r in all_results if r["match_rate"] == 1.0)
    any_structural = any(r["linkage_diagnosis"]["structural_limitation"] for r in all_results)

    print(f"\n  平均 match rate: {avg_match:.0%}")
    print(f"  全匹配: {full_match}/{len(all_results)}")
    print(f"  结构性限制: {'YES ⚠ → 考虑C2' if any_structural else 'NO → 继续内循环'}")

    # 链路系统性断点分析
    all_breakpoints = [r["linkage_diagnosis"]["primary_breakpoint"] for r in all_results if r["linkage_diagnosis"]["primary_breakpoint"]]
    from collections import Counter
    bp_counts = Counter(all_breakpoints)
    print(f"\n  断点分布:")
    for bp, count in bp_counts.most_common():
        print(f"    {bp}: {count}次")

    # 保存
    summary = {
        "batch_name": batch_name,
        "task_ids": task_ids,
        "candidate": "C1+skills+v2tools",
        "avg_match_rate": avg_match,
        "full_match_count": full_match,
        "has_structural_limitation": any_structural,
        "breakpoint_distribution": dict(bp_counts),
        "results": all_results,
    }
    summary_file = BATCH_DIR / f"{batch_name}-summary.json"
    summary_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\n  结果已保存: {summary_file.name}")


if __name__ == "__main__":
    main()
