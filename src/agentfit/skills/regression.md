# S6 · regression_skill（Validator）

> 回归验证（纯确定性） · 元层 L3 知识，可版本化重训练

## 步骤

1. 回归池分层抽样
2. 逐样本 replay
3. 曾通过现在失败 = 遗忘
4. 遗忘率>0 → ROLLBACK；=0 → COMMIT

## 版本

1.0.0