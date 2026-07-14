"""
数据清洗及预处理模块
去重、去噪、格式标准化
"""
import re
import hashlib
from datetime import datetime
from html import unescape


def clean_html(html_text):
    """
    清洗HTML标签，提取纯文本
    """
    if not html_text:
        return ''

    # 去除script和style标签
    text = re.sub(r'<script[^>]*>.*?</script>', '', html_text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)

    # 去除HTML标签
    text = re.sub(r'<[^>]+>', '', text)

    # HTML实体解码
    text = unescape(text)

    # 去除多余空白
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def remove_noise(text):
    """
    去除噪声内容
    """
    if not text:
        return ''

    # 去除URL
    text = re.sub(r'https?://\S+', '', text)

    # 去除email
    text = re.sub(r'\S+@\S+', '', text)

    # 去除特殊字符但保留中文标点
    text = re.sub(r'[^一-鿿＀-￯\w\s，。！？；：""''（）【】《》、…—\n]',
                  '', text)

    # 去除纯数字行
    text = re.sub(r'^\d+\s*$', '', text, flags=re.MULTILINE)

    # 去除多余换行
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


def normalize_text(text):
    """
    文本格式标准化
    """
    if not text:
        return ''

    # 全角转半角
    result = []
    for ch in text:
        code = ord(ch)
        if code == 0x3000:
            result.append(' ')
        elif 0xFF01 <= code <= 0xFF5E:
            result.append(chr(code - 0xFEE0))
        elif code == 0x2013 or code == 0x2014:
            result.append('-')
        elif code in [0x2018, 0x2019, 0x201C, 0x201D]:
            result.append("'")
        else:
            result.append(ch)

    text = ''.join(result)

    # 统一换行符
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # 去除首尾空白
    text = text.strip()

    return text


def compute_text_hash(text):
    """
    计算文本的MD5哈希（用于去重）
    """
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def deduplicate_reports(reports, similarity_threshold=0.85):
    """
    报道去重
    1. 精确去重：相同hash
    2. 近似去重：高相似度
    """
    if not reports:
        return []

    seen_hashes = set()
    unique_reports = []
    from .segmentation import compute_text_similarity

    for report in reports:
        text = report.get('content', '') or report.get('title', '')
        text_hash = compute_text_hash(text)

        # 精确去重
        if text_hash in seen_hashes:
            continue

        # 近似去重
        is_duplicate = False
        for existing in unique_reports[-10:]:  # 只检查最近10条
            existing_text = existing.get('content', '') or existing.get('title', '')
            if len(text) > 50 and len(existing_text) > 50:
                try:
                    sim = compute_text_similarity(text, existing_text)
                    if sim >= similarity_threshold:
                        is_duplicate = True
                        break
                except Exception:
                    pass

        if not is_duplicate:
            seen_hashes.add(text_hash)
            unique_reports.append(report)

    return unique_reports


def extract_main_content(html_or_text):
    """
    从网页文本中提取正文内容
    基于文本密度算法
    """
    text = clean_html(html_or_text)
    text = remove_noise(text)

    # 分段落
    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]

    # 过滤太短或太长的段落
    valid_paragraphs = [p for p in paragraphs if 20 < len(p) < 5000]

    if not valid_paragraphs:
        return text[:2000] if len(text) > 2000 else text

    return '\n\n'.join(valid_paragraphs)


def format_date(date_str):
    """
    标准化日期格式
    """
    if not date_str:
        return datetime.utcnow().isoformat()

    formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d %H:%M',
        '%Y-%m-%d',
        '%Y年%m月%d日 %H:%M:%S',
        '%Y年%m月%d日 %H:%M',
        '%Y年%m月%d日',
        '%m月%d日 %H:%M',
        '%m月%d日',
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.isoformat()
        except ValueError:
            continue

    return datetime.utcnow().isoformat()
