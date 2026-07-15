"""
中文分词与TF-IDF特征提取
"""
import jieba
import jieba.analyse
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
    # 新增：热搜/新闻场景常见噪音词
    '网友', '大家', '纷纷', '热议', '关注', '讨论', '话题', '事件', '相关',
    '方面', '情况', '问题', '方式', '时间', '地点', '原因', '结果', '影响',
    '平台', '内容', '信息', '数据', '用户', '发布', '评论', '视频', '文章',
    '真的', '太', '感觉', '觉得', '不是', '就是', '还是', '现在', '今天',
    '昨天', '明天', '一下', '起来', '出来', '过来', '回来', '进去', '上去',
    '下来', '之后', '之前', '以后', '结果', '然后', '虽然', '不过', '因为',
    '所以', '终于', '彻底', '简直', '完全', '直接', '根本', '确实', '居然',
    '竟然', '居然', '不过', '当然', '果然', '自然', '忽然', '突然',
    '为此', '对此', '此外', '另外', '同时', '随后', '紧接着', '实际上',
    '终于', '彻底', '日前', '不敌',
    '引发', '引起', '导致', '造成', '产生', '带来', '受到', '遭到',
    '引发热议', '引发关注', '广泛关注', '持续关注', '冲上热搜',
    '显示', '显示为', '分别为', '其中', '其它', '以及', '及其',
    '超过', '达到', '高达', '低至', '不到', '接近', '约为',
    '增长', '下降', '上升', '下跌', '大幅', '明显', '显著',
    '网友热议', '网友讨论', '网友关注', '网友评论', '网友表示',
    '热搜第一', '热搜榜', '登上热搜', '上热搜',
    '反映', '认为该',
])


# 中文词性标记 — 保留有实际含义的词性
_KEEP_POS = {'n', 'nr', 'ns', 'nt', 'nz', 'v', 'vn', 'a', 'an', 'i', 'j', 'l'}


def init_jieba():
    """初始化jieba分词器"""
    # 添加自定义词典
    custom_words = [
        '舆情', '热搜', '爆款', '刷屏', '出圈', '塌房', '反转',
        '大V', '官宣', '社死', '凡尔赛', '内卷', '躺平', '摆烂',
        '自媒体', '公众号', '短视频', '流量', '粉丝', '博主',
        '水军', '营销号', '官媒', '通报', '声明', '辟谣', '证实',
        '热搜榜', '头条', '话题', '超话', '热搜第一',
        # 新闻/科技常见复合词
        '人工智能', '大模型', '芯片', '半导体', '新能源',
        '自动驾驶', '元宇宙', '区块链', '量子计算',
        '首发', '旗舰', '发布', '上市', '量产', '预售',
        '销售额', '营收', '净利润', '市值', '融资',
        '政策', '监管', '罚款', '处罚', '整改', '召回',
        '突破', '创新', '研发', '专利', '核心技术',
        '危机', '争议', '丑闻', '曝光', '举报', '起诉',
        '合作', '签约', '收购', '合并', '拆分', '剥离',
        '涨价', '降价', '促销', '补贴', '优惠',
        '事故', '灾难', '地震', '台风', '洪水', '火灾',
        '疫情', '疫苗', '确诊', '防控', '解封',
        '冠军', '夺冠', '金牌', '世界杯', '奥运会', '联赛',
    ]
    for w in custom_words:
        jieba.add_word(w, freq=100)

    return jieba


