#!/usr/bin/env python3
"""AI Portfolio Builder — 一行命令从 GitHub 生成个人 Portfolio 网站"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("Error: requests not installed. Run: pip install -r requirements.txt")

try:
    from jinja2 import Template
except ImportError:
    sys.exit("Error: jinja2 not installed. Run: pip install -r requirements.txt")


GITHUB_API = "https://api.github.com"

# 语言显示名称映射
LANG_NAMES = {
    "Python": "Python",
    "JavaScript": "JavaScript",
    "TypeScript": "TypeScript",
    "HTML": "HTML",
    "CSS": "CSS",
    "Go": "Go",
    "Rust": "Rust",
    "Java": "Java",
    "C++": "C++",
    "C": "C",
    "Shell": "Shell",
    "Vue": "Vue",
    "Svelte": "Svelte",
    "Dart": "Dart",
    "Swift": "Swift",
    "Kotlin": "Kotlin",
    "PHP": "PHP",
    "Ruby": "Ruby",
    "Lua": "Lua",
    "Jupyter Notebook": "Jupyter",
}

# 技术栈图标映射（emoji）
LANG_ICONS = {
    "Python": "🐍",
    "JavaScript": "📜",
    "TypeScript": "🔷",
    "HTML": "🌐",
    "CSS": "🎨",
    "Go": "🐹",
    "Rust": "🦀",
    "Java": "☕",
    "C++": "⚙️",
    "Shell": "🖥️",
    "Vue": "💚",
    "Dart": "💙",
    "Jupyter Notebook": "📓",
}


def fetch_github_user(username: str) -> dict:
    """获取 GitHub 用户信息"""
    url = f"{GITHUB_API}/users/{username}"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_github_repos(username: str, sort: str = "updated", per_page: int = 30) -> list:
    """获取 GitHub 仓库列表"""
    url = f"{GITHUB_API}/users/{username}/repos"
    params = {
        "sort": sort,
        "per_page": per_page,
        "direction": "desc",
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def extract_description(repo: dict) -> str:
    """从仓库中提取描述，如果没有则生成一个"""
    if repo.get("description"):
        return repo["description"]
    # 根据语言和 star 数生成简要描述
    lang = repo.get("language", "Code")
    stars = repo.get("stargazers_count", 0)
    if stars > 100:
        return f"Popular {lang} project with {stars}+ stars"
    elif stars > 10:
        return f"{lang} project · {stars} stars"
    else:
        return f"{lang} project"


def clean_language(lang: str) -> str:
    """清理语言名称"""
    if not lang:
        return "Other"
    return LANG_NAMES.get(lang, lang)


def process_repos(repos: list, max_repos: int = 20) -> list:
    """处理仓库数据"""
    processed = []
    for repo in repos[:max_repos]:
        # 跳过 fork
        if repo.get("fork"):
            continue
        # 跳过模板仓库
        if repo.get("is_template"):
            continue

        lang = clean_language(repo.get("language"))
        icon = LANG_ICONS.get(lang, "📁")

        processed.append({
            "name": repo["name"],
            "description": extract_description(repo),
            "language": lang,
            "language_icon": icon,
            "stars": repo.get("stargazers_count", 0),
            "forks": repo.get("forks_count", 0),
            "watchers": repo.get("watchers_count", 0),
            "size_kb": round(repo.get("size", 0) / 1024, 1),
            "updated_at": repo.get("updated_at", ""),
            "created_at": repo.get("created_at", ""),
            "html_url": repo.get("html_url", ""),
            "homepage": repo.get("homepage", ""),
            "topics": repo.get("topics", []),
            "visibility": repo.get("visibility", "public"),
        })

    # 按 star 数排序
    processed.sort(key=lambda x: x["stars"], reverse=True)
    return processed


def get_tech_stats(repos: list) -> dict:
    """获取技术栈统计"""
    lang_count = {}
    for repo in repos:
        lang = repo.get("language")
        if lang:
            lang_count[lang] = lang_count.get(lang, 0) + 1

    # 排序
    sorted_langs = sorted(lang_count.items(), key=lambda x: x[1], reverse=True)
    total = sum(lang_count.values())

    stats = []
    for lang, count in sorted_langs[:8]:
        clean = clean_language(lang)
        icon = LANG_ICONS.get(clean, "📁")
        stats.append({
            "name": clean,
            "icon": icon,
            "count": count,
            "percentage": round(count / total * 100, 1) if total > 0 else 0,
        })

    return stats


# Jinja2 模板
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ name }} | Portfolio</title>
    <style>
        :root {
            --bg: #0f172a;
            --bg-card: #1e293b;
            --bg-card-hover: #334155;
            --text: #f1f5f9;
            --text-muted: #94a3b8;
            --accent: #3b82f6;
            --accent-hover: #60a5fa;
            --border: #334155;
            --gradient: linear-gradient(135deg, #3b82f6, #8b5cf6);
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
        }
        a { color: var(--accent); text-decoration: none; }
        a:hover { color: var(--accent-hover); }

        /* Hero */
        .hero {
            text-align: center;
            padding: 80px 20px 60px;
            background: linear-gradient(180deg, #1e293b 0%, var(--bg) 100%);
        }
        .hero img.avatar {
            width: 120px; height: 120px;
            border-radius: 50%;
            border: 3px solid var(--accent);
            margin-bottom: 20px;
        }
        .hero h1 { font-size: 2.5rem; margin-bottom: 8px; }
        .hero .bio { color: var(--text-muted); font-size: 1.1rem; max-width: 600px; margin: 0 auto 20px; }
        .hero .stats { display: flex; justify-content: center; gap: 40px; margin-top: 20px; }
        .hero .stats .stat { text-align: center; }
        .hero .stats .stat .num { font-size: 1.8rem; font-weight: 700; color: var(--accent); }
        .hero .stats .stat .label { color: var(--text-muted); font-size: 0.85rem; }
        .hero .social { margin-top: 20px; }
        .hero .social a {
            display: inline-block; margin: 0 8px; padding: 6px 16px;
            border: 1px solid var(--border); border-radius: 20px;
            color: var(--text-muted); font-size: 0.9rem;
            transition: all 0.2s;
        }
        .hero .social a:hover { border-color: var(--accent); color: var(--accent); }

        /* Section */
        .section { max-width: 1100px; margin: 0 auto; padding: 40px 20px; }
        .section h2 {
            font-size: 1.5rem; margin-bottom: 24px;
            padding-bottom: 12px; border-bottom: 2px solid var(--border);
        }

        /* Tech Stack */
        .tech-grid { display: flex; flex-wrap: wrap; gap: 12px; }
        .tech-badge {
            display: inline-flex; align-items: center; gap: 6px;
            padding: 8px 16px; background: var(--bg-card);
            border: 1px solid var(--border); border-radius: 20px;
            font-size: 0.9rem;
        }
        .tech-badge .pct { color: var(--text-muted); font-size: 0.8rem; }

        /* Projects Grid */
        .projects-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 20px;
        }
        .project-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            transition: all 0.2s;
            display: flex;
            flex-direction: column;
        }
        .project-card:hover {
            background: var(--bg-card-hover);
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(0,0,0,0.3);
        }
        .project-card h3 { margin-bottom: 8px; font-size: 1.15rem; }
        .project-card h3 a { color: var(--text); }
        .project-card h3 a:hover { color: var(--accent); }
        .project-card .desc { color: var(--text-muted); font-size: 0.9rem; flex: 1; margin-bottom: 16px; }
        .project-card .lang {
            display: inline-flex; align-items: center; gap: 4px;
            padding: 3px 10px; background: rgba(59,130,246,0.15);
            border-radius: 12px; font-size: 0.8rem; color: var(--accent);
            margin-bottom: 12px; width: fit-content;
        }
        .project-card .meta { display: flex; gap: 16px; color: var(--text-muted); font-size: 0.85rem; }
        .project-card .meta span { display: flex; align-items: center; gap: 4px; }
        .project-card .topics { margin-top: 12px; display: flex; flex-wrap: wrap; gap: 6px; }
        .project-card .topics span {
            padding: 2px 8px; background: rgba(139,92,246,0.15);
            border-radius: 10px; font-size: 0.75rem; color: #a78bfa;
        }

        /* Footer */
        footer {
            text-align: center; padding: 40px 20px;
            color: var(--text-muted); font-size: 0.85rem;
            border-top: 1px solid var(--border); margin-top: 40px;
        }

        @media (max-width: 640px) {
            .hero h1 { font-size: 1.8rem; }
            .projects-grid { grid-template-columns: 1fr; }
            .hero .stats { gap: 20px; }
        }
    </style>
</head>
<body>
    <!-- Hero -->
    <div class="hero">
        <img class="avatar" src="{{ avatar_url }}" alt="{{ name }}">
        <h1>{{ name }}</h1>
        {% if bio %}
        <p class="bio">{{ bio }}</p>
        {% endif %}
        <div class="stats">
            <div class="stat">
                <div class="num">{{ public_repos }}</div>
                <div class="label">Repositories</div>
            </div>
            <div class="stat">
                <div class="num">{{ followers }}</div>
                <div class="label">Followers</div>
            </div>
            <div class="stat">
                <div class="num">{{ following }}</div>
                <div class="label">Following</div>
            </div>
        </div>
        <div class="social">
            {% if html_url %}
            <a href="{{ html_url }}" target="_blank">🐙 GitHub</a>
            {% endif %}
            {% if blog_url %}
            <a href="{{ blog_url }}" target="_blank">📝 Blog</a>
            {% endif %}
            {% if email %}
            <a href="mailto:{{ email }}">📧 Email</a>
            {% endif %}
            {% if twitter_username %}
            <a href="https://twitter.com/{{ twitter_username }}" target="_blank">🐦 Twitter</a>
            {% endif %}
        </div>
    </div>

    <!-- Tech Stack -->
    <div class="section">
        <h2>🛠️ Tech Stack</h2>
        <div class="tech-grid">
            {% for tech in tech_stats %}
            <div class="tech-badge">
                {{ tech.icon }} {{ tech.name }}
                <span class="pct">({{ tech.percentage }}%)</span>
            </div>
            {% endfor %}
        </div>
    </div>

    <!-- Projects -->
    <div class="section">
        <h2>🚀 Projects</h2>
        <div class="projects-grid">
            {% for project in projects %}
            <div class="project-card">
                <h3><a href="{{ project.html_url }}" target="_blank">{{ project.name }}</a></h3>
                <p class="desc">{{ project.description }}</p>
                <div class="lang">{{ project.language_icon }} {{ project.language }}</div>
                <div class="meta">
                    <span>⭐ {{ project.stars }}</span>
                    <span>🍴 {{ project.forks }}</span>
                    <span>📅 {{ project.updated_at[:10] }}</span>
                </div>
                {% if project.topics %}
                <div class="topics">
                    {% for topic in project.topics[:5] %}
                    <span>{{ topic }}</span>
                    {% endfor %}
                </div>
                {% endif %}
            </div>
            {% endfor %}
        </div>
    </div>

    <footer>
        <p>Generated by <a href="https://github.com/kaising-openclaw1/ai-portfolio-builder" target="_blank">AI Portfolio Builder</a> · {{ generated_at }}</p>
    </footer>
</body>
</html>
"""


