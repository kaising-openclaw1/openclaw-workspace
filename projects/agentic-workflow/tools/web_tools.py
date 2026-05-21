"""网络工具集"""

from __future__ import annotations
import asyncio


async def web_search(query: str, num_results: int = 5) -> str:
    """搜索网络信息"""
    import httpx
    # 使用 DuckDuckGo 免费搜索 API
    url = f"https://html.duckduckgo.com/html/?q={query}"
    headers = {"User-Agent": "Mozilla/5.0"}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        # 简单解析
        from html.parser import HTMLParser
        results = []
        for line in resp.text.split("\n"):
            if "result__snippet" in line:
                parser = HTMLParser()
                text = parser.unescape(line)
                import re
                cleaned = re.sub(r"<[^>]+>", "", text).strip()
                if cleaned and len(cleaned) > 20:
                    results.append(cleaned)
                    if len(results) >= num_results:
                        break
    return "\n".join(results) if results else f"未找到关于 '{query}' 的搜索结果"


async def fetch_url(url: str) -> str:
    """抓取网页内容"""
    import httpx
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        # 提取文本内容（简化版）
        text = resp.text
        import re
        text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()[:5000]
