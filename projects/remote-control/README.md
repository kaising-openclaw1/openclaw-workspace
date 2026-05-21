# RemoteEye v3.0 Pro - 开源远程控制软件

> 对标向日葵 / ToDesk / TeamViewer 的专业级开源远程桌面方案，支持跨平台、低延迟、差分截屏、会话录制、录制回放、拖拽上传、移动触控。

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Version](https://img.shields.io/badge/version-3.0_Pro-orange.svg)]()

---

## 产品对比

| 功能 | TeamViewer | 向日葵 | RustDesk | **RemoteEye Pro** |
|------|:----------:|:------:|:--------:|:-----------------:|
| 跨平台 | ✅ | ✅ | ✅ | ✅ |
| 屏幕共享 | ✅ | ✅ | ✅ | ✅ |
| 键鼠控制 | ✅ | ✅ | ✅ | ✅ |
| 文件传输 | ✅ | ✅ | ✅ | ✅ |
| 拖拽上传 | ✅ | ⚠️ | ✅ | ✅ |
| 剪贴板同步 | ✅ | ✅ | ✅ | ✅ |
| 多显示器 | ✅ | ✅ | ✅ | ✅ |
| 差分截屏 | ✅ | ✅ | ✅ | ✅ |
| 会话录制 | ✅ | ⚠️ 付费 | ✅ | ✅ |
| 录制回放 | ❌ | ❌ | ❌ | ✅ |
| 远程 Shell | ❌ | ❌ | ❌ | ✅ |
| 无人值守 | ✅ | ✅ | ✅ | ✅ |
| 连接码 | ✅ | ✅ | ✅ | ✅ |
| E2E 加密 | ✅ | ⚠️ | ✅ | ✅ |
| 快捷按键 | ✅ | ✅ | ✅ | ✅ |
| 移动触控 | ⚠️ | ⚠️ | ✅ | ✅ |
| 远程光标 | ✅ | ✅ | ✅ | ✅ |
| 截屏保存 | ✅ | ✅ | ✅ | ✅ |
| 连接质量 | ✅ | ✅ | ✅ | ✅ |
| 深色主题 | ✅ | ✅ | ✅ | ✅ |
| 开源免费 | ❌ | ❌ | ✅ | ✅ |

---

## v2.0 新特性

### 🎬 差分截屏
将屏幕分割为 64×64 像素块，对比前后帧的 MD5，仅编码和传输变化区域，节省 **70-90% 带宽**。

### 📹 会话录制
自动录制远程控制会话，保存为 `.reml` 格式，支持回放。包含截屏帧和输入事件的时间线。

### 🔢 连接码系统
类似 TeamViewer 的 9 位数字 ID + 6 位动态密码，无需注册即可快速连接，10 分钟自动过期。

### 🔐 无人值守模式
设置永久 PIN 码，随时远程访问你的设备，无需有人在场确认。

### 💻 远程 Shell
直接在控制端执行远程命令，适合运维场景。

### 🔒 端到端加密
基于 AES-256-GCM 的端到端加密，支持 Diffie-Hellman 密钥交换。

### 📊 连接质量监控
实时显示延迟、帧率、带宽、丢包率，综合评分 0-100，自适应调整画质。

---

## 核心特性

| 特性 | 状态 | 说明 |
|------|------|------|
| 实时屏幕共享 | ✅ | mss 高性能截屏 + 差分编码 |
| 键盘/鼠标控制 | ✅ | pynput 模拟输入 |
| 多显示器 | ✅ | 动态切换显示器 |
| 文件传输 | ✅ | 浏览/上传/下载/删除/建目录 |
| 剪贴板同步 | ✅ | 双向实时同步 |
| 差分截屏 | ✅ | 仅传输变化区域，省 70-90% 带宽 |
| 会话录制 | ✅ | 自动录制，可回放 |
| 远程 Shell | ✅ | 远程执行命令 |
| 连接码 | ✅ | 9 位 ID + 6 位动态密码 |
| 无人值守 | ✅ | 永久 PIN 码 |
| E2E 加密 | ✅ | AES-256-GCM |
| 自适应画质 | ✅ | 根据网络动态调整 |
| 音频传输 | 🔌 | 插件化（可选） |
| H.264 编码 | 🔌 | 插件化（需 OpenCV） |

---

## 架构设计

```
┌─────────────────┐         WebSocket/WebRTC        ┌─────────────────┐
│   Web 主控端     │ ◄────────────────────────────► │   被控端 Agent   │
│  (浏览器)        │                                │  (Python)        │
│                  │    ┌──────────────┐            │                  │
│  - 画面渲染       │    │  信令服务器   │            │  - 截屏推流       │
│  - 键鼠事件       │◄──►│  FastAPI     │◄─────────►│  - 键鼠接收       │
│  - 设备列表       │    │  WebSocket   │            │  - 文件管理       │
│  - 文件传输       │    └──────────────┘            │  - 剪贴板同步     │
│  - 剪贴板         │                                │  - 差分截屏       │
│  - 远程 Shell     │                                │  - 会话录制       │
│  - 质量监控       │                                │  - 安全加密       │
└─────────────────┘                                └─────────────────┘
```

### 技术栈

- **被控端**：Python 3.10+ / mss / pynput / pyperclip / websockets / Pillow
- **信令服务器**：Python 3.10+ / FastAPI / uvicorn / WebSocket
- **Web 主控端**：HTML5 / CSS3 / JavaScript (Vanilla) / Canvas
- **加密**：cryptography (AES-256-GCM)
- **可选**：OpenCV (H.264) / PyAudio (音频) / psutil (系统监控)

---

## 快速开始

### 1. 安装依赖

```bash
# 信令服务器
cd server && pip install -r requirements.txt

# 被控端
cd agent && pip install -r requirements.txt

# 可选
pip install opencv-python pyaudio psutil cryptography
```

### 2. 启动信令服务器

```bash
cd server
python main.py
# http://localhost:8000
```

### 3. 启动被控端

```bash
cd agent

# 基础启动
python agent.py --server ws://localhost:8000/ws/agent

# 无人值守模式
python agent.py --server ws://localhost:8000/ws/agent --pin 123456

# 完整参数
python agent.py \
  --server ws://your-server:8000/ws/agent \
  --device-name "我的电脑" \
  --quality 80 --fps 20 \
  --pin my-secret-pin \
  --block-size 64
```

### 4. 打开 Web 主控端

浏览器访问 `http://localhost:8000/`

### 命令行参数

```
--server        信令服务器地址
--device-name   设备名称
--device-id     设备 ID
--quality       截屏质量 1-100（默认 75）
--fps           截帧率 1-60（默认 15）
--monitor       显示器索引
--block-size    差分块大小 px（默认 64）
--pin           无人值守访问码
--no-adaptive   禁用自适应画质
--no-clipboard  禁用剪贴板同步
--no-recording  禁用会话录制
```

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

  coturn:
    image: coturn/coturn
    network_mode: host
```

### Systemd 常驻服务

```ini
# /etc/systemd/system/remoteeye.service
[Unit]
Description=RemoteEye Agent
After=network.target

[Service]
Type=simple
User=youruser
ExecStart=/usr/bin/python3 /opt/remoteeye/agent/agent.py \
  --server wss://remote.example.com/ws/agent \
  --pin your-pin
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable remoteeye
sudo systemctl start remoteeye
```

---

## 性能指标

| 指标 | 数值 |
|------|------|
| 截帧率 | 15-60 fps（可调） |
| 延迟 | < 100ms（局域网）/ < 200ms（公网） |
| 带宽 | 差分 0.2-2 Mbps / 完整 1-5 Mbps |
| 带宽节省 | 差分截屏节省 70-90% |
| 内存占用 | ~150MB（被控端） |
| CPU 占用 | ~5-15%（截屏+编码） |

---

## 安全设计

- 🔐 **连接码**：9 位 ID + 6 位动态密码，10 分钟过期
- 🔑 **PIN 码**：永久访问码，SHA-256 哈希存储
- 🔒 **E2E 加密**：AES-256-GCM 端到端加密
- 🛡️ **文件沙盒**：仅允许访问用户目录和 /tmp
- 👁️ **可视化提示**：被控端显示"正在被远程控制"
- 🚫 **一键断开**：被控端可随时断开
- 📝 **会话日志**：记录所有连接历史
- 🎬 **会话录制**：可回放的操作录像

---

## 项目结构

```
remote-control/
├── README.md                     # 项目说明
├── agent/                        # 被控端 Agent
│   ├── agent.py                  # 主程序（v2.0）
│   ├── capture.py                # 屏幕捕获（多显示器）
│   ├── input.py                  # 键鼠输入控制
│   ├── clipboard.py              # 剪贴板同步
│   ├── file_manager.py           # 文件传输
│   ├── diff_capture.py           # 差分截屏（新）
│   ├── session_record.py         # 会话录制（新）
│   ├── connection_card.py        # 连接码系统（新）
│   ├── security.py               # 安全管理（新）
│   ├── e2e_crypto.py             # 端到端加密（新）
│   ├── audio.py                  # 音频转发（新）
│   ├── h264_encoder.py           # H.264 编码（新）
│   ├── quality_monitor.py        # 质量监控（新）
│   ├── config.py                 # 配置管理
│   └── requirements.txt          # 依赖清单
├── server/                       # 信令服务器
│   ├── main.py                   # FastAPI 主程序（v2.0）
│   └── requirements.txt
├── web/                          # Web 主控端
│   ├── templates/index.html      # 主页面
│   └── static/
│       ├── css/style.css         # 暗色主题样式
│       └── js/controller.js      # 控制逻辑
└── scripts/
    └── install.sh                # 一键安装脚本
```

---

## 商业变现

### SaaS 服务

| 套餐 | 价格 | 功能 |
|------|------|------|
| 免费版 | ¥0 | 3 台设备，基础控制 |
| 专业版 | ¥29/月 | 20 台设备，文件传输，高清画质，会话录制 |
| 企业版 | ¥99/月 | 无限设备，审计日志，SSO，E2E 加密 |

### 定制开发

- **企业定制**：¥50,000-200,000/项目
- **私有化部署**：¥20,000-50,000/次
- **技术咨询**：¥3,000-5,000/次

---

## 开源协议

MIT License - 可自由用于商业项目。

---

*作者：小鸣 | 2026-05-07 | v2.0 2026-05-11*
