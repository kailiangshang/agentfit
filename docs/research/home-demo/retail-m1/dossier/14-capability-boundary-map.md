# AgentFit C1 场景级能力边界图 — retail

> 状态：真实模型运行（DeepSeek + opencode CLI + τ³-bench db.json）
>
> evidence_role: scene-level-smoke-evidence
>
> 4 个 retail task 的批量运行结果 + 失败模式分析。
>
> 这回答的问题："C1 能解决 retail 场景么？"

## 1. 场景级结果

| task | 类型 | 期望工具 | 匹配 | 匹配率 | reward |
|---:|---|---:|---|---:|---|
| 0 | 换货(键盘+温控器) | 4 | 4/4 | **100%** | ✅ |
| 1 | 换货(同 task0 但 fallback 不同) | 4 | 0/4 | **0%** | ❌ |
| 5 | 换货(水瓶+台灯) | 5 | 4/5 | **80%** | ❌ |
| 10 | 退货(交叉退款→转人工) | 4 | 3/4 | **75%** | ❌ |

**平均 tool_match_rate: 64%**
**全匹配: 1/4**
**reward=1.0: 1/4（如果用 τ³-bench 原生 evaluator，可能更低，因为它检查精确参数不只是工具名）**

## 2. 失败模式分析

### 失败模式 A：fallback 推理错误（task 1）

**场景差异**（task 0 vs task 1）：

| | task 0 | task 1 |
|---|---|---|
| 订单 | #W2378156 | #W2378156（同一个） |
| 用户 | Yusuf Rossi | Yusuf Rossi（同一个） |
| 需求 | clicky+RGB+全尺寸，否则无背光 | clicky+RGB+全尺寸，否则**只换温控器** |

task 0：键盘首选存在（7706410293）→ 两件都换 ✓
task 1：键盘首选不存在（τ³-bench 数据库里 task 1 的产品变体不同）→ 只换温控器

**Agent 实际做了什么**：

Agent 发现没有 clicky+RGB+全尺寸的键盘，然后做了**正确的推理**——"per your instruction, we will only exchange the Smart Thermostat"。

**但为什么匹配率 0%？**

因为 task 1 的期望答案**只有 4 个唯一工具**（find_user / get_order / get_product / exchange），agent 应该调了这些工具——但我们的评估器在 task 1 的 raw output 里没找到工具名。

**根因分析**：task 1 的 raw output 可能被 opencode 的 ANSI 转义码或输出截断干扰了。Agent 的行为**可能是对的**（它说了"只换温控器"），但我们的简单文本匹配评估器没检测到。

**这是评估器的问题，不一定是 agent 的问题。** 需要 τ³-bench 原生 evaluator 才能判定。

### 失败模式 B：工具名不匹配（task 5）

**场景**：换水瓶 + 台灯

**期望工具**：`find_user_id_by_name_zip`, `get_user_details`, `get_order_details`, `get_product_details`, **`return_delivered_order_items`**

**Agent 实际调的**：前 4 个都对了，但第 5 个调了 `exchange_delivered_order_items`。

**期望的第 5 个是 `return_delivered_order_items`**——注意是 **return（退货）** 不是 exchange（换货）。

**Agent 做错的原因**：

task 5 的用户场景说的是"exchange the water bottle and the desk lamp"。但期望答案是 return（退货）。

这可能意味着：
1. 用户的 exchange 需求**实际无法满足**（没有合适的变体可选），正确做法是退化为 return
2. 或者 task 5 的期望答案代表另一种合法路径（用户可能接受 return 而非 exchange）

**这是意图理解错误**：agent 按字面意思做 exchange，但 task 期望的是 return。**Agent 缺少"当 exchange 不可行时退化为 return"的策略推理。**

**这个失败模式极有价值**——它揭示了一个 CAP（能力）缺口：**CAP-11: 动作退化解策**（exchange 不可行 → return）。

### 失败模式 C：email 认证 + 交叉退款（task 10）

**场景**：用户要退两个订单，要求把 A 订单退款到 B 订单的支付方式，反之亦然。如果不行就骂人然后转人工。

**期望工具**：`find_user_id_by_email`, `get_user_details`, `get_order_details` ×2, `transfer_to_human_agents`

**Agent 缺失**：
1. **`find_user_id_by_email` MISSING**：我们的工具脚本没有这个工具！τ³-bench 有，但我们没实现。Agent 被困在身份验证步骤。

2. **`transfer_to_human_agents` FOUND**：Agent 最终确实转人工了——这部分是对的。

**根因分析**：
- 工具缺失（我们没实现 email 认证工具）→ agent 无法完成身份验证 → 卡住
- 但 agent 最终识别到"无法处理 → 转人工"，这是**正确的策略决策**
- task 10 本身就是一个**故意设计的不可解任务**（交叉退款违反 policy），期望答案就是转人工

**这个失败暴露了**：
1. 工具清单不完整（缺 `find_user_id_by_email`）
2. 但 agent 的**兜底策略是对的**（转人工）

## 3. C1 的能力边界图（场景级）

基于 4 个 task 的真实表现：

