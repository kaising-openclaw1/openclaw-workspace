"""
Content Auto-Publisher - 内容格式适配器
读取 Markdown + YAML 格式的内容，自动生成各平台适配版本
"""

import sys
import yaml
from pathlib import Path
from jinja2 import Template


# 小红书适配模板（短平快、带emoji、话题标签）
XIAOHONGSHU_TEMPLATE = Template("""{{ title }}

{{ summary }}

💡 {{ key_points | default(['干货', '建议收藏']) | join(' | ') }}

{% if tags %}#{{ tags | join(' #') }}{% endif %}
""")

# 公众号适配模板（长文、分段、引导关注）
WECHAT_TEMPLATE = Template("""# {{ title }}

{% if subtitle %}
> {{ subtitle }}
{% endif %}

{{ content }}

---
💬 觉得有用？关注我获取更多实战技巧！
""")

# 知乎适配模板（Markdown直接发）
ZHIHU_TEMPLATE = Template("""# {{ title }}

{% if subtitle %}
> {{ subtitle }}
{% endif %}

{{ content }}

*—— 本文首发于公众号，欢迎关注获取更多实战内容 *""")

# 微博适配模板（短文案）
WEIBO_TEMPLATE = Template("""{{ title }}

{{ summary }}

{% if tags %}#{{ tags[0] }}# {% endif %}阅读全文：[链接]
""")


def parse_content(content_path: str) -> dict:
    """解析 Markdown 文件，分离 YAML front matter 和正文"""
    with open(content_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    parts = text.split('---', 2)
    if len(parts) < 3:
        raise ValueError(f"Invalid content format: {content_path}")
    
    meta = yaml.safe_load(parts[1])
    body = parts[2].strip()
    meta['content'] = body
    
    # 自动生成摘要
    if 'summary' not in meta:
        # 取第一段作为摘要
        first_para = body.split('\n\n')[0].replace('#', '').strip()
        meta['summary'] = first_para[:200] + ('...' if len(first_para) > 200 else '')
    
    # 提取关键要点
    if 'key_points' not in meta:
        meta['key_points'] = ['干货', '建议收藏']
    
    return meta


def generate_platform_versions(content_path: str, output_dir: str) -> dict:
    """读取原始内容，生成各平台适配版本"""
    meta = parse_content(content_path)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    
    results = {}
    
    # 小红书版本
    xhs_content = XIAOHONGSHU_TEMPLATE.render(**meta)
    xhs_path = output / 'xiaohongshu.txt'
    xhs_path.write_text(xhs_content, encoding='utf-8')
    results['xiaohongshu'] = str(xhs_path)
    
    # 公众号版本
    wechat_content = WECHAT_TEMPLATE.render(**meta)
    wechat_path = output / 'wechat.md'
    wechat_path.write_text(wechat_content, encoding='utf-8')
    results['wechat'] = str(wechat_path)
    
    # 知乎版本
    zhihu_content = ZHIHU_TEMPLATE.render(**meta)
    zhihu_path = output / 'zhihu.md'
    zhihu_path.write_text(zhihu_content, encoding='utf-8')
    results['zhihu'] = str(zhihu_path)
    
    # 微博版本
    weibo_content = WEIBO_TEMPLATE.render(**meta)
    weibo_path = output / 'weibo.txt'
    weibo_path.write_text(weibo_content, encoding='utf-8')
    results['weibo'] = str(weibo_path)
    
    return results


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("用法: python adapter.py <content.md> <output_dir>")
        print("示例: python adapter.py content/my-post.md output/")
        sys.exit(1)
    
    content_path = sys.argv[1]
    output_dir = sys.argv[2]
    
    results = generate_platform_versions(content_path, output_dir)
    
    print(f"✅ 已生成 {len(results)} 个平台版本:")
    for platform, path in results.items():
        print(f"   📄 {platform} → {path}")