def generate_html(user_data: dict, repos: list, output: str, theme: str = "dark") -> str:
    """生成 HTML 文件"""
    template = Template(HTML_TEMPLATE)

    tech_stats = get_tech_stats(repos)

    html = template.render(
        name=user_data.get("name", user_data.get("login", "Developer")),
        bio=user_data.get("bio", ""),
        avatar_url=user_data.get("avatar_url", ""),
        html_url=user_data.get("html_url", ""),
        blog_url=user_data.get("blog", ""),
        email=user_data.get("email", ""),
        twitter_username=user_data.get("twitter_username", ""),
        public_repos=user_data.get("public_repos", 0),
        followers=user_data.get("followers", 0),
        following=user_data.get("following", 0),
        projects=repos,
        tech_stats=tech_stats,
        generated_at=datetime.now().strftime("%Y-%m-%d"),
        theme=theme,
    )

    output_path = Path(output)
    output_path.write_text(html, encoding="utf-8")
    print(f"✅ Portfolio generated: {output_path.absolute()}")
    return str(output_path.absolute())


def main():
    parser = argparse.ArgumentParser(
        description="AI Portfolio Builder — 从 GitHub 生成个人 Portfolio 网站",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --github-username yourname
  %(prog)s --github-username yourname --output my-portfolio.html
  %(prog)s --github-username yourname --theme light
  %(prog)s --github-username yourname --max-repos 15 --sort stars
        """,
    )
    parser.add_argument("--github-username", required=True, help="GitHub 用户名")
    parser.add_argument("--output", default="portfolio.html", help="输出文件路径 (默认: portfolio.html)")
    parser.add_argument("--theme", default="dark", choices=["dark", "light"], help="主题 (默认: dark)")
    parser.add_argument("--max-repos", type=int, default=20, help="最多展示项目数 (默认: 20)")
    parser.add_argument("--sort", default="updated", choices=["updated", "stars", "created"], help="排序方式")
    parser.add_argument("--token", default=None, help="GitHub Personal Access Token (提高 API 限制)")

    args = parser.parse_args()

    # 设置 token
    headers = {}
    if args.token:
        headers["Authorization"] = f"token {args.token}"
        headers["Accept"] = "application/vnd.github.v3+json"

    print(f"🔍 Fetching GitHub profile: {args.github_username}")
    user_data = fetch_github_user(args.github_username)

    print(f"📦 Fetching repositories (sort={args.sort}, max={args.max_repos})")
    raw_repos = fetch_github_repos(args.github_username, sort=args.sort, per_page=args.max_repos)

    print(f"📊 Processing {len(raw_repos)} repositories...")
    repos = process_repos(raw_repos, max_repos=args.max_repos)

    print(f"🎨 Generating portfolio ({args.theme} theme)...")
    output_path = generate_html(user_data, repos, args.output, args.theme)

    print(f"\n🎉 Done! Open {output_path} in your browser to see your portfolio.")


if __name__ == "__main__":
    main()