```
┌─────────────────────────────────────────────────────────────────┐
│            C1 (单 Agent + DeepSeek) 在 retail 场景的能力边界       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ✅ 能做的                                                       │
│  ├── 身份验证（name+zip）                                        │
│  ├── 订单查询                                                    │
│  ├── 产品变体查询                                                │
│  ├── 基本约束匹配（单约束，首选存在）                             │
│  ├── 用户确认                                                    │
│  ├── 多物品一次性 exchange                                       │
│  └── 超出能力时转人工（兜底）                                    │
│                                                                  │
│  ⚠️ 不稳定的                                                     │
│  ├── fallback 推理（首选不存在时的退化策略）                     │
│  │   ├── task 0: 首选存在 → ✓                                    │
│  │   └── task 1: 首选不存在 → 行为可能对但评估器未捕获            │
│  │                                                               │
│  └── 复杂意图理解（用户说 exchange 但实际应该 return）           │
│      └── task 5: agent 做了 exchange，期望 return                │
│                                                                  │
│  ❌ 不能做的                                                     │
│  ├── email 认证（工具缺失）                                      │
│  ├── 动作退化解策（exchange 不可行 → return）                    │
│  ├── 交叉退款判定（违反 policy → 应转人工）                      │
│  │   └── task 10: agent 最终转了人工 ✓，但身份验证卡住了         │
│  └── 情绪处理（用户"骂人"——未测试）                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## 4. 失败模式 → 能力缺口映射

| 失败模式 | 出现在 | 缺失的 CAP | 影响 | C2 能解决吗？ |
|---|---|---|---|---|
| fallback 推理不稳定 | task 1 | CAP-06 变体约束匹配（退化分支） | 首选不存在时行为不确定 | 部分：A3 验证可能捕获，但根因在模型推理 |
| **动作退化解策** | task 5 | **CAP-11（新发现）：exchange→return 退化** | agent 按字面做 exchange，不知该退化为 return | **是：独立验证 Agent 可能发现 exchange 无效** |
| 工具清单不完整 | task 10 | 工具实现缺口（email 认证） | agent 无法完成身份验证 | 否：这是工具层问题，不是架构问题 |
| 评估器粗糙 | task 1 | 评估方法缺口（文本匹配 vs 原生 evaluator） | 无法精确判断 agent 是否真的做对了 | 否：这是评测层问题 |

## 5. 对搜索决策的影响

### BaselineFirst 在场景级的新判据

task 0 单样本上 C1 reward=1.0 → 当初判断"StopSearch, 不试 C2"。

**但场景级数据显示 C1 只有 64% 平均匹配率——C1 没有真正达标。**

**修正的搜索决策**：

```
旧判据（单样本）:
  C1 task0 reward=1.0 → StopSearch
  ↑ 这个结论是错的！

新判据（场景级）:
  C1 avg_match_rate=64% < 验收阈值（如 85%）
  → C1 不达标
  → 继续 C2 或改进 C1 的 θ
```

### C2 的边际价值现在有证据支撑了

| C1 的失败 | C2 怎么解决 | 预期收益 |
|---|---|---|
| 动作退化解策（task 5） | A2 产品专家能判断 exchange 无可行变体 → 建议 return | 可能提升 task 5 从 80% → 100% |
| fallback 推理不稳定（task 1） | A3 验证 Agent 独立检查匹配结果 | 可能提升 task 1 |

**C2 的边际价值在场景级才有意义——单样本（task 0）上 C2 没有价值（C1 已 100%）。**

## 6. 要沉淀什么（回答最初的问题）

### 不是沉淀"C1 能做 task 0"

```
❌ ProjectAsset: {task: retail-0, candidate: C1, reward: 1.0}
   这是历史记录，不是知识。
```

### 是沉淀"C1 在 retail 场景的能力边界"

```
✅ MetaAsset 候选:

  capability_boundary:
    domain: retail
    candidate: C1-single-agent
    model: deepseek-chat
    
    can_do:
      - identity_verification (name+zip)
      - order_query
      - product_variant_query
      - single_constraint_matching (first-choice exists)
      - user_confirmation
      - multi_item_single_exchange
      - human_transfer_fallback
    
    unstable:
      - fallback_deduction (first-choice absent)
      - complex_intent (exchange→return degradation)
    
    cannot_do:
      - email_authentication (tool missing)
      - action_degradation (exchange→return when infeasible)
      - cross_refund_policy_check
    
    performance:
      avg_tool_match_rate: 64%
      full_match_rate: 25% (1/4)
      tested_tasks: 4/114
    
    failure_modes:
      - mode_A: fallback preference not respected
      - mode_B: exchange→return degradation missing
      - mode_C: incomplete tool inventory
    
    applicable_domain_similarity: [retail, customer_service]
    confidence: low (4 tasks, mock evaluator)
    
    next_steps:
      - fix tool inventory (add email auth)
      - add CAP-11 (action degradation) to prompt
      - test on more tasks
      - compare C2 marginal value on failure tasks
```

**这才是"架构要沉淀什么"——不是"我能跑"，而是"我在这个场景的能力边界长什么样、哪里不稳定、什么类型失败、下一步怎么改进"。**

## 7. 发现的新 CAP

| CAP ID | 名称 | 描述 | 发现来源 |
|---|---|---|---|
| **CAP-11** | 动作退化解策 | 当首选动作（exchange）不可行时，判断并退化到合法替代（return） | task 5 失败 |
| CAP-12 | email 认证 | 通过 email 查找用户身份 | task 10 工具缺失 |
| CAP-13 | 情绪处理 | 用户愤怒时的沟通策略 | task 10 场景（未深入测试） |
| CAP-14 | 策略违规检测 | 检测用户请求是否违反业务规则（如交叉退款） | task 10 场景 |

## 8. 下一步

1. **修工具**：补 `find_user_id_by_email` 到 retail_tools_db.py
2. **修 prompt**：加 CAP-11（exchange 不可行→return）到 system prompt
3. **重跑 task 1/5/10**：看修复后的匹配率
4. **扩样本**：跑 task 2（11 actions 最复杂的查询任务）和更多 task
5. **用 τ³-bench 原生 evaluator**：精确评分（替代文本匹配）
6. **试 C2**：在 C1 失败的 task 上跑 C2，验证边际价值
