# Web Scraping API 🕷️

轻量级自部署网页抓取 API，支持 JS 渲染、智能缓存、反爬绕过。**可用于电商价格监控、舆情追踪、竞品分析等场景。**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688.svg)](https://fastapi.tiangolo.com)

---

## 🎯 适用场景

- **电商价格监控** — 定时抓取竞品价格，自动调价
- **舆情/新闻聚合** — 多源采集，关键词追踪
- **竞品分析** — 批量采集产品信息和评论
- **数据驱动决策** — 为投资/运营提供实时数据支撑

## 功能特性

- **RESTful API** — 简单的 `POST /scrape` 接口
- **JS 渲染** — 使用 Playwright 处理动态页面
- **智能缓存** — SQLite 缓存避免重复请求
- **多种输出格式** — JSON、Markdown、纯文本、原始 HTML
- **批量抓取** — 一次请求处理多个 URL
- **反检测模式** — 随机 UA、请求间隔、指纹伪装
- **速率限制** — 每域名请求频率控制

## 快速开始

```bash
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000
```

调用示例：

```bash
curl -X POST http://localhost:8000/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "format": "markdown"}'
```

## API 文档

### POST /scrape

抓取单个网页。

```json
{
  "url": "https://example.com/product/123",
  "format": "markdown",       // json | markdown | text | html
  "wait_for": ".price",       // CSS selector，等待元素出现
  "timeout": 15000,           // 超时（毫秒）
  "use_cache": true,          // 是否使用缓存
  "stealth": true             // 反检测模式
}
```

### POST /scrape/batch

批量抓取多个 URL。

```json
{
  "urls": [
    "https://example.com/page1",
    "https://example.com/page2"
  ],
  "format": "markdown",
  "concurrency": 3
}
```

### GET /stats

获取抓取统计信息。

### GET /health

健康检查。

## 技术栈

- **FastAPI** — 高性能 API 框架
- **Playwright** — 浏览器自动化
- **Readability-lxml** — 内容提取
- **SQLite** — 缓存存储
- **APScheduler** — 定时缓存清理

## 部署

```bash
# 本地开发
uvicorn src.main:app --reload

# 生产环境
gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

## 💼 商业服务

需要定制数据采集方案？提供以下服务：

| 服务 | 说明 | 起步价 |
|------|------|--------|
| 数据采集系统搭建 | 定制爬虫 + 定时任务 + 告警 | ¥2,000 |
| API 自部署 | 在您的服务器上部署本系统 | ¥500 |
| 运维支持 | 持续维护 + 反爬策略更新 | ¥500/月 |

📧 联系方式：通过 GitHub Issue 或 Portfolio 网站

---

## 📊 效果对比

| 指标 | 手动采集 | 使用本 API | 提升 |
|------|---------|-----------|------|
| 单页面采集时间 | 2-5 分钟 | 1-3 秒 | **40-100x** |
| 50 个竞品价格监控 | 2-4 小时/天 | 5 分钟/天 | **24-48x** |
| 多源舆情追踪 | 人工翻阅 | 自动汇总 + 告警 | **解放双手** |

---

## 📄 License

MIT License

---

*Made with ❤️ by 小鸣 | [Portfolio](https://github.com/kaising-openclaw1) | [更多项目](https://github.com/kaising-openclaw1)*