def segment_text(text, stopwords=None, use_pos_filter=True):
    """
    对文本进行分词，去除停用词和标点
    """
    if stopwords is None:
        stopwords = DEFAULT_STOPWORDS

    # 清洗文本：保留中文、英文、数字
    text = re.sub(r'[^一-鿿\w]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()

    if not text:
        return []

    # 分词（使用 POS tagging 过滤无意义词）
    if use_pos_filter:
        pairs = jieba.posseg.cut(text)
        result = []
        for word, flag in pairs:
            word = word.strip()
            if len(word) < 2:
                continue
            if word in stopwords:
                continue
            if word.isdigit():
                continue
            if re.match(r'^[\d\.\+\-\*\/\%]+$', word):
                continue
            # 只保留有实际语义的词性
            if flag in _KEEP_POS or len(word) >= 3:
                result.append(word)
        return result
    else:
        words = jieba.cut(text, cut_all=False)
        result = []
        for w in words:
            w = w.strip()
            if len(w) >= 2 and w not in stopwords and not w.isdigit():
                if not re.match(r'^[\d\.\+\-\*\/\%]+$', w):
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
        words = segment_text(doc, use_pos_filter=True)
        if words:
            processed_docs.append(' '.join(words))

    if not processed_docs:
        return []

    # TF-IDF计算 — 使用 \S+ 匹配非空白字符（兼容中文分词结果）
    try:
        vectorizer = TfidfVectorizer(
            max_features=300,
            token_pattern=r'(?u)\S+',
            min_df=1,
            max_df=0.9,
        )
        tfidf_matrix = vectorizer.fit_transform(processed_docs)
        feature_names = vectorizer.get_feature_names_out()
    except ValueError:
        # 文档太少时回退到简单词频
        return _simple_keywords(processed_docs, topk)

    # 计算每个词的平均TF-IDF权重（跨文档）
    avg_weights = {}
    for i, word in enumerate(feature_names):
        weights = tfidf_matrix[:, i].toarray().flatten()
        avg = float(weights.mean())
        if avg > 0.001:  # 过滤极低权重的噪音词
            avg_weights[word] = avg

    # 排序
    sorted_words = sorted(avg_weights.items(), key=lambda x: x[1], reverse=True)
    # 归一化到 0-100
    if sorted_words:
        max_w = sorted_words[0][1]
        result = [{
            'keyword': w,
            'weight': round(s / max_w * 100, 1) if max_w > 0 else 0
        } for w, s in sorted_words[:topk]]
    else:
        result = []

    return result


def extract_keywords_textrank(text, topk=20):
    """
    使用 jieba TextRank 从单文本中提取关键词
    适合短文本的关键词抽取，结果比纯TF-IDF更聚焦
    """
    if not text:
        return []

    # 清洗
    text = re.sub(r'[^一-鿿\w]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    if not text:
        return []

    try:
        # jieba.analyse.textrank 直接返回 (keyword, weight) 列表
        kw_pairs = jieba.analyse.textrank(
            text, topK=topk, withWeight=True,
            allowPOS=('n', 'nr', 'ns', 'nt', 'nz', 'v', 'vn', 'a', 'an', 'i', 'j')
        )
    except Exception:
        kw_pairs = []

    if not kw_pairs:
        return []

    max_w = kw_pairs[0][1] if kw_pairs else 1
    result = [{
        'keyword': w,
        'weight': round(s / max_w * 100, 1) if max_w > 0 else 0
    } for w, s in kw_pairs]

    return result


def extract_keywords_combined(documents, topk=20):
    """
    综合 TF-IDF + TextRank 提取关键词
    - 先用 TF-IDF 从全文档集提取候选词
    - 再用 TextRank 从拼接文本中提取关键词
    - 合并排序（TF-IDF 权重 * 0.4 + TextRank 权重 * 0.6）
    """
    if not documents:
        return []

    # TF-IDF 提取
    tfidf_kw = extract_keywords_tfidf(documents, topk=topk * 2)
    tfidf_map = {kw['keyword']: kw['weight'] for kw in tfidf_kw}

    # TextRank 提取（基于拼接后的全文）
    combined_text = '。'.join(documents)
    textrank_kw = extract_keywords_textrank(combined_text, topk=topk * 2)
    textrank_map = {kw['keyword']: kw['weight'] for kw in textrank_kw}

    # 合并得分
    all_words = set(tfidf_map.keys()) | set(textrank_map.keys())
    merged = {}
    for w in all_words:
        tfidf_score = tfidf_map.get(w, 0)
        tr_score = textrank_map.get(w, 0)
        if tfidf_score > 0 and tr_score > 0:
            # 两个算法都认为重要 — 高可信度
            merged[w] = tfidf_score * 0.4 + tr_score * 0.6
        elif tr_score > 0:
            merged[w] = tr_score * 0.7
        elif tfidf_score > 0:
            merged[w] = tfidf_score * 0.5

    # 排序
    sorted_words = sorted(merged.items(), key=lambda x: x[1], reverse=True)
    result = [{
        'keyword': w,
        'weight': round(s, 1)
    } for w, s in sorted_words[:topk]]

    return result


def _simple_keywords(processed_docs, topk=20):
    """简单词频统计（当TF-IDF不可用时的fallback）"""
    counter = Counter()
    for doc in processed_docs:
        counter.update(doc.split())
    total = sum(counter.values()) or 1
    sorted_words = counter.most_common(topk)
    result = [{
        'keyword': w,
        'weight': round(c / total * 1000, 1)
    } for w, c in sorted_words]
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
