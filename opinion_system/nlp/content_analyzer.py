"""
内容分析模块
- 正文提取：从HTML网页中提取正文内容（基于文本密度算法）
- 自动分词：jieba分词 + 词性标注 + 停用词过滤
- 特征表示：TF-IDF向量、文档统计特征、可读性评分
"""
import re
import math
import json
from collections import Counter
from bs4 import BeautifulSoup

from .segmentation import segment_text, extract_keywords_combined, extract_keywords


# HTML标签/脚本/样式清理正则
_RE_SCRIPT = re.compile(r'<script[^>]*>.*?</script>', re.DOTALL | re.IGNORECASE)
_RE_STYLE = re.compile(r'<style[^>]*>.*?</style>', re.DOTALL | re.IGNORECASE)
_RE_COMMENT = re.compile(r'<!--.*?-->', re.DOTALL)
_RE_TAG = re.compile(r'<[^>]+>')
_RE_SPACE = re.compile(r'\s+')
_RE_ENTITY = re.compile(r'&[a-z]+;|&#\d+;')


def extract_body_text(html, min_text_len=100):
    """
    从HTML中提取正文内容（基于文本密度算法）

    算法：
    1. 清理HTML（去除script/style/注释）
    2. 将所有块级元素分离，计算每个块的文本密度
    3. 选择文本密度最高的连续块作为正文
    4. 移除导航、页脚等锅炉内容

    Args:
        html: 原始HTML字符串
        min_text_len: 最短正文长度阈值

    Returns:
        dict: {
            'text': 提取的纯文本正文,
            'title': 页面标题,
            'quality': 正文质量评分 (0-1),
            'method': 'density' | 'bs4' | 'fallback'
        }
    """
    if not html or len(html) < 50:
        return {'text': '', 'title': '', 'quality': 0, 'method': 'fallback'}

    soup = BeautifulSoup(html, 'lxml')

    # 提取标题
    title = ''
    title_tag = soup.find('title')
    if title_tag:
        title = title_tag.get_text(strip=True)
    if not title:
        h1 = soup.find('h1')
        if h1:
            title = h1.get_text(strip=True)

    # 清理非内容标签
    for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'iframe', 'noscript']):
        tag.decompose()

    # 方法1：基于块密度选择
    body = soup.find('body')
    if body:
        blocks = _split_into_blocks(body)
        scored_blocks = _score_blocks(blocks, title)

        # 选择高密度连续块
        best_blocks = _select_best_blocks(scored_blocks, min_text_len)
        if best_blocks:
            text = '\n'.join(b['text'] for b in best_blocks)
            text = _clean_text(text)
            quality = _evaluate_quality(text, len(best_blocks))
            if len(text) >= min_text_len:
                return {'text': text, 'title': title, 'quality': quality, 'method': 'density'}

    # 方法2：BeautifulSoup get_text 回退
    if soup.body:
        text = soup.body.get_text(separator='\n', strip=True)
    else:
        text = soup.get_text(separator='\n', strip=True)
    text = _clean_text(text)

    if len(text) >= min_text_len:
        return {'text': text, 'title': title, 'quality': 0.5, 'method': 'bs4'}
    return {'text': text, 'title': title, 'quality': 0.2, 'method': 'fallback'}


