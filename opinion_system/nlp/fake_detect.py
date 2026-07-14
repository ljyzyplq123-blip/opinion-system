"""
虚假文本检测模块
对采集到的信息进行真实性判断，给出置信度
"""
import re
import math
from collections import Counter


# 虚假文本特征词
SENSATIONAL_WORDS = [
    '震惊', '紧急', '劲爆', '速看', '删前速看', '马上删除', '再不看就删了',
    '难以置信', '太可怕了', '出大事了', '惊呆', '惊爆', '独家爆料',
    '刚刚', '最新消息', '突发', '重大', '秘密', '内幕', '曝光',
    '揭秘', '惊天', '逆天', '必看', '不转不是中国人', '紧急扩散',
    '一定要看', '不可思议', '万万没想到', '竟然', '竟然会这样',
    '史上最', '全宇宙', '全世界都', '彻底', '绝密', '天机',
]

# 不可信来源特征
UNRELIABLE_SOURCE_MARKERS = [
    '匿名', '网友', '据说', '网传', '知情人士', '内部人士', '不愿透露',
    '未经证实', '仅供参考', '不代表', '小编', '有人爆料', '据称',
    '业内人士', '相关人士', '消息人士', '可靠消息', '据可靠消息',
]

# 可信来源
RELIABLE_SOURCES = [
    '人民日报', '新华社', '央视新闻', '光明日报', '经济日报',
    '中国新闻社', '中国日报', '人民网', '新华网', '央视网',
    '澎湃新闻', '新京报', '南方周末', '中国青年报', '法制日报',
]


def detect_fake_news(text, source_url='', platform='', author=''):
    """
    检测虚假新闻
    返回: {is_fake: bool, confidence: float, reasons: [...], score: float}
    """
    reasons = []
    risk_score = 0.0
    total_weight = 0.0

    # 1. 标题党特征检测（权重提升，标题党是最强信号）
    title_score, title_reasons = _check_sensational(text)
    risk_score += title_score * 0.35
    total_weight += 0.35
    reasons.extend(title_reasons)

    # 2. 来源可信度检测
    source_score, source_reasons = _check_source_credibility(
        source_url, platform, author)
    risk_score += source_score * 0.30
    total_weight += 0.30
    reasons.extend(source_reasons)

    # 3. 内容一致性检测
    content_score, content_reasons = _check_content_consistency(text)
    risk_score += content_score * 0.15
    total_weight += 0.15
    reasons.extend(content_reasons)

    # 4. 语言特征检测
    lang_score, lang_reasons = _check_language_features(text)
    risk_score += lang_score * 0.20
    total_weight += 0.20
    reasons.extend(lang_reasons)

    # 归一化风险分数
    normalized_score = risk_score / total_weight if total_weight > 0 else 0.0

    # 判断结果（敏感度适配网络舆情场景）
    if normalized_score > 0.35:
        verdict = '疑似虚假'
    elif normalized_score > 0.20:
        verdict = '存疑'
    else:
        verdict = '可信'

    return {
        'verdict': verdict,
        'fake_probability': round(normalized_score, 4),
        'confidence': round(1.0 - abs(normalized_score - 0.5) * 2, 4),
        'risk_score': round(risk_score, 4),
        'reasons': reasons[:5]  # 最多返回5个原因
    }


def _check_sensational(text):
    """检测标题党特征"""
    reasons = []
    score = 0.0

    # 检测震惊体
    sensational_count = sum(1 for w in SENSATIONAL_WORDS if w in text)
    if sensational_count > 4:
        score += 1.0
        reasons.append('包含大量夸张/标题党词汇')
    elif sensational_count > 2:
        score += 0.7
        reasons.append('包含较多夸张词汇，高度可疑')
    elif sensational_count > 1:
        score += 0.5
        reasons.append('包含部分夸张词汇')
    elif sensational_count > 0:
        score += 0.3
        reasons.append('包含疑似夸张用词')

    # 检测感叹号数量
    exclamation_count = text.count('！') + text.count('!')
    if exclamation_count > 5:
        score += 0.4
        reasons.append('过量使用感叹号（情绪煽动特征）')
    elif exclamation_count > 3:
        score += 0.2

    # 检测问号数量
    question_count = text.count('？') + text.count('?')
    if question_count > 5:
        score += 0.2

    return min(score, 1.0), reasons


def _check_source_credibility(source_url, platform, author):
    """检测来源可信度"""
    reasons = []
    score = 0.0

    # 检查是否为可信来源
    is_reliable = any(s in platform for s in RELIABLE_SOURCES)
    if is_reliable:
        score -= 0.5
        reasons.append('来源为权威媒体')

    # 检查不可信标记
    unreliable_count = sum(1 for m in UNRELIABLE_SOURCE_MARKERS if m in source_url)
    if unreliable_count > 0:
        score += 0.4
        reasons.append('来源包含不确定性表述')

    # 检查URL
    if not source_url or source_url == '':
        score += 0.3
        reasons.append('无明确来源URL')

    # 检查作者
    if not author or author == '' or author == '未知':
        score += 0.2

    # 归一化到[0,1]
    return max(0.0, min(1.0, score)), reasons


def _check_content_consistency(text):
    """检测内容一致性"""
    reasons = []
    score = 0.0

    # 检测矛盾性表述
    contradictions = [
        ('官方' in text and '未经证实' in text),
        ('确认' in text and '据说' in text),
    ]
    if any(contradictions):
        score += 0.5
        reasons.append('内容包含矛盾性表述')

    # 检测文本长度（过短的文本可信度低）
    if len(text) < 50:
        score += 0.3
        reasons.append('内容过短，信息量不足')
    elif len(text) < 100:
        score += 0.1

    # 检测数字/数据是否有来源
    numbers = re.findall(r'\d+', text)
    if len(numbers) > 3 and '据' not in text and '数据' not in text:
        score += 0.2
        reasons.append('包含大量数字但未说明来源')

    return min(score, 1.0), reasons


def _check_language_features(text):
    """检测语言特征（不规范语言可能是虚假信息）"""
    reasons = []
    score = 0.0

    # 检测错别字（简单模拟）
    common_errors = ['在再', '的得地', '做作', '既即', '连联']
    for error in common_errors:
        # 简单检测：查找可能的错用
        pass

    # 检测语气过于绝对
    absolute_words = ['一定', '肯定', '绝对', '百分之百', '100%', '毫无疑问',
                       '必然', '必定', '毋庸置疑', '天经地义', '毫无疑问']
    abs_count = sum(1 for w in absolute_words if w in text)
    if abs_count > 3:
        score += 0.4
        reasons.append('语气过于绝对，缺乏客观性')
    elif abs_count > 1:
        score += 0.2

    # 检测情绪化表达
    emotion_words = ['太', '好', '坏', '厉害', '可怕', '恐怖', '恶心', '讨厌',
                     '可恶', '该死的', '去死', '无耻', '下流', '卑鄙']
    emo_count = sum(1 for w in emotion_words if w in text)
    if emo_count > 5:
        score += 0.3
        reasons.append('情绪化表达过多，可能不够客观')

    return min(score, 1.0), reasons


def batch_detect_fake(reports):
    """
    批量检测虚假新闻
    """
    results = []
    for r in reports:
        result = detect_fake_news(
            text=r.get('content', '') or r.get('title', ''),
            source_url=r.get('source_url', ''),
            platform=r.get('platform', ''),
            author=r.get('author', '')
        )
        results.append({**r, 'fake_detection': result})
    return results
