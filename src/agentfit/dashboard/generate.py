"""Render a self-contained, script-safe Dashboard from one RunStore."""
from __future__ import annotations

import datetime
import html
import json
from pathlib import Path
from typing import Any

from ..store.run_store import RunStore


_STYLE = """
body{margin:0;background:#0b2236;color:#e8edf2;font:14px/1.5 -apple-system,'PingFang SC',sans-serif}
header{padding:24px 32px 12px;border-bottom:2px solid #28516d}header h1{margin:0;font-size:22px}
header .sub{color:#718190;font-family:monospace;font-size:12px;margin-top:4px}
main{padding:20px 32px 60px;display:grid;grid-template-columns:repeat(2,1fr);gap:16px;max-width:1400px;margin:auto}
section{min-width:0;overflow-x:auto;background:#132f47;border:2px solid #28516d;border-radius:14px;padding:16px 18px}section.wide{grid-column:1/-1}
h2{margin:0 0 10px;font-size:15px;color:#74d0c7;font-family:monospace}h3{margin:16px 0 8px;font-size:13px;color:#e8edf2}table{width:100%;border-collapse:collapse;font-size:12.5px}
th{color:#74d0c7;text-align:left;padding:5px 8px;border-bottom:1px solid #28516d}td{padding:5px 8px;border-bottom:1px solid #1d3d55;color:#a8c4d8}
.kpi{display:flex;gap:12px;flex-wrap:wrap}.kpi div{background:#1a3d4a;border:1px solid #1a8d85;border-radius:10px;padding:10px 14px;min-width:110px}
.kpi b{display:block;font-size:22px;color:#74d0c7;font-family:monospace}.kpi span{color:#718190;font-size:11px}
.bar{height:14px;background:#1a2d3f;border-radius:4px;overflow:hidden;display:inline-block;vertical-align:middle;width:180px}.bar i{display:block;height:100%;background:#74d0c7}
.tag{display:inline-block;border:1px solid #28516d;border-radius:6px;padding:1px 8px;margin:2px;font-size:11.5px;color:#a8c4d8}
.ok{color:#74d0c7}.bad{color:#f26b4b}.mut{color:#718190}.L1{color:#74a8c6}.L2{color:#4a90b8}.L3{color:#74d0c7}.L4{color:#d6a43b}
.status{margin-top:12px;font:600 13px/1.5 monospace;color:#a8c4d8}code{color:#74d0c7}
.runtime-line{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}.learning-story{margin-top:14px;padding-top:14px;border-top:1px solid #28516d}.learning-story h3{margin-top:0}.final-verdict{margin-top:10px;color:#a8c4d8}.flow{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}
.flow-step{min-width:0;background:#0f293e;border:1px solid #28516d;border-radius:10px;padding:12px;min-height:92px}.flow-step b{display:block;color:#74d0c7;margin-bottom:6px}.flow-step strong{display:block;font:700 17px/1.3 monospace;margin-bottom:5px}.flow-step span{overflow-wrap:anywhere;color:#a8c4d8;font-size:12px}
.evidence-wrap{overflow-x:auto}.result-pass{color:#74d0c7}.result-fail,.result-error{color:#f26b4b}.mono{font-family:monospace}
@media(max-width:900px){main{grid-template-columns:1fr;padding:14px}.flow{grid-template-columns:1fr}section{grid-column:1/-1}header{padding:18px 14px}}
"""