def _split_into_blocks(body_elem):
    """将HTML body拆分为文本块"""
    blocks = []
    # 块级元素和包含大量文本的内联容器
    block_tags = {'div', 'p', 'article', 'section', 'main', 'li', 'td', 'th',
                  'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'pre', 'dd', 'dt'}
    inline_tags = {'span', 'a', 'strong', 'em', 'b', 'i', 'code', 'font', 'label'}

    for elem in body_elem.descendants:
        if elem.name in block_tags or (elem.name in inline_tags and elem.get_text(strip=True)):
            text = elem.get_text(separator=' ', strip=True)
            if not text or len(text) < 5:
                continue

            # 计算标签密度
            html_str = str(elem)
            tag_count = len(re.findall(r'<\w+[^>]*>', html_str))
            text_len = len(text)
            link_text_len = sum(len(a.get_text(strip=True)) for a in elem.find_all('a'))
            link_ratio = link_text_len / text_len if text_len > 0 else 1

            blocks.append({
                'text': text,
                'tag_count': tag_count,
                'text_len': text_len,
                'link_ratio': link_ratio,
                'tag_name': elem.name,
            })

    return blocks


def _score_blocks(blocks, title=''):
    """为每个文本块打分"""
    for block in blocks:
        text = block['text']
        text_len = block['text_len']
        tag_count = block['tag_count']
        link_ratio = block['link_ratio']
        tag_name = block['tag_name']

        # 基础分：文本越长越好
        score = min(text_len / 200, 3.0)

        # 文本密度：文本/标签数 越高越好
        if tag_count > 0:
            density = text_len / max(tag_count, 1)
            score += min(density / 50, 2.0)

        # 链接密度惩罚：链接太多 → 可能是导航或评论区
        if link_ratio > 0.5:
            score -= 3.0
        elif link_ratio > 0.3:
            score -= 1.0

        # 段落和标题加分
        if tag_name == 'p':
            score += 1.0
        elif tag_name in ('h1', 'h2', 'h3'):
            score += 0.5

        # 包含标题关键词加分
        if title:
            title_words = set(title[:20])
            text_words = set(text[:100])
            overlap = len(title_words & text_words)
            score += overlap * 0.3

        # 噪音模式扣分
        noise_patterns = [
            r'版权所有', r'Copyright', r'免责声明', r'举报', r'投诉',
            r'登录', r'注册', r'退出', r'导航', r'下一页', r'上一篇',
            r'评论', r'回复', r'点赞', r'分享', r'收藏',
            r'广告', r'推广', r'赞助',
        ]
        for pat in noise_patterns:
            if re.search(pat, text):
                score -= 0.5

        block['score'] = max(0, score)

    return blocks


def _select_best_blocks(scored_blocks, min_len=100):
    """选择得分最高的连续块组合"""
    if not scored_blocks:
        return []

    # 过滤低分块
    threshold = max(1.0, sum(b['score'] for b in scored_blocks) / max(len(scored_blocks), 1) * 0.5)
    candidates = [b for b in scored_blocks if b['score'] >= threshold]

    # 贪婪选择：按分数排序，累积到足够长度
    candidates.sort(key=lambda b: b['score'], reverse=True)
    selected = []
    total_len = 0
    for b in candidates:
        if total_len >= min_len * 3:  # 最多3倍最小长度
            break
        selected.append(b)
        total_len += b['text_len']

    # 按原始顺序排列
    original_order = {id(b): i for i, b in enumerate(scored_blocks)}
    selected.sort(key=lambda b: original_order.get(id(b), 0))

    return selected


def _clean_text(text):
    """清理提取的文本"""
    text = _RE_ENTITY.sub(' ', text)
    text = _RE_SPACE.sub(' ', text)
    text = text.strip()
    # 删除过短的行
    lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 3]
    return '\n'.join(lines)


