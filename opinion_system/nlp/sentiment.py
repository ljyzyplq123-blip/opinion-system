"""
情感分析模块
基于情感词典进行正/负/中性分析
"""
import jieba
import re
import math


# 内置情感词典
POSITIVE_WORDS = set([
    '好', '优秀', '出色', '成功', '满意', '幸福', '快乐', '高兴', '开心',
    '积极', '正面', '有利', '优势', '进步', '发展', '提升', '改善', '改观',
    '利好', '突破', '创新', '安全', '稳定', '和谐', '繁荣', '光明', '美好',
    '赞扬', '称赞', '表扬', '支持', '点赞', '欢迎', '认可', '肯定', '赞赏',
    '正能量', '给力', '暖心', '感动', '震撼', '惊艳', '保障', '便利',
    '公平', '公正', '透明', '高效', '优质', '实惠', '便捷', '可靠', '专业',
    '合理', '完善', '健全', '规范', '有序', '精彩', '卓越', '伟大', '光荣',
    '正确', '英明', '果断', '及时', '有效', '有力', '扎实', '坚实', '负责',
    '敬业', '奉献', '热心', '爱心', '善良', '真诚', '友好', '宽容', '理解',
    '尊重', '信任', '合作', '共赢', '团结', '和谐', '和平', '健康', '安全',
    '顺利', '圆满', '完美', '最佳', '一流', '顶尖', '领先', '先进', '智能',
    '漂亮', '厉害', '牛', '赞', '强', '棒', '火', '爆', '热', '红',
    '涨', '升', '增', '赢', '赚', '胜', '优', '良', '佳', '美',
    '惠民', '便民', '利民', '为民', '亲民', '反腐', '打黑', '维权', '环保',
    '低碳', '绿色', '节能', '减排', '可持续', '数字化', '信息化', '现代化',
])

NEGATIVE_WORDS = set([
    '差', '糟糕', '失败', '失望', '不幸', '悲伤', '痛苦', '愤怒', '生气',
    '消极', '负面', '不利', '劣势', '退步', '下降', '恶化', '变差', '衰落',
    '利空', '瓶颈', '危机', '危险', '风险', '动荡', '混乱', '黑暗', '糟糕',
    '批评', '指责', '投诉', '反对', '差评', '抵制', '否认', '质疑', '谴责',
    '负能量', '坑爹', '寒心', '无奈', '无语', '愤怒', '悲哀', '腐败', '贪污',
    '不公', '黑暗', '模糊', '低效', '劣质', '昂贵', '不便', '不可靠', '业余',
    '不合理', '不完善', '不健全', '不规范', '无序', '糟糕', '耻辱', '可耻',
    '错误', '失误', '失职', '渎职', '不力', '拖延', '推诿', '敷衍', '欺瞒',
    '造假', '诈骗', '欺骗', '暴力', '欺凌', '歧视', '偏见', '冷漠', '无视',
    '傲慢', '自私', '虚伪', '背叛', '分裂', '冲突', '战争', '疾病', '危难',
    '困难', '挫折', '损失', '损害', '破坏', '摧毁', '崩溃', '破产', '失败',
    '烂', '废', '渣', '坑', '骗', '黑', '假', '毒', '劣', '差',
    '跌', '降', '减', '亏', '输', '败', '死', '坏', '恶', '丑',
    '房价高', '看病难', '上学难', '就业难', '污染', '雾霾', '有毒',
    '有害', '致癌', '超标', '违规', '违法', '犯罪', '暴力', '恐怖',
])


# 程度副词权重
DEGREE_WORDS = {
    '极其': 2.0, '非常': 1.8, '十分': 1.8, '特别': 1.7, '相当': 1.6,
    '很': 1.5, '挺': 1.4, '比较': 1.2, '有点': 0.8, '稍微': 0.6,
    '略微': 0.5, '不太': 0.7, '不怎么': 0.6, '几乎不': 0.3, '完全不': 0.1,
    '更加': 1.5, '更': 1.5, '越来越': 1.6, '尤其': 1.7, '格外': 1.7,
    '最': 2.0, '最为': 2.0, '太': 1.6, '真': 1.4, '好': 1.3,
}


