# CS-Agent - 生产级 AI 客服系统

一个轻量、可扩展的 AI 客服 Agent 框架，支持工具调用、对话记忆、多模型切换。

## 特性

- ✅ 工具调用（Tool Calling）- Agent 可自动调用外部工具
- ✅ 对话记忆管理 - SQLite 持久化用户画像和历史对话
- ✅ 多模型切换 - 支持 OpenAI / Claude / 本地模型
- ✅ FastAPI 部署 - 生产就绪的 API 服务
- ✅ Docker 容器化 - 一键部署
- ✅ 完整文档 - 包含部署指南和使用示例

## 快速开始

### 安装

```bash
pip install -r requirements.txt
```

### 配置

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入你的 API Key
```

### 运行

```bash
# 开发模式
python -m uvicorn main:app --reload

# 生产模式
docker-compose up -d
```

### 测试

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "你好，帮我查询订单"}'
```

## 架构

```
┌─────────────────────────────────────────────┐
│              API 层 (FastAPI)                │
├─────────────────────────────────────────────┤
│            Agent 核心 (Agent)                │
│  ┌──────────┬──────────┬─────────────────┐  │
│  │ 工具调用  │ 对话记忆  │  模型适配器      │  │
│  └──────────┴──────────┴─────────────────┘  │
├─────────────────────────────────────────────┤
│            服务层 (Services)                 │
│  ┌──────────┬──────────┬─────────────────┐  │
│  │ 数据库   │ 缓存     │  外部 API        │  │
│  └──────────┴──────────┴─────────────────┘  │
└─────────────────────────────────────────────┘
```

## 工具集

- `web_search` - 网络搜索
- `database_query` - 数据库查询
- `calculator` - 数学计算
- `order_query` - 订单查询（示例）
- `knowledge_base` - 知识库检索

## 部署

### Docker

```bash
docker-compose up -d
```

### 手动部署

```bash
# 安装依赖
pip install -r requirements.txt

# 运行服务
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 成本分析

| 项目 | 成本 |
|------|------|
| GPT-4o-mini | ¥5-10/月（1000 次对话） |
| 服务器（2C4G） | ¥50-100/月 |
| 总计 | ¥55-110/月 |

对比 SaaS 方案（¥500-2000/月），自建成本降低 90% 以上。

## 许可证

MIT License
