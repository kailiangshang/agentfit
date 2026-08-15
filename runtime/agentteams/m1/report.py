#!/usr/bin/env python3
"""Self-contained HTML round report (observation plane).

Renders one run from its own artifacts: role swimlane from the
conversation trace, metrics from usage deltas, gate/audit checks, and
the ledger chain status. No external assets, no server - the report is
a Dossier artifact, not a product UI.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ledger import compute_metrics, load_ledger, verify_chain  # noqa: E402

REPORT_SCHEMA = "agentfit.round-report/v1"

STYLE = """
body{font-family:'Noto Sans CJK SC',Arial,sans-serif;background:#f6f2e8;color:#102a43;margin:0;padding:24px}
h1{font-size:22px;margin:0 0 4px} h2{font-size:16px;margin:24px 0 8px;color:#1a8d85}
.meta{color:#53697c;font-size:13px}
table{border-collapse:collapse;background:#fff;font-size:13px;margin-top:8px}
th,td{border:1px solid #d6ddd9;padding:6px 10px;text-align:left;vertical-align:top}
th{background:#dceeea}
.pass{color:#1a8d85;font-weight:700} .fail{color:#c64c32;font-weight:700}
.lane{border:1px solid #d6ddd9;background:#fff}
.lane b{display:block;background:#132f47;color:#fff;padding:4px 8px;font-size:13px}
.ev{border-left:3px solid #1a8d85;padding:2px 8px;margin:4px 0;font-size:12px;color:#53697c}
.ev .t{color:#718190;font-size:11px}
footer{margin-top:24px;color:#718190;font-size:11px}
"""


def render_report(run_dir: Path, run_id: str, ledger_path: Path | None) -> str:
    metrics = compute_metrics(run_dir, run_id)
    conversation = run_dir / "conversation.json"
    events: list[dict[str, Any]] = []
    if conversation.is_file():
        document = json.loads(conversation.read_text(encoding="utf-8"))
        events = document if isinstance(document, list) else document.get("events", [])

    roles = ["engagement-lead", "business-engineer", "governance-auditor"]
    for event in events:
        sender = event.get("sender", "?").split(":")[0].replace("@agentfit-", "")
        if sender not in roles and sender != "admin":
            roles.append(sender)
    lanes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        sender = event.get("sender", "?").split(":")[0].replace("@agentfit-", "")
        lanes[sender].append(event)

    parts: list[str] = []
    parts.append("<h1>AgentFit Round Report</h1>")
    parts.append(
        f'<p class="meta">run <b>{html.escape(run_id)}</b> · '
        f"{len(events)} events · generated {datetime.utcnow().isoformat()}Z</p>"
    )

    parts.append("<h2>Metrics</h2>")
    parts.append("<table><tr><th>metric</th><th>value</th></tr>")
    for key, value in metrics.items():
        if key == "per_role":
            continue
        parts.append(f"<tr><td>{key}</td><td>{value}</td></tr>")
    if metrics.get("per_role"):
        parts.append(
            "<tr><td>per_role</td><td>"
            + ", ".join(f"{k}: {v}" for k, v in sorted(metrics["per_role"].items()))
            + "</td></tr>"
        )
    parts.append("</table>")

    parts.append("<h2>Role swimlane</h2>")
    parts.append('<div style="display:flex;gap:8px;align-items:flex-start">')
    for role in roles:
        parts.append('<div class="lane" style="flex:1;min-width:180px">')
        parts.append(f"<b>{html.escape(role)}</b>")
        for event in lanes.get(role, [])[-14:]:
            ts = datetime.utcfromtimestamp(
                event.get("origin_server_ts", 0) / 1000
            ).strftime("%H:%M:%S")
            room = "DM" if event.get("room") == "leader_dm" else "TEAM"
            body = html.escape(str(event.get("body", ""))[:90].replace("\n", " "))
            parts.append(
                f'<div class="ev"><span class="t">{ts} {room}</span><br>{body}</div>'
            )
        parts.append("</div>")
    parts.append("</div>")

    send = run_dir / "send.json"
    if send.is_file():
        meta = json.loads(send.read_text(encoding="utf-8"))
        parts.append("<h2>Dispatch anchor</h2>")
        parts.append(
            '<table><tr><th>field</th><th>value</th></tr>'
            f"<tr><td>event_id</td><td>{html.escape(meta.get('event_id',''))}</td></tr>"
            f"<tr><td>started_at_ms</td><td>{meta.get('started_at_ms')}</td></tr>"
            f"<tr><td>terminal_prefix</td><td>{html.escape(meta.get('terminal_prefix','')[:34])}…</td></tr>"
            "</table>"
        )

    if ledger_path is not None and ledger_path.is_file():
        ledger = load_ledger(ledger_path)
        errors = verify_chain(ledger)
        parts.append("<h2>Ledger chain</h2>")
        status = "pass" if not errors else "fail"
        parts.append(
            f'<p class="{status}">{"chain ok" if not errors else "CHAIN BROKEN"} · '
            f"{len(ledger.get('records', []))} records</p>"
        )
        parts.append("<table><tr><th>#</th><th>round</th><th>stage</th><th>hash</th></tr>")
        for index, record in enumerate(ledger.get("records", []), 1):
            parts.append(
                "<tr>"
                f"<td>{index}</td>"
                f"<td>{html.escape(str(record.get('round_id',''))[:40])}</td>"
                f"<td>{html.escape(str(record.get('lifecycle_position','')))}</td>"
                f"<td style='font-family:monospace'>{str(record.get('record_sha256',''))[:16]}…</td>"
                "</tr>"
            )
        parts.append("</table>")

    parts.append(
        f'<footer>{REPORT_SCHEMA} · self-contained · evidence in run dir '
        f"{html.escape(str(run_dir))}</footer>"
    )
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<style>{STYLE}</style></head><body>"
        + "\n".join(parts)
        + "</body></html>"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--ledger", type=Path, default=None)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        render_report(args.run_dir, args.run_id, args.ledger), encoding="utf-8"
    )
    print(f"report -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