_DOM_HELPERS = r"""
function el(tag, cls, text){const node=document.createElement(tag);if(cls)node.className=cls;if(text!==undefined&&text!==null)node.textContent=String(text);return node;}
function add(parent,...children){children.flat().forEach(child=>{if(child!==undefined&&child!==null)parent.appendChild(child instanceof Node?child:document.createTextNode(String(child)));});return parent;}
function table(columns,rows){const out=el('table');const head=el('tr');columns.forEach(value=>head.appendChild(el('th',null,value)));out.appendChild(head);rows.forEach(row=>{const tr=el('tr');row.forEach(value=>{const td=el('td');add(td,value);tr.appendChild(td);});out.appendChild(tr);});return out;}
function kpi(value,label){const box=el('div');add(box,el('b',null,value),el('span',null,label));return box;}
function badge(value,cls='tag'){return el('span',cls,value);}
function badges(values){const box=el('span');values.forEach(value=>box.appendChild(badge(value)));return box;}
function status(value,good,bad){return badge(value,good?'ok':bad?'bad':'mut');}
function code(value){return el('code',null,value);}
function shortRef(value){const text=String(value||'');return text?text.slice(0,12)+'…':'—';}
function humanOutcomeCounts(items){const count={PASS:0,FAIL:0,ERROR:0};items.forEach(item=>{if(item.result in count)count[item.result]++;});return items.length+' 个样本 · '+count.PASS+' 通过 / '+count.FAIL+' 失败 / '+count.ERROR+' 运行错误';}
function failureLabel(value){return({missing_rule:'缺少路由规则',tool_error:'工具调用错误',permission_denied:'权限不足'})[value]||value||'没有失败';}
function actionLabel(value){return({add:'新增',update:'更新',remove:'删除'})[value]||value||'无变更';}
function resultBadge(value){return badge(value,'result-'+String(value||'').toLowerCase());}
function flowStep(title,value,detail){const box=el('div','flow-step');add(box,el('b',null,title),el('strong',null,value),el('span',null,detail));return box;}
"""


