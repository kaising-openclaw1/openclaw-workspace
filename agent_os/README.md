# Agent OS — 多机器 Agent 算力操作系统

> 掌控多源算力，保护源码安全，最大化智力输出

## 架构总览

```
┌──────────────────────────────────────────────────────────┐
│                     Agent OS                             │
├───────────┬───────────┬───────────┬──────────────────────┤
│ 智能路由    │ 算力抽象    │ 安全飞地    │ 可观测性              │
│ Intelligence│ Compute    │ Security  │ Observability       │
├───────────┴───────────┴───────────┴──────────────────────┤
│                    Mesh 网络层                            │
│         节点发现 · gRPC传输 · 状态同步 · NAT穿透          │
├──────────────────────────────────────────────────────────┤
│                   Agent 运行时 + 沙箱                      │
│       Python Sandbox · WASM Runtime · Docker Runtime     │
├──────────────────────────────────────────────────────────┤
│                   存储层                                   │
│         对象存储 · 向量DB · 消息队列 · 文件同步            │
└──────────────────────────────────────────────────────────┘
```

## 核心特性

| 特性 | 说明 |
|------|------|
| 🧠 **智力分级路由** | 简单任务→轻量模型，复杂推理→最强模型，自动分级 |
| 🔗 **Mesh 网络** | 去中心化 P2P，任何节点可做控制面，无单点故障 |
| 🔒 **安全飞地** | 代码 AES-256-GCM 加密存储，运行时解密，全审计追踪 |
| 💻 **算力抽象** | 本地 GPU / 远程服务器 / 云实例 / 边缘设备统一接口 |
| 📊 **可观测性** | OpenTelemetry 全链路追踪 + 结构化日志 + 实时指标 |
| 🏗️ **状态机引擎** | 每个任务有明确定义的状态机，可 checkpoint/restore |
| 🔌 **插件系统** | 热加载插件，能力即服务 (Tool-as-a-Service) |
| 📦 **多运行时** | Python Sandbox / WASM / Docker / 原生进程 |

## 快速开始

```bash
# 安装
pip install agent-os

# 启动节点
agent-os start --name node-1

# 加入集群
agent-os join --seed 192.168.1.100:8765

# 提交任务
agent-os run "用 GPT-4 分析这份代码" --source ./src

# 查看集群状态
agent-os status

# 启动 Web Dashboard
agent-os dashboard
```

## 目录结构

```
agent-os/
├── core/              # 核心引擎
│   ├── event_bus.py       # 异步事件总线
│   ├── state_machine.py   # 状态机引擎
│   ├── plugin_system.py   # 插件系统
│   └── config.py          # 配置管理
├── network/           # Mesh 网络层
│   ├── mesh.py            # P2P 节点发现与连接
│   ├── transport.py       # gRPC 传输层
│   ├── nat_traversal.py   # NAT 穿透
│   └── protocol.proto     # 通信协议
├── compute/           # 算力抽象层
│   ├── resource_manager.py # 资源管理
│   ├── scheduler.py       # 任务调度器
│   ├── providers/         # 算力提供商
│   │   ├── local.py       # 本地 CPU/GPU
│   │   ├── remote.py      # 远程服务器
│   │   ├── docker.py      # Docker 容器
│   │   └── cloud.py       # 云实例
│   └── sandbox.py         # 沙箱执行环境
├── intelligence/      # 智能路由层
│   ├── router.py          # 智力分级路由
│   ├── model_registry.py  # 模型注册表
│   ├── context_manager.py # 上下文管理
│   └── providers/         # 模型提供商
│       ├── openai.py
│       ├── anthropic.py
│       ├── deepseek.py
│       └── local.py       # 本地模型
├── security/          # 安全层
│   ├── enclave.py         # 安全飞地
│   ├── crypto.py          # 加密解密
│   ├── audit.py           # 审计日志
│   ├── rbac.py            # 访问控制
│   └── vault.py           # 密钥管理
├── storage/           # 存储层
│   ├── object_store.py    # 对象存储
│   ├── vector_store.py    # 向量数据库
│   ├── message_queue.py   # 消息队列
│   └── file_sync.py       # 文件同步
├── observability/     # 可观测性
│   ├── tracing.py         # 分布式追踪
│   ├── metrics.py         # 指标收集
│   ├── logging.py         # 结构化日志
│   └── dashboard.py       # Web Dashboard
├── api/               # API 层
│   ├── grpc_server.py     # gRPC 服务
│   ├── http_server.py     # HTTP/REST API
│   ├── websocket.py       # WebSocket
│   └── cli.py             # 命令行接口
├── agent/             # Agent 运行时
│   ├── runtime.py         # Agent 运行时
│   ├── sandbox.py         # 沙箱
│   ├── tool_registry.py   # 工具注册
│   └── lifecycle.py       # 生命周期管理
├── deploy/            # 部署配置
├── tests/             # 测试
├── examples/          # 示例
└── docs/              # 文档
```

## 设计哲学

1. **算力即资源** — 所有计算资源统一抽象，按需分配
2. **智力最大化** — 自动选择最优模型，不浪费任何智力
3. **安全第一** — 代码加密、访问控制、审计追踪三位一体
4. **去中心化** — Mesh 架构，无单点故障
5. **可观测内建** — 从第一天起就追踪一切
6. **工程卓越** — 类型安全、全面测试、优雅 API

## License

MIT
