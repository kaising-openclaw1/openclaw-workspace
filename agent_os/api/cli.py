"""
Agent OS — 命令行接口
=====================
完整的 CLI 体验，类似 `kubectl` 但面向 Agent 算力
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger("agent-os.cli")


def create_parser() -> argparse.ArgumentParser:
    """创建 CLI 参数解析器"""
    parser = argparse.ArgumentParser(
        prog="agent-os",
        description="🧠 Agent OS — 多机器 Agent 算力操作系统",
        epilog="更多信息: https://github.com/kaising-openclaw1/agent-os",
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # ── start ─────────────────────────────────────────
    start_parser = subparsers.add_parser("start", help="启动 Agent OS 节点")
    start_parser.add_argument("--name", "-n", help="节点名称")
    start_parser.add_argument("--port", "-p", type=int, default=8765, help="监听端口")
    start_parser.add_argument("--seed", "-s", action="append", help="种子节点 (host:port)")
    start_parser.add_argument("--data-dir", default="~/.agent-os", help="数据目录")
    start_parser.add_argument("--debug", action="store_true", help="调试模式")
    start_parser.add_argument("--no-mesh", action="store_true", help="禁用 Mesh 网络")
    start_parser.add_argument("--no-security", action="store_true", help="禁用安全飞地")

    # ── status ────────────────────────────────────────
    subparsers.add_parser("status", help="查看节点状态")

    # ── join ──────────────────────────────────────────
    join_parser = subparsers.add_parser("join", help="加入集群")
    join_parser.add_argument("seed", help="种子节点地址 (host:port)")

    # ── run ───────────────────────────────────────────
    run_parser = subparsers.add_parser("run", help="提交任务")
    run_parser.add_argument("prompt", nargs="?", help="任务描述")
    run_parser.add_argument("--file", "-f", help="从文件读取任务")
    run_parser.add_argument("--model", "-m", help="指定模型")
    run_parser.add_argument("--priority", "-p", type=int, default=5, choices=range(1, 11),
                          help="优先级 (1-10)")
    run_parser.add_argument("--timeout", "-t", type=float, default=300, help="超时秒数")
    run_parser.add_argument("--wait", "-w", action="store_true", help="等待完成")

    # ── task ──────────────────────────────────────────
    task_parser = subparsers.add_parser("task", help="任务管理")
    task_sub = task_parser.add_subparsers(dest="task_action")
    task_sub.add_parser("list", help="列出任务")
    task_sub.add_parser("ls", help="列出任务（别名）")
    task_view = task_sub.add_parser("view", help="查看任务详情")
    task_view.add_argument("task_id", help="任务 ID")
    task_cancel = task_sub.add_parser("cancel", help="取消任务")
    task_cancel.add_argument("task_id", help="任务 ID")

    # ── node ──────────────────────────────────────────
    node_parser = subparsers.add_parser("node", help="节点管理")
    node_sub = node_parser.add_subparsers(dest="node_action")
    node_sub.add_parser("list", help="列出集群节点")
    node_sub.add_parser("ls", help="列出集群节点（别名）")

    # ── model ─────────────────────────────────────────
    model_parser = subparsers.add_parser("model", help="模型管理")
    model_sub = model_parser.add_subparsers(dest="model_action")
    model_sub.add_parser("list", help="列出可用模型")
    model_sub.add_parser("ls", help="列出可用模型（别名）")
    model_route = model_sub.add_parser("route", help="测试路由决策")
    model_route.add_argument("--input-tokens", type=int, default=1000)
    model_route.add_argument("--output-tokens", type=int, default=500)
    model_route.add_argument("--complex", action="store_true", help="复杂任务")

    # ── plugin ────────────────────────────────────────
    plugin_parser = subparsers.add_parser("plugin", help="插件管理")
    plugin_sub = plugin_parser.add_subparsers(dest="plugin_action")
    plugin_sub.add_parser("list", help="列出插件")
    plugin_sub.add_parser("ls", help="列出插件（别名）")

    # ── encrypt ───────────────────────────────────────
    encrypt_parser = subparsers.add_parser("encrypt", help="加密源码文件")
    encrypt_parser.add_argument("path", help="文件路径")
    encrypt_parser.add_argument("--delete", action="store_true", help="加密后删除原文件")

    # ── decrypt ───────────────────────────────────────
    decrypt_parser = subparsers.add_parser("decrypt", help="解密源码文件")
    decrypt_parser.add_argument("path", help="加密文件路径")
    decrypt_parser.add_argument("--output", "-o", help="输出路径")

    # ── dashboard ─────────────────────────────────────
    dash_parser = subparsers.add_parser("dashboard", help="启动 Web Dashboard")
    dash_parser.add_argument("--port", type=int, default=8080, help="Dashboard 端口")
    dash_parser.add_argument("--host", default="127.0.0.1", help="监听地址")

    # ── version ───────────────────────────────────────
    subparsers.add_parser("version", help="显示版本信息")

    return parser


def main():
    """CLI 入口"""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "version":
        print("Agent OS v0.1.0")
        print("Node: https://github.com/kaising-openclaw1/agent-os")
        return

    # 需要引擎的命令
    engine_commands = {"start", "status", "join", "run", "task", "node",
                       "model", "plugin", "encrypt", "decrypt", "dashboard"}

    if args.command in engine_commands:
        asyncio.run(_run_command(args))


async def _run_command(args):
    """运行 CLI 命令"""
    from .core.engine import AgentOSEngine, AgentOSConfig

    if args.command == "start":
        await _cmd_start(args)
    elif args.command == "status":
        await _cmd_status()
    elif args.command == "join":
        await _cmd_join(args)
    elif args.command == "run":
        await _cmd_run(args)
    elif args.command == "task":
        await _cmd_task(args)
    elif args.command == "node":
        await _cmd_node()
    elif args.command == "model":
        await _cmd_model(args)
    elif args.command == "plugin":
        await _cmd_plugin()
    elif args.command == "encrypt":
        await _cmd_encrypt(args)
    elif args.command == "decrypt":
        await _cmd_decrypt(args)
    elif args.command == "dashboard":
        await _cmd_dashboard(args)


async def _cmd_start(args):
    """启动节点"""
    config = AgentOSConfig(
        node_name=args.name or f"node-{os.uname().nodename}",
        listen_port=args.port,
        seed_nodes=args.seed or [],
        data_dir=args.data_dir,
        enable_mesh=not args.no_mesh,
        enable_security=not args.no_security,
        debug=args.debug,
    )

    engine = AgentOSEngine(config)
    await engine.start()

    print(f"\n✅ Agent OS 已启动")
    print(f"   Node:     {engine.node_id}")
    print(f"   Name:     {config.node_name}")
    print(f"   Mesh:     {'enabled' if config.enable_mesh else 'disabled'}")
    print(f"   Security: {'enabled' if config.enable_security else 'disabled'}")
    print(f"   Port:     {config.listen_port}")
    print(f"\n   按 Ctrl+C 停止\n")

    # 保持运行
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n正在关闭...")
        await engine.shutdown("ctrl_c")


async def _cmd_status():
    """查看状态"""
    engine = _get_engine()
    status = engine.get_status()

    print(f"\n📊 Agent OS 状态")
    print(f"{'='*50}")
    print(f"  Node ID:    {status['node_id']}")
    print(f"  State:      {status['state']}")
    print(f"  Uptime:     {status['uptime']:.1f}s")
    print(f"  Tasks:      {status['tasks']['total']} total "
          f"({status['tasks']['running']} running, "
          f"{status['tasks']['completed']} completed)")
    print(f"\n  子系统:")
    for name, enabled in status['subsystems'].items():
        print(f"    {'✅' if enabled else '❌'} {name}")
    print(f"\n  插件: {len(status['plugins'])}")
    for p in status['plugins']:
        print(f"    {p['name']} v{p['version']} [{p['state']}]")
    print(f"{'='*50}\n")


async def _cmd_join(args):
    """加入集群"""
    print(f"🔗 正在连接种子节点: {args.seed}")
    # 简化实现：直接启动并连接
    config = AgentOSConfig(seed_nodes=[args.seed])
    engine = AgentOSEngine(config)
    await engine.start()
    print(f"✅ 已加入集群")


async def _cmd_run(args):
    """提交任务"""
    prompt = args.prompt
    if args.file:
        with open(args.file) as f:
            prompt = f.read()

    if not prompt:
        print("❌ 请提供任务描述或使用 --file")
        return

    engine = _get_engine()

    task_id = await engine.submit_task(
        task_type="execute",
        payload={"command": prompt},
        priority=args.priority,
        timeout=args.timeout,
    )

    print(f"📝 任务已提交: {task_id}")

    if args.wait:
        print("⏳ 等待完成...")
        while True:
            task = engine.get_task(task_id)
            if task and task["status"] in ("completed", "failed", "timeout"):
                if task["status"] == "completed":
                    result = task.get("result", {})
                    print(f"\n✅ 完成:")
                    print(result.get("stdout", ""))
                    if result.get("stderr"):
                        print(f"⚠️  Stderr:\n{result['stderr']}")
                else:
                    print(f"❌ {task['status']}: {task.get('error', '')}")
                break
            await asyncio.sleep(0.5)


async def _cmd_task(args):
    """任务管理"""
    engine = _get_engine()

    if args.task_action in ("list", "ls"):
        tasks = engine.list_tasks()
        if not tasks:
            print("📭 没有任务")
            return
        print(f"\n📋 任务列表 ({len(tasks)})")
        print(f"{'='*60}")
        for t in tasks:
            status_icon = {"pending": "⏳", "running": "🔄", "completed": "✅",
                          "failed": "❌", "timeout": "⏰"}
            icon = status_icon.get(t["status"], "❓")
            print(f"  {icon} {t['id']} | {t['type']} | {t['status']} | "
                  f"priority={t['priority']}")
        print()

    elif args.task_action == "view":
        task = engine.get_task(args.task_id)
        if not task:
            print(f"❌ 任务未找到: {args.task_id}")
            return
        print(f"\n📋 任务详情: {args.task_id}")
        print(json.dumps(task, indent=2, default=str))
        print()

    elif args.task_action == "cancel":
        print(f"🛑 取消任务: {args.task_id}")
        # 简化：标记为取消
        task = engine.get_task(args.task_id)
        if task:
            task["status"] = "cancelled"
            print("✅ 已取消")


async def _cmd_node():
    """节点管理"""
    engine = _get_engine()
    if engine.mesh:
        peers = engine.mesh.peers
        print(f"\n🔗 集群节点 ({len(peers)})")
        print(f"{'='*60}")
        for pid, node in peers.items():
            status_icon = "🟢" if node.status.name == "ONLINE" else "🔴"
            print(f"  {status_icon} {node.name} ({node.id[:8]})")
            print(f"     Role: {node.role.name} | Address: {node.address}")
            print(f"     Resources: {node.resources.get('cpu_count', '?')} CPUs")
        print()
    else:
        print("❌ Mesh 网络未启用")


async def _cmd_model(args):
    """模型管理"""
    engine = _get_engine()
    router = engine.intelligence_router

    if args.model_action in ("list", "ls"):
        models = router.registry.list_models()
        print(f"\n🧠 可用模型 ({len(models)})")
        print(f"{'='*70}")
        print(f"  {'Name':<25} {'Provider':<12} {'Level':<10} {'Cost In':<10} {'Score':<6}")
        print(f"{'-'*70}")
        for m in models:
            print(f"  {m['name']:<25} {m['provider']:<12} {m['level']:<10} "
                  f"${m['cost_in']:<8.4f} {m['score']:<6.2f}")
        print()

    elif args.model_action == "route":
        from .intelligence.router import TaskProfile
        task = TaskProfile(
            estimated_input_tokens=args.input_tokens,
            estimated_output_tokens=args.output_tokens,
            priority=8 if args.complex else 5,
        )
        decision = router.route(task)
        print(f"\n🧠 路由决策")
        print(f"{'='*50}")
        print(f"  复杂度:   {decision.intelligence_level.name}")
        print(f"  模型:     {decision.selected_model}")
        print(f"  提供商:   {decision.selected_provider}")
        print(f"  成本:     ${decision.estimated_cost:.4f}")
        print(f"  延迟:     {decision.estimated_latency:.0f}ms")
        print(f"  置信度:   {decision.confidence:.2f}")
        print(f"  原因:     {decision.reason}")
        if decision.alternatives:
            print(f"  备选:     {', '.join(decision.alternatives)}")
        print()


async def _cmd_plugin():
    """插件管理"""
    engine = _get_engine()
    plugins = engine.plugin_registry.list_plugins()
    if not plugins:
        print("📭 没有加载的插件")
        return
    print(f"\n🔌 插件 ({len(plugins)})")
    print(f"{'='*60}")
    for p in plugins:
        print(f"  {p['name']} v{p['version']} [{p['state']}]")
        if p['description']:
            print(f"    {p['description']}")
        if p['tools']:
            print(f"    工具: {p['tools']}")
    print()


async def _cmd_encrypt(args):
    """加密文件"""
    engine = _get_engine()
    if not engine.enclave:
        print("❌ 安全飞地未启用")
        return
    enc_path = await engine.enclave.encrypt_source(
        args.path, delete_original=args.delete
    )
    print(f"🔒 已加密: {args.path} → {enc_path}")


async def _cmd_decrypt(args):
    """解密文件"""
    engine = _get_engine()
    if not engine.enclave:
        print("❌ 安全飞地未启用")
        return
    out_path = await engine.enclave.decrypt_source(
        args.path, output_path=args.output
    )
    if out_path:
        print(f"🔓 已解密: {args.path} → {out_path}")
    else:
        print("❌ 解密失败（权限不足或密钥错误）")


async def _cmd_dashboard(args):
    """启动 Dashboard"""
    print(f"🌐 Dashboard 启动中: http://{args.host}:{args.port}")
    # 使用内置 HTTP 服务器
    from .api.http_server import start_dashboard
    await start_dashboard(host=args.host, port=args.port)


def _get_engine() -> "AgentOSEngine":
    """获取或创建引擎实例"""
    from .core.engine import AgentOSEngine, AgentOSConfig
    # 单例模式
    if not hasattr(_get_engine, "_engine"):
        config = AgentOSConfig()
        engine = AgentOSEngine(config)
        _get_engine._engine = engine
    return _get_engine._engine


if __name__ == "__main__":
    main()
