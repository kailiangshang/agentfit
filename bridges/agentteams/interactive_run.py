#!/usr/bin/env python3
"""交互式训练入口（AgentTeams 真实执行）。

用法：
  PYTHONPATH=src:. .venv/bin/python bridges/agentteams/interactive_run.py \
    --bundle output/pilot/telecom-pilot-bundle.json \
    --output output/pilot/interactive-001
"""
import sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))

from bridges.agentteams.interactive import main

if __name__ == "__main__":
    main()
