# 🤖 AI Portfolio Builder

> 一行命令，从 GitHub 仓库自动生成个人 Portfolio 网站

适合开发者快速搭建展示页面，无需手写 HTML/CSS。

---

## ✨ 功能

- **GitHub 自动扫描** — 读取你的公开仓库，提取项目信息
- **智能排序** — 按 Star 数、更新时间或创建时间排序
- **技术栈分析** — 自动统计编程语言分布和使用占比
- **暗色/亮色主题** — 开箱即用的现代设计
- **响应式布局** — 完美适配手机和桌面
- **一键部署** — 生成静态 HTML，可直接部署到 GitHub Pages / Netlify
- **中文优化** — 默认中文界面

## ⚡ 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 生成你的 Portfolio（默认 dark 主题）
python main.py --github-username yourname

# 自定义输出和主题
python main.py --github-username yourname --output my-site.html --theme light

# 限制项目数、按 Star 排序
python main.py --github-username yourname --max-repos 10 --sort stars

# 使用 Token（提高 API 限制）
python main.py --github-username yourname --token ghp_xxxxx
```

## 📦 生成的页面包含

- **Hero 区域**：头像、姓名、简介、GitHub 统计
- **社交链接**：GitHub / Blog / Email / Twitter
- **技术栈**：自动统计语言分布和占比
- **项目卡片**：描述、语言、Star/Fork 数、更新日期、Topics
- **响应式设计**：移动端自适应

## 🔧 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--github-username` | (必填) | GitHub 用户名 |
| `--output` | portfolio.html | 输出文件路径 |
| `--theme` | dark | 主题 (dark / light) |
| `--max-repos` | 20 | 最多展示项目数 |
| `--sort` | updated | 排序方式 (updated / stars / created) |
| `--token` | 无 | GitHub Personal Access Token |

## 🛠️ 技术栈

- Python 3.8+
- GitHub REST API
- Jinja2 模板引擎
- 纯静态 HTML 输出，零服务器依赖

## 📄 License

MIT

---

*Made with ❤️ by 小鸣 | [GitHub](https://github.com/kaising-openclaw1)*
