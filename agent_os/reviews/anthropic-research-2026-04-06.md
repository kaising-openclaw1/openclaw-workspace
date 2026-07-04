# Anthropic 近 3 个月产品研究（2026-04 ~ 2026-06）

> 研究日期：2026-06-29
> 来源：官方 Changelog、Releasebot、Tygart Media、Appscribed、APIYI、claudefa.st、gradually.ai 等

---

## 一、Claude Code 版本迭代

### 版本节奏
- **v2.1.69 → v2.1.141+**（3月-6月，约 70+ 个 release）
- 3-4 月：5 周内 30+ 个 release（几乎每天发布）
- 6 月：最新版本 v2.1.141+（377 条 release notes 累计）

### 里程碑版本

| 版本 | 日期 | 核心变化 |
|------|------|---------|
| v2.1.75 | 3月13日 | Opus 4.6 1M 上下文窗口 GA |
| v2.1.84 | 3月26日 | PowerShell 工具预览、线性文本流式输出 |
| v2.1.88 | 3月31日 | **源码泄露事件**（59.8MB source map 暴露 512K 行 TS） |
| v2.1.90 | 4月1日 | /powerup 交互教程、NO_FLICKER 渲染引擎 |
| v2.1.92 | 4月4日 | Bedrock 交互式设置向导、/release-notes 版本选择器 |
| v2.1.98 | 4月9日 | Vertex AI 设置向导、Monitor 工具、子进程沙箱 |
| v2.1.101 | 4月10日 | /team-onboarding、OS CA 证书信任 |
| v2.1.105 | 4月中旬 | 多终端修复（Ghostty/Kitty/Alacritty 等 16 色调色板修复） |
| v2.1.128 | 5月 | 随机会话颜色、MCP 工具计数、插件 zip 支持、OTEL 隔离 |
| v2.1.141+ | 6月 | 持续迭代 |

---

## 二、核心功能更新

### 2.1 模型能力

| 模型 | 发布日期 | 关键指标 | 价格 |
|------|---------|---------|------|
| Claude Fable 5 | 6月9日 | 首个公开 Mythos 级模型，比 Opus 4.8 高 10%+ | $10/$50 per MTok |
| Claude Opus 4.8 | 4月16日 | CursorBench 70%，Rakuten-SWE-Bench 3x | $5/$25 per MTok |
| Claude Opus 4.7 | 5月8日 | SWE-Bench Verified 87.6% | $5/$25 per MTok |
| Claude Sonnet 4.6 | 2月17日 | 默认编码模型 | — |

**关键变化**：
- Opus 4.8 新增 `xhigh` effort level（介于 high 和 max 之间）
- Task Budgets 公开 beta（token 花费指导）
- 新 tokenizer（token 用量增加 1.0-1.35x）
- Fable 5 仅支持 adaptive thinking，不支持 temperature/top_p/top_k
- Fable 5 在 6月12日被美国政府要求全球暂停

### 2.2 渲染引擎

**NO_FLICKER 模式**（v2.1.90）：
- 解决终端闪烁问题
- Focus View：专注模式，只显示最终消息
- 对比：Textualize 创始人 Will McGugan 开发的 Toad 原型证明 Python Textual 框架可以做得更好

### 2.3 团队协作

- **/team-onboarding**：从本地 Claude Code 使用数据生成队友上手指南
- **/powerup**：交互式教程
- **命名子 Agent**：支持为子 Agent 命名

### 2.4 安全沙箱

- PID 命名空间隔离（Linux）
- PowerShell 权限加固（Windows）
- 凭证擦除
- 命令注入漏洞修复
- 子进程 OTEL 环境变量隔离

### 2.5 MCP 生态

- OAuth RFC 9728 支持
- 500K 结果持久化
- 条件过滤 Hooks
- 插件 zip 支持
- MCP 工具计数（标记零工具服务器）
- `workspace` 成为保留服务器名

### 2.6 企业功能

- **Workload Identity Federation**（6月17日 GA）：无密钥认证
- OS CA 证书信任（企业 TLS 代理无需额外设置）
- Console channels 支持 API 密钥认证
- 自定义 CA 证书支持

---

## 三、源码泄露事件（3月31日）

### 事实
- 意外将 59.8MB source map 打包进 v2.1.88
- 暴露了 ~512K 行 TypeScript 源码
- Anthropic 称"打包错误，非安全漏洞"
- 已通过版权删除请求控制传播

### 泄露揭示的隐藏功能

