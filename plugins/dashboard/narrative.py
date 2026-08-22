"""训练完成后调 LLM 生成人话叙事（dashboard 可读性增强）。

非阻塞：LLM 失败时 dashboard 正常呈现（无叙事区）。
叙事存储在 narrative.json，不进哈希链（它是呈现辅助不是证据）。
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from agentfit.store.run_store import RunStore

NARRATIVE_PROMPT = """你是 AgentFit 的 Steward（交互官），面向非技术用户解释这次训练发生了什么。
基于以下训练数据，用中文写一段 200 字以内的叙事，包含：
1. 初始方案有多少能力，第一批测试结果如何
2. 发现了什么问题（用日常语言，不说"L3 missing_rule"）
3. 训练做了什么修改（"维护新增了一条路由规则"而不是"L3 add rule_xxx"）
4. 最终结果和下一步建议

训练数据：
{data}

只输出叙事文本，不要标题、格式或代码。"""


def _http_chat(prompt: str, model: str = "deepseek-v4-flash") -> str | None:
    """最小直连调用（不引入 SDK 依赖）。密钥只从环境读取。"""
    api_key = os.environ.get("AGENTTEAMS_LLM_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        return None
    import urllib.request
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 500,
    }).encode()
    req = urllib.request.Request(
        "https://api.deepseek.com/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {api_key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read())
        return body["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


def generate_narrative(run_dir: str | Path) -> str | None:
    """训练收尾仪制的一部分：LLM 生成叙事。"""
    store = RunStore(run_dir)
    summary = store.load_json("summary.json") if (store.root / "summary.json").exists() else {}
    if not summary:
        return None

    # 组装 LLM 输入（只给汇总级数据，不给逐样本明细防泄漏）
    data = {
        "epochs_run": summary.get("epochs_run"),
        "final_pass_rate": summary.get("final_pass_rate"),
        "stop_reason": summary.get("stop_reason"),
        "validation_series": summary.get("validation_series"),
        "transactions": [
            {"origin": c.get("origin"), "semantic": c.get("semantic")}
            for t in (summary.get("transactions_committed") or [])
            for c in (t.get("changes") or [])
        ][:10],
        "advisories": [
            item.get("semantic")
            for item in (summary.get("optimization_suggestions") or [])
        ][:5],
    }
    narrative = _http_chat(NARRATIVE_PROMPT.format(data=json.dumps(data, ensure_ascii=False)))
    if narrative:
        (store.root / "narrative.json").write_text(
            json.dumps({"narrative": narrative, "model": "deepseek-v4-flash"},
                       ensure_ascii=False, indent=1),
            encoding="utf-8",
        )
    return narrative
