#!/bin/bash
# 每日开源AI生态日报生成脚本（5大信息源，按来源分类 + 标注新增）
# 覆盖: Blogwatcher + GitHub + HuggingFace + ClawHub + ModelScope
# 用法: bash scripts/daily-ai-ecosystem-report.sh

set -e

# 确保 go bin 和 npm global bin 在 PATH
export PATH="/home/kaising/go/bin:$HOME/.local/share/pnpm/global/5/node_modules/.bin:$PATH"

REPORT_DATE=$(date +%Y-%m-%d)
REPORT_DIR="/home/kaising/.openclaw/workspace/ai-daily-reports"
REPORT_FILE="${REPORT_DIR}/${REPORT_DATE}.md"
TEMP_DIR="/tmp/ai-daily-${REPORT_DATE}"
PREV_DATE=$(date -d '1 day ago' +%Y-%m-%d)
PREV_FILE="${REPORT_DIR}/${PREV_DATE}.md"

mkdir -p "$REPORT_DIR" "$TEMP_DIR"

# 检查是否已生成今日报告
if [ -f "$REPORT_FILE" ] && grep -q "已推送" "$REPORT_FILE" 2>/dev/null; then
    echo "今日报告已推送，跳过"
    exit 0
fi

echo "📡 生成 ${REPORT_DATE} 开源AI生态日报（5大信息源）..."

# 加载昨天的报告用于对比
PREV_GITHUB_ITEMS=""
PREV_CLAWHUB_ITEMS=""
PREV_HF_MODELS=""
PREV_HF_SPACES=""

if [ -f "$PREV_FILE" ]; then
    PREV_GITHUB_ITEMS=$(sed -n '/##.*GitHub.*新项目/,/---/{/###/p}' "$PREV_FILE" 2>/dev/null || true)
    PREV_CLAWHUB_ITEMS=$(sed -n '/##.*ClawHub/,/---/{/###/p}' "$PREV_FILE" 2>/dev/null || true)
    PREV_HF_MODELS=$(sed -n '/##.*HuggingFace.*模型/,/---/{/^[0-9]/p}' "$PREV_FILE" 2>/dev/null || true)
fi

# ==================== 1. Blogwatcher AI 新闻 ====================
echo "🔍 扫描 Blogwatcher..."
export ALL_PROXY=socks5://127.0.0.1:1080