_TRAINING_SCRIPT = r"""
const app=document.getElementById('app');
const trainingEvidence=DATA.training_evidence||[];const forward=trainingEvidence.filter(item=>item.phase==='forward');const candidateEvaluation=trainingEvidence.filter(item=>item.phase==='candidate_evaluation');const lossItems=Object.values(DATA.loss_traces||{}).flat();const firstLoss=lossItems[0]||{};const committed=((DATA.summary&&DATA.summary.transactions_committed)||[]).flatMap(item=>item.changes||[]);const firstChange=committed[0]||{};const finalEvidence=DATA.evaluation_evidence||[];

const overview=el('section','wide');overview.appendChild(el('h2',null,'① 运行概览'));const overviewKpis=el('div','kpi');
if(DATA.summary){const valid=typeof DATA.summary.final_pass_rate==='number';const costObserved=!DATA.run||!DATA.run.runtime_provenance||DATA.run.runtime_provenance.cost_accounting!=='unavailable';overviewKpis.appendChild(kpi(valid?(DATA.summary.final_pass_rate*100).toFixed(0)+'%':'—',valid?'训练批次通过率':'训练批次通过率 · 无有效方案评测'));overviewKpis.appendChild(kpi('v'+DATA.summary.final_solution_version,'方案版本'));overviewKpis.appendChild(kpi(costObserved?'$'+DATA.summary.total_cost_usd:'不可用','总成本'));overviewKpis.appendChild(kpi(DATA.summary.log_chain_valid?'✓':'✗','哈希链'));overviewKpis.appendChild(kpi(DATA.summary.converged?'收敛':'进行中','状态'));}
else overviewKpis.appendChild(el('span','mut','无 summary（训练未完成）'));
const runtime=(DATA.run&&DATA.run.runtime_provenance)||{};const runtimeLine=el('div','runtime-line');['平台 '+(runtime.platform||'未记录'),'模型 '+(runtime.model_ref||'未记录'),'边界 '+(runtime.execution_boundary||'未记录'),'模式 '+(runtime.binding_mode||'未记录')].forEach(value=>runtimeLine.appendChild(badge(value)));
add(overview,overviewKpis,el('div','status',ACCEPTANCE_STATUS),runtimeLine);
const learningStory=el('div','learning-story');learningStory.appendChild(el('h3',null,'训练阶段发生了什么'));
if(trainingEvidence.length){const flow=el('div','flow');add(flow,flowStep('1 · 初始测试',humanOutcomeCounts(forward),'用 adaptation 样本检验当前方案'),flowStep('2 · 找到原因',failureLabel(firstLoss.failure_mode),(firstLoss.sample_id||'—')+' · 归因到 '+(firstLoss.root_cause_layer||'未定位')),flowStep('3 · 修改方案',(firstChange.layer||'方案')+' · '+actionLabel(firstChange.action),firstChange.element||'没有产生变更'),flowStep('4 · 再次测试',humanOutcomeCounts(candidateEvaluation),'对同一批样本执行回归'));learningStory.appendChild(flow);}else learningStory.appendChild(el('div','mut','本次 RunStore 没有训练前后 Episode。'));
if(finalEvidence.length)learningStory.appendChild(el('div','final-verdict','最终验收：'+humanOutcomeCounts(finalEvidence)+'；'+ACCEPTANCE_STATUS));
overview.appendChild(learningStory);app.appendChild(overview);

const acceptance=el('section','wide');acceptance.appendChild(el('h2',null,'② 四集合验收'));
const purposeOrder=['adaptation','validation','sealed_holdout','stress_and_failure'];const evaluations=(DATA.summary&&DATA.summary.evaluation_by_purpose)||{};const criterionByPurpose={};(DATA.objective&&DATA.objective.criteria||[]).forEach(item=>criterionByPurpose[item.purpose]=item);const criteriaMet=(DATA.acceptance&&DATA.acceptance.criteria_met)||{};
const acceptanceRows=purposeOrder.map(purpose=>{const metric=evaluations[purpose]||{};const criterion=criterionByPurpose[purpose];const rate=typeof metric.pass_rate==='number'?(metric.pass_rate*100).toFixed(0)+'%':'—';const threshold=criterion?'通过率≥'+(criterion.min_pass_rate*100).toFixed(0)+'%; ERROR≤'+criterion.max_errors+'; 成本≤$'+criterion.max_cost_usd+'; 风险≤'+criterion.max_risk_events:'未定义';const verdict=criteriaMet[purpose]===true?status('PASS',true,false):criteriaMet[purpose]===false?status('REJECT',false,true):status('PENDING',false,false);const cost=metric.cost_observed===false?'不可用':typeof metric.cost_usd==='number'?'$'+metric.cost_usd:'—';return[purpose,rate,(metric.passed??'—')+' / '+(metric.failed??'—')+' / '+(metric.errors??'—'),cost,metric.risk_events??0,threshold,verdict];});
acceptance.appendChild(table(['集合','通过率','PASS / FAIL / ERROR','成本','风险事件','验收门槛','结果'],acceptanceRows));const failures=(DATA.acceptance&&DATA.acceptance.failures)||[];if(failures.length)acceptance.appendChild(el('div','bad','未满足条件：'+failures.join(' · ')));
acceptance.appendChild(el('h3',null,'逐样本结果'));if(finalEvidence.length){const rows=finalEvidence.map(item=>[item.purpose||'—',item.sample_id,resultBadge(item.result),item.run_index,item.error_code||(item.route||[]).join(' → ')||'—',code(shortRef(item.candidate_ref))]);const wrap=el('div','evidence-wrap');wrap.appendChild(table(['集合','样本','结果','RunIndex','实际路径 / 运行错误','Candidate'],rows));acceptance.appendChild(wrap);}else acceptance.appendChild(el('div','mut','最终评价尚未运行；当前只展示 adaptation 学习证据。'));app.appendChild(acceptance);

const mapping=el('section');mapping.appendChild(el('h2',null,'③ 材料与四层映射（初始方案）'));const first=DATA.solutions[Object.keys(DATA.solutions).sort((a,b)=>Number(a)-Number(b))[0]];
if(first){const solution=first.solution;mapping.appendChild(table(['层','元素数','清单'],[['L1 Solid',solution.L1_atoms.length,badges(solution.L1_atoms.map(item=>item.id+' ('+item.type+')'))],['L2 能力',solution.L2_tools.length,badges(solution.L2_tools.map(item=>item.id+' → ['+item.wraps.join(', ')+']'))],['L3 知识',solution.L3_knowledge.length,badges(solution.L3_knowledge.map(item=>item.id+': '+item.type))],['L4 拓扑',solution.L4_topology.agents.length,badges(solution.L4_topology.agents.map(item=>item.id))]]));}app.appendChild(mapping);

const samples=el('section');samples.appendChild(el('h2',null,'④ 样本与聚类分组'));if(DATA.task_samples){const groups={};DATA.task_samples.samples.forEach(sample=>{const key=Object.entries(sample.input_data||{}).map(([name,value])=>name+'='+String(value)).sort().join(', ');(groups[key]=groups[key]||[]).push(sample.id);});const rows=Object.entries(groups).map(([key,ids])=>[badge(key,'mut'),ids.length,ids.slice(0,4).join(', ')+(ids.length>4?' …':'')]);if(DATA.sample_sets)rows.push(['集合','—',DATA.sample_sets.manifests.map(item=>item.purpose+' × '+item.sample_refs.length).join(' · ')]);samples.appendChild(table(['特征签名（聚类）','样本数','示例'],rows));}app.appendChild(samples);

const curve=el('section');curve.appendChild(el('h2',null,'⑤ 训练曲线'));const epochRows=(DATA.epochs||[]).map(epoch=>{const rate=Math.max(0,Math.min(1,Number(epoch.entry.pass_rate)||0));const bar=el('span','bar');const fill=el('i');fill.style.width=(rate*100)+'%';bar.appendChild(fill);const rateCell=el('span');add(rateCell,bar,' '+(rate*100).toFixed(0)+'%');return[epoch.entry.epoch,rateCell,'$'+Number(epoch.entry.cost_usd||0).toFixed(3),Object.values(epoch.entry.lambda_values||{}).map(value=>Number(value).toFixed(2)).join('/'),(epoch.entry.updates_applied||[]).length,status(epoch.entry.rolled_back?'是':'否',!epoch.entry.rolled_back,epoch.entry.rolled_back)];});curve.appendChild(table(['epoch','通过率','成本','λ(L1/L2/L3/L4)','更新数','回滚'],epochRows));app.appendChild(curve);

const losses=el('section');losses.appendChild(el('h2',null,'⑥ 损失归因全景'));const layerCount={};let totalLosses=0;Object.values(DATA.loss_traces||{}).forEach(items=>items.forEach(item=>{layerCount[item.root_cause_layer]=(layerCount[item.root_cause_layer]||0)+1;totalLosses++;}));const lossKpis=el('div','kpi');Object.entries(layerCount).forEach(([layer,count])=>lossKpis.appendChild(kpi(count,layer+' '+(totalLosses?(count/totalLosses*100).toFixed(0):0)+'%')));losses.appendChild(lossKpis);const lossRows=[];Object.entries(DATA.loss_traces||{}).forEach(([epoch,items])=>items.forEach(item=>lossRows.push(['e'+epoch,item.sample_id,badge(item.root_cause_layer,['L1','L2','L3','L4'].includes(item.root_cause_layer)?item.root_cause_layer:'mut'),item.failure_mode,item.root_cause_element,Number(item.confidence??1).toFixed(2),(item.side_issues||[]).length?'⚠ '+item.side_issues.length+' 附带':'-'])));losses.appendChild(table(['轮','样本','层','模式','元素','置信度','附带问题'],lossRows.slice(0,40)));app.appendChild(losses);

const evolution=el('section');evolution.appendChild(el('h2',null,'⑦ L1-L4 方案证据与版本演化'));const versions=Object.keys(DATA.solutions||{}).sort((a,b)=>Number(a)-Number(b));const last=DATA.solutions[versions[versions.length-1]];if(last){const solution=last.solution;evolution.appendChild(table(['版本','演化说明'],versions.map(version=>['v'+version,DATA.solutions[version].note||'-'])));evolution.appendChild(table(['L3 路由规则（当前）'],solution.L3_knowledge.filter(item=>item.type==='routing_rule'&&!item.superseded).map(item=>[item.id+' '+(item.condition||'')+' → '+(item.dispatches_to||'')])));evolution.appendChild(table(['L4 Agent'],solution.L4_topology.agents.map(item=>[item.id+' ('+item.role+')'])));}app.appendChild(evolution);

const transactions=el('section');transactions.appendChild(el('h2',null,'⑧ 事务与中间链路'));if(DATA.summary){const tx=[...(DATA.summary.transactions_committed||[]),...(DATA.summary.transactions_rolled_back||[])];transactions.appendChild(table(['状态','版本','层','动作','元素','理由'],tx.flatMap(item=>(item.changes||[]).map(change=>[status(item.rolled_back?'回滚':'提交',!item.rolled_back,item.rolled_back),'v'+item.version,change.layer,change.action,change.element,String(change.reason||'').slice(0,40)]))));const messages=Object.entries(DATA.messages||{}).map(([epoch,items])=>['e'+epoch,items.length,items.filter(item=>item.dir==='task').map(item=>item.type).join(' · ').slice(0,80)]);transactions.appendChild(el('h2',null,'消息因果链（按轮）'));transactions.appendChild(table(['轮','消息数','类型流'],messages));}app.appendChild(transactions);
"""


