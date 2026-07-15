"""
服务端词云生成模块 v2
参照 weibo_wordcloud 思路，使用手选配色方案 + 自定义颜色函数
"""
import io
import base64
import os
import random
import numpy as np
from PIL import Image, ImageDraw
from wordcloud import WordCloud


# 中文字体路径
_FONT_PATH = None
_CANDIDATE_FONTS = [
    'C:/Windows/Fonts/msyhbd.ttc',   # 微软雅黑 Bold 优先 — 词云需要粗体
    'C:/Windows/Fonts/msyh.ttc',
    'C:/Windows/Fonts/simhei.ttf',
    'C:/Windows/Fonts/simsun.ttc',
    '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
    '/System/Library/Fonts/PingFang.ttc',
]


# ============================================================
# 精心挑选的配色方案 — 4组不同风格的调色板
# ============================================================
PALETTES = {
    # 活力暖色 — 红/橙/粉/金
    'warm': [
        '#E74C3C', '#E67E22', '#F39C12', '#D35400', '#C0392B',
        '#FF6B6B', '#FF8E53', '#FFD93D', '#FF6B6B', '#FFA502',
        '#EE5A24', '#F8B500', '#EA2027', '#FFC312', '#e0565b',
    ],
    # 清新冷色 — 蓝/青/紫
    'cool': [
        '#2980B9', '#3498DB', '#1ABC9C', '#16A085', '#27AE60',
        '#2ECC71', '#00B894', '#00CEC9', '#0984E3', '#6C5CE7',
        '#A29BFE', '#74B9FF', '#55EFC4', '#00B4D8', '#0077B6',
    ],
    # 现代混合 — 冷暖搭配，高饱和度
    'vivid': [
        '#E74C3C', '#3498DB', '#2ECC71', '#F39C12', '#9B59B6',
        '#1ABC9C', '#E67E22', '#2980B9', '#27AE60', '#E91E63',
        '#00BCD4', '#FF5722', '#8BC34A', '#FF9800', '#673AB7',
        '#009688', '#FF6F00', '#4CAF50', '#03A9F4', '#F44336',
    ],
    # 暗夜霓虹 — 深底亮色
    'neon': [
        '#FF6B6B', '#4ECDC4', '#FFE66D', '#A8E6CF', '#FF8B94',
        '#B8F2E6', '#F7DC6F', '#85C1E9', '#F0B27A', '#82E0AA',
        '#F1948A', '#73C6B6', '#F9E79F', '#AED6F1', '#FAD7A0',
    ],
}


def _get_font_path():
    global _FONT_PATH
    if _FONT_PATH:
        return _FONT_PATH
    for fp in _CANDIDATE_FONTS:
        if os.path.exists(fp):
            _FONT_PATH = fp
            return _FONT_PATH
    font_dir = 'C:/Windows/Fonts'
    if os.path.exists(font_dir):
        for f in os.listdir(font_dir):
            if f.endswith(('.ttc', '.ttf')):
                _FONT_PATH = os.path.join(font_dir, f)
                return _FONT_PATH
    return None


