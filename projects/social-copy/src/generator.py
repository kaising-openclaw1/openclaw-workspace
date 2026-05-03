"""Social Copy Generator - Core generator"""

from src.templates import (
    XIAOHONGSHU_TEMPLATE,
    WEIBO_TEMPLATE,
    TWITTER_TEMPLATE,
    JUEJIN_TEMPLATE,
)


class SocialCopyGenerator:
    """多平台社交媒体文案生成器"""

    def generate_xiaohongshu(self, topic, key_points, target_audience="", title=""):
        """生成小红书风格文案"""
        if not title:
            title = f"{topic} | {target_audience}必看" if target_audience else f"{topic} 完全指南"

        emojis = ["🔥", "✨", "💡", "📌", "🚀", "⭐", "💪", "🎯"]
        intro = f"今天给大家分享一下关于 **{topic}** 的干货！"
        if target_audience:
            intro += f" 特别是{target_audience}朋友们，建议收藏！"

        outro = "觉得有用的话记得 ❤️⭐ 收藏 + 关注，我会持续分享更多干货！"

        hashtags = "#" + topic.replace(" ", "")
        hashtags += "".join(f" #{kp.replace(' ', '')}" for kp in key_points[:3])
        hashtags += " #干货分享 #实用技巧"

        return XIAOHONGSHU_TEMPLATE.format(
            title=title,
            intro=intro,
            key_points=key_points,
            outro=outro,
            hashtags=hashtags,
        )

    def generate_weibo(self, topic, content, max_chars=140):
        """生成微博文案"""
        hashtags = f"#{topic}#"

        # 精简内容
        if len(content) + len(hashtags) > max_chars:
            content = content[:max_chars - len(hashtags) - 4] + "..."

        return WEIBO_TEMPLATE.format(
            topic=topic,
            content=content,
            hashtags=f"#{topic}#",
        )

    def generate_twitter(self, content, hashtags=None, is_thread=False):
        """生成Twitter文案"""
        if is_thread:
            # Thread 模式：按280字符分割
            parts = []
            sentences = content.replace("\n", " ").split(". ")
            current = ""

            for sentence in sentences:
                if len(current) + len(sentence) + 2 > 270:
                    parts.append(current.strip())
                    current = sentence + ". "
                else:
                    current += sentence + ". "

            if current.strip():
                parts.append(current.strip())

            # 添加序号和thread标识
            total = len(parts)
            result = []
            for i, part in enumerate(parts, 1):
                suffix = f" ({i}/{total})" if total > 1 else ""
                result.append(f"{part}{suffix}")

            return "\n\n---\n\n".join(result)

        # 单条推文
        hashtags_str = " ".join(f"#{h}" for h in (hashtags or []))
        return TWITTER_TEMPLATE.format(content=content[:250], hashtags=hashtags_str)

    def generate_juejin(self, title, intro, body, tags=None):
        """生成掘金/知乎风格文章"""
        tags_str = " ".join(f"`{t}`" for t in (tags or ["AI", "自动化", "Python"]))

        return JUEJIN_TEMPLATE.format(
            title=title,
            intro=intro,
            body=body,
            tags=tags_str,
        )
