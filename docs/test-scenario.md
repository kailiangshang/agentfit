# AgentFit 测试场景：Telecom 故障诊断全链路执行方案

> 这不是 AgentFit 本身的设计——这是**用于测试 AgentFit 的具体场景的详尽执行方案**。回答"怎么启动、怎么对比、监控什么、交付什么"。

---

## 一、场景设定

| 项 | 值 |
|---|---|
| **业务** | 电信运营商移动网络故障排查客服 |
| **用户输入** | τ²-bench telecom 域 2285 个故障工单（含标准答案）+ 通过率评价 |
| **目标** | 训练出一个能自动处理 ≥80% 工单的 Agent 方案 |
| **baseline** | DeepSeek + τ²-bench 裸跑 = 80%（已验证，10/10 样本实测） |
| **AgentFit 要证明的** | 经过训练的方案比裸跑 baseline 更好（更高通过率 / 更低成本 / 更清晰边界） |

---

## 二、全链路流程

```
Phase 0: 环境准备（一次性，约 30 分钟）
  ├── 安装 AgentFit 源码 + τ²-bench
  ├── 配置 DeepSeek API key
  └── 验证 baseline 能跑（跑 10 个样本确认）

Phase 1: 样本准备（约 10 分钟）
  ├── 加载 2285 个 telecom 工单
  ├── 自动聚类为 11 类根因
  ├── 分层抽样 50 个代表性样本（初始训练批次）
  ├── 留出 50 个样本（对照组，不参与训练）
  └── 用户确认聚类合理性

Phase 2: 初始方案构建（约 20 分钟）
  ├── 从聚类反推 L1 原子（17 个工具操作）
  ├── 构建 L2 封装（安全包装 + 送审路由）
  ├── 从解决轨迹归纳 L3 路由规则
  └── 设计 L4 拓扑（初始 = 单 Agent）

Phase 3: 训练循环（每轮约 10 分钟，预计 3-5 轮）
  ├── ① 取一批样本（50 个/轮）
  ├── ② 用当前方案执行
  ├── ③ 失败样本自底向上归因
  ├── ④ 聚合损失 + 计算正则
  ├── ⑤ 生成更新建议
  ├── ⑥ 用户审核（预计 5 分钟/轮）
  ├── ⑦ 原子事务应用更新
  ├── ⑧ 回归验证（旧样本重跑）
  └── ⑨ 训练日志追加
  └── 循环直到收敛

Phase 4: 对照测试（约 20 分钟）
  ├── 用训练后的方案跑 50 个对照样本
  ├── 用 baseline（裸跑）跑同样 50 个对照样本
  └── 对比通过率/成本/失败模式

Phase 5: 交付（自动生成）
  ├── 可部署方案包
  ├── 训练过程记录（通过率曲线 + 更新日志 + 回归记录）
  ├── 适用边界报告
  └── 持续监控配置
```

---

## 三、怎么启动

### 前置条件

```bash
# 1. 克隆仓库
git clone https://github.com/kailiangshang/agentfit.git
cd agentfit

# 2. 安装依赖
uv venv .venv --python 3.12
uv pip install -e ".[dev]"

# 3. 配置 API
export DEEPSEEK_API_KEY="sk-..."
# 或者写入 .env 文件

# 4. 安装 τ²-bench（执行环境）
git clone https://github.com/sierra-research/tau2-bench ../tau2-bench
cd ../tau2-bench && uv sync && cd ../agentfit
```

### 启动训练

```bash
# 一条命令启动全链路
python -m agentfit.train \
  --domain telecom \
  --executor tau2bench \
  --samples ../tau2-bench/data/tau2/domains/telecom/tasks.json \
  --evaluation pass_rate \
  --train-batch-size 50 \
  --control-batch-size 50 \
  --max-epochs 5 \
  --convergence-window 3 \
  --output ./output/telecom-run-001

# 训练过程中的交互点（自动暂停等人审）:
#   Phase 1 后: "确认聚类结果" → 按 Enter 继续
#   Phase 2 后: "确认初始方案" → 按 Enter 继续
#   每轮 Phase 3: "审核更新建议" → 按 Enter 接受 / 输入 reject 拒绝
```