def _make_cloud_mask(size=800):
    """生成云朵形状的遮罩 — 多个圆叠加形成蓬松云朵轮廓"""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = size // 2, size // 2
    r = size // 2 - 20

    # 中心大圆
    draw.ellipse([cx - r, cy - r + 20, cx + r, cy + r + 20], fill=(255, 255, 255, 255))
    # 四周凸起的小圆（云朵蓬松感）
    bumps = [
        (cx - r//2, cy - r//2, r * 0.55),
        (cx + r//3, cy - r//2, r * 0.50),
        (cx - r//3, cy + r//3, r * 0.48),
        (cx + r//2, cy + r//4, r * 0.45),
        (cx, cy - r//2 + 20, r * 0.52),
        (cx - r//2 + 10, cy + r//4 - 10, r * 0.42),
        (cx + r//2 - 20, cy - r//4, r * 0.40),
    ]
    for bx, by, br in bumps:
        draw.ellipse([int(bx - br), int(by - br), int(bx + br), int(by + br)],
                     fill=(255, 255, 255, 255))
    return np.array(img)


def _make_heart_mask(size=800):
    """生成爱心形状的遮罩"""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 爱心参数方程
    scale = size / 22
    cx, cy = size // 2, size // 2 + scale * 2
    points = []
    for t in range(0, 628, 2):  # 0 to 2π in 0.02 rad steps
        rad = t / 100
        x = 16 * np.sin(rad) ** 3
        y = 13 * np.cos(rad) - 5 * np.cos(2 * rad) - 2 * np.cos(3 * rad) - np.cos(4 * rad)
        px = int(cx + x * scale * 0.7)
        py = int(cy - y * scale * 0.7)
        points.append((px, py))

    if len(points) >= 3:
        draw.polygon(points, fill=(255, 255, 255, 255))
    return np.array(img)


def _make_rounded_rect_mask(size=800):
    """圆角矩形"""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    margin = 15
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=100, fill=(255, 255, 255, 255)
    )
    return np.array(img)


MASK_SHAPES = {
    'cloud': _make_cloud_mask,
    'heart': _make_heart_mask,
    'rounded': _make_rounded_rect_mask,
}


def _color_func_factory(palette_name, word_freq):
    """
    创建颜色函数：高频词用醒目色，低频词用柔和色
    """
    palette = PALETTES.get(palette_name, PALETTES['vivid'])
    max_freq = max(word_freq.values()) if word_freq else 1
    freq_list = sorted(set(word_freq.values()), reverse=True)

    # 建立频率 → 颜色的映射
    freq_color_map = {}
    for i, freq in enumerate(freq_list):
        # 高优先级词用鲜艳色，低优先级用柔和色
        if i < len(palette):
            freq_color_map[freq] = palette[i]
        else:
            # 循环但降低饱和度
            base = palette[i % len(palette)]
            freq_color_map[freq] = _desaturate(base, 0.3)

    def color_func(word, font_size, position, orientation, font_path, **kwargs):
        freq = word_freq.get(word, 1)
        return freq_color_map.get(freq, palette[0])

    return color_func


def _desaturate(hex_color, amount):
    """降低颜色饱和度"""
    r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
    gray = int(0.299 * r + 0.587 * g + 0.114 * b)
    r = int(r + (gray - r) * amount)
    g = int(g + (gray - g) * amount)
    b = int(b + (gray - b) * amount)
    return f'#{r:02x}{g:02x}{b:02x}'


def generate_wordcloud(keywords, mask_shape='cloud', width=800, height=800,
                       bg_color=None, max_words=60, palette='vivid'):
    """
    生成词云图片，返回 base64 PNG

    Args:
        keywords: [{'keyword': '芯片', 'weight': 85.2}, ...]
        mask_shape: 'cloud' | 'heart' | 'rounded'
        width/height: 输出尺寸
        bg_color: 背景色 (None=透明, '#ffffff'=白色)
        max_words: 最大词数
        palette: 'warm' | 'cool' | 'vivid' | 'neon'

    Returns:
        base64 编码的 PNG 字符串
    """
    font_path = _get_font_path()
    if not font_path:
        raise RuntimeError('未找到中文字体文件')

    # 构建词频字典 — 拉开权重差距，让高频词更突出
    if not keywords:
        raise ValueError('无有效关键词')

    weights = [kw['weight'] for kw in keywords if kw['keyword'].strip()]
    if not weights:
        raise ValueError('无有效关键词')

    max_w = max(weights)
    min_w = min(weights)
    word_freq = {}
    for kw in keywords:
        w = kw['keyword'].strip()
        if not w or len(w) < 2:
            continue
        # 权重映射到 1~100 范围，指数放大差异
        if max_w > min_w:
            normalized = (kw['weight'] - min_w) / (max_w - min_w)
        else:
            normalized = 0.5
        # 非线性映射：高权重词获得不成比例的高频
        freq = int(1 + normalized ** 1.5 * 100)
        if freq > 0:
            word_freq[w] = freq

    # 创建遮罩
    mask_func = MASK_SHAPES.get(mask_shape, _make_cloud_mask)
    mask = mask_func(min(width, height))

    # 背景色
    if bg_color is None:
        bg_color = '#ffffff'

    # 颜色函数
    color_func = _color_func_factory(palette, word_freq)

    wc = WordCloud(
        font_path=font_path,
        mask=mask,
        width=width,
        height=height,
        background_color=bg_color,
        max_words=max_words,
        max_font_size=160,
        min_font_size=10,
        prefer_horizontal=0.85,
        relative_scaling=0.35,       # 更小值 = 高频词与低频词的字号差距更大
        margin=6,
        scale=2,
        collocations=False,
        repeat=False,
        color_func=color_func,
        mode='RGBA',
        random_state=42,
    )
    wc.generate_from_frequencies(word_freq)

    img = wc.to_image()
    buf = io.BytesIO()
    img.save(buf, format='PNG', optimize=True)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode('utf-8')
    return f'data:image/png;base64,{b64}'
