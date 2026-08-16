# 开放与合规披露

## 开源承诺

- **License**: MIT
- **开源范围**: 四层骨架文档、训练循环代码、测试场景、示例
- **仓库地址**: https://github.com/kailiangshang/agentfit
- **持续维护**: 骨架定稿后不再变更，实现驱动迭代

## 依赖清单

| 依赖 | 角色 | License |
|---|---|---|
| τ²-bench | 执行+评测环境 | MIT |
| DeepSeek API | LLM 提供者 | 商业 API |
| AgentTeams | Agent 运行底座 | 官方许可 |
| Python 3.12+ | 运行环境 | PSF |

## 未实现披露

以下是设计但尚未实现的功能，如实披露：

- 正则约束的 16 个指标有操作定义但未代码化
- ChangeTransaction（原子事务）有伪代码但未实现
- 漂移检测有设计但未部署验证
- 持续监控有配置定义但未运行
- 仅 telecom 场景有实测数据（80% baseline），其他场景未测试

## 数据授权

- τ²-bench 的 telecom 数据为公开基准数据，MIT License 允许使用
- 训练日志和回归池数据由 AgentFit 生成，MIT License 开源
- 不使用任何私有企业数据