### 单独跑 baseline 对照

```bash
# 不经过 AgentFit，直接跑 τ²-bench
cd ../tau2-bench
.venv/bin/tau2 run --domain telecom \
  --agent-llm deepseek/deepseek-chat \
  --user-llm deepseek/deepseek-chat \
  --num-trials 1 --num-tasks 50
```

---

## 四、监控什么

### 训练期间监控（AgentFit 自动输出）

| 指标 | 每轮更新 | 告警条件 |
|---|---|---|
| 通过率 | ✅ | 连续 3 轮变化 < 2% → 疑似收敛 |
| 各层损失分布 | ✅ | 某层占比 > 60% → 该层是瓶颈 |
| 回归通过率 | ✅ | < 95% → 触发回滚 |
| L1 原子使用率 | ✅ | > 80% → 某原子过度耦合 |
| L3 链路覆盖度 | ✅ | > 60% → 万能路由风险 |
| L4 人工介入率 | ✅ | > 30% → 自动化价值不足 |
| Token 成本 | ✅ | 超预算 → 告警 + 暂停 |
| λ 值变化 | ✅ | 累计变化 > ±50% → 建议人审 |

### 实时控制台输出（示例）

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  AgentFit Training · telecom · Epoch 2/5
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Pass Rate:    ████████████░░░░  76% (+11%)
  Regression:   ████████████████  100% ✓
  Cost/Sample:  $0.009

  Loss Distribution:
    L1 ████░░░░░░░░░░░░  2 (4%)
    L2 ████████░░░░░░░░  4 (8%)
    L3 █████████████░░░  8 (16%)
    L4 ░░░░░░░░░░░░░░░░  0
    Human ████░░░░░░░░░  6 (12%)

  Regularization:
    L1: 0.00 ✓  L2: 0.12 ✓  L3: 0.08 ✓  L4: 0.00 ✓
    λ₃ adjusted: 0.30 → 0.36 (auto, coverage trigger)

  Pending Updates (2):
    [L3] Add compound routing rule → press Enter to approve
    [L2] Fix refuel calculation → press Enter to approve
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 部署后监控

| 指标 | 检测什么 | 触发动作 |
|---|---|---|
| 实时通过率 | 部署后的实际表现 | < 部署时 -5% → 告警 |
| 新失败模式 | 未见过的错误类型 | 通知用户分析 |
| 成本趋势 | Token 消耗是否异常 | 超预算 → 告警 |
| 分布漂移 | 工单类型分布变化 | 偏移 > 15% → 建议重训练 |

---

## 五、怎么对比

### 对比方案

| 方案 | 描述 | 怎么跑 |
|---|---|---|
| **Baseline** | DeepSeek 直接跑 τ²-bench，无 AgentFit | `tau2 run --domain telecom ...` |
| **AgentFit C1** | 训练后的单 Agent 方案 | AgentFit 训练收敛后自动跑对照 |
| **AgentFit C2** | 训练后拆分为诊断+修复双 Agent（如果 L4 触发了拓扑变更） | 同上 |

### 对比维度

| 维度 | Baseline 怎么测 | AgentFit 怎么测 | 报告格式 |
|---|---|---|---|
| **通过率** | τ²-bench evaluator 直接出分 | 同样用 τ²-bench evaluator | 百分比 + 每样本明细 |
| **成本** | τ²-bench 输出的 API 费用 | 训练日志中的 token 记录 | $/样本 |
| **失败模式** | 手工分析失败样本 | 损失归因器自动分类 | 各层/各类失败占比 |
| **可维护性** | 无（baseline 不可度量） | 正则指标量化 | 各层正则值 |
| **可追溯性** | 无 | 训练日志 + 损失轨迹 | 每个失败→根因→修复 |
| **回归保障** | 无 | 回归池通过率 | 必须 100% |
| **适用边界** | 无（不知道什么时候会失败） | 收敛分析 | 哪些能自动/哪些留人工 |

