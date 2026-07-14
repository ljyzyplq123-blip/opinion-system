"""
事件聚合/聚类模块
将同一事件的多条报道聚合为单一事件
支持历史事件和相似事件检索
"""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from .segmentation import segment_text


def cluster_reports(reports, eps=0.5, min_samples=1):
    """
    使用DBSCAN对报道进行聚类，聚合同一事件
    Args:
        reports: 报道列表，每项为{'id': ..., 'text': ...}
        eps: DBSCAN邻域半径（控制聚类粒度）
        min_samples: 最小样本数
    Returns:
        clusters: 聚类结果 [{cluster_id: int, reports: [...]}, ...]
    """
    if len(reports) < 2:
        return [{'cluster_id': 0, 'reports': reports}]

    # 预处理文本
    texts = []
    for r in reports:
        words = segment_text(r.get('text', '') or r.get('title', ''))
        texts.append(' '.join(words))

    # TF-IDF向量化
    vectorizer = TfidfVectorizer(max_features=500)
    try:
        tfidf_matrix = vectorizer.fit_transform(texts)
    except ValueError:
        return [{'cluster_id': 0, 'reports': reports}]

    # DBSCAN聚类
    clustering = DBSCAN(eps=eps, min_samples=min_samples, metric='cosine')
    labels = clustering.fit_predict(tfidf_matrix)

    # 整理结果
    clusters = {}
    for i, label in enumerate(labels):
        label = int(label)
        if label == -1:
            label = max(clusters.keys(), default=-1) + 1
        if label not in clusters:
            clusters[label] = []
        clusters[label].append(reports[i])

    result = []
    for cid, items in clusters.items():
        result.append({'cluster_id': cid, 'reports': items})

    return result


def find_similar_events(query_text, event_texts, threshold=0.6):
    """
    查找与查询文本相似的历史事件
    Args:
        query_text: 查询文本
        event_texts: 历史事件文本列表 [{id: ..., text: ...}, ...]
        threshold: 相似度阈值
    Returns:
        similar: 相似事件列表（按相似度降序）
    """
    if not event_texts:
        return []

    # 预处理
    query_words = segment_text(query_text)
    query_str = ' '.join(query_words)

    texts = []
    for e in event_texts:
        words = segment_text(e.get('text', '') or e.get('title', ''))
        texts.append(' '.join(words))

    all_texts = [query_str] + texts

    # TF-IDF向量化
    vectorizer = TfidfVectorizer(max_features=300)
    try:
        tfidf_matrix = vectorizer.fit_transform(all_texts)
    except ValueError:
        return []

    # 计算相似度
    similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])[0]

    # 筛选和排序
    result = []
    for i, sim in enumerate(similarities):
        if sim >= threshold:
            result.append({
                'event': event_texts[i],
                'similarity': round(float(sim), 4)
            })

    result.sort(key=lambda x: x['similarity'], reverse=True)
    return result


def compute_heat_index(reports, time_window_days=7, decay_factor=0.9):
    """
    计算事件热度指数
    Args:
        reports: 事件报道列表
        time_window_days: 时间窗口（天）
        decay_factor: 时间衰减因子
    Returns:
        heat_index: 热度指数
    """
    from datetime import datetime, timedelta

    if not reports:
        return 0.0

    now = datetime.utcnow()
    window_start = now - timedelta(days=time_window_days)

    total_heat = 0.0

    for r in reports:
        pub_time = r.get('publish_time')
        if isinstance(pub_time, str):
            try:
                pub_time = datetime.fromisoformat(pub_time)
            except Exception:
                pub_time = now

        # 时间衰减
        days_ago = (now - pub_time).days
        time_weight = decay_factor ** days_ago

        # 平台权重
        platform = r.get('platform', '')
        platform_weight = _get_platform_weight(platform)

        # 情感权重（极端情感更受关注）
        sentiment = abs(r.get('sentiment_score', 0))
        sentiment_weight = 1.0 + sentiment

        total_heat += time_weight * platform_weight * sentiment_weight

    return round(total_heat, 2)


def _get_platform_weight(platform):
    """获取平台权重"""
    weights = {
        '微博': 0.4, '抖音': 0.35, '快手': 0.3,
        '今日头条': 0.3, '百度热搜': 0.35,
        '知乎': 0.25, '豆瓣': 0.2, '小红书': 0.25,
        '人民日报': 0.5, '新华社': 0.5, '央视新闻': 0.5,
        '腾讯新闻': 0.3, '网易新闻': 0.25, '搜狐新闻': 0.2,
        '澎湃新闻': 0.3, '新京报': 0.3, '南方周末': 0.3,
    }
    return weights.get(platform, 0.15)
