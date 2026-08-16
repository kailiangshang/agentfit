# AgentFit 落地设计：真实实现架构

> 基于四层骨架 v4-FINAL，设计 AgentFit 的真实实现。回答"代码怎么写、组件怎么组合、数据怎么流转"。

---

## 一、系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         用户                                     │
│    提供材料+样本+评价 → 审核更新建议 → 接收交付                    │
└──────────┬──────────────────────────────────────┬───────────────┘
           │                                       │
           ▼                                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AgentFit 训练系统                              │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              训练循环控制器 (train_loop.py)                 │  │
│  │  管理轮次、预算、收敛判定、λ 调节、安全约束                    │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │ 数据工程      │  │ 方案管理      │  │ 损失归因器            │ │
│  │ (data.py)    │  │ (solution.py)│  │ (attribution.py)     │ │
│  │              │  │              │  │                      │ │
│  │ 样本解析      │  │ L1-L4 CRUD  │  │ 自底向上 L1→L4      │ │
│  │ 聚类分析      │  │ 依赖验证     │  │ 因果性验证           │ │
│  │ 批次构建      │  │ 版本管理     │  │ 附带问题记录         │ │
│  │ 回归池管理    │  │ 原子事务     │  │ 正则指标计算         │ │
│  └──────────────┘  └──────────────┘  └──────────────────────┘ │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │ 执行适配器    │  │ 回归验证器    │  │ 监控协程              │ │
│  │(executor.py) │  │(regression.py)│  │(monitor.py)         │ │
│  │              │  │              │  │                      │ │
│  │ τ²-bench    │  │ 旧样本重跑    │  │ 漂移检测             │ │
│  │ 自建模拟器   │  │ 遗忘检测     │  │ 预算告警             │ │
│  │ 影子模式     │  │ 回滚触发     │  │ 正则追踪             │ │
│  └──────────────┘  └──────────────┘  └──────────────────────┘ │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              训练日志 (training_log.py)                     │  │
│  │  哈希链保护 · 通过率 · 损失分布 · 更新记录 · 回归 · λ       │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 二、核心数据结构

### Solution（方案）

```python
@dataclass
class Solution:
    version: int
    L1_atoms: list[SolidAtom]           # 原子能力
    L2_tools: list[CapabilityTool]       # 安全封装
    L3_knowledge: list[Knowledge]        # 路由/Skill/链/阈值/经验
    L4_topology: Topology                # Agent 架构
    regularization_state: RegState       # 正则指标当前值
    lambda_values: dict[str, float]      # λ₁~λ₄ 当前值
```

### SolidAtom（L1 原子）

```python
@dataclass
class SolidAtom:
    id: str                    # "toggle_roaming"
    type: str                  # "read" | "write" | "human" | "notify"
    backend: str               # "telecom_api" | "human_finance_team"
    input_schema: dict         # 参数定义
    output_schema: dict        # 返回值定义
    description: str           # 人可读描述
```

### CapabilityTool（L2 工具）

```python
@dataclass
class CapabilityTool:
    id: str                    # "safe_toggle_roaming"
    wraps: list[str]           # L1 原子 ID 列表
    preconditions: list[str]   # 执行前检查
    postconditions: list[str]  # 执行后记录
    human_gate: HumanGate | None  # 人工审批条件
    aggregation_logic: str | None  # 组合/口径逻辑
```

### Knowledge（L3 知识）

```python
@dataclass
class Knowledge:
    id: str                    # "roaming_routing"
    type: str                  # "skill" | "routing_rule" | "chain" | "threshold" | "experience"
    # 路由规则
    condition: str | None      # "no_data AND abroad AND roaming_off"
    dispatches_to: str | None  # L2 工具 ID（调度，不是调用）
    # 排查链
    steps: list[ChainStep] | None  # 有序步骤
    # 经验
    lesson: str | None         # 教训内容
    evidence_sample_ids: list[str]  # 来源样本
```

### Topology（L4 拓扑）

```python
@dataclass
class Topology:
    agents: list[Agent]
    edges: list[TopologyEdge]      # Agent 间通信边
    human_gates: list[HumanGatePosition]
    trigger_mode: str             # "passive" | "proactive" | "scheduled" | "event"

@dataclass
class TopologyEdge:
    from_agent: str
    to_agent: str
    payload_type: str  # "L3_decision" | "L3_diagnosis" | "L3_route_result"
```

