# 手把手教你用 Python 构建 AI 代码安全扫描器——防御 Slopsquatting 攻击

> 当 AI 替你写代码时，它可能正在给你的项目埋雷。

## 什么是 Slopsquatting？

2026 年 7 月，VentureBeat 报道了一种新型软件供应链攻击——**Slopsquatting**（垃圾占位攻击）。

它的工作原理很简单：

1. 你用 Cursor/Copilot 写代码，AI 生成了 `import openai_sdk` 或 `from requessts import get`
2. 这两个包名 **不存在于 PyPI**——它们是 AI 的幻觉
3. 攻击者发现这些幻觉包名，注册到 PyPI，植入恶意代码
4. 你的 `pip install` 毫无防备地安装了恶意包

这不是理论攻击。Slopsquatting 已经出现在真实项目中。

## 与 Typosquatting 的区别

Typosquatting（域名抢注）针对的是**打字错误**（`request` vs `requests`），而 Slopsquatting 针对的是 **AI 幻觉**——AI 生成的包名可能和任何知名包都不像，纯粹是模型"编造"出来的。

## 构建扫描器

我们写一个零外部依赖的 Python 扫描器，三行命令就能用。

### 核心逻辑

```python
import re, json, tomllib
from pathlib import Path
from difflib import SequenceMatcher
from urllib.request import urlopen, Request

def check_package(name):
    """检查包是否存在于 PyPI"""
    url = f"https://pypi.org/pypi/{name}/json"
    req = Request(url, headers={"User-Agent": "slopsquat-scanner/1.0"})
    try:
        urlopen(req, timeout=5)
        return True
    except Exception:
        return False

def calc_similarity(a, b):
    """计算两个包名的相似度"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()
```

### 检测流程

1. **解析依赖文件**：读取 `requirements.txt` 或 `pyproject.toml`
2. **查询 PyPI**：每个包名发 HEAD 请求检查是否存在
3. **相似度分析**：不存在的包与知名包列表计算编辑距离
4. **风险评级**：
   - 🟢 **安全**：包存在于 PyPI
   - 🟡 **可疑**：包不存在，但与某知名包相似
   - 🔴 **危险**：包不存在，且与知名包高度相似（>85%）

### 完整代码

完整的 `scanner.py`（551 行）已开源，支持：

- 扫描 `requirements.txt` / `pyproject.toml`
- 递归扫描目录
- 输出终端彩色报告 / HTML 报告 / JSON 报告
- 内置 200+ 知名 Python 包名库

项目地址：`projects/slopsquat-scanner/`

## 使用示例

```bash
# 扫描单个文件
python scanner.py scan requirements.txt

# 输出 HTML 报告
python scanner.py scan requirements.txt --output report.html

# 递归扫描项目目录
python scanner.py scan . --recursive
```

输出：

```
[🟢] requests → 已存在于 PyPI
[🟡] requessts → 不存在，但与 'requests' 相似度 92%
[🔴] openai-sdk-pro → 不存在，疑似恶意包名
```

## 防御建议

1. **锁依赖版本**：用 `pip freeze > requirements.txt` 锁定所有传递依赖
2. **用 lock 文件**：Poetry 的 `poetry.lock` 或 Pipenv 的 `Pipfile.lock`
3. **私有 PyPI 镜像**：只从受信任的镜像源安装
4. **CI 集成扫描**：在 CI 中运行本扫描器，阻止未验证的依赖
5. **审查 AI 生成的代码**：特别注意 import 语句

## 商业机会

Slopsquatting 是一个全新的安全赛道。可能的变现方向：

- **SaaS 服务**：提供 API，集成到 CI/CD 管道
- **IDE 插件**：VSCode/JetBrains 插件，实时检测
- **企业版**：私有部署 + 自定义包名库 + LDAP 集成
- **安全审计服务**：扫描现有项目的依赖风险

---

**项目代码在 `projects/slopsquat-scanner/`，零外部依赖，开箱即用。**
