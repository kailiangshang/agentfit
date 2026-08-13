# AgentFit 搜索引擎框架（收敛版）

> 本文档是 dossier 00-22 的唯一有效整合。历史文档仅保留演进痕迹，不再作为设计依据。

## 1. 三维能力体系

Agent 完成任务的能力来自三个维度。搜索在每个维度上独立迭代。

### 执行层（Execution）

agent 的感官和手脚——所有可调用的外部接口。

| 类型 | 作用 | 例子 |
|---|---|---|
| 结构化工具 | 查数据库/API | find_user / get_order / get_product |
| 检索工具（RAG） | 查非结构化文档或 Skill 库 | search_policy / search_skill_library |
| 执行工具 | 写入或改变外部状态 | exchange / cancel / return / transfer_to_human |

**确定性规则归代码，不归 Skill。** 能写成 if-else 的约束直接写进工具函数，agent 不需要"知道"这些规则——工具层强制保证。

### 知识层（Knowledge）

agent 遇到情况时"怎么决策"的经验——需要推理的知识。

| 类型 | 回答 | 例子 |
|---|---|---|
| 策略知识 | "怎么做" | "首选不可行→检查替代路径" |
| 领域知识 | "是什么" | retail 的退换货政策 |
| 案例知识 | "上次怎么做的" | task 0 的换货流程 |

**Skill = 需要推理的知识。** 触发条件需要语义理解、执行路径需要推理的才提炼为 Skill。确定性规则（exchange 只能调一次、身份验证必须在操作前）归执行层代码。

### 推理层（Reasoning）

agent 用什么脑力理解并执行。

| 子层 | 作用 | 迭代成本 |
|---|---|---|
| 提示词（θ） | 信息怎么组织给模型 | 低 |
| 模型 | 推理引擎的脑力上限 | 高 |
| 架构（Π） | 几个 Agent、怎么分工 | 最高 |

### 存在判据：频率决定颗粒度

维护成本不随数量增长，但建造成本必须被频率摊平。

| 频率 | 工具/Skill | 做法 |
|---|---|---|
| ≥30% task 用到 | 值得独立 | 独立存在 |
| 5-30% | 合并或抽象 | 合并到通用工具/Skill |
| <5% | 不值得独立 | 留在 prompt 或标注边界 |

**最少的能力，最广的覆盖。** 这是"最简合格者"原则在工具/Skill 层的延伸。

---

## 2. 两层搜索

### 外循环：架构搜索（Π）

**只在全链路评估发现结构性限制时触发。** 不是 reward 低就换架构。

触发条件（任一）：
- 自验证偏差：agent 检查不了自己的错误
- 上下文过载：单 Agent 遗漏信息
- 权限冲突：同一 Agent 需要矛盾权限
- 并行需求：独立子任务必须同时执行

策略：BaselineFirst——从最简候选开始，达标就停，不预设多 Agent 更好。

### 内循环：能力迭代

架构 Π 固定。跑 batch → 全链路评估 → 链路级修复 → 新 batch 验证泛化。

**90% 的失败在内循环解决。** 架构变换是最后手段。

---

## 3. 全链路评估

### 核心区别

```
梯度下降（局部）: "哪层失败最多?" → 修那一层
全链路评估（系统性）: "数据怎么流的? 哪里系统性断了?" → 链路级协同修复
```

### 链路模型

候选处理一个 task 时，数据经过一条完整链路：

```
执行层·感知 → 知识层·指导 → 推理层·理解 → 执行层·动作 → 结果
```

每一环依赖上一环的输出。断点可能在任何环节，也可能在环节之间。

### 链路健康度

对每个 task 记录每环的健康度（0-1）+ 具体问题：

```
task5 的链路:
  执行层·感知    0.8  变体数据扁平呈现，推理负担重
  知识层·指导    0.0  ★ 主断点（无任何 Skill 匹配此场景）
  推理层·理解    0.4  16个选项上下文过载 + 无指导
  执行层·动作    0.0  未到达（上游断了）
```

### Batch 级链路统计

```
Batch 1 (task 0/1/5/10):
                    task0  task1  task5  task10  系统性?
执行层·感知          1.0    1.0    0.8    0.3    task10 工具缺失(个别)
知识层·指导          N/A    N/A    0.0    0.0    ★ 所有失败都是0%(系统缺失)
推理层·理解          1.0    0.8    0.4    0.5    复杂task下降
执行层·动作          1.0    0.5    0.0    0.5    上游断点的后果
```

系统性发现：知识层在所有失败 task 上都是 0%——不是个别 task 问题，是链路系统缺失。

