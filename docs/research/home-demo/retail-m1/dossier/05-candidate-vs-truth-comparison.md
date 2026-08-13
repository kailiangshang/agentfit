# task 0 候选设计 vs 真实期望答案对比

> 状态：设计演练，非运行证据。以下是基于 task-0.json 的 evaluation_criteria 与候选设计的静态对比分析，不含任何模型运行结果。

## 真实期望答案（sealed holdout，对比用）

task 0 期望 agent 执行 5 个工具调用，无自然语言断言：

| 步 | 工具 | 参数 | 目的 |
|---:|---|---|---|
| 1 | `find_user_id_by_name_zip` | Yusuf / Rossi / 19122 | 身份验证（policy 强制） |
| 2 | `get_order_details` | #W2378156 | 确认订单存在 + 状态 delivered |
| 3 | `get_product_details` | product_id=1656367028 | 查键盘变体（找 clicky+RGB+full size，或 fallback no backlight） |
| 4 | `get_product_details` | product_id=4896585277 | 查温控器变体（找 Google Home 兼容） |
| 5 | `exchange_delivered_order_items` | item_ids=[1151293680, 4983901480] → new_item_ids=[7706410293, 7747408585] | 执行换货 |

### 关键推断：变体映射

从 item_ids 推断：

| 原始 item_id | → 新 item_id | 用户约束 | 推断 |
|---|---|---|---|
| 1151293680 | 7706410293 | 键盘：clicky + RGB + full size，否则 no backlight | 7706410293 满足其中一种组合 |
| 4983901480 | 7747408585 | 温控器：Google Home 兼容（非 Apple HomeKit） | 7747408585 是 Google Home 兼容款 |

支付方式：`credit_card_9513926`（用户已有的信用卡，用于支付差价）。

### fallback 是否被触发？

用户说 "If there is no keyboard that is clicky, RGB backlight, full size, you'd go for no backlight."

期望答案是 item 7706410293——但我们**无法仅从 task.json 判断这个 item 是 clicky+RGB 还是 no backlight**，因为产品变体详情在 mock server 运行时注入，不在 task.json 里。

**这正是 CAP-06（变体约束匹配）的核心挑战：agent 必须在运行时查 get_product_details，解析返回的 variant 列表，按约束过滤+ fallback 推理，才能得到正确的 item_id。这不是硬编码能解决的。**

---

## 逐候选对比

### C0（Agentless 固定流程）vs 真实答案

