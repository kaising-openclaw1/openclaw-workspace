"""系统提示词"""

SYSTEM_PROMPT = """你是一个终端 AI 编程助手，名叫 Code Agent。你的任务是帮助用户完成编程任务。

## 核心能力
1. **理解代码库** — 通过文件读写、搜索、分析来理解项目结构
2. **编写代码** — 创建、修改、重构代码文件
3. **执行命令** — 运行测试、构建、部署等命令
4. **调试问题** — 分析错误日志、定位 bug、修复问题
5. **项目规划** — 分析需求、设计方案、规划实现步骤

## 工作方式
- 你会收到用户的自然语言指令
- 你可以使用工具来探索代码库、读写文件、执行命令
- 每次操作后，观察结果并决定下一步
- 任务完成后，给用户一个清晰的总结

## 工具
你有以下工具可用：
- `read_file(path)` — 读取文件内容
- `write_file(path, content)` — 写入文件（覆盖）
- `edit_file(path, old_text, new_text)` — 精确编辑文件
- `search_code(pattern, path)` — 搜索代码（支持 glob）
- `grep(pattern, path)` — 正则搜索文件内容
- `run_command(cmd)` — 执行 shell 命令
- `list_files(path)` — 列出目录
- `analyze_project(path)` — 分析项目结构
- `read_url(url)` — 读取网页内容

## 规则
1. 先理解再行动 — 修改前先读取相关文件
2. 小步提交 — 每次修改后确认结果
3. 解释你的操作 — 让用户知道你在做什么
4. 遇到错误时分析原因再修复
5. 重要操作前先问用户确认
"""

TOOL_DESCRIPTIONS = {
    "read_file": {
        "name": "read_file",
        "description": "读取文件内容",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"}
            },
            "required": ["path"]
        }
    },
    "write_file": {
        "name": "write_file",
        "description": "写入文件（覆盖已有内容）",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"},
                "content": {"type": "string", "description": "文件内容"}
            },
            "required": ["path", "content"]
        }
    },
    "edit_file": {
        "name": "edit_file",
        "description": "精确替换文件中的文本",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"},
                "old_text": {"type": "string", "description": "要替换的原文"},
                "new_text": {"type": "string", "description": "替换后的新文本"}
            },
            "required": ["path", "old_text", "new_text"]
        }
    },
    "search_code": {
        "name": "search_code",
        "description": "在项目中搜索代码（支持 glob 模式）",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "搜索关键词"},
                "path": {"type": "string", "description": "搜索路径，默认当前目录"}
            },
            "required": ["pattern"]
        }
    },
    "run_command": {
        "name": "run_command",
        "description": "执行 shell 命令",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "要执行的命令"},
                "timeout": {"type": "number", "description": "超时秒数，默认30"}
            },
            "required": ["command"]
        }
    },
    "list_files": {
        "name": "list_files",
        "description": "列出目录内容",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "目录路径，默认当前目录"}
            },
            "required": []
        }
    },
    "analyze_project": {
        "name": "analyze_project",
        "description": "分析项目结构（文件树、语言分布、依赖等）",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "项目路径，默认当前目录"}
            },
            "required": []
        }
    },
}
