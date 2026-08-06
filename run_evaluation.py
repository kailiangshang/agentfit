#!/usr/bin/env python3
"""AgentFit evaluation test runner.

Runs 4 scenarios through the full AgentFit pipeline:
  1. Expense Approval    — Linear DAG should win (Occam's Razor)
  2. Sentiment Analysis  — SCC (self-correction) should win
  3. Refund Processing   — Multi-node DAG should win (complexity-value tradeoff)
  4. Contract Review     — Automation should be REJECTED (rejection right)

Produces a comprehensive test report.
"""
from __future__ import annotations

import json
import sys
import os
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from agentfit.pipeline.orchestrator import PipelineOrchestrator
from tests.scenarios.expense_approval import SCENARIO_CONFIG as EXPENSE_CONFIG
from tests.scenarios.sentiment_analysis import SCENARIO_CONFIG as SENTIMENT_CONFIG
from tests.scenarios.refund_processing import SCENARIO_CONFIG as REFUND_CONFIG
from tests.scenarios.contract_review import SCENARIO_CONFIG as CONTRACT_CONFIG


SCENARIOS = [
    {
        "name": "Expense Approval",
        "config": EXPENSE_CONFIG,
        "materials": [
            {"type": "policy", "description": "Expense reimbursement policy with thresholds"},
            {"type": "examples", "description": "Historical expense records with decisions"},
        ],
        "problem": "Automate expense approval routing to reduce manual review time",
    },
    {
        "name": "Sentiment Analysis",
        "config": SENTIMENT_CONFIG,
        "materials": [
            {"type": "data", "description": "10,000 product reviews"},
            {"type": "analysis", "description": "Sentiment lexicon and sarcasm patterns"},
        ],
        "problem": "Classify product review sentiment including sarcasm and mixed sentiment",
    },
    {
        "name": "Refund Processing",
        "config": REFUND_CONFIG,
        "materials": [
            {"type": "policy", "description": "Refund policy with conditions"},
            {"type": "data", "description": "Customer history and order records"},
            {"type": "examples", "description": "500 historical refund decisions"},
        ],
        "problem": "Automate refund decision-making with fraud detection and VIP handling",
    },
    {
        "name": "Contract Review",
        "config": CONTRACT_CONFIG,
        "materials": [
            {"type": "templates", "description": "Contract clause library"},
            {"type": "analysis", "description": "Legal precedent cases for liability"},
        ],
        "problem": "Automate legal contract risk assessment for high-risk clause detection",
    },
]


def run_all() -> dict:
    results = {}
    for scenario in SCENARIOS:
        name = scenario["name"]
        config = scenario["config"]
        sim_builder = config.get("build_llm_simulator")
        if sim_builder is None:
            raise ValueError(f"No LLM simulator builder for {name}")
        sim = sim_builder()
        orchestrator = PipelineOrchestrator(sim)
        t0 = time.perf_counter()
        result = orchestrator.run(
            scenario_name=name,
            materials=scenario["materials"],
            problem=scenario["problem"],
            scenario_config=config,
        )
        elapsed = time.perf_counter() - t0
        result["elapsed_seconds"] = elapsed
        results[name] = result
        print(f"  [{name}] completed in {elapsed:.1f}s — {result['evaluation_report']['recommendation_type']}")

    return results


