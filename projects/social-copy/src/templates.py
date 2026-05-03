"""Social Copy Generator - Platform templates"""

# 小红书模板
XIAOHONGSHU_TEMPLATE = """💡 {title}

{intro}

{''.join(f'✅ {point}\n' for point in key_points)}

{outro}

{hashtags}
"""

# 微博模板
WEIBO_TEMPLATE = """#{topic}# {content} {hashtags}"""

# Twitter模板
TWITTER_TEMPLATE = """{content}

{hashtags}"""

# 掘金模板
JUEJIN_TEMPLATE = """# {title}

{intro}

{body}

---

> 觉得有用？[关注我的GitHub](https://github.com/kaising-openclaw1) 获取更多自动化工具

{tags}
"""