# 否定词
NEGATION_WORDS = set(['不', '没', '没有', '无', '非', '未', '否', '别', '莫',
                      '勿', '休', '毋', '难以', '难于', '无法', '未能'])


def analyze_sentiment(text):
    """
    对文本进行情感分析
    返回: {score: -1到1, label: positive/negative/neutral,
           positive_ratio, negative_ratio, neutral_ratio}
    """
    if not text:
        return {'score': 0.0, 'label': 'neutral',
                'positive_ratio': 0.0, 'negative_ratio': 0.0, 'neutral_ratio': 1.0}

    # 清理文本
    text = re.sub(r'[^一-鿿]', '', text)

    # 分词
    words = list(jieba.cut(text))
    words = [w.strip() for w in words if w.strip()]

    if not words:
        return {'score': 0.0, 'label': 'neutral',
                'positive_ratio': 0.0, 'negative_ratio': 0.0, 'neutral_ratio': 1.0}

    pos_score = 0
    neg_score = 0
    total_sentiment_words = 0

    i = 0
    while i < len(words):
        word = words[i]
        weight = 1.0
        negation = False

        # 检查前面的否定词
        if i > 0 and words[i - 1] in NEGATION_WORDS:
            negation = True

        # 检查前面的程度副词
        if i > 0 and words[i - 1] in DEGREE_WORDS:
            weight = DEGREE_WORDS[words[i - 1]]
        elif i > 1 and words[i - 2] in DEGREE_WORDS:
            weight = DEGREE_WORDS[words[i - 2]]

        if word in POSITIVE_WORDS:
            if negation:
                neg_score += weight
            else:
                pos_score += weight
            total_sentiment_words += 1
        elif word in NEGATIVE_WORDS:
            if negation:
                pos_score += weight
            else:
                neg_score += weight
            total_sentiment_words += 1

        i += 1

    # 计算综合得分 (-1 到 1)
    if total_sentiment_words == 0:
        return {'score': 0.0, 'label': 'neutral',
                'positive_ratio': 0.0, 'negative_ratio': 0.0, 'neutral_ratio': 1.0}

    total = pos_score + neg_score
    if total == 0:
        score = 0.0
    else:
        # 归一化到[-1, 1]
        score = (pos_score - neg_score) / (pos_score + neg_score)

    # 计算比例
    pos_ratio = pos_score / (pos_score + neg_score) if total > 0 else 0.0
    neg_ratio = neg_score / (pos_score + neg_score) if total > 0 else 0.0
    neu_ratio = max(0, 1.0 - (total_sentiment_words / max(len(words), 1)))

    # 确定标签
    if score > 0.2:
        label = 'positive'
    elif score < -0.2:
        label = 'negative'
    else:
        label = 'neutral'

    return {
        'score': round(score, 4),
        'label': label,
        'positive_ratio': round(pos_ratio, 4),
        'negative_ratio': round(neg_ratio, 4),
        'neutral_ratio': round(neu_ratio, 4)
    }


def analyze_sentiment_batch(texts):
    """
    批量情感分析
    """
    results = []
    for text in texts:
        results.append(analyze_sentiment(text))
    return results


def aggregate_sentiment(results):
    """
    汇总多个情感分析结果
    """
    if not results:
        return {'positive': 0.0, 'negative': 0.0, 'neutral': 1.0}

    # 使用标签统计
    pos_count = sum(1 for r in results if r['label'] == 'positive')
    neg_count = sum(1 for r in results if r['label'] == 'negative')
    neu_count = sum(1 for r in results if r['label'] == 'neutral')
    total = len(results)

    if total == 0:
        return {'positive': 0.0, 'negative': 0.0, 'neutral': 1.0}

    pos = pos_count / total
    neg = neg_count / total
    neu = neu_count / total

    # 确保至少有最小值
    if neu < 0.05 and (pos > 0 and neg > 0):
        pos = pos * 0.9
        neg = neg * 0.9
        neu = 1.0 - pos - neg

    return {
        'positive': round(pos, 4),
        'negative': round(neg, 4),
        'neutral': round(neu, 4)
    }
