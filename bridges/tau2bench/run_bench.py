#!/usr/bin/env python3
"""桥接：τ²-bench 批量执行（子进程方式，库零依赖）。

用法：
  python bridges/tau2bench/run_bench.py --domain telecom --num-tasks 50 \\
      --agent-llm deepseek/deepseek-chat --output results.json
前提：本机已 clone tau2-bench 并 uv sync（见 docs/test-scenario.md §三）。
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tau2-dir", default="../tau2-bench", help="tau2-bench 仓库位置")
    parser.add_argument("--domain", default="telecom")
    parser.add_argument("--num-tasks", type=int, default=50)
    parser.add_argument("--agent-llm", default="deepseek/deepseek-chat")
    parser.add_argument("--user-llm", default="deepseek/deepseek-chat")
    parser.add_argument("--output", default="tau2_results.json")
    args = parser.parse_args()

    tau2 = Path(args.tau2_dir)
    if not tau2.exists():
        raise SystemExit(f"tau2-bench 不存在于 {tau2}（git clone https://github.com/sierra-research/tau2-bench）")
    venv_bin = tau2 / ".venv" / "bin" / "tau2"
    cmd = [str(venv_bin) if venv_bin.exists() else shutil.which("tau2") or "tau2",
           "run", "--domain", args.domain,
           "--agent-llm", args.agent_llm, "--user-llm", args.user_llm,
           "--num-trials", "1", "--num-tasks", str(args.num_tasks)]
    print("exec:", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=tau2, capture_output=True, text=True)
    Path(args.output).write_text(json.dumps(
        {"returncode": proc.returncode, "stdout": proc.stdout[-20000:], "stderr": proc.stderr[-20000:]},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"raw output → {args.output}（returncode={proc.returncode}）")


if __name__ == "__main__":
    main()