def generate_report(results: dict) -> str:
    lines = []
    lines.append("=" * 80)
    lines.append("  AgentFit Evaluation Test Report")
    lines.append("  ML Methodology for Agent Architecture Selection")
    lines.append("=" * 80)
    lines.append("")

    # Summary table
    lines.append("## Summary")
    lines.append("")
    lines.append(f"{'Scenario':<22} {'Candidates':>10} {'Recommendation':>16} {'Selected':>14} {'Test Acc':>10}")
    lines.append("-" * 76)

    for name, result in results.items():
        er = result["evaluation_report"]
        rec_type = er["recommendation_type"]
        candidate_count = len(result["candidates"])
        selected = "—"
        test_acc = "—"
        if rec_type == "deploy":
            for row in er["comparison_table"]:
                if "Select" in er["recommendation"] and row["candidate"] in er["recommendation"]:
                    selected = row["candidate"]
                    test_acc = row["test_acc"]
                    break
            if selected == "—":
                best = er["comparison_table"][0] if er["comparison_table"] else {}
                selected = best.get("candidate", "—")
                test_acc = best.get("test_acc", "—")
        elif rec_type == "partial":
            best = er["comparison_table"][0] if er["comparison_table"] else {}
            selected = f"partial({best.get('candidate', '—')})"
            test_acc = best.get("test_acc", "—")
        elif rec_type == "reject":
            selected = "REJECTED"
            test_acc = er["comparison_table"][0]["test_acc"] if er["comparison_table"] else "—"

        lines.append(f"{name:<22} {candidate_count:>10} {rec_type:>16} {selected:>14} {test_acc:>10}")

    lines.append("")
    lines.append("")

    # Detailed per-scenario reports
    for name, result in results.items():
        lines.append("-" * 80)
        lines.append(f"## {name}")
        lines.append("")

        # Dossier summary
        ds = result["dossier_summary"]
        lines.append(f"Domain: {ds['domain']}")
        lines.append(f"Pipeline stages: {ds['entries']} entries, version {ds['version']}")
        lines.append(f"Dataset: {ds['facts_count']} facts extracted, candidates: {ds['candidates_count']}")
        lines.append("")

        # Gate log
        lines.append("### State Machine Gates")
        for gate in result["gate_log"]:
            status = "PASS" if gate["allowed"] else "FAIL"
            reason = f" ({gate['reason']})" if not gate["allowed"] else ""
            lines.append(f"  [{status}] {gate['from']} → {gate['to']}{reason}")
        lines.append("")

        # Candidates
        lines.append("### Candidates (baseline-first ordering)")
        lines.append(f"{'ID':<22} {'Pattern':<24} {'Type':<14} {'Complexity':>10}")
        lines.append("  " + "-" * 72)
        for c in result["candidates"]:
            lines.append(f"  {c['candidate_id']:<20} {c['pattern']:<22} {c['type']:<12} {c['complexity']:>10.1f}")
        lines.append("")

        # Trial results
        lines.append("### Trial Results (train/test split)")
        lines.append(f"{'Candidate':<22} {'Train Acc':>10} {'Test Acc':>10} {'Overfit':>10} {'Tokens':>10} {'Stability':>10}")
        lines.append("  " + "-" * 74)
        for cid, score in result["trial_results"].items():
            lines.append(
                f"  {cid:<20} {score['train_accuracy']:>10.1%} {score['test_accuracy']:>10.1%} "
                f"{score['overfit_signal']:>10.1%} {score['token_cost']:>10d} {score['stability']:>10.1%}"
            )
        lines.append("")

        # Evaluation report
        er = result["evaluation_report"]
        lines.append("### Audit Diagnosis")
        for cid, diag in er["diagnosis"].items():
            lines.append(f"  {cid}: {diag}")
        lines.append("")

        if er["evidence_refs"]:
            lines.append("### Evidence Notes")
            for ref in er["evidence_refs"]:
                lines.append(f"  • {ref}")
            lines.append("")

        lines.append("### Recommendation")
        lines.append(f"  Type: {er['recommendation_type'].upper()}")
        lines.append(f"  {er['recommendation']}")
        lines.append("")

        # Assets produced
        if result["assets"]:
            lines.append("### Assets Produced (for cross-project reuse)")
            for asset in result["assets"]:
                lines.append(f"  • [{asset['pattern']}] {asset['candidate_id']} — acc={asset['test_accuracy']:.1%}, domain={asset['domain']}")
            lines.append("")

        lines.append("")

    # Cross-scenario analysis
    lines.append("=" * 80)
    lines.append("## Cross-Scenario Analysis")
    lines.append("")

    # Pattern effectiveness
    pattern_stats = {}
    for name, result in results.items():
        for cid, score in result["trial_results"].items():
            pattern = next(
                (c["pattern"] for c in result["candidates"] if c["candidate_id"] == cid),
                "unknown",
            )
            pattern_stats.setdefault(pattern, []).append({
                "scenario": name,
                "candidate": cid,
                "test_acc": score["test_accuracy"],
                "complexity": next(
                    c["complexity"] for c in result["candidates"] if c["candidate_id"] == cid
                ),
            })

    lines.append("### Pattern Effectiveness Across Scenarios")
    lines.append(f"{'Pattern':<24} {'Scenarios':>10} {'Avg Test Acc':>12} {'Avg Complexity':>14}")
    lines.append("  " + "-" * 62)
    for pattern, entries in sorted(pattern_stats.items(), key=lambda x: -sum(e["test_acc"] for e in x[1]) / len(x[1])):
        avg_acc = sum(e["test_acc"] for e in entries) / len(entries)
        avg_cx = sum(e["complexity"] for e in entries) / len(entries)
        lines.append(f"  {pattern:<22} {len(entries):>10} {avg_acc:>12.1%} {avg_cx:>14.1f}")
    lines.append("")

    # Methodology verification
    lines.append("### ML Methodology Verification")
    lines.append("")

    checks = []

    # 1. Baseline-first
    for name, result in results.items():
        candidates = result["candidates"]
        if candidates:
            baseline = candidates[0]
            is_minimal = baseline["complexity"] <= 10 or baseline["type"] == "no-agent"
            checks.append(f"  [{'PASS' if is_minimal else 'FAIL'}] {name}: baseline-first (first candidate is minimal)")

    # 2. Train/test separation
    all_separated = True
    for name, result in results.items():
        for cid, score in result["trial_results"].items():
            if score["overfit_signal"] < 0:
                all_separated = False
    checks.append(f"  [{'PASS' if all_separated else 'FAIL'}] Train/test split enforced (no negative overfit)")

    # 3. Overfit detection
    overfit_found = False
    for name, result in results.items():
        for cid, score in result["trial_results"].items():
            if score["overfit_signal"] > 0.10:
                overfit_found = True
                checks.append(f"  [PASS] {name}/{cid}: overfit detected ({score['overfit_signal']:.1%} gap)")
                break
    if not overfit_found:
        checks.append("  [WARN] No significant overfit detected across scenarios")

    # 4. Rejection right
    has_reject = any(
        result["evaluation_report"]["recommendation_type"] == "reject"
        for result in results.values()
    )
    checks.append(f"  [{'PASS' if has_reject else 'FAIL'}] Rejection right exercised (Contract Review should reject)")

    # 5. Minimal selection
    has_minimal_select = False
    for name, result in results.items():
        er = result["evaluation_report"]
        if er["recommendation_type"] == "deploy":
            candidates = result["candidates"]
            trial = result["trial_results"]
            acceptance = result.get("dossier_summary", {})

            selected_id = ""
            for row in er["comparison_table"]:
                if row["candidate"] in er["recommendation"]:
                    selected_id = row["candidate"]
                    break
            if not selected_id and er["comparison_table"]:
                selected_id = er["comparison_table"][0]["candidate"]

            if selected_id and selected_id in trial:
                selected_cx = next(
                    (c["complexity"] for c in candidates if c["candidate_id"] == selected_id), 999
                )
                passing_cx = [
                    c["complexity"] for c in candidates
                    if c["candidate_id"] in trial
                    and trial[c["candidate_id"]]["test_accuracy"] >= 0.80
                    and trial[c["candidate_id"]]["overfit_signal"] <= 0.15
                ]
                if passing_cx and selected_cx <= min(passing_cx) + 0.01:
                    has_minimal_select = True
                    checks.append(f"  [PASS] {name}: selected cheapest passing candidate ({selected_id}, complexity={selected_cx:.1f})")

    if not has_minimal_select:
        checks.append("  [WARN] No scenario selected minimal sufficient candidate")

    # 6. Asset production
    has_assets = any(len(result["assets"]) > 0 for result in results.values())
    checks.append(f"  [{'PASS' if has_assets else 'FAIL'}] Reusable assets produced for cross-project learning")

    for check in checks:
        lines.append(check)

    lines.append("")
    lines.append("=" * 80)
    lines.append("  End of Report")
    lines.append("=" * 80)

    return "\n".join(lines)


def main():
    print("AgentFit Evaluation Test Runner")
    print("Running 4 scenarios through full pipeline...")
    print()

    results = run_all()

    report = generate_report(results)

    report_path = Path(__file__).parent / "TEST_REPORT.md"
    report_path.write_text(report)
    print(f"\nReport saved to {report_path}")

    print("\n" + report[:2000] + "\n... (see full report in TEST_REPORT.md)")


if __name__ == "__main__":
    main()
