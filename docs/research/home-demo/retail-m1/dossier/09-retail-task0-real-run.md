# AgentFit retail task 0 真实运行记录（DeepSeek + opencode）

> 状态：真实模型运行（非设计模拟）。这是 AgentFit 第一次用真实 LLM + 工具调用跑通完整流程的证据。
>
> 运行时间：2026-08-13
>
> 模型：`deepseek/deepseek-chat`（免费 API）
>
> 环境：opencode CLI（非 τ³-bench 原生框架）+ 自建 retail mock 工具
>
> **重要边界**：这不是 τ³-bench 原生 eval，不是 AgentFit Candidate/EvaluationUnit。它验证了 C1（单 Agent）+ DeepSeek + 工具调用能否完成 task 0 的逻辑流程。reward 基于我们的 mock evaluator，非 τ³-bench 官方。

## 1. 运行方式

- **Agent**：opencode CLI（支持工具调用 + bash 执行）
- **Model**：`deepseek/deepseek-chat`
- **工具**：`retail_mock_tool.py`（self-contained，5 个工具）
- **Prompt**：retail policy.md 全文 + task 0 用户场景 + 工具用法说明

没有用 τ³-bench 原生 runner。Mock 工具是自建的，模拟 τ³-bench retail 数据库和工具行为。

## 2. Agent 完整工具调用轨迹（Trace）

| 步 | 工具 | 参数（关键） | 结果 | 对应期待 action |
|---:|---|---|---|---|
| 1 | `find_user_id_by_name_zip` | `{first_name: Yusuf, last_name: Rossi, zip: 19122}` | `user_id: 10201` | `0_0` ✅ |
| 2 | `get_order_details` | `{order_id: #W2378156}` | delivered, 2 items, total $219.98 | `0_1` ✅ |
| 3 | `get_product_details` | `{product_id: 1656367028}` | 键盘 4 变体 | `0_2` ✅ |
| 4 | `get_product_details` | `{product_id: 4896585277}` | 温控器 3 变体 | `0_3` ✅ |
| 5 | `exchange_delivered_order_items` | 见下 | `exchange_requested` | `0_4` ✅ |

### 第 5 步（exchange）参数

Agent 选出的参数**与 sealed holdout 完全一致**：

```json
{
  "order_id": "#W2378156",
  "item_ids": ["1151293680", "4983901480"],
  "new_item_ids": ["7706410293", "7747408585"],
  "payment_method_id": "credit_card_9513926"
}
```

## 3. 变体匹配决策（Agent 推理的关键）

用户需求：键盘要 `clicky + RGB + full_size`，温控器要 `Google Home` 兼容。

### 键盘（product 1656367028，4 变体）

| item_id | switch | backlight | size | 符合？ |
|---|---|---|---|---|
| 1151293680 | tactile | RGB | full | ❌（tactile 不是 clicky）|
| **7706410293** | **clicky** | **RGB** | **full** | ✅ **Agent 选中** |
| 8812540634 | linear | RGB | full | ❌ |
| 9923651745 | clicky | none | full | ❌（无背光）|

agent 正确辨识 `clicky + RGB + full_size` 存在的唯一变体 = **7706410293**。fallback（无背光）未被触发，因为首选存在。

### 温控器（product 4896585277，3 变体）

| item_id | compatibility | 符合？ |
|---|---|---|
| 4983901480 | Apple HomeKit | ❌（用户要换掉）|
| **7747408585** | **Google Home** | ✅ **Agent 选中** |
| 6655299472 | Amazon Alexa | ❌ |

## 4. Policy 遵守检查

| policy 规则 | Agent 表现 | 通过 |
|---|---|---|
| 身份验证（email或姓名+zip）| 第 1 步就验证 | ✅ |
| 换货前检查订单状态 | 确认 delivered | ✅ |
| 用户确认后才执行 | 明确列出计划 + 等用户 yes | ✅ |
| exchange 只调一次 | 多物品收集齐才准备调用 | ✅ |
| 一次一个工具调用 | 每步一个工具调用 | ✅ |
| 价格差处理 | 识别 $0 差价，质疑是否需要 payment；提示不用付差价 | ✅ |

### 一个政策细节发现

Agent 指出：价格差 $0，**技术上不需要 payment_method_id**。但在密封答案里 `payment_method_id` 是 `credit_card_9513926`。

- τ³-bench 的 DB 检查可能要求传送这个字段
- 或可能允许 null（价格差 0 时）
- **这暴露了一个潜在分歧**：真实 agent 合理地质疑了参数，但密封答案要求传信用卡。这需要 M3 真实 eval 才知道 τ³-bench evaluator 怎么判。

## 5. 运行结论

### task 0 预测结果

| 候选 | 预测 task_success | 本次真实验证 |
|---|---|---|
| C1（单 Agent + DeepSeek） | 60-95%（依赖模型） | **~100%（本 mock 场景，5/5 步骤正确，item_id 全对）** |

### 验证的假设

1. ✅ **C1 能做约束匹配**：DeepSeek 成功从 4 键盘变体选对 clicky+RGB+full，从 3 温控器变体选对 Google Home
2. ✅ **C1 遵守 policy**：身份验证、用户确认、单工具调用全对
3. ✅ **变体 item_id 与密封答案完全一致**：7706410293 + 7747408585
4. ✅ **fallback 推理存在**：agent 检查了 fallback 但未触发（首选存在）

### 未验证的（需要 τ³-bench 原生 eval）

- ❌ τ³-bench 官方 evaluator 的 DB 检查是否接受我们的参数
- ❌ 1000 次运行的稳定性（本 mock 只跑了一次）
- ❌ 其他 41 个 retail task 的泛化
- ❌ 模型不确定性（temperature 用 0 需重验）

## 6. 对设计文档的反馈

### C1 是最简合格者（本 mock 范围）

- C0（Agentless）无法做变体约束匹配（变体解析 + fallback 推理超出规则能力）
- C1（单 Agent + DeepSeek）在 task 0 上**完整跑通**
- C2（多 Agent）未测试，但本 mock 表明 C1 已达标——**Baseline-first 应在此停止，不试 C2**

**这验证了 AgentFit 的核心主张：先跑最简候选，达标就停。**

### 搜索引擎的价值在真实运行下更清晰

这次真实运行产生了**真实 TrialRecord 的原料**：
- theta = {prompt: retail_policy_full, model: deepseek-chat, max_steps: 未设, temperature: 默认}
- metrics = {reward: 1.0 (本 mock), action_match: 4/4 步骤, item_match: 2/2 变体}
- cost = {约 8k tokens, 5 次工具调用, 真实延迟}
- trace = 本文件第 2 节

这就是 Trial Tracker 要记录的东西——真实数字，不是预测。

## 7. 遗留

- [ ] 用 τ³-bench 原生 runner 复跑（需 litellm 装好 + 免费模型配置）
- [ ] 多 task 稳定性测试
- [ ] 与 sealed holdout 的正式对比（tau2 evaluator）
- [ ] 记录到 AgentFit 搜索结果（非 preflight-only，而是 design+smoke evidence）
