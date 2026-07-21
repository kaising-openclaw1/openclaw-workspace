# Portfolio 站点状态检查报告

**检查时间**: 2026-07-12
**检查范围**: `/home/kaising/.openclaw/workspace/portfolio/` vs `/home/kaising/.openclaw/workspace/projects/`

---

## 1. 现状分析

### 1.1 Portfolio 站点结构
| 文件 | 大小 | 说明 |
|------|------|------|
| `index.html` | 25 KB | 主页，含项目展示区（30 个项目卡片 + 1 个旗舰项目） |
| `case-studies.html` | 12 KB | 案例展示页，5 个真实客户案例 |
| `blog.html` | 8.5 KB | 技术博客，15 篇文章 |

### 1.2 项目展示区统计 (index.html)
- **旗舰项目**: 1 个（墨韵 AI — 书法字体智能生成）
- **常规项目卡片**: 30 个
- **服务/套餐卡片（误放入项目区）**: 17 个（见第 2.2 节）

**portfolio 显示的"项目"总计: 48 个，但实际开源项目仅 30 个**

### 1.3 实际开源项目目录统计
`/home/kaising/.openclaw/workspace/projects/` 下共有 **31 个** 项目目录：

| # | 项目名 | 状态 |
|---|--------|------|
| 1 | agent-cost-optimizer | ✓ 在 portfolio |
| 2 | agent-eval-framework | ✓ 在 portfolio |
| 3 | agent-memory-toolkit | ✓ 在 portfolio |
| 4 | agent-native-starter | ✓ 在 portfolio |
| 5 | agent-observability | ✓ 在 portfolio |
| 6 | agent-ops-platform | ✓ 在 portfolio |
| 7 | agent-security-scanner | ✓ 在 portfolio |
| 8 | agent-test-framework | ✓ 在 portfolio |
| 9 | agentic-workflow | ✓ 在 portfolio |
| 10 | ai-agent-gateway | ✓ 在 portfolio |
| 11 | ai-code-reviewer | ❌ **缺失** |
| 12 | ai-portfolio-builder | ✓ 在 portfolio |
| 13 | calligraphy-ai | ✓ 在 portfolio (旗舰) |
| 14 | code-navigator | ✓ 在 portfolio |
| 15 | code-review-bot | ✓ 在 portfolio |
| 16 | content-auto-publisher | ✓ 在 portfolio |
| 17 | cs-agent | ✓ 在 portfolio |
| 18 | deepfake-guard | ✓ 在 portfolio |
| 19 | doc-guard | ✓ 在 portfolio |
| 20 | doc-intelligence | ✓ 在 portfolio |
| 21 | enterprise-knowledge-base | ✓ 在 portfolio |
| 22 | llm-cost-calculator | ✓ 在 portfolio |
| 23 | mcp-toolkit | ✓ 在 portfolio |
| 24 | price-tracker | ✓ 在 portfolio |
| 25 | prompt-injection-guard | ✓ 在 portfolio |
| 26 | prompt-injection-tester | ❌ **缺失** |
| 27 | proposal-generator | ✓ 在 portfolio |
| 28 | remote-control | ❌ **缺失** |
| 29 | scraping-api | ✓ 在 portfolio |
| 30 | social-copy | ✓ 在 portfolio |
| 31 | wechat-content-assistant | ✓ 在 portfolio |

---

## 2. 差异对比

### 2.1 需要新增到 Portfolio 的 3 个开源项目

| 项目名 | 类型 | 核心价值 | 现有对应项 |
|--------|------|----------|------------|
| **ai-code-reviewer** | 代码审查 Agent | 静态规则(100+) + LLM 增强，支持 GitHub/GitLab CI，有定价体系 | `code-review-bot` (已在 portfolio) —— **不同产品**：ai-code-reviewer 侧重规则引擎+定价；code-review-bot 侧重 PR 自动评论 |
| **prompt-injection-tester** | 安全测试工具 | 纯前端、20+ 注入模式、在线演示、OWASP LLM Top 10 | `prompt-injection-guard` (已在 portfolio) —— **不同产品**：tester 是检测工具；guard 是防护引擎 |
| **remote-control** (RemoteEye v3.0 Pro) | 远程桌面 | 对标 TeamViewer/向日葵，差分截屏、会话录制回放、E2E 加密、远程 Shell | **无同类项目**，独特品类 |

### 2.2 Portfolio 中误放入"项目区"的服务/套餐项 (17 个)

这些位于 index.html `#projects` section 的 `.card` 中，但**不是开源项目**，应移至 `#services` 或 `#packages`：

| # | 当前显示名称 | 实际性质 | 建议位置 |
|---|-------------|----------|----------|
| 1 | AI Skill 定制开发 | 服务 | `#services` |
| 2 | 数据自动化方案 | 服务 | `#services` |
| 3 | 书法字库定制 | 服务 | `#services` |
| 4 | 自动化工作流 | 服务 | `#services` |
| 5 | 企业知识库搭建 | 服务 | `#services` |
| 6 | MCP 协议集成 | 服务 | `#services` |
| 7 | AI Agent 安全审计 | 服务 | `#services` |
| 8 | Agent 评估与测试 | 服务 | `#services` |
| 9 | 快速脚本包 | 套餐 | `#packages` |
| 10 | 标准自动化包 | 套餐 | `#packages` |
| 11 | AI Agent / MCP 包 | 套餐 | `#packages` |
| 12-16 | FAQ 5 个卡片 | FAQ 内容 | `#faq` section (已存在) |

### 2.3 Portfolio 有但 projects 目录无的 2 个"项目"

