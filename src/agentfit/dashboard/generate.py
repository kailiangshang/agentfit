"""Dashboard 生成器：RunStore → 自包含单文件 HTML（内嵌 JSON + 原生 JS，零依赖零服务）。

七个区块：① 运行概览 ② 材料与四层映射 ③ 样本与聚类分组 ④ 训练曲线
⑤ 损失归因全景 ⑥ L1-L4 方案全景与版本演化 ⑦ 事务/回归/消息链路。
"""
from __future__ import annotations

import json
from pathlib import Path

from ..store.run_store import RunStore

_TPL = """<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>AgentFit Dashboard · {run_name}</title>
<style>
 body{{margin:0;background:#0b2236;color:#e8edf2;font:14px/1.5 -apple-system,'PingFang SC',sans-serif}}
 header{{padding:24px 32px 12px;border-bottom:2px solid #28516d}}
 header h1{{margin:0;font-size:22px}} header .sub{{color:#718190;font-family:monospace;font-size:12px;margin-top:4px}}
 main{{padding:20px 32px 60px;display:grid;grid-template-columns:repeat(2,1fr);gap:16px;max-width:1400px}}
 section{{background:#132f47;border:2px solid #28516d;border-radius:14px;padding:16px 18px}}
 section.wide{{grid-column:1/-1}}
 h2{{margin:0 0 10px;font-size:15px;color:#74d0c7;font-family:monospace}}
 table{{width:100%;border-collapse:collapse;font-size:12.5px}}
 th{{color:#74d0c7;text-align:left;padding:5px 8px;border-bottom:1px solid #28516d}}
 td{{padding:5px 8px;border-bottom:1px solid #1d3d55;color:#a8c4d8}}
 .kpi{{display:flex;gap:12px;flex-wrap:wrap}}
 .kpi div{{background:#1a3d4a;border:1px solid #1a8d85;border-radius:10px;padding:10px 14px;min-width:110px}}
 .kpi b{{display:block;font-size:22px;color:#74d0c7;font-family:monospace}}
 .kpi span{{color:#718190;font-size:11px}}
 .bar{{height:14px;background:#1a2d3f;border-radius:4px;overflow:hidden;display:inline-block;vertical-align:middle;width:180px}}
 .bar i{{display:block;height:100%}}
 .L1{{background:#74a8c6}}.L2{{background:#4a90b8}}.L3{{background:#74d0c7}}.L4{{background:#d6a43b}}.human{{background:#f26b4b}}
 .tag{{display:inline-block;border:1px solid #28516d;border-radius:6px;padding:1px 8px;margin:2px;font-size:11.5px;color:#a8c4d8}}
 .ok{{color:#74d0c7}} .bad{{color:#f26b4b}} .mut{{color:#718190}}
</style></head><body>
<header><h1>AgentFit 训练全景 · {run_name}</h1><div class="sub">方案不是设计出来的，是训练出来的 · 生成于 {generated_at}</div></header>
<main id="app"></main>
<script>
const DATA = {payload_json};
function el(tag, cls, html){{const e=document.createElement(tag); if(cls)e.className=cls; if(html!==undefined)e.innerHTML=html; return e;}}
function table(cols, rows){{const t=el('table'); t.innerHTML = '<tr>'+cols.map(c=>'<th>'+c+'</th>').join('')+'</tr>'+rows.map(r=>'<tr>'+r.map(c=>'<td>'+c+'</td>').join('')+'</tr>').join(''); return t;}}
function kpi(v,label){{const d=el('div');d.innerHTML='<b>'+v+'</b><span>'+label+'</span>';return d;}}

// ① 运行概览
const s1=el('section','wide'); s1.appendChild(el('h2',null,'① 运行概览'));
const k=el('div','kpi');
if(DATA.summary){{ k.appendChild(kpi((DATA.summary.final_pass_rate*100).toFixed(0)+'%','最终通过率'));
 k.appendChild(kpi('v'+DATA.summary.final_solution_version,'方案版本')); k.appendChild(kpi('$'+DATA.summary.total_cost_usd,'总成本'));
 k.appendChild(kpi(DATA.summary.log_chain_valid?'✓':'✗','哈希链')); k.appendChild(kpi(DATA.summary.converged?'收敛':'进行中','状态'));}}
else k.appendChild(el('span','mut','无 summary（训练未完成）'));
s1.appendChild(k); document.getElementById('app').appendChild(s1);

// ② 材料与四层映射
const s2=el('section'); s2.appendChild(el('h2',null,'② 材料与四层映射（初始方案）'));
const v0=DATA.solutions[Object.keys(DATA.solutions).sort((a,b)=>a-b)[0]];
if(v0){{ const so=v0.solution;
 s2.appendChild(table(['层','元素数','清单'],[
  ['L1 Solid',so.L1_atoms.length, so.L1_atoms.map(a=>'<span class=tag>'+a.id+'('+a.type+')</span>').join('')],
  ['L2 能力',so.L2_tools.length, so.L2_tools.map(t=>'<span class=tag>'+t.id+'→['+t.wraps.join(',')+']</span>').join('')],
  ['L3 知识',so.L3_knowledge.length, so.L3_knowledge.map(x=>'<span class=tag>'+x.id+':'+x.type+'</span>').join('')],
  ['L4 拓扑',so.L4_topology.agents.length, so.L4_topology.agents.map(a=>'<span class=tag>'+a.id+'</span>').join('')]]));}}
document.getElementById('app').appendChild(s2);

// ③ 样本与聚类分组
const s3=el('section'); s3.appendChild(el('h2',null,'③ 样本与聚类分组'));
if(DATA.samples){{ const sig={{}};
 DATA.samples.samples.forEach(s=>{{const key=Object.entries(s.features).map(([k,v])=>k+'='+(v?'1':'0')).sort().join(','); (sig[key]=sig[key]||[]).push(s.id);}});
 const rows=Object.entries(sig).map(([k,ids])=>['<span class=mut>'+k+'</span>', ids.length, ids.slice(0,4).join(', ')+(ids.length>4?' …':'')]);
 rows.push(['<b>分组</b>','—', Object.entries(DATA.samples.groups).map(([g,l])=>g+'×'+l.length).join(' · ')]);
 s3.appendChild(table(['特征签名（聚类）','样本数','示例'],rows));}}
document.getElementById('app').appendChild(s3);

// ④ 训练曲线
const s4=el('section'); s4.appendChild(el('h2',null,'④ 训练曲线'));
const ep=DATA.epochs;
s4.appendChild(table(['epoch','通过率','成本','λ(L1/L2/L3/L4)','更新数','回滚'],ep.map(e=>[
 e.entry.epoch,'<span class="bar"><i style="width:'+(e.entry.pass_rate*100)+'%;background:#74d0c7"></i></span> '+(e.entry.pass_rate*100).toFixed(0)+'%',
 '$'+e.entry.cost_usd.toFixed(3), Object.values(e.entry.lambda_values).map(v=>v.toFixed(2)).join('/'), e.entry.updates_applied.length, e.entry.rolled_back?'<span class=bad>是</span>':'<span class=ok>否</span>'])));
document.getElementById('app').appendChild(s4);

// ⑤ 损失归因全景
const s5=el('section'); s5.appendChild(el('h2',null,'⑤ 损失归因全景'));
const layerCount={{}}; let totalLt=0;
Object.values(DATA.loss_traces).forEach(lts=>lts.forEach(lt=>{{layerCount[lt.root_cause_layer]=(layerCount[lt.root_cause_layer]||0)+1; totalLt++;}}));
const lc=el('div','kpi');
Object.entries(layerCount).forEach(([layer,n])=>{{ const d=el('div'); d.innerHTML='<b>'+n+'</b><span>'+layer+' '+ (totalLt?(n/totalLt*100).toFixed(0):0)+'%</span>'; lc.appendChild(d); }});
s5.appendChild(lc);
const ltRows=[]; Object.entries(DATA.loss_traces).forEach(([e,lts])=>lts.forEach(lt=>ltRows.push([
 'e'+e, lt.sample_id, '<span class="'+(lt.root_cause_layer||'')+'">'+lt.root_cause_layer+'</span>', lt.failure_mode,
 lt.root_cause_element, (lt.confidence??1).toFixed(2), (lt.side_issues||[]).length?'⚠ '+lt.side_issues.length+' 附带':'-'])));
s5.appendChild(table(['轮','样本','层','模式','元素','置信度','附带问题'],ltRows.slice(0,40)));
document.getElementById('app').appendChild(s5);

// ⑥ L1-L4 全景与版本演化
const s6=el('section'); s6.appendChild(el('h2',null,'⑥ L1-L4 最终方案与版本演化'));
const vLast=DATA.solutions[Object.keys(DATA.solutions).sort((a,b)=>b-a)[0]];
if(vLast){{ const so=vLast.solution;
 s6.appendChild(table(['版本','演化说明'],Object.keys(DATA.solutions).sort((a,b)=>a-b).map(v=>['v'+v, DATA.solutions[v].note||'-'])));
 s6.appendChild(table(['L3 路由规则（当前）'],so.L3_knowledge.filter(x=>x.type==='routing_rule'&&!x.superseded).map(r=>[
  '<b class=ok>'+r.id+'</b> <span class=mut>'+r.condition+'</span> → '+r.dispatches_to])));
 s6.appendChild(table(['L4 Agent'],so.L4_topology.agents.map(a=>[a.id+' <span class=mut>('+a.role+')</span>'])));}}
document.getElementById('app').appendChild(s6);

// ⑦ 事务 / 回归 / 消息链路
const s7=el('section'); s7.appendChild(el('h2',null,'⑦ 事务与中间链路'));
if(DATA.summary){{ const tx=[...DATA.summary.transactions_committed,...DATA.summary.transactions_rolled_back];
 s7.appendChild(table(['状态','版本','层','动作','元素','理由'],tx.flatMap(t=>t.changes.map(c=>[
  t.rolled_back?'<span class=bad>回滚</span>':'<span class=ok>提交</span>','v'+t.version,c.layer,c.action,c.element,(c.reason||'').slice(0,40)]))));
 const msgs=Object.entries(DATA.messages).map(([e,m])=>['e'+e, m.length, m.filter(x=>x.dir==='task').map(x=>x.type).join(' · ').slice(0,80)]);
 s7.appendChild(el('h2',null,'消息因果链（按轮）')); s7.appendChild(table(['轮','消息数','类型流'],msgs));}}
document.getElementById('app').appendChild(s7);
</script></body></html>"""


def generate_dashboard(run_dir: str | Path, output: str | Path | None = None) -> Path:
    store = RunStore(run_dir)
    payload = store.dashboard_payload()
    run_name = payload.get("run", {}).get("scenario", Path(run_dir).name)
    import datetime
    html = _TPL.format(run_name=run_name, generated_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                       payload_json=json.dumps(payload, ensure_ascii=False))
    out = Path(output) if output else Path(run_dir) / "dashboard.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out