### 链路级修复

```
梯度下降: 改一个参数（补一个 Skill）
全链路: 改链路的一段（可能跨多层，协同修复）

task5 修复:
  ① 执行层: get_product 返回增加属性摘要 → 降低推理负担
  ② 知识层: SK-GEN-001 "首选路径阻塞处理" → 给决策指导
  ③ 推理层·prompt: 分阶段引导 → 降低单步上下文负担
  → 三个改动协同，因为是链路问题不是单层问题
```

### 步长

| 步长 | 改动 | 适用 |
|---|---|---|
| 小 | 只改断点那一环 | 断点明确孤立 |
| 中 | 断点 + 直接贡献因子 | 断点有上游贡献因素 |
| 大 | 重构链路段 | 多环节低分，结构有问题 |

---

## 4. Batch 迭代机制

### 类比 ML 训练

| ML | AgentFit |
|---|---|
| mini-batch | 一批 task |
| forward | 跑候选 × N 个 task |
| loss | reward |
| gradient | 链路健康度分布 |
| backprop | 链路级修复 |
| learning rate | 修复步长 |
| next batch | 新一批 task 验证泛化 |
| overfitting | 修复只对旧 task 有效 |
| early stop | 场景达标 → StopSearch |

### 流程

```
① Batch forward: N个task用同一候选+θ+Skill库跑
② 链路诊断: 每个task追踪数据流，标记每环健康度
③ 链路统计: 找系统性断点 + 贡献因子
④ 链路修复: 沿断点做协同修复（可能跨多层）
⑤ 新Batch验证: 跑新task，看修复是否泛化
   - 同类失败减少 → 泛化成功
   - 同类失败不变 → 修复无效
   - 新失败出现 → 修复引入回归
⑥ 场景达标? → NO → 回到①
              → YES → Freeze → Deliver
```

### 不重跑旧 task

修复后跑**新 batch**（不是重跑旧的），验证泛化。重跑旧的会 overfit。

### 场景级判据（不是单样本）

```
达标条件（全部满足）:
  ① 连续2个Batch平均reward ≥ 阈值
  ② 没有新增高频失败模式
  ③ 剩余失败都有明确归因
  ④ 没有结构性限制（全链路无系统性断点）
```

---

## 5. 归因诊断（链路断点定位）

失败时沿链路追踪断点：

```
候选在样本上失败
│
├─ 执行层·感知: 工具够吗？数据可用吗？格式好吗？
│   ├─ 缺工具 → 合并或补通用工具(先问频率)
│   ├─ 缺约束 → 加确定性代码到工具层
│   └─ OK ↓
│
├─ 知识层·指导: agent 有决策指导吗？
│   ├─ 缺策略 → 提炼通用Skill(先问频率,先问能否代码化)
│   └─ OK ↓
│
├─ 推理层·理解: 信息传达清楚吗？脑力够吗？
│   ├─ prompt不清 → 改θ
│   ├─ 模型不够 → 换model
│   └─ OK ↓
│
├─ 结构性限制: 单Agent有结构问题吗？
│   ├─ 自验证偏差/上下文过载/权限冲突/并行需求
│   │   → YES → 上报外循环（架构变换）
│   └─ NO → 不可修复（故意不可解task）→ 标注边界
```

**关键：不是"归因到层"，是"追踪数据流找到断点 + 贡献因子"。一个断点可能有多个层的贡献因子。**

---

## 6. Skill 体系

### Skill 结构

```json
{
  "skill_id": "SK-GEN-001",
  "name": "首选路径阻塞处理",
  "type": "tactic",
  "trigger": "用户首选动作无法满足",
  "knowledge": "回溯到用户目标层面，寻找替代路径",
  "action_guidance": "①告诉首选不可用 ②找用户底层目标 ③检查替代 ④询问",
  "why_not_code": "触发需语义理解，退化需推理",
  "abstraction_level": "K2",
  "verification": {"status": "tested", "verified_on": ["retail-task-5"]},
  "source": "task-5-failure"
}
```

### 三级抽象

```
K1 具体级（70%）: "retail exchange→return" → 同场景直接复用
K2 模式级（25%）: "首选不可行→替代"     → 跨同类型场景
K3 元级  （5%）: "路径阻塞→回溯目标"   → 跨任意场景
```

### 验证晋升

```
新Skill (hypothesis)
  → 同场景多task验证 → tested (K1 ProjectAsset)
  → 抽象+跨场景验证 → verified (K2 MetaAsset候选)
  → 跨场景类型验证 → K3 MetaAsset
```

