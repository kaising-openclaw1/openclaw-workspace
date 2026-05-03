# Price Tracker Pro 🔍

> 轻量级竞品价格监控工具 — 自动抓取、价格变动提醒、数据导出

## 功能特性

- 🕷️ **多平台价格监控** — 支持电商、SaaS等网站的价格抓取
- 📊 **价格变动追踪** — 记录历史价格，生成趋势图
- 🔔 **智能提醒** — 价格下降/上涨超过阈值时自动通知
- 📁 **数据导出** — 导出为 CSV/JSON 格式
- ⚡ **定时任务** — 支持 Cron 定时自动抓取

## 安装

```bash
pip install -r requirements.txt
```

## 快速开始

### 1. 配置监控目标

编辑 `config.yaml`：

```yaml
targets:
  - name: "竞品A"
    url: "https://example.com/product-a"
    selector: ".price"
    notify_threshold: 10  # 价格变动超过10%时通知
  
  - name: "竞品B"
    url: "https://example.com/product-b"
    selector: "#price-tag"
    notify_threshold: 5
```

### 2. 运行监控

```bash
# 单次抓取
python src/scraper.py

# 定时监控（每天9点）
python src/scheduler.py --cron "0 9 * * *"
```

### 3. 查看报告

```bash
# 生成价格趋势报告
python src/report.py --output report.html

# 导出数据
python src/export.py --format csv
```

## 项目结构

```
price-tracker-pro/
├── config.yaml          # 监控配置
├── requirements.txt     # 依赖
├── src/
│   ├── __init__.py
│   ├── scraper.py       # 抓取核心
│   ├── scheduler.py     # 定时任务
│   ├── report.py        # 报告生成
│   ├── export.py        # 数据导出
│   └── notifier.py      # 通知模块
├── data/                # 存储历史数据
└── README.md
```

## 技术栈

- Python 3.10+
- Playwright (网页抓取)
- SQLite (数据存储)
- Jinja2 (报告模板)
- APScheduler (定时任务)

## 许可证

MIT License
