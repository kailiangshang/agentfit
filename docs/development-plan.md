# AgentFit 稳定收敛与闭环开发计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `test-driven-development` task-by-task. Every behavior change must show RED before GREEN.

**Goal:** 将现有算法原型收敛为单正本、证据可信、平台解耦且可端到端验证的 Agent 方案训练系统。

**Architecture:** `src/agentfit` 持有稳定领域合同、确定性训练内核和通用适配器接口；`bridges` 负责 AgentTeams 与 τ²-bench 转换。活构件稳定命名，运行快照用内容哈希和 run ID 标识。

**Tech Stack:** Python 3.10+、dataclasses、pytest、JSON/YAML、AgentTeams 桥接脚本、τ²-bench 桥接脚本。

## Global Constraints

- `competition/2026-08-16/submission/` 冻结，不得修改。
- 不在 `src/agentfit` 中导入 AgentTeams、τ²-bench 或供应商 SDK。
- 活构件只有稳定名称；Git 记录演化。
- 协议、包、依赖版本和不可变运行证据身份可以保留。
- 所有结论必须能从 RunStore 真实证据重算。
- 生产 Human Gate 默认阻断；自动批准只允许显式测试注入。

---

### Task 1: 单正本与冻结门禁

**Files:**
- Modify: `docs/README.md`
- Delete after consolidation: `docs/agentfit-skeleton.md`
- Delete after consolidation: `docs/agentfit-solution.md`
- Delete after consolidation: `docs/agentfit-implementation.md`
- Modify: `src/agentfit/skills/*.md`
- Modify: `tests/test_decoupling.py`
- Create: `tests/test_repository_policy.py`

**Interfaces:**
- Consumes: Git tracked-file list and the frozen submission tree.
- Produces: `find_policy_violations(repo: Path) -> list[str]` and a single architecture document.

- [ ] Write failing tests that reject version/stage suffixes in active filenames, forbidden active prose, duplicate architecture documents and changes to the frozen path.
- [ ] Run `pytest tests/test_repository_policy.py tests/test_decoupling.py -q` and confirm failures identify the existing documents, Skill metadata and bridge example.
- [ ] Consolidate active architecture prose into `docs/architecture.md`, remove overlapping documents, remove Skill version sections, and update README links.
- [ ] Replace the old “Skill must carry a version” test with Registry/loadability and stable-name assertions.
- [ ] Re-run focused tests and the full suite.
- [ ] Commit the independently reviewable policy change.

### Task 2: 可信证据缺陷

**Files:**
- Modify: `src/agentfit/core/regularization.py`
- Modify: `src/agentfit/core/proposals.py`
- Modify: `src/agentfit/agents/orchestrator.py`
- Modify: `src/agentfit/delivery/package.py`
- Modify: `bridges/tau2bench/results_to_runstore.py`
- Create: `tests/test_evidence_integrity.py`

**Interfaces:**
- Produces: `stable_element_id(prefix: str, payload: object) -> str`.
- Produces: structured solution-package JSON and honest hash-chain status.

- [ ] Write a failing λ test proving empty over-threshold lists never increment a streak.
- [ ] Write a cross-process deterministic-ID test for equivalent proposal evidence.
- [ ] Write a boundary test proving `requires_human=True` is reported as Human-required even when the Episode succeeds.
- [ ] Write a package-schema test proving agents and topology edges are JSON objects, not strings.
- [ ] Write a τ² conversion test proving an empty or invalid hash chain cannot be marked valid.
- [ ] Implement the minimum fixes, re-run each RED test to GREEN, then run all tests.
- [ ] Commit the evidence-integrity change.

### Task 3: 样本、Manifest 与评价身份

**Files:**
- Create: `src/agentfit/models/sample.py`
- Create: `src/agentfit/models/manifest.py`
- Modify: `src/agentfit/models/loss.py`
- Modify: `src/agentfit/data/sample_pool.py`
- Modify: `src/agentfit/store/run_store.py`
- Create: `tests/test_sample_contract.py`

**Interfaces:**
- Produces: `SourceObservation`, `TaskSample`, `Episode`, `SampleRef`.
- Produces: `SampleSetManifest`, `AccessPolicy`, `FreezeDecision`.
- Produces: `EvaluationIdentity(candidate_ref, sample_ref, run_index)`.

- [ ] Write failing construction and validation tests for all contract types.
- [ ] Require exactly four distinct set purposes and immutable content hashes.
- [ ] Require Human Freeze before candidate generation and enforce sealed-holdout access after candidate freeze.
- [ ] Persist manifest references and evaluation identity in RunStore.
- [ ] Add compatibility conversion from current `Sample` inputs without weakening the new contract.
- [ ] Run contract tests and the full suite, then commit.