blogwatcher scan 2>/dev/null || true
BLOG_ARTICLES=$(blogwatcher articles 2>/dev/null | python3 -c "
import sys, re

raw = sys.stdin.read()
# 解析 blogwatcher articles 输出格式
# [1844] [new] Title...
#        Blog: xxx
#        URL: xxx
#        Published: xxx
articles = []
lines = raw.strip().split('\n')
current = {}
for line in lines:
    # 标题行
    m = re.match(r'\s*\[(\d+)\]\s*\[new\]\s*(.+)', line)
    if m:
        if current.get('title'):
            articles.append(current)
        current = {'id': m.group(1), 'title': m.group(2).strip(), 'blog': '', 'url': '', 'date': ''}
        continue
    # Blog行
    m = re.match(r'\s*Blog:\s*(.+)', line)
    if m and current:
        current['blog'] = m.group(1).strip()
        continue
    # URL行
    m = re.match(r'\s*URL:\s*(.+)', line)
    if m and current:
        current['url'] = m.group(1).strip()
        continue
    # Published行
    m = re.match(r'\s*Published:\s*(.+)', line)
    if m and current:
        current['date'] = m.group(1).strip()
        continue
if current.get('title'):
    articles.append(current)

# 筛选 AI 相关
ai_keywords = ['AI', 'ai', 'ML', 'ml', 'LLM', 'llm', 'GPT', 'model', '模型', '机器学习', '深度学习', 'neural', 'transformer', 'Agent', 'agent', 'robot', 'automation', 'chatbot', 'deep learning', 'generative']
ai_articles = [a for a in articles if any(kw in a.get('title','') + ' ' + a.get('blog','') for kw in ai_keywords)][:15]

for i, a in enumerate(ai_articles, 1):
    print(f'{i}. **{a[\"title\"]}**')
    if a.get('blog'):
        print(f'   来源: {a[\"blog\"]}')
    if a.get('url'):
        print(f'   链接: {a[\"url\"]}')
    if a.get('date'):
        print(f'   发布: {a[\"date\"]}')
    print()
print(f'[今日共 {len(ai_articles)} 篇AI相关文章]')
" 2>/dev/null || echo "⚠️ Blogwatcher 扫描失败")

echo "$BLOG_ARTICLES" > "$TEMP_DIR/blogwatcher.md"
BLOG_COUNT=$(echo "$BLOG_ARTICLES" | grep -c "^[0-9]" 2>/dev/null || echo "0")

# ==================== 2. GitHub 新项目 ====================
echo "🔍 扫描 GitHub..."
DATE_1D=$(date -u -d '1 day ago' +%Y-%m-%d)

GITHUB_REPOS=$(curl -s "https://api.github.com/search/repositories?q=created:>${DATE_1D}+language:python+language:javascript+language:typescript&sort=stars&order=desc&per_page=20" | python3 -c "
import json, sys
from collections import Counter

data = json.load(sys.stdin)
items = data.get('items', [])

# 过滤垃圾: 同一用户批量创建 + 描述完全相同 + 1星
user_counts = Counter(i['full_name'].split('/')[0] for i in items)
desc_groups = {}
for i in items:
    desc = i.get('description', '')
    if desc:
        desc_groups.setdefault(desc, []).append(i)

spam_users = {u for u, c in user_counts.items() if c >= 4}
spam_items = set()
for desc, group in desc_groups.items():
    if len(group) >= 3:
        for i in group:
            if i['stargazers_count'] <= 1:
                spam_items.add(i['full_name'])

filtered = [i for i in items if i['full_name'] not in spam_items and i['full_name'].split('/')[0] not in spam_users][:15]

for i, item in enumerate(filtered, 1):
    desc = (item.get('description') or '')[:120]
    lang = item.get('language', '?')
    stars = item['stargazers_count']
    forks = item['forks_count']
    name = item['full_name']
    url = item['html_url']
    print(f'### {i}. {name}')
    print(f'- **语言:** {lang} | **⭐** {stars} | **🍴** {forks}')
    print(f'- **描述:** {desc}')
    print(f'- **链接:** {url}')
    print()
if not filtered:
    print('今日无值得关注的GitHub新项目（已过滤低质量批量创建的repo）')
    print()
" 2>/dev/null || echo "⚠️ GitHub 扫描失败")

echo "$GITHUB_REPOS" > "$TEMP_DIR/github.md"
GITHUB_COUNT=$(echo "$GITHUB_REPOS" | grep -c "^###" 2>/dev/null || echo "0")

# 对比昨天：标记新增仓库
if [ -n "$PREV_GITHUB_ITEMS" ]; then
    NEW_GITHUB=$(echo "$GITHUB_REPOS" | python3 -c "
import sys
prev_items = '''$PREV_GITHUB_ITEMS'''
prev_names = set()
for line in prev_items.strip().split('\n'):
    if line.startswith('###'):
        # 提取仓库名
        parts = line.split('.', 1)
        if len(parts) > 1:
            name = parts[1].strip().lstrip('.').strip()
            prev_names.add(name)

new_count = 0
for line in sys.stdin:
    if line.startswith('###'):
        parts = line.split('.', 1)
        if len(parts) > 1:
            name = parts[1].strip().lstrip('.').strip()
            if name not in prev_names:
                new_count += 1
print(f'其中 {new_count} 个为新出现项目')
" 2>/dev/null || echo "")
else
    NEW_GITHUB="（无昨日数据，全部为新项目）"
fi

# ==================== 3. HuggingFace 模型 ====================
echo "🔍 扫描 HuggingFace..."

HF_MODELS=$(curl -s "https://huggingface.co/api/models?sort=likes&direction=-1&limit=20" | python3 -c "
import json, sys
data = json.load(sys.stdin)
# 按类型分类
categories = {'text-generation': [], 'text-to-image': [], 'multimodal': [], 'speech': [], 'other': []}
for item in data[:15]:
    pipeline = item.get('pipeline_tag', 'other')
    entry = f\"**{item['modelId']}** — ❤️{item.get('likes',0)} | {pipeline} | {', '.join(item.get('tags',[])[:3])}\"
    if 'text-to-image' in pipeline or 'image' in pipeline.lower():
        categories['text-to-image'].append(entry)
    elif 'speech' in pipeline.lower() or 'audio' in pipeline.lower():
        categories['speech'].append(entry)
    elif 'text-generation' in pipeline:
        categories['text-generation'].append(entry)
    elif any(t in pipeline.lower() for t in ['multimodal', 'vision', 'image-text']):
        categories['multimodal'].append(entry)
    else:
        categories['other'].append(entry)

for cat, entries in categories.items():
    if entries:
        cat_names = {'text-generation': '📝 文本生成', 'text-to-image': '🎨 图像生成', 'multimodal': '🔮 多模态', 'speech': '🎤 语音/音频', 'other': '📦 其他'}
        print(f'**{cat_names.get(cat, cat)}**')
        for e in entries:
            print(f'- {e}')
        print()
" 2>/dev/null || echo "⚠️ HF 模型扫描失败")

HF_SPACES=$(curl -s "https://huggingface.co/api/spaces?sort=likes&direction=-1&limit=15" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for i, item in enumerate(data[:10], 1):
    sdk = item.get('sdk','?')
    likes = item.get('likes',0)
    title = item.get('title', item['id'].split('/')[-1])
    desc = (item.get('description') or '')[:100]
    print(f'{i}. **{item[\"id\"]}** — ❤️{likes} | {sdk} | {title}')
    if desc:
        print(f'   {desc}')
    print()
" 2>/dev/null || echo "⚠️ HF Spaces 扫描失败")

echo "$HF_MODELS" > "$TEMP_DIR/hf_models.md"
echo "$HF_SPACES" > "$TEMP_DIR/hf_spaces.md"

# ==================== 4. ClawHub Skills ====================
echo "🔍 扫描 ClawHub..."

CLAWHUB=$(clawhub explore --limit 15 --json 2>/dev/null | python3 -c "
import json, sys
from datetime import datetime, timedelta

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

today = datetime.now()
yesterday = today - timedelta(days=1)

new_items = []
updated_items = []

for item in items[:15]:
    slug = item['slug']
    display = item.get('displayName', slug)
    summary = item.get('summary', '')[:150]
    stars = item['stats'].get('stars', 0)
    downloads = item['stats'].get('downloads', 0)
    version = item['latestVersion']['version']
    updated_ts = item['updatedAt'] / 1000
    updated = datetime.fromtimestamp(updated_ts)
    updated_str = updated.strftime('%Y-%m-%d')
    tags = list(item.get('tags', {}).keys())
    tags_str = ', '.join([t for t in tags if t != 'latest'][:3])
    
    entry = f\"**{display}** ({slug}) | v{version} | ⭐{stars} | ⬇{downloads} | 更新: {updated_str}\"
    if summary:
        entry += f\"\n   {summary}\"
    entry += f\"\n   https://clawhub.ai/skills/{slug}\"
    
    if updated >= yesterday:
        new_items.append(entry)
    else:
        updated_items.append(entry)

if new_items:
    print(f'**🆕 今日新增/更新 ({len(new_items)} 个):**')
    for e in new_items:
        print(f'- {e}')
    print()

if updated_items:
    print(f'**📋 近期更新 ({len(updated_items)} 个):**')
    for e in updated_items[:8]:
        print(f'- {e}')
    print()

print(f'[今日新增: {len(new_items)} | 近期更新: {len(updated_items)}]')
" 2>/dev/null || echo "⚠️ ClawHub 扫描失败")

echo "$CLAWHUB" > "$TEMP_DIR/clawhub.md"

# ==================== 5. 组合报告 ====================
echo "📝 组合报告..."

cat > "$REPORT_FILE" << EOF
# 🦊 开源 AI 生态日报 — ${REPORT_DATE}（$(date +%A)）

> 扫描时间：$(date '+%Y-%m-%d %H:%M CST') | 数据来源：Blogwatcher / GitHub / HuggingFace / ClawHub / ModelScope

---

## 📊 今日速览

| 信息源 | 今日新增 | 变化 |
|--------|---------|------|
| 📰 Blogwatcher AI 新闻 | ${BLOG_COUNT} 篇 | 按相关性筛选 |
| 🐙 GitHub 新项目 | ${GITHUB_COUNT} 个 | ${NEW_GITHUB} |
| 🤗 HuggingFace | Top 模型/Spaces | 分类展示 |
| 🦞 ClawHub Skills | 见详情 | 标注新增/更新 |
| 📡 ModelScope | 待补充 | 浏览器抓取 |

---

## 📰 Blogwatcher AI 新闻（今日新文章）

${BLOG_ARTICLES}

---

## 🐙 GitHub 新项目（过去 24h 新建，按 stars 排序）

${GITHUB_REPOS}

---

## 🤗 HuggingFace 动态

### 热门模型（按类型分类）

${HF_MODELS}

### 热门 Spaces

${HF_SPACES}

---

## 🦞 ClawHub 最新 Skills

${CLAWHUB}

---

## 📡 ModelScope（魔搭）

> ⚠️ ModelScope API 返回 404，暂无法通过 API 获取数据。后续考虑通过浏览器抓取补充。

---

## 📊 今日趋势总结 & 赚钱机会

*（待小鸣分析补充 — 基于以上5大信息源的新信息，提炼趋势和变现机会）*

---

> 🦊 *小鸣 | 开源 AI 生态日报 | 每日自动扫描 · 重点不在信息搬运，在于发现赚钱机会*

EOF

# 清理临时文件
rm -rf "$TEMP_DIR"

echo "✅ 报告已生成: ${REPORT_FILE}"
