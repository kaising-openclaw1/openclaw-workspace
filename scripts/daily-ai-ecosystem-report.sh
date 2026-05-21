#!/bin/bash
# 每日开源AI生态日报生成脚本（5大信息源）
# 覆盖: Blogwatcher + GitHub + HuggingFace + ClawHub + ModelScope
# 用法: bash scripts/daily-ai-ecosystem-report.sh

set -e

REPORT_DATE=$(date +%Y-%m-%d)
REPORT_DIR="/home/kaising/.openclaw/workspace/ai-daily-reports"
REPORT_FILE="${REPORT_DIR}/${REPORT_DATE}.md"
TEMP_DIR="/tmp/ai-daily-${REPORT_DATE}"

mkdir -p "$REPORT_DIR" "$TEMP_DIR"

# 检查是否已生成今日报告
if [ -f "$REPORT_FILE" ] && grep -q "已推送" "$REPORT_FILE" 2>/dev/null; then
    echo "今日报告已推送，跳过"
    exit 0
fi

echo "📡 生成 ${REPORT_DATE} 开源AI生态日报（5大信息源）..."

# ==================== 1. Blogwatcher AI 新闻 ====================
echo "🔍 扫描 Blogwatcher..."
export ALL_PROXY=socks5://127.0.0.1:1080

blogwatcher scan 2>/dev/null || true
BLOG_ARTICLES=$(blogwatcher articles 2>/dev/null | python3 -c "
import sys
articles = []
for line in sys.stdin:
    line = line.strip()
    if line:
        articles.append(line)
# 筛选今日文章（简单判断：包含今天日期）
today = '$(date +%Y-%m-%d)'
ai_keywords = ['AI', 'ai', 'ML', 'ml', 'LLM', 'llm', 'GPT', 'model', '模型', '机器学习', '深度学习', 'neural', 'transformer']
ai_articles = [a for a in articles if any(kw in a for kw in ai_keywords)][:15]
for i, a in enumerate(ai_articles, 1):
    print(f'{i}. {a}')
    print()
" 2>/dev/null || echo "⚠️ Blogwatcher 扫描失败")

echo "$BLOG_ARTICLES" > "$TEMP_DIR/blogwatcher.md"

# ==================== 2. GitHub 新项目 ====================
echo "🔍 扫描 GitHub..."
DATE_1D=$(date -u -d '1 day ago' +%Y-%m-%d)

GITHUB_REPOS=$(curl -s "https://api.github.com/search/repositories?q=created:>${DATE_1D}&sort=stars&order=desc&per_page=15" | python3 -c "
import json, sys
data = json.load(sys.stdin)
items = data.get('items', [])
for i, item in enumerate(items[:15], 1):
    desc = (item.get('description') or '')[:100]
    print(f\"{i}. **{item['full_name']}** - ⭐{item['stargazers_count']} - 🍴{item['forks_count']} - [{item.get('language','?')}] -> {item['html_url']}\")
    print(f\"   {desc}\")
    print()
" 2>/dev/null || echo "⚠️ GitHub 扫描失败")

echo "$GITHUB_REPOS" > "$TEMP_DIR/github.md"

# ==================== 3. HuggingFace 模型 ====================
echo "🔍 扫描 HuggingFace..."

HF_MODELS=$(curl -s "https://huggingface.co/api/models?sort=likes&direction=-1&limit=20&filter=text-generation" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for i, item in enumerate(data[:15], 1):
    pipeline = item.get('pipeline_tag','?')
    likes = item.get('likes',0)
    lm = item.get('lastModified','')[:10]
    tags = item.get('tags',[])[:3]
    print(f\"{i}. **{item['modelId']}** - ❤️{likes} | {pipeline} | {', '.join(tags)} -> https://huggingface.co/{item['modelId']}\")
    print()
" 2>/dev/null || echo "⚠️ HF 模型扫描失败")

HF_SPACES=$(curl -s "https://huggingface.co/api/spaces?sort=likes&direction=-1&limit=15" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for i, item in enumerate(data[:10], 1):
    sdk = item.get('sdk','?')
    likes = item.get('likes',0)
    print(f\"{i}. **{item['id']}** - ❤️{likes} | {sdk} -> https://huggingface.co/{item['id']}\")
    print()
" 2>/dev/null || echo "⚠️ HF Spaces 扫描失败")

echo "$HF_MODELS" > "$TEMP_DIR/hf_models.md"
echo "$HF_SPACES" > "$TEMP_DIR/hf_spaces.md"

# ==================== 4. ClawHub Skills ====================
echo "🔍 扫描 ClawHub..."

CLAWHUB=$(clawhub explore --limit 15 --json 2>/dev/null | python3 -c "
import json, sys
from datetime import datetime

raw = sys.stdin.read()
lines = raw.strip().split('\n')
json_start = None
for i, line in enumerate(lines):
    if line.strip().startswith('{') or line.strip().startswith('['):
        json_start = i
        break

if json_start is None:
    print('⚠️ ClawHub 扫描失败')
    sys.exit(0)

data = json.loads('\n'.join(lines[json_start:]))
items = data.get('items', [])

for i, item in enumerate(items[:15], 1):
    slug = item['slug']
    display = item.get('displayName', slug)
    summary = item.get('summary', '')[:150]
    stars = item['stats'].get('stars', 0)
    downloads = item['stats'].get('downloads', 0)
    version = item['latestVersion']['version']
    updated = datetime.fromtimestamp(item['updatedAt']/1000).strftime('%Y-%m-%d')
    tags = list(item.get('tags', {}).keys())
    tags_str = ', '.join([t for t in tags if t != 'latest'][:3])
    
    print(f\"{i}. **{display}** ({slug}) | v{version} | ⭐{stars} | ⬇{downloads} | {updated}\")
    print(f\"   标签: {tags_str}\")
    print(f\"   {summary}\")
    print(f\"   https://clawhub.ai/skills/{slug}\")
    print()
" 2>/dev/null || echo "⚠️ ClawHub 扫描失败")

echo "$CLAWHUB" > "$TEMP_DIR/clawhub.md"

# ==================== 5. 组合报告 ====================
echo "📝 组合报告..."

cat > "$REPORT_FILE" << EOF
# 📡 开源 AI 生态日报 - ${REPORT_DATE}

## 📰 Blogwatcher AI 技术博客（今日新文章）

$(cat "$TEMP_DIR/blogwatcher.md")

---

## GitHub 新项目（过去 24h 新建，按 stars 排序）

$(cat "$TEMP_DIR/github.md")

---

## HuggingFace 值得关注的模型

$(cat "$TEMP_DIR/hf_models.md")

---

## HuggingFace 热门 Spaces

$(cat "$TEMP_DIR/hf_spaces.md")

---

## ClawHub 最新 Skills（今日更新）

$(cat "$TEMP_DIR/clawhub.md")

---

## ModelScope（魔搭）

*待浏览器抓取*

---

## 📊 趋势总结 & 赚钱机会

*（待小鸣分析补充）*

---
*报告生成时间：$(date '+%Y-%m-%d %H:%M CST') | 数据源：Blogwatcher + GitHub API + HuggingFace API + ClawHub CLI*
EOF

# 清理临时文件
rm -rf "$TEMP_DIR"

echo "✅ 报告已生成: ${REPORT_FILE}"
