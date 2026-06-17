"""
Agent OS — HTTP Dashboard 服务器
================================
实时监控多节点状态、任务、资源
"""

import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, Optional

logger = logging.getLogger("agent-os.api.http_server")

try:
    from aiohttp import web
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False


async def start_dashboard(host: str = "127.0.0.1", port: int = 8080):
    """启动 Dashboard HTTP 服务器"""
    if not AIOHTTP_AVAILABLE:
        print("❌ 需要安装 aiohttp: pip install aiohttp")
        return

    from .core.engine import AgentOSEngine

    app = web.Application()
    engine = _get_or_create_engine()

    # ── API 路由 ──────────────────────────────────────

    async def get_status(request):
        status = engine.get_status()
        return web.json_response(status)

    async def get_tasks(request):
        status_filter = request.query.get("status")
        tasks = engine.list_tasks(status_filter)
        return web.json_response(tasks)

    async def get_task(request):
        task_id = request.match_info.get("task_id")
        task = engine.get_task(task_id)
        if not task:
            return web.json_response({"error": "not found"}, status=404)
        return web.json_response(task)

    async def get_nodes(request):
        if engine.mesh:
            peers = engine.mesh.peers
            nodes = [
                {
                    "id": pid,
                    "name": node.name,
                    "role": node.role.name,
                    "status": node.status.name,
                    "address": node.address,
                    "resources": node.resources,
                    "last_seen": node.last_seen,
                }
                for pid, node in peers.items()
            ]
        else:
            nodes = []
        return web.json_response(nodes)

    async def get_models(request):
        if engine.intelligence_router:
            models = engine.intelligence_router.registry.list_models()
        else:
            models = []
        return web.json_response(models)

    async def get_metrics(request):
        if engine.metrics:
            metrics = engine.metrics.snapshot()
        else:
            metrics = {}
        return web.json_response(metrics)

    async def submit_task(request):
        try:
            data = await request.json()
            task_id = await engine.submit_task(
                task_type=data.get("type", "generic"),
                payload=data.get("payload", {}),
                priority=data.get("priority", 5),
                timeout=data.get("timeout", 300),
            )
            return web.json_response({"task_id": task_id, "status": "submitted"})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)

    # ── Dashboard HTML ────────────────────────────────

    async def dashboard_html(request):
        html = _generate_dashboard_html()
        return web.Response(text=html, content_type="text/html")

    # 注册路由
    app.router.add_get("/", dashboard_html)
    app.router.add_get("/api/status", get_status)
    app.router.add_get("/api/tasks", get_tasks)
    app.router.add_get("/api/tasks/{task_id}", get_task)
    app.router.add_get("/api/nodes", get_nodes)
    app.router.add_get("/api/models", get_models)
    app.router.add_get("/api/metrics", get_metrics)
    app.router.add_post("/api/tasks", submit_task)

    # 启动
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()

    print(f"🌐 Dashboard: http://{host}:{port}")
    print(f"   API:       http://{host}:{port}/api/status")

    # 保持运行
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        await runner.cleanup()


def _get_or_create_engine() -> "AgentOSEngine":
    """获取或创建引擎实例"""
    from .core.engine import AgentOSEngine, AgentOSConfig
    if not hasattr(_get_or_create_engine, "_engine"):
        _get_or_create_engine._engine = AgentOSEngine(AgentOSConfig())
    return _get_or_create_engine._engine


