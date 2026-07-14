# -*- coding: utf-8 -*-
"""
批量蒸馏脚本 - 批量读取 raw/ 中的拆分文稿，生成 distill/ 知识卡片
供 Claude Code /ingest 命令调用，也可独立运行进行预处理
"""
import os
import sys
import io
import re
import json
import glob
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 分类关键词映射
CATEGORY_KEYWORDS = {
    "AI工具/平台推荐": ["AI", "大模型", "模型", "GPT", "Claude", "ChatGPT", "OpenAI", "DeepSeek", "提示词", "prompt", "API", "开源", "网站", "工具", "agent", "Agent", "Skill", "skill", "MCP"],
    "AI教育/学习": ["学习", "教育", "课程", "教学", "培训", "吴恩达", "路线图", "入门", "孩子", "学生"],
    "编程开发": ["代码", "开发", "编程", "程序员", "开源", "GitHub", "Java", "Python", "PHP", "前端", "后端", "部署"],
    "电商运营/跨境": ["跨境", "电商", "TK", "TikTok", "选品", "1688", "小店", "店铺", "物流", "货代", "美区", "运营"],
    "短视频制作": ["视频", "剪辑", "运镜", "拍摄", "字幕", "短剧"],
    "投资理财/股票": ["股票", "炒股", "A股", "投资", "大盘", "涨停", "量能", "成交量", "K线", "回购"],
    "Windows/电脑技巧": ["Windows", "win", "电脑", "软件", "卸载", "系统", "设置", "英特尔"],
    "自媒体/内容创作": ["博主", "自媒体", "创作", "IP", "文案", "粉丝", "播放"],
    "生活/育儿": ["孩子", "小朋友", "宝宝", "食材", "食谱", "汤"],
}

PLATFORM_EMOJI = {"douyin": "📱抖音", "bilibili": "📺B站"}


def detect_categories(text):
    """根据内容自动检测分类"""
    scores = {}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in text.lower())
        if score > 0:
            scores[cat] = score
    if not scores:
        return ["其他"]
    sorted_cats = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [cat for cat, _ in sorted_cats[:2]]


def detect_knowledge_type(text):
    """检测知识类型"""
    if any(kw in text for kw in ["步骤", "点击", "设置", "打开", "输入", "注册"]):
        return "教程"
    if any(kw in text for kw in ["避坑", "弯路", "不要", "误区", "别", "坑"]):
        return "避坑指南"
    if any(kw in text for kw in ["推荐", "关注", "博主", "宝藏"]):
        return "工具推荐"
    if any(kw in text for kw in ["趋势", "未来", "时代", "机会", "行业"]):
        return "行业分析"
    if any(kw in text for kw in ["参数", "配置", "参数", "设置参数"]):
        return "参数配置"
    return "经验总结"


def create_knowledge_card(input_file, output_dir):
    """读取拆分后的文稿，生成预标注的待蒸馏文件"""
    with open(input_file, 'r', encoding='utf-8') as f:
        text = f.read()

    # 提取元数据
    title_match = re.search(r'^# (.+)$', text, re.MULTILINE)
    title = title_match.group(1) if title_match else os.path.basename(input_file)

    categories = detect_categories(text)
    ktype = detect_knowledge_type(text)

    # 生成输出文件名
    safe_title = re.sub(r'[\\/:*?"<>|]', '', title)[:50]
    out_name = f"[待蒸馏]_{safe_title}.md"
    out_path = os.path.join(output_dir, out_name)

    # 检查是否已存在
    if os.path.exists(out_path):
        return None, "exists"

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(f"# {title}\n\n")
        f.write(f"- **来源平台**：📱抖音\n")
        f.write(f"- **分类标签**：{' / '.join(categories)}\n")
        f.write(f"- **来源**：[抖音作者](待补充链接)\n")
        f.write(f"- **知识类型**：{ktype}\n")
        f.write(f"- **状态**：待蒸馏 (需确认来源链接+作者)\n\n")
        f.write(f"---\n\n")
        f.write(f"## 原始文稿\n\n{text}\n")

    return out_name, "created"


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Batch pre-process Douyin transcripts for distillation')
    parser.add_argument('input_dir', help='Directory containing split transcript files (.md)')
    parser.add_argument('-o', '--output', default='./distill/待处理/', help='Output directory for pre-labeled cards')
    parser.add_argument('--dry-run', action='store_true', help='Preview only, do not create files')

    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    files = sorted(glob.glob(os.path.join(args.input_dir, '*.md')))
    print(f"[SCAN] Found {len(files)} transcript files in {args.input_dir}")
    print()

    created = 0
    skipped = 0
    results = []

    for fpath in files:
        fname = os.path.basename(fpath)
        if args.dry_run:
            with open(fpath, 'r', encoding='utf-8') as f:
                text = f.read()
            cats = detect_categories(text)
            ktype = detect_knowledge_type(text)
            results.append((fname, cats, ktype))
        else:
            result, status = create_knowledge_card(fpath, args.output)
            if status == "created":
                created += 1
                results.append((result, [], ""))
            else:
                skipped += 1

    if args.dry_run:
        for fname, cats, ktype in results:
            print(f"  {fname}")
            print(f"    -> 分类: {cats}  |  类型: {ktype}")
    else:
        print(f"[DONE] Created: {created}  |  Skipped (exists): {skipped}")
        print(f"[NEXT] Run /ingest on files in {args.output}")


if __name__ == '__main__':
    main()