| 项目名 | 说明 |
|--------|------|
| Auto Backup | 服务/套餐描述，非开源项目 |
| Security Audit Toolkit | 服务描述，非开源项目 (OpenClaw 安全审计工具集对应 `agent-security-scanner` 已在 portfolio) |

---

## 3. 具体更新建议

### 3.1 新增 3 个项目卡片到 index.html `#projects` section

#### A. ai-code-reviewer — AI 代码审查 Agent (规则引擎版)
```html
<div class="card">
  <h3>🔍 AI Code Reviewer</h3>
  <p>基于 LLM 的智能代码审查系统，100+ 静态规则（安全/性能/质量）+ LLM 增强审查，支持 GitHub/GitLab CI 集成，多格式报告输出。提供开源/SaaS/企业版三档定价。</p>
  <span class="tag">Python</span><span class="tag">AST</span><span class="tag">LLM</span><span class="tag">CI/CD</span>
  <a href="https://github.com/kaising-openclaw1/ai-code-reviewer" class="link">查看详情 →</a>
</div>
```

#### B. prompt-injection-tester — Prompt Injection 在线检测器
```html
<div class="card">
  <h3>🛡️ Prompt Injection Tester</h3>
  <p>纯前端在线检测工具，20+ 注入攻击模式（角色劫持/提示词泄露/越狱/编码混淆），零后端、数据不出浏览器，实时可视化安全评分。参考 OWASP LLM Top 10 2026。</p>
  <span class="tag">JavaScript</span><span class="tag">安全</span><span class="tag">在线工具</span>
  <a href="https://kaising-openclaw1.github.io/prompt-injection-tester/" class="link" target="_blank">在线体验 →</a>
</div>
```

#### C. remote-control — RemoteEye v3.0 Pro
```html
<div class="card">
  <h3>🖥️ RemoteEye v3.0 Pro</h3>
  <p>对标 TeamViewer/向日葵的开源远程桌面方案：差分截屏省 70-90% 带宽、会话录制回放、远程 Shell、E2E 加密、连接码/无人值守模式、移动端触控支持。</p>
  <span class="tag">Python</span><span class="tag">FastAPI</span><span class="tag">WebRTC</span><span class="tag">远程控制</span>
  <a href="https://github.com/kaising-openclaw1/remote-control" class="link">查看详情 →</a>
</div>
```

### 3.2 清理 `#projects` section：移除 17 个服务/套餐/FAQ 卡片
- 将服务类卡片移至 `#services` section（已有对应服务卡，可合并或补充）
- 将套餐类卡片移至 `#packages` section（已有对应套餐卡，可合并）
- 删除 FAQ 卡片（`#faq` section 已存在完整版本）

### 3.3 修正/移除 2 个无对应项目的卡片
- **Auto Backup** → 移除，或改为链接到 `auto-backup` 项目（如存在计划）
- **Security Audit Toolkit** → 移除，已有 `🛡️ Agent Security Scanner` 覆盖同类功能

### 3.4 更新统计数据
index.html 第 383 行：
```html
<div class="stat"><div class="num">50+</div><div class="label">开源项目</div></div>
```
建议更新为 **31+**（实际项目数），或 **33+**（加上即将新增的 3 个）。

---

## 4. 执行清单

| 任务 | 优先级 | 预估工时 | 状态 |
|------|--------|----------|------|
| 1. 向 index.html 添加 3 个新项目卡片 | P0 | 15 min | ⬜ 待办 |
| 2. 从 #projects 移除 17 个服务/套餐/FAQ 卡片 | P0 | 20 min | ⬜ 待办 |
| 3. 移除/修正 Auto Backup 和 Security Audit Toolkit 卡片 | P1 | 5 min | ⬜ 待办 |
| 4. 更新 "开源项目" 统计数字 (50+ → 33+) | P1 | 2 min | ⬜ 待办 |
| 5. 验证所有 GitHub 链接指向正确仓库 (kaising-openclaw1) | P1 | 10 min | ⬜ 待办 |
| 6. 考虑将 remote-control 添加到 case-studies.html 作为产品级案例 | P2 | 15 min | ⬜ 待办 |

---

## 5. 补充信息：新增项目详情速查

### ai-code-reviewer
- **GitHub**: https://github.com/kaising-openclaw1/ai-code-reviewer
- **核心**: 100+ 静态规则 + LLM 增强 + GitHub/GitLab CI + 多格式报告
- **定价**: 开源免费 / ¥199/月/仓库 / ¥2000/月企业版 / ¥50/次

### prompt-injection-tester
- **在线演示**: https://kaising-openclaw1.github.io/prompt-injection-tester/
- **GitHub**: https://github.com/kaising-openclaw1/prompt-injection-tester
- **核心**: 纯前端、20+ 攻击模式、实时可视化、OWASP LLM Top 10 参考

### remote-control (RemoteEye v3.0 Pro)
- **GitHub**: https://github.com/kaising-openclaw1/remote-control
- **核心**: 差分截屏、会话录制回放、远程 Shell、E2E 加密、连接码/无人值守、移动触控
- **定位**: 对标 TeamViewer/向日葵/RustDesk 的专业级开源远程桌面

---

## 6. 结论

**Portfolio 站点当前展示 30 个真实开源项目 + 17 个服务/套餐项 + 2 个无对应项目项 = 49 个卡片**，但实际 `/projects` 目录有 **31 个开源项目**。

**核心问题**: 
1. 3 个成熟开源项目未展示（ai-code-reviewer, prompt-injection-tester, remote-control）
2. 服务/套餐/FAQ 混杂在项目展示区，稀释了开源作品的展示权重
3. 统计数字（50+）与实际（31）严重不符

**建议**: 按执行清单逐项修复，预计 1 小时内完成。修复后项目区将展示 **33 个** 真实开源项目，结构更清晰，数据更真实。