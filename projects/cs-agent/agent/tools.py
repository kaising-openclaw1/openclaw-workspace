"""工具定义"""
import sqlite3
from typing import Optional
from .core import Tool


def create_default_tools() -> list:
    """创建默认工具集"""
    return [
        Tool(
            name="web_search",
            description="搜索互联网获取最新信息",
            func=web_search,
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="database_query",
            description="查询 SQLite 数据库",
            func=database_query,
            parameters={
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "SQL 查询语句"}
                },
                "required": ["sql"]
            }
        ),
        Tool(
            name="calculator",
            description="执行数学计算",
            func=calculator,
            parameters={
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "数学表达式"}
                },
                "required": ["expression"]
            }
        ),
        Tool(
            name="order_query",
            description="查询订单状态",
            func=order_query,
            parameters={
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "订单号"}
                },
                "required": ["order_id"]
            }
        ),
        Tool(
            name="knowledge_base",
            description="检索知识库",
            func=knowledge_base_search,
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索问题"}
                },
                "required": ["query"]
            }
        )
    ]


def web_search(query: str) -> dict:
    """网络搜索"""
    # 这里可以用 SerpAPI、Tavily 等搜索服务
    return {"results": f"搜索'{query}'的结果（演示）"}


def database_query(sql: str) -> dict:
    """数据库查询"""
    try:
        conn = sqlite3.connect("data/agent_data.db")
        cursor = conn.cursor()
        cursor.execute(sql)
        results = cursor.fetchall()
        conn.close()
        return {"results": results}
    except Exception as e:
        return {"error": str(e)}


def calculator(expression: str) -> dict:
    """计算器"""
    try:
        # 安全评估：仅允许数学表达式
        result = eval(expression, {"__builtins__": {}}, {})
        return {"result": result}
    except Exception as e:
        return {"error": str(e)}


def order_query(order_id: str) -> dict:
    """订单查询（示例）"""
    # 实际项目中连接真实数据库
    orders = {
        "ORD001": {"status": "已发货", "tracking": "SF1234567890"},
        "ORD002": {"status": "处理中", "estimated": "2026-05-10"},
    }
    return orders.get(order_id, {"error": "订单不存在"})


def knowledge_base_search(query: str) -> dict:
    """知识库检索"""
    # 实际项目中连接向量数据库
    kb = {
        "退货政策": "7 天无理由退货，需保持商品完好",
        " shipping": "全国包邮，预计 3-5 天送达",
        "支付方式": "支持微信、支付宝、银联",
    }
    results = {k: v for k, v in kb.items() if k.lower() in query.lower()}
    return {"results": results} if results else {"results": "未找到相关信息"}
