#!/usr/bin/env python3
"""Fail closed until the τ² runner uses the direct DeepSeek official API bridge.

The pinned upstream τ²-bench model runner uses a stock third-party LLM client.
AgentFit's current execution contract requires the user-owned DeepSeek official
API and ``deepseek-v4-flash`` without that client or a model-routing gateway.
Keep this stable entrypoint blocked until the direct bridge is implemented and
verified; existing result files remain importable through
``results_to_runstore.py``.
"""
from __future__ import annotations


def main() -> None:
    raise SystemExit(
        "τ² stock LLM runner 已禁用：DeepSeek 官网 API direct adapter 尚未实现；"
        "不得启动 smoke 或正式样本"
    )


if __name__ == "__main__":
    main()
