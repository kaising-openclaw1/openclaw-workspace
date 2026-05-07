# RemoteEye - 开源远程控制软件

> 对标向日葵/ToDesk 的开源远程桌面控制方案，支持跨平台、低延迟、穿透 NAT。

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)

---

## 项目简介

RemoteEye 是一套完整的远程控制解决方案，包含：

- **被控端 Agent**：Python 编写，支持 Linux/macOS/Windows，截屏 + 键鼠控制
- **信令服务器**：Python + FastAPI + WebSocket，设备注册 + 信令中继 + NAT 穿透
- **Web 主控端**：纯浏览器端，无需安装，实时画面 + 键鼠操作

### 核心特性

| 特性 | 状态 | 说明 |
|------|------|------|
| 实时屏幕共享 | ✅ | mss 高性能截屏，60fps |
| 键盘控制 | ✅ | pynput 模拟输入 |
| 鼠标控制 | ✅ | 移动/点击/滚轮 |
| NAT 穿透 | ✅ | WebRTC P2P 直连 |
| 设备管理 | ✅ | 在线状态 + 设备列表 |
| 文件传输 | 🔄 | 开发中 |
| 音频传输 | 🔄 | 开发中 |
| 剪贴板同步 | 📋 | 计划中 |

---

## 架构设计

```
┌─────────────────┐         WebSocket/WebRTC        ┌─────────────────┐
│   Web 主控端     │ ◄────────────────────────────► │   被控端 Agent   │
│  (浏览器)        │                                │  (Python)        │
│                  │    ┌──────────────┐            │                  │
│  - 画面渲染       │    │  信令服务器   │            │  - 截屏推流       │
│  - 键鼠事件       │◄──►│  FastAPI     │◄─────────►│  - 键鼠接收       │
│  - 设备列表       │    │  WebSocket   │            │  - 设备注册       │
│                  │    └──────────────┘            │                  │
└─────────────────┘                                └─────────────────┘
```

### 技术栈

- **被控端**：Python 3.10+ / mss (截屏) / pynput (键鼠) / websockets
- **信令服务器**：Python 3.10+ / FastAPI / uvicorn / WebSocket
- **Web 主控端**：HTML5 / CSS3 / JavaScript (Vanilla) / Canvas

---

## 快速开始

### 1. 安装依赖

```bash
# 信令服务器
cd server
pip install -r requirements.txt

# 被控端
cd agent
pip install -r requirements.txt
```

### 2. 启动信令服务器

```bash
cd server
python main.py
# 服务器启动在 http://localhost:8000
```

### 3. 启动被控端 Agent

```bash
cd agent
python agent.py --server ws://localhost:8000 --device-name "我的电脑"
# Agent 连接到服务器，注册设备，开始接受控制
```

### 4. 打开 Web 主控端

浏览器访问 `http://localhost:8000/`，选择要控制的设备即可。

---

## 部署方案

### Docker Compose

```yaml
version: '3.8'

services:
  server:
    build: ./server
    ports:
      - "8000:8000"
    environment:
      - SECRET_KEY=your-secret-key
    restart: unless-stopped

  # 可选：TURN 服务器（用于 NAT 穿透失败时的中继）
  coturn:
    image: coturn/coturn
    network_mode: host
    command: -n --log-file=stdout
```

### 公网部署

```bash
# 1. 购买服务器（推荐阿里云/腾讯云，2C4G 即可）
# 2. 配置域名和 SSL 证书
# 3. 部署信令服务器
# 4. 在每台被控设备上安装 Agent
# 5. 浏览器访问 Web 端即可控制
```

---

## 性能指标

| 指标 | 数值 |
|------|------|
| 截帧率 | 30-60 fps（取决于网络） |
| 延迟 | < 100ms（局域网）/ < 200ms（公网） |
| 带宽 | 1-5 Mbps（可调画质） |
| 内存占用 | ~150MB（被控端） |
| CPU 占用 | ~5-15%（截屏+编码） |

---

## 安全设计

- 🔐 **设备认证**：每台设备需要配对码才能连接
- 🔒 **TLS 加密**：所有通信使用 WSS/HTTPS
- 👁️ **可视化提示**：被控端屏幕显示"正在被远程控制"
- 🚫 **一键断开**：被控端可随时断开连接
- 📝 **操作日志**：记录所有远程控制会话

---

## 项目结构

```
remote-control/
├── README.md                 # 项目说明
├── LICENSE                   # MIT 许可证
├── agent/                    # 被控端 Agent
│   ├── agent.py              # 主程序（截屏 + 键鼠控制）
│   ├── capture.py            # 屏幕捕获模块
│   ├── input.py              # 键鼠输入模块
│   ├── config.py             # 配置管理
│   └── requirements.txt      # 依赖清单
├── server/                   # 信令服务器
│   ├── main.py               # FastAPI 主程序
│   ├── signaling.py          # WebSocket 信令处理
│   ├── devices.py            # 设备管理
│   └── requirements.txt      # 依赖清单
├── web/                      # Web 主控端
│   ├── templates/
│   │   └── index.html        # 主页面
│   └── static/
│       ├── css/
│       │   └── style.css     # 样式
│       └── js/
│           └── controller.js # 控制逻辑
├── docs/                     # 文档
│   ├── architecture.md       # 架构文档
│   ├── deployment.md         # 部署指南
│   └── api.md                # API 文档
└── scripts/                  # 工具脚本
    ├── install.sh            # 一键安装脚本
    └── benchmark.py          # 性能测试
```

---

## 商业变现

### SaaS 服务

| 套餐 | 价格 | 功能 |
|------|------|------|
| 免费版 | ¥0 | 3 台设备，基础控制 |
| 专业版 | ¥29/月 | 20 台设备，文件传输，高清画质 |
| 企业版 | ¥99/月 | 无限设备，审计日志，SSO |

### 定制开发

- **企业定制**：¥50,000-200,000/项目
- **私有化部署**：¥20,000-50,000/次
- **技术咨询**：¥3,000-5,000/次

---

## 开源协议

MIT License - 可自由用于商业项目。

---

*作者：小鸣 | 2026-05-07*