### Skill 和 RAG 的关系

Skill 库可被执行层的检索工具动态查询。agent 遇到不确定情况时：
1. search_skill_library("exchange不可行") → 命中 SK-GEN-001
2. 按知识决策

随着 Skill 积累，prompt 不膨胀，agent 按需检索。

---

## 7. 搜索引擎组件

```
Trial Tracker     记录每次试验 + 链路诊断 + 修复记录
Diagnostician     对每个失败task做链路追踪，定位断点+贡献因子
Inner Strategy    给定链路诊断 → 推荐链路级修复(可能跨多层)
Outer Strategy    只处理结构性限制 → 推荐Π变换或StopSearch
State Machine     IDLE→RUNNING→ANALYZING→FIXING→RUNNING / →OUTER_DECIDE
Monitor           收敛/预算/泄漏/局部最优检测
Skill Library     存储已验证Skill，支持RAG检索
```

### State Machine

```
IDLE → [Human批准] → RUNNING_INNER

RUNNING_INNER (跑Batch)
  → [Batch完成] → ANALYZING

ANALYZING (全链路评估)
  → 统计链路健康度 + 找系统性断点
  → [有结构性限制] → OUTER_EVAL
  → [无] → FIXING

FIXING (链路级修复)
  → 沿断点协同修复(跨多层)
  → [场景达标] → FROZEN
  → [未达标] → RUNNING_INNER (下一Batch)

OUTER_EVAL → OUTER_DECIDE
  → [BaselineFirst: 变换Π] → RUNNING_INNER (下一代)
  → [StopSearch] → STOPPED
  → [FROZEN] → DELIVERED
```

### TrialRecord（含链路诊断）

```json
{
  "trial_id": {"generation": 1, "batch": 1, "inner_index": 3},
  "candidate_ref": {"class": "C1", "Pi": "{A1}"},
  "sample_ref": {"id": "tau2-retail-5"},
  "theta_snapshot": {"prompt": "policy+skills", "model": "deepseek-chat"},
  "metrics": {"reward": 0.0, "action_match_rate": 0.8},
  "cost": {"tokens": 17000, "tool_calls": 6, "usd": 0.14},
  "trace_ref": "traces/task-5.json",
  
  "linkage_diagnosis": {
    "execution_perceive": {"score": 0.8, "issues": ["变体数据扁平呈现"]},
    "knowledge_guide": {"score": 0.0, "issues": ["无Skill匹配"], "primary_breakpoint": true},
    "reasoning_understand": {"score": 0.4, "issues": ["上下文过载"]},
    "execution_act": {"score": 0.0, "issues": ["未到达"]},
    "contributing_factors": ["execution_perceive数据格式", "reasoning上下文管理"],
    "fix_needed": ["knowledge", "execution_format", "prompt_structure"]
  },
  
  "fix_applied": {
    "type": "linkage协同修复",
    "changes": ["SK-GEN-001", "get_product属性摘要", "prompt分阶段引导"],
    "step_size": "medium"
  }
}
```

---

## 8. 沉淀机制

### 三级沉淀

```
TrialRecord (每次试验)
  ↓ 提炼
Skill (复用知识)
  ↓ 单项目验证 → ProjectAsset
  ↓ 跨项目验证 → MetaAsset
```

### 每次迭代的产出

```
内循环每次Batch:
  ├─ TrialRecord×N (含链路诊断)
  ├─ 工具清单更新（如果补了工具）
  ├─ Skill库更新（如果提炼了Skill）
  └─ 链路健康度趋势（每环是否改善）

外循环每次变换:
  ├─ 架构变换记录（Π变化 + 结构性限制证据）
  └─ 新候选的能力Profile
```

---

## 9. 和六层 ML 映射的关系

六层映射保留为方法论对照，搜索的实际驱动逻辑以三维体系为准。

| 六层映射 | 三维体系 |
|---|---|
| L1 Sample 语义 | 跨层（定义评价单位） |
| L2 任务语义 | 跨层（定义优化目标） |
| L3 能力语义 | 执行层 + 知识层 |
| L4 候选 (G,Π,θ,ρ) | 推理层 |
| L5 内循环 | 内循环（范围扩大：执行层+知识层+θ+model） |
| L6 外循环 | 外循环（只在结构性限制时触发） |
| L7 元学习 | Skill 库积累和晋升 |

候选定义扩大：候选 = (工具清单, Skill库, θ, model, Π)。两个候选可以 Π 相同但 Skill 库不同。

---

## 10. retail 场景完整搜索轨迹

### Generation 0: C0 Agentless (Π=∅)

