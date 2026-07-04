# Code Agent — 完全替代 Claude Code 的自有工具

## 定位
终端 AI 编程助手，能理解代码库、读写文件、执行命令、搜索代码。

## 架构
```
code-agent/
├── core/
│   ├── loop.py          # 主对话循环
│   ├── context.py       # 上下文管理
│   └── session.py       # 会话持久化
├── llm/
│   ├── client.py        # LLM API 客户端（火山引擎 DeepSeek）
│   └── prompts.py       # 系统提示词
├── tools/
│   ├── file_ops.py      # 文件读写
│   ├── code_search.py   # 代码搜索
│   ├── exec_cmd.py      # 命令执行
│   └── project.py       # 项目分析
├── ui/
│   └── terminal.py      # 终端交互
└── main.py              # 入口
```

## 使用
```bash
python -m code-agent.main
```