### LossTrace（损失轨迹）

```python
@dataclass
class LossTrace:
    sample_id: str
    root_cause_layer: str       # "L1" | "L2" | "L3" | "L4" | "human" | "eval_error"
    root_cause_element: str     # 具体的原子/工具/知识/Agent ID
    failure_mode: str           # "missing_atom" | "tool_error" | "routing_error" | ...
    detail: str                 # 人可读描述
    evidence: dict              # 执行轨迹关键步骤
    confidence: float           # 归因置信度
    side_issues: list[SideIssue]  # 附带问题（不阻塞但记录
```

---

## 三、核心算法

### 训练循环

```python
def train(initial_solution, sample_pool, evaluation, config):
    solution = initial_solution
    regression_pool = RegressionPool()
    training_log = TrainingLog()
    
    for epoch in range(config.max_epochs):
        # ① 前向
        batch = sample_pool.next_batch(config.batch_size)
        traces = execute_batch(solution, batch, config.executor)
        
        # ② 损失归因
        loss_traces = []
        for trace, sample in zip(traces, batch):
            if trace.result != "PASS":
                lt = attribute_loss(sample, trace, evaluation, solution)
                if lt:
                    loss_traces.append(lt)
        
        # ③ 聚合 + 正则
        aggregated = aggregate_losses(loss_traces)
        reg_metrics = compute_regularization(solution, traces)
        
        # ④ 反向传播
        proposals = generate_update_proposals(aggregated, reg_metrics)
        
        # ⑤ λ 调节
        lambda_adjustments = check_lambda_adjustment(reg_metrics, config)
        
        # ⑥ 人审
        approved = human_review_gate(proposals, lambda_adjustments)
        
        # ⑦ 应用（原子事务）
        if approved:
            transaction = ChangeTransaction(solution, approved)
            new_solution = transaction.execute()  # commit or rollback
        
        # ⑧ 回归
        regression_result = validate_regression(new_solution, regression_pool)
        if regression_result.status == "FAIL":
            transaction.rollback()
            continue
        
        # ⑨ 日志
        solution = new_solution
        training_log.append(epoch, solution, traces, loss_traces,
                          reg_metrics, approved, regression_result)
        regression_pool.update(traces, batch)
        
        # 收敛检查
        if check_convergence(training_log, config):
            break
    
    return build_delivery(solution, training_log)
```

### 反向归因

```python
def attribute_loss(sample, trace, evaluation, solution):
    """自底向上逐层检查，找到即验证（因果性校验）。"""
    
    side_issues = []
    
    # Step 1: L1
    for expected_action in sample.expected.actions:
        if expected_action.tool not in solution.L1_atoms:
            if is_root_cause(expected_action.tool, trace, "missing"):
                return LossTrace(layer="L1", ...)
            else:
                side_issues.append(...)
    
    # Step 2: L2
    for step in trace.steps:
        if step.layer == "L2" and step.has_error:
            if is_on_critical_path(step, trace):
                return LossTrace(layer="L2", ...)
            else:
                side_issues.append(...)
    
    # Step 3: L3
    actual_path = extract_path(trace)
    expected_path = sample.expected.actions
    if actual_path != expected_path:
        if is_root_cause(actual_path, expected_path, trace):
            return LossTrace(layer="L3", ...)
        else:
            side_issues.append(...)
    
    # Step 4: L4（含前置检查）
    if sample.complexity == "compound" and solution.L4_topology.agents == 1:
        return LossTrace(layer="L4", ...)
    
    # 前置检查：真的需要 AI 吗？
    if sample.requires_human:
        return LossTrace(layer="human", ...)
    if sample.expected_uses_missing_atoms:
        return attribute_loss(...)  # 回到 L1
    return LossTrace(layer="eval_error", ...)
```

---

## 四、文件结构