### Task 4: 元层角色、Skill Registry 与 Human Gate

**Files:**
- Create: `src/agentfit/agents/steward.py`
- Create: `src/agentfit/agents/attributor.py`
- Create: `src/agentfit/agents/architect.py`
- Create: `src/agentfit/agents/validator.py`
- Create: `src/agentfit/skills/registry.py`
- Create: `src/agentfit/gates/human.py`
- Modify: `src/agentfit/agents/team.py`
- Modify: `src/agentfit/agents/orchestrator.py`
- Create: `tests/test_runtime_contract.py`

**Interfaces:**
- Produces: `SkillRegistry.load() -> dict[str, SkillDefinition]`.
- Produces: `HumanGatePolicy.review(request: ReviewRequest) -> ReviewDecision`.
- Produces: role handlers with typed TaskMsg/ResultMsg boundaries.

- [ ] Write failing tests proving Skill files are loaded once and role manifests derive from Registry output.
- [ ] Write failing tests for G0/G1/G2/G3 default-block behavior and explicit test approval.
- [ ] Write failing tests for low-confidence, topology and budget escalation.
- [ ] Split the four embedded role handlers into focused modules and wire them through MessageBus.
- [ ] Make payload references and context chains epoch-correct.
- [ ] Run focused tests and full suite, then commit.

### Task 5: 核心 CLI 与结构化交付

**Files:**
- Create: `src/agentfit/cli.py`
- Create: `src/agentfit/__main__.py`
- Create: `src/agentfit/delivery/boundary.py`
- Modify: `src/agentfit/delivery/package.py`
- Modify: `pyproject.toml`
- Create: `tests/test_cli.py`

**Interfaces:**
- Produces: `agentfit validate`, `agentfit train`, `agentfit report`, `agentfit export`.
- Produces: canonical `solution_package`, `evidence_package`, and bridge input manifest.

- [ ] Write failing CLI help, invalid-input and simulator-run tests.
- [ ] Implement the stable command surface without platform-specific imports.
- [ ] Export structured L1-L4 objects, gates, provenance and content hashes.
- [ ] Generate boundary analysis from Samples and Episodes rather than failure-only traces.
- [ ] Run CLI tests and full suite, then commit.

### Task 6: AgentTeams 与 τ²-bench 桥接闭环

**Files:**
- Create: `bridges/agentteams/render_team.py`
- Modify: `bridges/agentteams/team.yaml`
- Modify: `bridges/agentteams/apply_team.py`
- Modify: `bridges/agentteams/export_solution.py`
- Modify: `bridges/agentteams/import_results.py`
- Modify: `bridges/tau2bench/run_bench.py`
- Modify: `bridges/tau2bench/results_to_runstore.py`
- Create: `tests/test_bridges.py`

**Interfaces:**
- Produces: stable Team manifest `metadata.name=agentfit` from canonical Registry data.
- Produces: `reconcile_status(expected, actual) -> DriftReport`.
- Produces: τ² TaskSample/Episode converters and RunStore ingestion.

- [ ] Write failing tests for stable deployment names, generated role/Skill content and deployment drift.
- [ ] Write failing fixture-driven τ² conversion tests for task, reward, trace, cost and compound failures.
- [ ] Remove deployment version suffixes and stale manifest examples.
- [ ] Render the Team manifest and compare it with the checked-in canonical bridge output.
- [ ] Run fixture tests without requiring Docker.
- [ ] Reconcile the live AgentTeams deployment only after read-only drift output identifies exact deletions and creations.
- [ ] Run a real bridge smoke, capture immutable evidence and commit.

### Task 7: 全链验收与开源维护

**Files:**
- Modify: `tests/test_full_chain.py`
- Modify: `docs/README.md`
- Modify: `docs/test-scenario.md`
- Create: `CONTRIBUTING.md`
- Create: `SECURITY.md`

**Interfaces:**
- Consumes all prior task interfaces.
- Produces a reproducible local simulator path and separately evidenced real-platform path.

- [ ] Extend the full-chain test through material, freeze, candidate, Episode, attribution, update, regression and delivery.
- [ ] Add repository-policy, contract, bridge-fixture and frozen-submission gates to the standard test command.
- [ ] Replace nonexistent commands and aspirational output trees in user documentation with verified commands and artifacts.
- [ ] Run compile, full tests, repository scans, manifest validation and Git diff checks.
- [ ] Perform an independent code review against `docs/architecture.md`; fix all Critical and Important findings.
- [ ] Commit and push the complete main branch after confirming remote fast-forward safety.
