# -*- coding: utf-8 -*-
"""
抖音合并文稿拆分器
将剪映导出的合并 TXT 文稿按话题边界拆分为独立视频文件
"""
import re
import os
import sys
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 视频边界特征（话题转换关键词）
BOUNDARY_MARKERS = [
    "这是一个",
    "每天认识一个",
    "如果你还在",
    "假如你从",
    "你说你要",
    "现在做跨境",
    "哈喽大家好",
    "兄弟们",
    "重磅消息",
    "如果你最近",
    "这是一个可以",
    "这是一个让",
    "这是一个再",
    "这是一个不",
    "这就是",
    "让你儿子",
    "怎么还有人",
    "拥有这两个",
    "这微软也太",
    "Windows 11",
    "37岁学AI",
    "清华大学做了",
    "这是行业首款",
    "清华开源了",
    "您现在看到的",
    "360环绕",
    "为什么小朋友",
    "如果你也",
    "免费dipstick",
]


def split_by_markers(text):
    """按话题转换标记拆分，返回 (标题, 内容) 列表"""
    lines = text.strip().split('\n')
    segments = []
    current_title = "未知视频"
    current_lines = []

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue

        # 检测是否为行号+内容格式（剪映导出特征）
        match = re.match(r'^\d+\t(.+)$', line_stripped)
        if match:
            content = match.group(1)
        else:
            content = line_stripped

        # 检测话题边界
        is_boundary = False
        for marker in BOUNDARY_MARKERS:
            if content.startswith(marker):
                is_boundary = True
                break

        if is_boundary and current_lines:
            full_text = '\n'.join(current_lines)
            if len(full_text) > 200:
                segments.append((current_title, full_text))
            current_title = content[:50].strip()
            current_lines = [content]
        else:
            current_lines.append(content)

    # 保存最后一个片段
    if current_lines:
        full_text = '\n'.join(current_lines)
        if len(full_text) > 200:
            segments.append((current_title, full_text))

    return segments


def sanitize_filename(name):
    """清理文件名"""
    name = re.sub(r'[\\/:*?"<>|]', '', name)
    name = re.sub(r'\s+', '_', name)
    return name[:60]


def save_segments(segments, output_dir, date_prefix="20260714"):
    """将拆分后的片段保存为独立 MD 文件"""
    os.makedirs(output_dir, exist_ok=True)
    saved = []

    for idx, (title, content) in enumerate(segments, 1):
        safe_title = sanitize_filename(title)
        filename = f"{date_prefix}_{idx:02d}_{safe_title}.md"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# {title}\n\n")
            f.write(f"<!-- 来源平台：抖音 -->\n")
            f.write(f"<!-- 原始文件：千字第一集合并文稿，片段 #{idx} -->\n\n")
            f.write(f"## 完整口播逐字稿\n\n")
            f.write(content)

        saved.append((filename, title))

    return saved


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Split Douyin merged transcripts')
    parser.add_argument('input', help='Input merged TXT file path')
    parser.add_argument('-o', '--output', default='./raw/douyin/', help='Output directory')
    parser.add_argument('--date', default='20260714', help='Date prefix')

    args = parser.parse_args()

    with open(args.input, 'r', encoding='utf-8') as f:
        text = f.read()

    print(f"[READ] File: {len(text)} chars, {len(text.split(chr(10)))} lines")

    segments = split_by_markers(text)
    print(f"[SPLIT] Found {len(segments)} independent video segments")

    saved = save_segments(segments, args.output, args.date)
    print(f"[SAVED] {len(saved)} files -> {args.output}")
    print()

    for filename, title in saved:
        print(f"  -> {filename}")
        print(f"     {title[:60]}...")

    print()
    print(f"[DONE] Next step: /ingest each file to distill into knowledge cards")


if __name__ == '__main__':
    main()