```
agentfit/
├── LICENSE                          # MIT
├── docs/
│   ├── agentfit-skeleton.md        # 四层骨架（定稿，不改）
│   ├── agentfit-solution.md        # 方案文档
│   ├── agentfit-implementation.md  # 本文件
│   ├── test-scenario.md            # 测试场景执行方案
│   └── README.md                   # 入口
├── src/agentfit/
│   ├── __init__.py
│   ├── models/                     # 数据结构
│   │   ├── solution.py             # Solution, SolidAtom, CapabilityTool, ...
│   │   ├── loss.py                 # LossTrace, SideIssue
│   │   └── config.py               # TrainingConfig, LambdaConfig
│   ├── core/                       # 核心算法
│   │   ├── train_loop.py           # 训练循环控制器
│   │   ├── attribution.py          # 反向归因器
│   │   ├── aggregation.py          # 损失聚合分析器
│   │   ├── regularization.py       # 正则指标计算
│   │   ├── regression.py           # 回归验证器
│   │   └── transaction.py          # ChangeTransaction
│   ├── data/                       # 数据工程
│   │   ├── sample_pool.py          # 样本池管理
│   │   ├── clustering.py           # 聚类分析
│   │   └── batch.py                # 批次构建
│   ├── executors/                  # 执行环境适配
│   │   ├── base.py                 # 执行器接口
│   │   └── tau2bench.py            # τ²-bench 适配器
│   ├── solution/                   # 方案管理
│   │   ├── builder.py              # 初始方案构建
│   │   ├── validator.py            # 依赖验证 + 同层约束检查
│   │   └── versioning.py           # 版本管理
│   ├── monitoring/                 # 监控
│   │   ├── monitor.py              # 监控协程
│   │   └── drift.py               # 漂移检测
│   ├── log/                        # 训练日志
│   │   ├── training_log.py         # 哈希链日志
│   │   └── report.py              # 报告生成
│   └── delivery/                   # 交付
│       ├── package.py              # 方案打包
│       └── boundary.py             # 适用边界
└── tests/
    ├── test_attribution.py
    ├── test_regularization.py
    ├── test_transaction.py
    ├── test_regression.py
    └── test_scenarios/
        ├── test_telecom.py
        └── test_ecommerce.py
```

---

## 五、执行环境适配器设计

执行环境是可插拔的。任何系统只要实现三个接口就能作为 AgentFit 的执行环境：

```python
class ExecutorBase(ABC):
    """执行环境接口。τ²-bench、自建模拟器、生产影子模式都实现这个接口。"""
    
    @abstractmethod
    def execute(self, solution: Solution, sample: Sample) -> Trace:
        """用当前方案执行一个样本，返回执行轨迹。"""
        ...
    
    @abstractmethod
    def evaluate(self, trace: Trace, expected: Expected) -> Result:
        """评测一个执行轨迹，返回通过/失败。"""
        ...
    
    @abstractmethod
    def replay(self, solution: Solution, samples: list[Sample]) -> list[Result]:
        """批量重跑（用于回归验证）。"""
        ...



class Tau2BenchExecutor(ExecutorBase):
    """τ²-bench 适配器。"""
    
    def execute(self, solution, sample):
        # 把 Solution 转换为 τ²-bench 可理解的 agent 配置
        # 调用 τ²-bench 执行
        # 把结果转换为 AgentFit 的 Trace 格式
        ...
    
    def evaluate(self, trace, expected):
        # 调用 τ²-bench 的 evaluator
        # 转换为 AgentFit 的 Result 格式
        ...
```

---

## 六、ChangeTransaction 实现

```python
class ChangeTransaction:
    """级联变更的原子性保障。"""
    
    def __init__(self, solution: Solution, changes: list[UpdateProposal]):
        self.solution = solution
        self.changes = changes
        self.snapshot = None
        self.status = "PENDING"
    
    def execute(self) -> Solution:
        self.snapshot = deepcopy(self.solution)
        self.status = "IN_PROGRESS"
        
        try:
            # 按自底向上顺序应用
            for change in sorted(self.changes, key=lambda c: c.layer):
                self._apply(change)
            
            # 验证依赖完整性
            errors = validate_existence_dependencies(self.solution)
            if errors:
                raise ValidationError(errors)
            
            # 验证通过依赖验证
            self._commit()
            return self.solution
            
        except Exception:
            self._rollback()
            raise
    
    def _commit(self):
        self.solution.version += 1
        self.status = "COMMITTED"
    
    def _rollback(self):
        self.solution = self.snapshot
        self.status = "ROLLED_BACK"
```