def _evaluate_quality(text, block_count):
    """评估提取质量"""
    if not text:
        return 0
    score = 1.0
    # 文本长度适中
    if len(text) < 200:
        score *= 0.5
    elif len(text) > 5000:
        score *= 0.8
    # 块数适中
    if block_count < 2:
        score *= 0.7
    # 句子长度正常
    sentences = re.split(r'[。！？!?\n]', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if sentences:
        avg_sent_len = sum(len(s) for s in sentences) / len(sentences)
        if avg_sent_len < 10:
            score *= 0.6
        elif avg_sent_len > 80:
            score *= 0.7
    return round(min(score, 1.0), 2)


def analyze_document(html_or_text, is_html=False):
    """
    对文档执行完整的内容分析管道
    正文提取 → 分词 → 关键词提取 → 特征表示

    Args:
        html_or_text: HTML字符串或纯文本
        is_html: 是否为HTML

    Returns:
        dict: {
            'body_text': 正文,
            'title': 标题,
            'word_count': 词数,
            'char_count': 字符数,
            'sentence_count': 句数,
            'keywords': [{'keyword': ..., 'weight': ...}, ...],
            'word_freq': {词: 频次},
            'features': {
                'avg_sentence_len': 平均句长,
                'lexical_diversity': 词汇多样性,
                'readability': 可读性评分,
                'sentiment_leaning': 情感倾向,
                'information_density': 信息密度,
            },
            'extraction_quality': 提取质量,
        }
    """
    # Step 1: 正文提取
    if is_html:
        extracted = extract_body_text(html_or_text)
        body_text = extracted['text']
        title = extracted['title']
        extraction_quality = extracted['quality']
    else:
        body_text = html_or_text
        title = ''
        extraction_quality = 1.0

    if not body_text:
        return _empty_analysis()

    # Step 2: 分词
    words = segment_text(body_text, use_pos_filter=True)
    word_count = len(words)

    if word_count < 5:
        return _empty_analysis()

    # Step 3: 关键词提取
    try:
        keywords = extract_keywords_combined([body_text], topk=15)
    except Exception:
        keywords = extract_keywords(body_text, topk=15)

    # Step 4: 词频统计
    word_freq = Counter(words)
    top_words = word_freq.most_common(30)

    # Step 5: 计算文档特征
    char_count = len(body_text.replace(' ', '').replace('\n', ''))

    # 句子
    sentences = re.split(r'[。！？!?\n]+', body_text)
    sentences = [s.strip() for s in sentences if len(s.strip()) >= 5]
    sentence_count = len(sentences)

    # 平均句长
    avg_sentence_len = char_count / max(sentence_count, 1)

    # 词汇多样性 (TTR: Type-Token Ratio)
    unique_words = len(set(words))
    lexical_diversity = round(unique_words / max(word_count, 1), 3)

    # 可读性评分（中文简化版：基于句长+词长）
    avg_word_len = sum(len(w) for w in words) / max(word_count, 1)
    readability = round(max(0, min(1, 1.0 - (avg_sentence_len - 20) / 100)), 2)

    # 信息密度（实词占比）
    content_word_count = sum(1 for w in words if len(w) >= 2)
    information_density = round(content_word_count / max(word_count, 1), 3)

    # 情感倾向（基于简单情感词典）
    sentiment_leaning = _quick_sentiment(body_text)

    return {
        'body_text': body_text[:2000],
        'title': title,
        'word_count': word_count,
        'char_count': char_count,
        'sentence_count': sentence_count,
        'keywords': keywords,
        'word_freq': [{'word': w, 'count': c} for w, c in top_words],
        'features': {
            'avg_sentence_len': round(avg_sentence_len, 1),
            'lexical_diversity': lexical_diversity,
            'readability': readability,
            'sentiment_leaning': sentiment_leaning,
            'information_density': information_density,
        },
        'extraction_quality': extraction_quality,
    }


def _quick_sentiment(text):
    """快速情感倾向判断（简化版）"""
    positive_words = {'好', '优秀', '出色', '成功', '突破', '创新', '领先', '进步',
                      '满意', '利好', '增长', '提升', '改善', '优化', '获奖', '冠军'}
    negative_words = {'差', '失败', '问题', '危机', '事故', '丑闻', '投诉', '举报',
                      '下跌', '亏损', '裁员', '倒闭', '处罚', '违法', '争议', '造假'}

    pos_count = sum(1 for w in positive_words if w in text)
    neg_count = sum(1 for w in negative_words if w in text)

    if pos_count > neg_count + 1:
        return 'positive'
    elif neg_count > pos_count + 1:
        return 'negative'
    return 'neutral'


def extract_features_from_documents(documents):
    """
    从多文档集合中提取聚合特征
    用于事件级别的特征表示（如用于相似事件匹配、聚类等）

    Args:
        documents: 文档文本列表

    Returns:
        dict: 聚合特征向量
    """
    if not documents:
        return {}

    all_words = []
    all_keywords = Counter()

    for doc in documents:
        words = segment_text(doc, use_pos_filter=True)
        all_words.extend(words)
        try:
            kws = extract_keywords(doc, topk=10)
        except Exception:
            kws = []
        for kw in kws:
            all_keywords[kw['keyword']] += kw['weight']

    total_words = len(all_words)
    unique_words = len(set(all_words))

    return {
        'total_words': total_words,
        'unique_words': unique_words,
        'lexical_diversity': round(unique_words / max(total_words, 1), 3),
        'top_keywords': [{'keyword': w, 'weight': round(c, 1)}
                         for w, c in all_keywords.most_common(20)],
        'doc_count': len(documents),
        'avg_doc_length': total_words / len(documents) if documents else 0,
    }


def _empty_analysis():
    return {
        'body_text': '',
        'title': '',
        'word_count': 0,
        'char_count': 0,
        'sentence_count': 0,
        'keywords': [],
        'word_freq': [],
        'features': {
            'avg_sentence_len': 0,
            'lexical_diversity': 0,
            'readability': 0,
            'sentiment_leaning': 'neutral',
            'information_density': 0,
        },
        'extraction_quality': 0,
    }
