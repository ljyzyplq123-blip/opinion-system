"""
QA API - 智能问答（LLM集成）
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, Event, QAHistory

qa_bp = Blueprint('qa', __name__)


@qa_bp.route('/qa/ask', methods=['POST'])
@login_required
def ask_question():
    """智能问答"""
    data = request.get_json() or {}
    question = data.get('question', '').strip()
    event_id = data.get('event_id')

    if not question:
        return jsonify({'success': False, 'message': '请输入问题'}), 400

    # 收集上下文信息
    context = ""
    event = None
    if event_id:
        event = db.session.get(Event, event_id)
        if event:
            context = f"""
当前讨论的事件：{event.title}
事件概要：{event.summary}
发生时间：{event.event_time}
地点：{event.location}
起因：{event.cause}
涉事方：{event.involved}
热度指数：{event.heat_index}
风险等级：{event.risk_level}
情感倾向：正面{event.positive_ratio}% / 负面{event.negative_ratio}% / 中性{event.neutral_ratio}%
生命周期阶段：{event.lifecycle_stage}
"""

    # 尝试调用LLM API
    answer = _call_llm(question, context)

    # 保存问答记录
    history = QAHistory(
        user_id=current_user.id,
        event_id=event_id,
        question=question,
        answer=answer
    )
    db.session.add(history)
    db.session.commit()

    return jsonify({
        'success': True,
        'answer': answer,
        'event': event.to_dict() if event else None
    })


@qa_bp.route('/qa/history', methods=['GET'])
@login_required
def get_history():
    """获取问答历史"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    pagination = QAHistory.query.filter_by(user_id=current_user.id).order_by(
        QAHistory.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'success': True,
        'history': [h.to_dict() for h in pagination.items],
        'total': pagination.total,
        'page': page,
        'pages': pagination.pages
    })


@qa_bp.route('/qa/history/<int:history_id>', methods=['DELETE'])
@login_required
def delete_history(history_id):
    """删除问答记录"""
    h = QAHistory.query.filter_by(
        id=history_id, user_id=current_user.id).first()
    if not h:
        return jsonify({'success': False, 'message': '记录不存在'}), 404
    db.session.delete(h)
    db.session.commit()
    return jsonify({'success': True, 'message': '已删除'})


def _call_llm(question, context):
    """调用大模型API（支持多后端fallback）"""
    from config import Config
    import requests

    system_prompt = """你是一个网络舆情分析助手，专门帮助用户分析网络舆情事件。
请基于提供的舆情事件信息，专业、客观地回答用户的问题。
如果提供了事件上下文，请结合事件信息进行分析。
如果没有具体事件上下文，请基于你的专业知识回答。
回答要简洁、有条理，使用中文。"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"事件背景：\n{context}\n\n用户问题：{question}"}
    ]

    # 尝试调用配置的LLM API
    try:
        response = requests.post(
            Config.LLM_API_URL,
            headers={
                "Authorization": f"Bearer {Config.LLM_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": Config.LLM_MODEL,
                "messages": messages,
                "max_tokens": 1000,
                "temperature": 0.7
            },
            timeout=30
        )
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            return _local_answer(question, context)
    except Exception:
        # LLM不可用时使用本地分析
        return _local_answer(question, context)


def _local_answer(question, context):
    """本地智能回答（LLM不可用时的fallback）"""
    import re

    if '情感' in question or '情绪' in question or '态度' in question:
        return _extract_sentiment_answer(context)

    if '趋势' in question or '发展' in question or '预测' in question:
        return _extract_trend_answer(context)

    if '风险' in question or '危害' in question or '严重' in question:
        return _extract_risk_answer(context)

    if '原因' in question or '起因' in question or '为什么' in question:
        return _extract_cause_answer(context)

    if '影响' in question or '后果' in question:
        return _extract_impact_answer(context)

    if '关键' in question or '传播' in question or '来源' in question:
        return _extract_source_answer(context)

    # 默认综合分析
    return f"""基于当前舆情数据，为您分析如下：

【事件概况】
{context}

【分析要点】
1. 从事件热度来看，该事件已引起广泛关注，建议持续监测舆情走势。
2. 情感分析方面，公众态度呈现多元化分布，需要关注极端情绪蔓延风险。
3. 事件发展仍需进一步跟踪，特别是关键节点的信息发布和官方回应。

