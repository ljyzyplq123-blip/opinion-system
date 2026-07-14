"""
中文分词与TF-IDF特征提取
"""
import jieba
import re
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer


# 停用词表（常见中文停用词）
DEFAULT_STOPWORDS = set([
    '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
    '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
    '自己', '这', '他', '她', '它', '们', '那', '些', '所', '为', '所以', '因为',
    '但是', '然而', '虽然', '如果', '可以', '还是', '这个', '那个', '什么', '怎么',
    '如何', '为什么', '这样', '那样', '已经', '还', '又', '再', '才', '刚', '就',
    '能', '能够', '该', '应该', '必须', '需要', '随着', '通过', '等等', '等', '对',
    '从', '以', '之', '至', '与', '及', '或', '但', '而', '且', '因', '只', '把',
    '被', '让', '给', '向', '由', '于', '按', '照', '如', '比', '啊', '吧', '呢',
    '吗', '嗯', '呀', '哦', '哈', '嘛', '哇', '呵', '啦', '噢', '哪', '么', '其',
    '其中', '各', '每', '某', '另', '别', '各', '该', '本', '此', '前', '后', '中',
    '内', '外', '间', '旁', '边', '里', '下', '左', '右', '东', '西', '南', '北',
    '目前', '近日', '据悉', '据', '报道', '记者', '新闻', '来源', '原标题', '图',
    '第', '年月日', '时分秒', '日', '月', '年', '时', '分', '秒', '来', '用',
    '做', '作', '使', '进行', '发生', '出现', '成为', '表示', '称', '说', '认为',
    '指出', '强调', '透露', '获悉', '了解', '继续', '开始', '结束', '已经', '将',
    '正在', '会', '可能', '已', '未', '无', '非', '很', '非常', '比较', '更',
    '最', '极', '极其', '稍微', '有点', '更', '更加', '越', '越来越', '较', '较',
    '相当', '略微', '几乎', '差不多', '太', '实在', '真是', '多', '少', '许多',
    '很多', '一些', '有些', '一点', '一点', '各种', '其他', '所有', '全部', '部分',
    '大', '小', '高', '低', '长', '短', '快', '慢', '新', '旧', '好', '坏',
    'http', 'https', 'www', 'com', 'cn', 'html', 'htm', 'php', 'net', 'org',
])


def init_jieba():
    """初始化jieba分词器"""
    # 添加自定义词典
    custom_words = [
        '舆情', '热搜', '爆款', '刷屏', '出圈', '塌房', '反转',
        '大V', '官宣', '社死', '凡尔赛', '内卷', '躺平', '摆烂',
        '自媒体', '公众号', '短视频', '流量', '粉丝', '博主',
        '水军', '营销号', '官媒', '通报', '声明', '辟谣', '证实',
        '热搜榜', '头条', '话题', '超话', '热搜第一',
    ]
    for w in custom_words:
        jieba.add_word(w, freq=100)

    return jieba


def segment_text(text, stopwords=None):
    """
    对文本进行分词，去除停用词和标点
    """
    if stopwords is None:
        stopwords = DEFAULT_STOPWORDS

    # 清洗文本
    text = re.sub(r'[^一-鿿\w]', ' ', text)
    # 分词
    words = jieba.cut(text, cut_all=False)
    # 过滤
    result = []
    for w in words:
        w = w.strip()
        if len(w) >= 2 and w not in stopwords and not w.isdigit():
            result.append(w)

    return result


def extract_keywords(text, topk=20, stopwords=None):
    """
    提取文本关键词（基于TF-IDF）
    """
    words = segment_text(text, stopwords)
    if not words:
        return []

    # 词频统计
    word_freq = Counter(words)

    # 按频率排序
    total = sum(word_freq.values())
    keywords = []
    for word, freq in word_freq.most_common(topk):
        keywords.append({
            'keyword': word,
            'weight': freq / total if total > 0 else 0,
            'count': freq
        })

    return keywords


def extract_keywords_tfidf(documents, topk=20):
    """
    使用TF-IDF从文档集合中提取关键词
    """
    if not documents:
        return []

    # 预处理：分词并用空格连接
    processed_docs = []
    for doc in documents:
        words = segment_text(doc)
        processed_docs.append(' '.join(words))

    # TF-IDF计算
    vectorizer = TfidfVectorizer(max_features=500, token_pattern=r'(?u)\b\w+\b')
    tfidf_matrix = vectorizer.fit_transform(processed_docs)

    # 获取特征名和权重
    feature_names = vectorizer.get_feature_names_out()

    # 计算每个词在所有文档中的平均权重
    avg_weights = {}
    for i, word in enumerate(feature_names):
        weights = tfidf_matrix[:, i].toarray().flatten()
        avg_weights[word] = float(weights.mean())

    # 排序
    sorted_words = sorted(avg_weights.items(), key=lambda x: x[1], reverse=True)
    result = [{'keyword': w, 'weight': round(s, 4)} for w, s in sorted_words[:topk]]

    return result


def compute_text_similarity(text1, text2):
    """
    计算两段文本的余弦相似度（基于TF-IDF向量）
    """
    from sklearn.metrics.pairwise import cosine_similarity

    words1 = segment_text(text1)
    words2 = segment_text(text2)

    if not words1 or not words2:
        return 0.0

    doc1 = ' '.join(words1)
    doc2 = ' '.join(words2)

    vectorizer = TfidfVectorizer()
    try:
        tfidf = vectorizer.fit_transform([doc1, doc2])
        similarity = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
        return round(float(similarity), 4)
    except Exception:
        return 0.0
