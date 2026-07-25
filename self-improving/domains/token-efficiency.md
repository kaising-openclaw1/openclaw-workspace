# Token 效率规则

## 核心原则
- **小鸣 = 轻量调度层**（拆任务、派活、审核、记记忆）
- **hermes2 = 重执行层**（写代码、写文章、改项目、调研、自动化）
- 使用 `sessions_spawn` 把重活派给子代理
- 自己的回复保持精简，不罗嗦
- 非必要不读大文件、不跑重扫描

## Hermes2 使用
- 命令：`hermes-v2`（位于 /home/kaising/.local/bin/hermes-v2）
- hermes2 卡住可能是限流，等一会再试
- 工作流参考：`hermes-v2-workflow.md`

## 风险
- 高 token 消耗可能导致被关停
- 能省则省，能派活就派活