_EXTERNAL_SCRIPT = r"""
const summary=DATA.summary||{};const evaluation=summary.evaluation||{};const kpis=document.getElementById('kpis');[['通过率',(Number(evaluation.pass_rate||0)*100).toFixed(0)+'%'],['PASS/FAIL/ERROR',(evaluation.passed||0)+'/'+(evaluation.failed||0)+'/'+(evaluation.errors||0)],['成本','$'+(evaluation.cost_usd||0)],['风险事件',evaluation.risk_events||0],['证据记录',summary.evidence_records||0]].forEach(item=>kpis.appendChild(kpi(item[1],item[0])));
const candidate=document.getElementById('candidate');const first=el('p');add(first,'CandidateRef: ',code(summary.candidate_ref||''));const second=el('p',null,'Provenance: '+(DATA.candidate_manifest&&DATA.candidate_manifest.provenance_complete?'完整':'不完整，禁止扩大结论'));const third=el('p');add(third,'证据链根: ',code(summary.evidence_chain_root||''));add(candidate,first,second,third);
const rows=(DATA.external_evidence||[]).map(record=>[record.source_index,record.sample_ref.sample_id,record.run_index,record.result,code(String(record.content_hash||'').slice(0,16)+'…')]);document.getElementById('records').appendChild(table(['source','sample','run','result','hash'],rows));
"""


