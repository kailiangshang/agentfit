# S5 · validation_skill（Validator）

> 结构、训练边界与候选选择验证（纯确定性） · 元层 L3 知识，稳定正本由 Git 记录演化

## 步骤

1. validate_existence_dependencies 全链无悬空
2. 同层约束检查（dispatch 与 invocation 区分）
3. 检查一个 Epoch 完整且不重复地覆盖 adaptation manifest
4. 区分 adaptation 回归、可选 train_replay 与 Epoch 末 validation
5. Validation 不产生 ChangeProposal，不把样本、标签或逐样本结论交给 Architect
6. 依据 validation、Objective、预算和停止窗口选择、恢复或停止 Candidate
7. 结构性正则计算与确定性裁决