【建议】
- 持续关注事件相关报道和社交媒体讨论
- 注意辨别信息来源的真实性
- 关注官方渠道的权威信息发布

如需更详细分析，请提出具体问题。"""


def _extract_sentiment_answer(context):
    """提取情感分析回答"""
    pos_match = _extract_field(context, '正面')
    neg_match = _extract_field(context, '负面')
    neu_match = _extract_field(context, '中性')
    return f"""【情感倾向分析】
公众对该事件的情感态度分析如下：
- 正面态度占比：{pos_match}%
- 负面态度占比：{neg_match}%
- 中性态度占比：{neu_match}%

整体来看，{'负面情绪较为突出，需要引起重视' if float(neg_match) > 30 else '舆论情绪相对平稳'}。
建议重点关注负面评论集中的平台和话题，及时了解公众关切。"""


def _extract_trend_answer(context):
    """提取趋势分析回答"""
    stage = _extract_field(context, '生命周期阶段')
    return f"""【发展趋势分析】
当前事件处于【{stage}】阶段。

根据事件传播规律分析：
- 潜伏期：事件初步发酵，报道量缓慢增长
- 成长期：关注度快速攀升，多平台扩散
- 高潮期：报道量达到峰值，广泛社会讨论
- 衰退期：关注度逐渐回落，事件趋于平息

当前阶段{'需要密切关注舆论走向' if stage in ['潜伏期', '成长期'] else '已进入后期阶段，但需防范二次发酵'}。建议根据阶段特点制定应对策略。"""


def _extract_risk_answer(context):
    """提取风险分析回答"""
    risk = _extract_field(context, '风险等级')
    return f"""【风险评估】
该事件风险等级：{risk}

风险评估维度分析：
1. 传播范围：事件在多平台扩散，{'影响面较大' if risk in ['中', '高'] else '目前可控'}
2. 公众情绪：需关注负面情绪蔓延风险
3. 舆论走向：{'存在升级风险' if risk == '高' else '趋势相对平稳'}
4. 社会影响：需评估对相关领域的实际影响

建议：{'立即启动舆情应急预案' if risk == '高' else '保持常规监测，做好应对准备'}"""


def _extract_cause_answer(context):
    """提取原因分析回答"""
    cause = _extract_field(context, '起因')
    location = _extract_field(context, '地点')
    involved = _extract_field(context, '涉事方')
    return f"""【事件原因分析】
事件起因：{cause}
发生地点：{location}
涉及方：{involved}

事件发生的深层原因需要从多个维度分析：
1. 直接触发因素：事件的直接导火索
2. 社会背景因素：当前社会环境和公众关注点
3. 传播放大因素：媒体报道和社交传播的作用
4. 利益相关方：各方诉求和博弈关系

建议辩证看待事件成因，避免简单归因。"""


def _extract_impact_answer(context):
    """提取影响分析回答"""
    return """【影响分析】
该事件可能产生以下影响：

1. 社会影响：
   - 引发公众对相关议题的广泛讨论
   - 可能推动相关政策的完善和调整

2. 行业影响：
   - 涉事机构/企业面临舆论压力
   - 行业规范可能得到加强

3. 舆情生态影响：
   - 话题持续发酵可能引发连锁反应
   - 需关注谣言和虚假信息的传播

建议各方理性看待，以事实为依据，避免情绪化判断。"""


def _extract_source_answer(context):
    """提取信息源分析回答"""
    return """【信息来源分析】
事件信息传播路径分析：

1. 首发来源：事件的初始信息发布渠道
2. 关键传播节点：
   - 主流媒体的介入报道
   - 社交平台的意见领袖转发
   - 官方机构的正式回应
3. 信息扩散模式：从点到面的传播扩散

建议：
- 核实信息源头，避免引用未经证实的消息
- 关注官方发布的权威信息
- 警惕断章取义和虚假信息"""


def _extract_field(context, field_name):
    """从上下文字符串中提取字段值"""
    import re
    # 尝试多种模式匹配
    patterns = [
        rf'{field_name}[：:]?\s*([^\n]+)',
        rf'{field_name}[：:]?\s*(\d+\.?\d*)%',
    ]
    for pattern in patterns:
        match = re.search(pattern, context)
        if match:
            return match.group(1).strip()
    return '未知'