| 步 | 真实期望 | C0 能否执行 | 差距 |
|---:|---|---|---|
| 1 | find_user_id_by_name_zip | ✅ 能。关键词匹配到"Yusuf Rossi 19122"→ 调用 find_user | — |
| 2 | get_order_details(#W2378156) | ✅ 能。用户提到订单号 → 调用 get_order_details | — |
| 3 | get_product_details(1656367028) | ⚠️ 半能。能查产品，但**不知道哪个 product_id 对应键盘** | 需要从 order_details 返回值里解析 item → product_id 映射。C0 的规则可以硬编码"item 的 parent product_id"提取逻辑 |
| 4 | get_product_details(4896585277) | ⚠️ 同上 | 同上 |
| 5 | exchange(1151293680→7706410293) | ❌ **不能**。C0 无法做变体约束匹配 | **这是 C0 的致命点**：7706410293 是哪个变体？clicky？no backlight？需要解析 product_details 返回的 variant 列表，按"clicky+RGB+full size → 否则 no backlight"过滤。规则引擎无法处理自然语言约束 + fallback 逻辑 |

**C0 预测失败点：第 5 步的变体匹配。** 步骤 1-4 可能通过，但第 5 步大概率选错 item_id。

**C0 vs 真实：action_match_rate 预测 4/5（80%），但 task_success = 0（最后一步失败 = reward 0）。**

---

### C1（单 Agent）vs 真实答案

| 步 | 真实期望 | C1 能否执行 | 关键依赖 |
|---:|---|---|---|
| 1 | find_user_id_by_name_zip | ✅ | system prompt 包含 policy（必须验证身份） |
| 2 | get_order_details | ✅ | 从用户消息提取订单号 |
| 3-4 | get_product_details ×2 | ✅ | 从 order_details 返回解析出 item 的 product_id |
| 5 | exchange(correct item_ids) | 🟡 **依赖模型推理能力** | 必须解析 product variant 列表 + 约束匹配 + fallback |

**C1 在步骤 5 的核心挑战**：

agent 收到 get_product_details 返回后，需要：
1. 解析 variant 列表（每个 item_id + 属性描述）
2. 对键盘：找 clicky + RGB + full size → 如果存在选它，否则找 no backlight
3. 对温控器：找 Google Home 兼容
4. 把两个 new_item_id 收集到同一个 exchange 调用（policy 限制只调一次）

**这是一个单 Agent 的 ReAct SCC 能处理的吗？** 理论上能——LLM 可以多步推理。但风险是：
- 上下文可能很长（两件商品的所有变体信息）
- 约束推理出错（选了 tactile 而不是 clicky）
- 遗漏 fallback（直接选 clicky 而不检查 RGB+full size）
- 过早调用 exchange（只收集了一件就调，违反"只能调一次"）

**C1 vs 真实：task_success 预测取决于模型。弱模型可能 60-70%；强模型（GPT-4 级）可能 85-95%。**

---

### C2（多 Agent）vs 真实答案

| 步 | 真实期望 | C2 能否执行 | 与 C1 的差异 |
|---:|---|---|---|
| 1 | find_user_id | ✅ A1 执行 | 同 C1 |
| 2 | get_order_details | ✅ A1 执行 | 同 C1 |
| 3-4 | get_product_details ×2 | ✅ **A2 执行** | A1 把约束传给 A2，A2 查产品+匹配 |
| 5 | exchange | ✅ A1 执行，A3 可验证 | A2 返回匹配结果给 A1；可选 A3 独立检查 |

**C2 在步骤 5 的差异**：

A2（产品专家）有独立上下文，专门处理变体信息——**理论上上下文更干净**（不会被用户对话历史污染）。

A3（独立验证）可以检查 A2 的匹配是否正确——**理论上能捕获 A2 的错误**。

**但**：
- A1 必须把约束**准确传递**给 A2（"clicky + RGB + full size，否则 no backlight"→ A2 需要完整理解这个 fallback 逻辑）
- A2 返回的 item_id 必须**原样传递**给 A1 的 exchange 调用
- 每多一次 Agent 间通信 = 多一次信息丢失风险

**C2 vs 真实：task_success 可能略高于 C1（如果 A3 验证有效），但也可能略低（如果通信损耗 > 验证收益）。这是需要 M3 证据的核心问题。**

---

## 对比结论

### 核心洞察：task 0 的难度不在"调对工具"，在"选对变体"

5 步工具调用里，前 4 步（身份验证、查订单、查产品）几乎所有候选都能做。**真正的分水岭是第 5 步：从产品变体列表里选出正确的 new_item_id。**

这正好验证了 AgentFit 的核心主张：

> "该用几个 Agent"不是拍脑袋决定的。task 0 的核心能力是变体约束匹配（CAP-06），这个能力决定了 C0 失败、C1 可能成功、C2 是否值得。

### 预测矩阵（需要 M3 真实验证）

| 候选 | 步骤 1-4 | 步骤 5（变体匹配） | task_success 预测 | 最简合格者？ |
|---|---|---|---|---|
| C0 | ✅ | ❌ 规则无法做约束推理 | ~0% | 否 |
| C1 | ✅ | 🟡 依赖模型推理 | 60-95% | **可能** |
| C2 | ✅ | 🟡 A2 匹配 + A3 验证 | 65-95% | 取决于边际价值 |
| C3 | ✅ | ✅ 人工能做 | ~100% | 安全但不可扩展 |

### Baseline-first 判据应用

按 AgentFit 纪律：
1. 先跑 C0 → 预期在第 5 步失败 → 证明约束匹配超出规则能力
2. 跑 C1 → 如果 task_success ≥ 阈值 → **C1 是最简合格者**
3. 只在 C1 不达标时跑 C2
4. C2 的独立验证（A3）必须证明：它捕获的错误数 > 它增加的通信成本

**这是 AgentFit "搜索"的真正含义：不是试所有候选，是按复杂度从低到高搜索，找到第一个合格的就停。**

### 与 S1 演练发现的一致性

S1 演练时发现 task 0 的核心复杂度在 CAP-06（变体约束匹配）。真实答案的对比**证实了这个判断**——第 5 步的 item_id 选择是唯一真正困难的决策点。

---

## 无法静态确定的问题（需要运行）

| 问题 | 为什么静态无法回答 | 需要 |
|---|---|---|
| C1 的实际成功率 | 取决于模型推理能力 + prompt 设计 | M3 真实运行 |
| C2 的 A3 验证是否有效 | 取决于 A3 能否发现 A2 的错误 | M3 真实运行 |
| fallback 是否被触发 | 7706410293 是 clicky 还是 no backlight？ | 运行 get_product_details 看返回 |
| C2 通信损耗 vs 验证收益 | 依赖具体实现 | M3 真实运行 |

**以上全部标注 requires_runtime_trial。**