```
Batch 0 (task 0):
  执行层·感知: 1.0  工具都在
  知识层·指导: N/A  无模型
  推理层·理解: 0.0  纯规则无法做约束推理
  执行层·动作: 0.0  未到达

链路断点: 推理层·理解 = 0.0
  原因: 纯 DAG 无 LLM 决策主体
  这是结构性限制（不是缺工具/Skill的问题）
  → Q5 → 外循环触发

外循环: agentize → C1
  证据: 核心能力需要 LLM 决策主体，C0 结构性无法提供
```

### Generation 1: C1 单Agent (Π={A1}, DeepSeek)

#### Batch 1: task 0/1/5/10

```
forward 结果:
  task0:  reward=1.0 ★ (真实运行)
  task1:  reward=? (评估器bug)
  task5:  reward=0.0 (exchange→return)
  task10: reward=0.0 (email认证)

链路健康度:
                    task0  task1  task5  task10  系统性?
执行层·感知          1.0    1.0    0.8    0.3    task10工具缺失
知识层·指导          N/A    N/A    0.0    0.0    ★ 系统缺失
推理层·理解          1.0    0.8    0.4    0.5    复杂task下降
执行层·动作          1.0    0.5    0.0    0.5    上游后果

系统性断点:
  ① 知识层 0% — 所有失败task的共同断点
  ② 执行层 task10 个别工具缺失
  无结构性限制 → 不触发外循环
```

#### 链路级修复

```
断点: 知识层(系统0%) + 执行层感知(贡献因子)

① 执行层:
   find_user 合并(支持 name_zip/email/user_id) → task10感知修复
   get_product 返回增加属性摘要 → task5感知改善

② 知识层:
   SK-GEN-001 "首选路径阻塞处理"(K2通用)
   → 覆盖 task1(fallback遵守) + task5(exchange→return) 的共性

③ 推理层·prompt:
   分阶段引导: "多变体先查范围→缩小→匹配→不可行则回溯"

步长: 中等(链路段协同修复，一次改3层)
```

#### Batch 2: task 2/3/6/7/8（新样本验证泛化）

```
验证目标:
  ① SK-GEN-001 泛化? → "路径阻塞"类失败应减少
  ② find_user 合并有效? → 身份验证类失败应消失
  ③ 数据格式改善? → 推理层健康度应提升
  ④ 新断点? → task2/3(11-12 actions)可能暴露上下文过载

如果 Batch 2 暴露:
  推理层·理解在复杂task持续低分
  + prompt调整无法解决
  + 链路追踪显示单Agent上下文过长
  → 结构性限制 → 外循环触发 → 考虑C2

如果 Batch 2 达标:
  连续2个Batch ≥ 85% → Freeze → Deliver
```

### 搜索轨迹汇总

```
C0 (Π=∅)
  → Batch0: 链路断点=推理层0%(结构性)
  → 外循环: agentize

C1 (Π={A1})
  → Batch1: 链路断点=知识层0%(系统缺失) + 执行层个别
  → 修复: Skill + 工具合并 + prompt(链路协同)
  → Batch2: 新样本验证泛化
  → [待运行]
  → 如果达标 → StopSearch (C1是最简合格候选)
  → 如果有结构性限制 → C2

成本: ~$0.25 / $5.00 (5%)
架构变换: 1次(C0→C1)，有结构性限制证据
Skill产出: SK-GEN-001 (待跨场景验证)
```

### 最终交付包

```
最优候选: C1 + 修复后的执行层 + Skill库
├── 架构: Π={A1}, ReAct SCC
├── 模型: deepseek-chat
├── 执行层: 通用工具 + 确定性约束(代码)
├── 知识层: SK-GEN-001 (K2, tested)
├── 推理层·θ: policy + skill注入 + 分阶段引导
├── 能力边界图: can_do / unstable / cannot_do
├── 架构决策: C0结构性限制→C1，C1场景达标→不试C2
└── TrialRecord全量(含链路诊断，可审计)
```

---

## 11. 核心原则总结

1. **失败 → 先归因 → 90%在底层修复**，架构变换是最后手段
2. **能 if-else 的归代码，需要推理的才叫 Skill**
3. **低频的不独立**——合并、抽象、或留 prompt
4. **batch 跑完看链路系统性断点**，不为单个 task overfit
5. **新 batch 验证泛化**，不重跑旧 task
6. **Skill 库增长 = 越用越聪明**，这是 Meta-learning 的落地形式
7. **候选定义 = (工具清单, Skill库, θ, model, Π)**，不只是架构和参数
