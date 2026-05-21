# HEARTBEAT.md

## AI 日报推送检测
- 检查 `ai-daily-reports/` 目录下是否有今天的报告文件
- 如果有，读取并推送给用户（markdown 格式，不要表格，用列表）
- 推送后在文件中加 `[已推送]` 标记
- 报告覆盖：GitHub 新项目 + HuggingFace 模型/Spaces + ClawHub Skills + ModelScope