### 对照实验设计

```
样本分组（从 2285 个工单中）:
  Group A (训练集): 200 个 → AgentFit 训练用
  Group B (回归池): 100 个 → 训练中做回归验证
  Group C (对照组): 50 个 → 不参与训练，最终对比用
  Group D (压力组): 20 个 → 极端/边界案例

实验流程:
  1. Baseline 跑 Group C (50 个) → 得到 baseline 通过率
  2. AgentFit 用 Group A 训练 → 收敛
  3. AgentFit 方案跑 Group C (同样的 50 个) → 得到 agentfit 通过率
  4. 对比: agentfit_pass_rate vs baseline_pass_rate
  5. AgentFit 方案跑 Group D (压力组) → 得到边界分析

统计检验:
  如果 agentfit_pass_rate > baseline_pass_rate + 5%: AgentFit 有效
  如果 agentfit_pass_rate ≈ baseline_pass_rate: 检查失败模式是否减少
  如果 agentfit_pass_rate < baseline_pass_rate: AgentFit 需要调整
```

---

## 六、交付什么

### 交付物清单

```
📦 output/telecom-run-001/
│
├── solution_package/              # 可部署的 Agent 方案
│   ├── agent_config.yaml          # Agent 配置
│   ├── tool_bindings.json         # L1/L2 工具绑定
│   ├── routing_rules.json         # L3 路由规则
│   ├── human_gates.json           # 人工门禁配置
│   └── monitoring_config.yaml     # 持续监控配置
│
├── training_history/              # 训练证据
│   ├── training_log.json          # 完整训练日志（哈希链）
│   ├── pass_rate_curve.png        # 通过率曲线图
│   ├── loss_distribution.png     # 各层损失分布变化图
│   ├── update_changelog.md       # 每轮改了什么、为什么
│   ├── regression_results.json   # 回归验证记录
│   └── lambda_adjustments.json   # 正则权重变化记录
│
├── comparison_report/             # 对比分析
│   ├── baseline_vs_agentfit.md   # 通过率/成本/失败模式对比
│   ├── per_sample_detail.csv     # 每个对照样本的双方结果
│   └── statistical_significance.md  # 统计检验结果
│
├── boundary_analysis/             # 适用边界
│   ├── coverage_report.md        # 能自动处理的范围
│   ├── human_required.md        # 必须人工的场景和原因
│   ├── cost_analysis.md          # 成本对比（AI vs 人工）
│   └── retrain_triggers.md      # 什么时候需要重训练
│
└── visual_report.html            # 自包含 HTML 全景报告
                                     通过率曲线 / 损失分布 /
                                     训练时间线 / 对比图表 /
                                     适用边界 / 部署指南
```

---

## 七、预算估算

| 项 | 预计 Token | 预计成本 (DeepSeek) |
|---|---|---|
| Baseline 跑 50 样本 | ~500K | ~$0.75 |
| AgentFit 训练 5 轮 × 50 样本 | ~2.5M | ~$3.75 |
| AgentFit 跑 50 对照样本 | ~500K | ~$0.75 |
| AgentFit 跑 20 压力样本 | ~200K | ~$0.30 |
| 回归验证（每轮 ~100 样本） | ~1M | ~$1.50 |
| **总计** | **~4.7M** | **~$7.05** |

---

## 八、成功标准

| 维度 | 标准 | 为什么重要 |
|---|---|---|
| **通过率提升** | AgentFit > Baseline + 5% | 证明训练有价值 |
| **回归通过率** | 100% | 证明不遗忘 |
| **失败模式减少** | 复合根因类失败显著降低 | 证明 L3 更新有效 |
| **可维护性达标** | 各层正则值在阈值内 | 证明方案可长期维护 |
| **成本可控** | 每样本 < $0.05 | 证明比人工便宜 |
| **边界清晰** | 明确哪些能/不能自动化 | 交付可信 |