def _generate_dashboard_html() -> str:
    """生成 Dashboard HTML"""
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Agent OS Dashboard</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         background: #0a0a0f; color: #e0e0e0; }
  .header { background: linear-gradient(135deg, #1a1a2e, #16213e);
            padding: 20px 30px; border-bottom: 1px solid #2a2a4a; }
  .header h1 { font-size: 24px; background: linear-gradient(90deg, #00d4ff, #7b2ff7);
               -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
  .header .subtitle { color: #888; font-size: 14px; margin-top: 4px; }
  .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
          gap: 16px; margin-bottom: 20px; }
  .card { background: #14141f; border: 1px solid #2a2a4a; border-radius: 12px;
          padding: 20px; }
  .card h3 { font-size: 14px; color: #888; text-transform: uppercase; letter-spacing: 1px;
             margin-bottom: 12px; }
  .stat-value { font-size: 32px; font-weight: 700; color: #00d4ff; }
  .stat-label { font-size: 12px; color: #666; margin-top: 4px; }
  table { width: 100%; border-collapse: collapse; }
  th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #2a2a4a;
           font-size: 13px; }
  th { color: #888; font-weight: 600; text-transform: uppercase; font-size: 11px; }
  .status-online { color: #00ff88; }
  .status-offline { color: #ff4444; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px;
           font-weight: 600; }
  .badge-running { background: #00d4ff22; color: #00d4ff; border: 1px solid #00d4ff44; }
  .badge-completed { background: #00ff8822; color: #00ff88; border: 1px solid #00ff8844; }
  .badge-failed { background: #ff444422; color: #ff4444; border: 1px solid #ff444444; }
  .badge-pending { background: #ffaa0022; color: #ffaa00; border: 1px solid #ffaa0044; }
  .refresh-btn { background: #2a2a4a; color: #e0e0e0; border: none; padding: 8px 16px;
                 border-radius: 6px; cursor: pointer; font-size: 13px; }
  .refresh-btn:hover { background: #3a3a5a; }
  .flex { display: flex; justify-content: space-between; align-items: center; }
  @media (max-width: 768px) {
    .grid { grid-template-columns: 1fr; }
    .container { padding: 10px; }
  }
</style>
</head>
<body>
<div class="header">
  <div class="flex">
    <div>
      <h1>🧠 Agent OS Dashboard</h1>
      <div class="subtitle">多机器 Agent 算力操作系统 · 实时监控</div>
    </div>
    <button class="refresh-btn" onclick="refreshAll()">🔄 刷新</button>
  </div>
</div>
<div class="container">
  <div class="grid" id="stats-grid">
    <div class="card"><h3>节点状态</h3><div class="stat-value" id="node-status">-</div></div>
    <div class="card"><h3>运行中任务</h3><div class="stat-value" id="running-tasks">-</div></div>
    <div class="card"><h3>已完成任务</h3><div class="stat-value" id="completed-tasks">-</div></div>
    <div class="card"><h3>运行时间</h3><div class="stat-value" id="uptime">-</div></div>
  </div>

  <div class="card" style="margin-bottom: 16px;">
    <h3>📋 任务列表</h3>
    <table>
      <thead><tr><th>ID</th><th>类型</th><th>状态</th><th>优先级</th><th>创建时间</th></tr></thead>
      <tbody id="tasks-table"><tr><td colspan="5">加载中...</td></tr></tbody>
    </table>
  </div>

  <div class="card" style="margin-bottom: 16px;">
    <h3>🔗 集群节点</h3>
    <table>
      <thead><tr><th>名称</th><th>角色</th><th>状态</th><th>地址</th><th>最后活跃</th></tr></thead>
      <tbody id="nodes-table"><tr><td colspan="5">加载中...</td></tr></tbody>
    </table>
  </div>

  <div class="card">
    <h3>🧠 可用模型</h3>
    <table>
      <thead><tr><th>名称</th><th>提供商</th><th>智力等级</th><th>上下文</th><th>成本/1k输入</th><th>评分</th></tr></thead>
      <tbody id="models-table"><tr><td colspan="6">加载中...</td></tr></tbody>
    </table>
  </div>
</div>

<script>
async function fetchJSON(url) {
  try {
    const resp = await fetch(url);
    return await resp.json();
  } catch(e) { return null; }
}

function formatTime(ts) {
  if (!ts) return '-';
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString('zh-CN');
}

async function refreshAll() {
  // Status
  const status = await fetchJSON('/api/status');
  if (status) {
    document.getElementById('node-status').textContent =
      status.running ? '🟢 运行中' : '🔴 已停止';
    document.getElementById('running-tasks').textContent =
      status.tasks?.running || 0;
    document.getElementById('completed-tasks').textContent =
      status.tasks?.completed || 0;
    document.getElementById('uptime').textContent =
      Math.floor(status.uptime || 0) + 's';
  }

  // Tasks
  const tasks = await fetchJSON('/api/tasks');
  if (tasks) {
    const tbody = document.getElementById('tasks-table');
    if (tasks.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5">暂无任务</td></tr>';
    } else {
      tbody.innerHTML = tasks.slice(0, 20).map(t => `
        <tr>
          <td style="font-family: monospace; font-size: 12px;">${t.id}</td>
          <td>${t.type}</td>
          <td><span class="badge badge-${t.status}">${t.status}</span></td>
          <td>${t.priority}</td>
          <td>${formatTime(t.created_at)}</td>
        </tr>
      `).join('');
    }
  }

  // Nodes
  const nodes = await fetchJSON('/api/nodes');
  if (nodes) {
    const tbody = document.getElementById('nodes-table');
    if (nodes.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5">无其他节点</td></tr>';
    } else {
      tbody.innerHTML = nodes.map(n => `
        <tr>
          <td>${n.name}</td>
          <td>${n.role}</td>
          <td class="status-${n.status.toLowerCase()}">${n.status}</td>
          <td>${n.address}</td>
          <td>${formatTime(n.last_seen)}</td>
        </tr>
      `).join('');
    }
  }

  // Models
  const models = await fetchJSON('/api/models');
  if (models) {
    const tbody = document.getElementById('models-table');
    tbody.innerHTML = models.map(m => `
      <tr>
        <td>${m.name}</td>
        <td>${m.provider}</td>
        <td><span class="badge badge-running">${m.level}</span></td>
        <td>${(m.context / 1024).toFixed(0)}K</td>
        <td>$${m.cost_in.toFixed(4)}</td>
        <td>${m.score.toFixed(2)}</td>
      </tr>
    `).join('');
  }
}

// Auto refresh every 10s
refreshAll();
setInterval(refreshAll, 10000);
</script>
</body>
</html>"""
