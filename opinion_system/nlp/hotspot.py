"""
热点事件发现模块
- 使用ML方法对舆情主题进行分类
- 根据时间和报道数量发现热点事件
"""
from datetime import datetime, timedelta
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import numpy as np


def discover_hotspots(reports, n_clusters=5, time_window_days=7, min_reports=3):
    """
    从报道中发现热点事件
    Args:
        reports: 报道列表
        n_clusters: 聚类数量
        time_window_days: 时间窗口
        min_reports: 最少报道数阈值
    Returns:
        hotspots: 热点事件列表
    """
    if len(reports) < min_reports:
        return []

    # 过滤时间窗口内的报道
    now = datetime.utcnow()
    window_start = now - timedelta(days=time_window_days)

    recent_reports = []
    for r in reports:
        pub_time = r.get('publish_time', now)
        if isinstance(pub_time, str):
            try:
                pub_time = datetime.fromisoformat(pub_time)
            except Exception:
                pub_time = now
        if pub_time >= window_start:
            recent_reports.append(r)

    if len(recent_reports) < min_reports:
        return []

    # 提取文本特征
    from .segmentation import segment_text
    texts = [' '.join(segment_text(r.get('text', '') or r['title']))
             for r in recent_reports if r.get('text') or r.get('title')]

    if len(texts) < min_reports:
        return []

    # TF-IDF向量化
    vectorizer = TfidfVectorizer(max_features=200)
    try:
        X_tfidf = vectorizer.fit_transform(texts)
    except ValueError:
        return []

    # K-Means聚类
    actual_clusters = min(n_clusters, len(texts))
    if actual_clusters < 2:
        return [{'cluster': 0, 'reports': recent_reports}]

    kmeans = KMeans(n_clusters=actual_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_tfidf)

    # 按聚类分组
    clusters = {}
    for i, label in enumerate(labels):
        label = int(label)
        if label not in clusters:
            clusters[label] = []
        clusters[label].append(recent_reports[i])

    # 筛选热点（报道数 >= min_reports）
    hotspots = []
    for cid, items in clusters.items():
        if len(items) >= min_reports:
            # 提取聚类的关键词
            indices = [i for i, l in enumerate(labels) if l == cid]
            if indices:
                cluster_center = X_tfidf[indices].mean(axis=0)
                if hasattr(cluster_center, 'A1'):
                    cluster_center = cluster_center.A1
                else:
                    cluster_center = np.array(cluster_center).flatten()
                top_indices = np.argsort(cluster_center)[-10:]
                keywords = [vectorizer.get_feature_names_out()[i] for i in top_indices if i < len(vectorizer.get_feature_names_out())]
            else:
                keywords = []

            hotspots.append({
                'cluster_id': cid,
                'report_count': len(items),
                'reports': items,
                'keywords': keywords
            })

    # 按报道数降序
    hotspots.sort(key=lambda x: x['report_count'], reverse=True)
    return hotspots


def classify_event_category(text):
    """
    对事件文本进行分类（社会/科技/财经/健康/教育等）
    基于关键词规则 + TF-IDF特征
    """
    text_lower = text.lower()

    # 分类规则
    categories = {
        '科技': ['ai', '人工智能', '芯片', '5g', '科技', '互联网', '手机', '数据',
                '算法', '软件', '硬件', '机器人', '自动驾驶', '航天', '卫星',
                '科技公司', '程序员', '黑客', '网络安全', '云计算', '大数据'],
        '财经': ['股市', '经济', '房市', '房价', '基金', '银行', '金融', '投资',
                '降息', '加息', '通胀', '贸易', '关税', '销售额', '利润', '亏损'],
        '健康': ['疫情', '疫苗', '医院', '疾病', '病毒', '药品', '医生', '患者',
                '食品安全', '添加剂', '转基因', 'pm2.5', '污染', '中医', '西医'],
        '教育': ['学校', '学生', '教师', '高考', '考试', '教育', '大学', '中学',
                '小学', '幼儿园', '考研', '留学', '课程', '教材', '学区房'],
        '娱乐': ['明星', '电影', '综艺', '音乐', '演唱会', '电视剧', '导演',
                '演员', '歌手', '网红', '直播', '粉丝', '票房', '收视率'],
        '社会': ['事件', '事故', '通报', '警方', '法院', '政府', '官员', '投诉',
                '维权', '抗议', '暴力', '慈善', '志愿者', '社区', '公交车', '地铁'],
        '体育': ['比赛', '奥运', '世界杯', '冠军', '运动员', '球队', '教练',
                '联赛', '决赛', '金牌', '足球', '篮球', '乒乓球', '电竞'],
    }

    scores = {}
    for cat, keywords in categories.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        scores[cat] = score

    if max(scores.values()) == 0:
        return '社会'

    return max(scores, key=scores.get)


def predict_risk_level(event, reports):
    """
    预测事件风险等级
    Args:
        event: 事件信息
        reports: 相关报道
    Returns:
        risk_level: 低/中/高
    """
    risk_score = 0

    # 报道数量因素
    report_count = len(reports)
    if report_count > 100:
        risk_score += 30
    elif report_count > 50:
        risk_score += 20
    elif report_count > 20:
        risk_score += 10

    # 负面情感因素
    neg_ratio = event.get('negative_ratio', 0)
    if neg_ratio > 0.5:
        risk_score += 30
    elif neg_ratio > 0.3:
        risk_score += 20
    elif neg_ratio > 0.2:
        risk_score += 10

    # 增长速度因素
    from .lifecycle import predict_lifecycle_stage
    lifecycle = predict_lifecycle_stage(event, reports)
    if lifecycle == '成长期':
        risk_score += 20
    elif lifecycle == '高潮期':
        risk_score += 15
    elif lifecycle == '潜伏期':
        risk_score += 10

    # 分类因素
    if event.get('category') in ['社会', '健康', '财经']:
        risk_score += 10

    # 确定风险等级
    if risk_score >= 50:
        return '高'
    elif risk_score >= 30:
        return '中'
    else:
        return '低'