| 功能代号 | 描述 | 状态 |
|---------|------|------|
| **Kairos** | 主动空闲模式，后台自主 Agent | 已编译但被标志隐藏 |
| **Undercover** | 隐身模式 | 未发布 |
| **Bridge** | 跨仓库操作 | 未发布 |
| **Coordinator** | 多 Agent 编排 | 未发布 |
| **UltraPlan** | 高级规划 | 部分已发布（云端环境） |
| **Buddy** | 结对编程模式 | 未发布 |
| 记忆系统 | 会话+项目记忆 | 部分已发布 |
| 子 Agent | 多 Agent 协作 | 部分已发布 |
| 云端执行 | 远程沙箱执行 | 已发布 |

### 对 Agent OS 的意义
- **Kairos 验证了"异步模式"方向**——Claude Code 确实在做类似的事情
- **512K 行 TS 的架构复杂度**——我们的 15K LOC 策略（专注差异化）是对的
- **泄露揭示了 Anthropic 的路线图**——记忆、子 Agent、云端执行是未来方向

---

## 四、商业动态

### 定价变化
- **4月21日**：Claude Code 从 Pro 计划移除（$20/月 → $100/月起）
- **4月23日**：24 小时内撤回，恢复 Pro 计划包含
- Anthropic 称"2% 新用户测试"，但官方文档已更新

### 竞争应对
- **5月13日**：Anthropic 将 Claude Code 周限额提升 50%（至 7月13日）
- 同日 OpenAI 为切换企业提供 2 个月免费 Codex
- 原因：用户向 Codex 迁移（token 消耗更低、性能相当）

### SpaceX 算力合作
- 5月宣布合作，访问 Colossus 1 算力
- 直接效果：订阅者速率限制翻倍

### 营收增长
- 2025年底：$9B ARR
- 2026年2月：$14B ARR
- 2026年4月：$30B ARR
- 2026年5月：$47B ARR
- 5 个月内 29 个产品发布

---

## 五、对 Agent OS 架构的影响

### 5.1 验证的方向

| Agent OS 决策 | Claude Code 证据 | 结论 |
|-------------|----------------|------|
| 双模（同步+异步） | Kairos 隐藏功能 | ✅ 方向正确 |
| 上下文压缩 | 5 层压缩系统 | ✅ 方向正确 |
| MCP 协议 | 原生 MCP 支持 | ✅ 方向正确 |
| 权限系统 | 4 路竞速 | ✅ 方向正确 |
| 沙箱隔离 | PID 命名空间隔离 | ✅ 方向正确 |
| 自我进化 | KAIROS 自主模式 | ✅ 方向正确（但更保守） |

### 5.2 需要重新评估的

| Agent OS 计划 | Claude Code 实际 | 差距 |
|-------------|----------------|------|
| 2 层上下文压缩（Phase 0） | 5 层（Snip→Micro→Collapse→Auto→Reactive） | ⚠️ 至少需要 3 层 |
| 终端 UI 800 LOC | React+Ink 60K LOC + NO_FLICKER | ⚠️ Textual 框架值得评估 |
| 工具系统 20 个 | 40+ 工具 | ⚠️ Phase 0 应扩展到 10 个 |
| 团队协作 Phase 2 | /team-onboarding 已发布 | ⚠️ 可推迟到 Phase 3 |

### 5.3 新发现的差距

1. **Workload Identity Federation** — Claude Code 已支持无密钥认证，Agent OS 未规划
2. **OTEL 隔离** — 子进程环境变量隔离，Agent OS 未规划
3. **插件系统** — Claude Code 支持 zip 插件，Agent OS 的 plugin_system.py 是 v1.0 遗留
4. **终端兼容性** — Claude Code 修复了 8 个终端的 16 色调色板问题，这是细节工程
5. **Claude Design** — Anthropic 推出了可视化设计工具，Agent OS 没有对应功能

---

## 六、关键结论

1. **Claude Code 的迭代速度惊人**——70+ 个 release 在 3 个月内，几乎每天更新
2. **Kairos 验证了异步模式**——这是 Agent OS 双模战略的关键证据
3. **512K LOC 的复杂度是不可复制的**——15K LOC 的差异化策略是正确的
4. **Fable 5 被暂停是地缘政治风险**——开源替代方案的机会窗口
5. **企业功能是主战场**——WIF、沙箱、审计、合规是 Claude Code 的投入重点
6. **NO_FLICKER 证明终端 UI 是竞争维度**——Textual 框架值得评估

---

*研究日期：2026-06-29*
*来源：Anthropic 官方 Changelog、Releasebot、Tygart Media、Appscribed、APIYI、claudefa.st、gradually.ai、VentureBeat、TechCrunch*