def _script_json(value: Any) -> str:
    """Serialize JSON so data cannot close the containing script element."""
    return (
        json.dumps(value, ensure_ascii=False)
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def _document(*, run_name: str, generated_at: str, body: str,
              payload_json: str, script: str,
              acceptance_status: str = "") -> str:
    safe_name = html.escape(run_name, quote=True)
    safe_generated = html.escape(generated_at, quote=True)
    return f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>AgentFit Dashboard · {safe_name}</title><style>{_STYLE}</style></head><body>
<header><h1>AgentFit 训练全景 · {safe_name}</h1><div class="sub">方案不是设计出来的，是训练出来的 · 生成于 {safe_generated}</div></header>
{body}<script>
const DATA = {payload_json};
const ACCEPTANCE_STATUS = {_script_json(acceptance_status)};
{_DOM_HELPERS}{script}</script></body></html>"""


def generate_dashboard(run_dir: str | Path, output: str | Path | None = None) -> Path:
    store = RunStore(run_dir)
    payload = store.dashboard_payload()
    run_name = str(payload.get("run", {}).get("scenario", Path(run_dir).name))
    generated_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    is_external = (payload.get("run") or {}).get("run_kind") == "external_evaluation"
    if is_external:
        body = """<main><section class="wide"><h2>外部评价证据 · 评价概览</h2><div class="kpi" id="kpis"></div></section>
<section><h2>候选与证据边界</h2><div id="candidate"></div></section><section><h2>逐条证据链</h2><div id="records"></div></section></main>"""
        document = _document(
            run_name=run_name,
            generated_at=generated_at,
            body=body,
            payload_json=_script_json(payload),
            script=_EXTERNAL_SCRIPT,
        )
    else:
        acceptance = payload.get("acceptance") or {}
        summary = payload.get("summary") or {}
        acceptance_state = (
            "PASS" if acceptance.get("met") is True
            else "REJECT" if acceptance.get("met") is False
            else "PENDING"
        )
        g3_state = (
            "APPROVED" if summary.get("delivery_approved") is True
            else "REJECTED" if summary.get("acceptance_met") is False
            else "PENDING"
        )
        document = _document(
            run_name=run_name,
            generated_at=generated_at,
            body='<main id="app"></main>',
            payload_json=_script_json(payload),
            script=_TRAINING_SCRIPT,
            acceptance_status=f"验收 {acceptance_state} · G3 {g3_state}",
        )
    out = Path(output) if output else Path(run_dir) / "dashboard.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(document, encoding="utf-8")
    return out
