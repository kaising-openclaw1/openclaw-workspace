# Social Copy Generator 📝

> 一键生成多平台社交媒体文案 — 小红书、微博、掘金、Twitter/X

## 功能

- 📱 **多平台适配** — 同一内容自动适配不同平台格式
- ✨ **小红书文案** — Emoji + 分段 + 标签，符合平台调性
- 🐦 **Twitter/X** — 280字符限制 + Thread 模式
- 📖 **掘金/知乎** — 技术社区风格，带代码块支持
- 📰 **微博** — 140字精简版 + 话题标签

## 快速使用

```python
from src.generator import SocialCopyGenerator

gen = SocialCopyGenerator()

# 生成小红书风格文案
result = gen.generate_xiaohongshu(
    topic="AI自动化",
    key_points=["节省时间", "降低成本", "提高效率"],
    target_audience="程序员/创业者"
)
print(result)
```

## 项目结构

```
social-copy-generator/
├── src/
│   ├── __init__.py
│   ├── generator.py    # 核心生成器
│   ├── templates.py    # 平台模板
│   └── utils.py        # 工具函数
├── examples/           # 示例输出
└── README.md
```

## 技术栈

- Python 3.10+
- 模板引擎
- 文本处理

## 许可证

MIT License
