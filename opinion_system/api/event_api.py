"""
Event API - 事件详情
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required
from models import db, Event, EventReport, EventKeyword, EventTrend

event_bp = Blueprint('event', __name__)


@event_bp.route('/events/<int:event_id>', methods=['GET'])
@login_required
def get_event(event_id):
    """获取事件完整详情"""
    event = db.session.get(Event, event_id)
    if not event:
        return jsonify({'success': False, 'message': '事件不存在'}), 404
    return jsonify({'success': True, 'event': event.to_detail_dict()})


@event_bp.route('/events/<int:event_id>/trend', methods=['GET'])
@login_required
def get_event_trend(event_id):
    """获取事件趋势数据"""
    event = db.session.get(Event, event_id)
    if not event:
        return jsonify({'success': False, 'message': '事件不存在'}), 404

    trends = EventTrend.query.filter_by(event_id=event_id).order_by(
        EventTrend.date).all()

    if not trends:
        return jsonify({'success': True, 'trend': {'dates': [], 'counts': [],
                                                    'key_nodes': []}})

    return jsonify({
        'success': True,
        'trend': {
            'dates': [t.date.isoformat() for t in trends],
            'counts': [t.report_count for t in trends],
            'key_nodes': [
                {'date': t.date.isoformat(), 'desc': t.key_node}
                for t in trends if t.key_node
            ],
            'positive': [t.positive_count for t in trends],
            'negative': [t.negative_count for t in trends],
            'neutral': [t.neutral_count for t in trends]
        }
    })


@event_bp.route('/events/<int:event_id>/sentiment', methods=['GET'])
@login_required
def get_event_sentiment(event_id):
    """获取事件情感分析"""
    event = db.session.get(Event, event_id)
    if not event:
        return jsonify({'success': False, 'message': '事件不存在'}), 404

    # 情感分布
    sentiment = {
        'positive': round(event.positive_ratio * 100, 1),
        'negative': round(event.negative_ratio * 100, 1),
        'neutral': round(event.neutral_ratio * 100, 1)
    }

    # 情感趋势
    trends = EventTrend.query.filter_by(event_id=event_id).order_by(
        EventTrend.date).all()
    sentiment_trend = {
        'dates': [t.date.isoformat() for t in trends],
        'positive': [t.positive_count for t in trends],
        'negative': [t.negative_count for t in trends],
        'neutral': [t.neutral_count for t in trends]
    }

    return jsonify({
        'success': True,
        'sentiment': sentiment,
        'sentiment_trend': sentiment_trend
    })


@event_bp.route('/events/<int:event_id>/platforms', methods=['GET'])
@login_required
def get_event_platforms(event_id):
    """获取平台分布"""
    event = db.session.get(Event, event_id)
    if not event:
        return jsonify({'success': False, 'message': '事件不存在'}), 404

    platforms = event._get_platform_distribution()
    return jsonify({'success': True, 'platforms': platforms})


@event_bp.route('/events/<int:event_id>/keywords', methods=['GET'])
@login_required
def get_event_keywords(event_id):
    """获取高频关键词"""
    keywords = EventKeyword.query.filter_by(event_id=event_id).order_by(
        EventKeyword.weight.desc()).limit(100).all()
    return jsonify({
        'success': True,
        'keywords': [k.to_dict() for k in keywords]
    })


@event_bp.route('/events/<int:event_id>/reports', methods=['GET'])
@login_required
def get_event_reports(event_id):
    """获取事件相关报道"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    sentiment = request.args.get('sentiment', '')  # positive/negative/neutral

    query = EventReport.query.filter_by(event_id=event_id)

    if sentiment == 'positive':
        query = query.filter(EventReport.sentiment_score > 0.3)
    elif sentiment == 'negative':
        query = query.filter(EventReport.sentiment_score < -0.3)
    elif sentiment == 'neutral':
        query = query.filter(
            db.and_(EventReport.sentiment_score >= -0.3,
                    EventReport.sentiment_score <= 0.3))

    pagination = query.order_by(EventReport.publish_time.desc()).paginate(
        page=page, per_page=per_page, error_out=False)

    return jsonify({
        'success': True,
        'reports': [r.to_dict() for r in pagination.items],
        'total': pagination.total,
        'page': page,
        'pages': pagination.pages
    })


@event_bp.route('/events/<int:event_id>/trace', methods=['GET'])
@login_required
def get_event_trace(event_id):
    """获取事件溯源与传播路径"""
    event = db.session.get(Event, event_id)
    if not event:
        return jsonify({'success': False, 'message': '事件不存在'}), 404

    import json
    trace_data = json.loads(event.source_trace) if event.source_trace else {}

    # 获取所有报道（不仅仅是关键节点），按时间排序
    all_reports = EventReport.query.filter_by(
        event_id=event_id
    ).order_by(EventReport.publish_time).all()

    if not all_reports:
        return jsonify({
            'success': True,
            'trace': {'nodes': [], 'edges': [], 'trace_data': trace_data}
        })

    nodes = []
    edges = []

    # 找到首发报道（origin节点）
    origin_reports = [r for r in all_reports if r.is_original]
    key_reports = [r for r in all_reports if r.is_key_node]

    # 构建节点：所有报道参与图谱
    seen_platforms = set()
    for r in all_reports:
        node = {
            'id': r.id,
            'name': r.platform,
            'label': r.author or r.platform,
            'type': r.node_type or ('origin' if r.is_original else 'normal'),
            'is_key': r.is_key_node,
            'is_origin': r.is_original,
            'time': r.publish_time.isoformat() if r.publish_time else '',
            'title': r.title,
            'sentiment': round(r.sentiment_score, 2),
        }
        nodes.append(node)
        seen_platforms.add(r.platform)

    # 构建边：从首发平台 → 各关键节点（树状传播），再→普通报道
    origin_ids = [r.id for r in origin_reports]
    key_ids = [r.id for r in key_reports]

    for origin_id in origin_ids:
        # 首发 → 各关键节点
        for key_r in key_reports:
            if key_r.id != origin_id:
                edges.append({'source': origin_id, 'target': key_r.id,
                              'label': '传播'})

    # 关键节点 → 同平台后续报道
    if key_reports:
        # 按平台分组非关键报道
        platform_key_node = {}
        for kr in key_reports:
            if kr.platform not in platform_key_node:
                platform_key_node[kr.platform] = kr.id

        for r in all_reports:
            if not r.is_key_node and not r.is_original:
                src = platform_key_node.get(r.platform)
                if src and src != r.id:
                    edges.append({'source': src, 'target': r.id,
                                  'label': '跟进'})
                elif key_ids:
                    # 如果该平台无关键节点，连到任意关键节点
                    edges.append({'source': key_ids[0], 'target': r.id,
                                  'label': '扩散'})

    # 如果没有任何边（只有1条报道），确保至少有节点展示
    if not edges and len(nodes) >= 2:
        # 简单按时间连接
        for i in range(1, len(nodes)):
            edges.append({'source': nodes[i-1]['id'], 'target': nodes[i]['id'],
                          'label': '后续'})

    # 提取溯源中的关键节点信息
    trace_nodes_from_data = []
    if trace_data:
        initial = trace_data.get('initial_source', {})
        if initial:
            trace_nodes_from_data.append({
                'id': 'trace_initial',
                'name': initial.get('platform', '未知'),
                'label': '信息首发',
                'type': 'origin',
                'time': initial.get('time', ''),
                'description': initial.get('description', ''),
            })
        for kn in trace_data.get('key_nodes', []):
            trace_nodes_from_data.append({
                'id': f"trace_kn_{kn.get('platform','')}_{kn.get('time','')}",
                'name': kn.get('platform', ''),
                'label': kn.get('type', '关键节点'),
                'type': kn.get('type', 'key'),
                'time': kn.get('time', ''),
                'description': kn.get('description', ''),
            })

    return jsonify({
        'success': True,
        'trace': {
            'nodes': nodes,
            'edges': edges,
            'trace_data': trace_data,
            'trace_nodes_from_data': trace_nodes_from_data,
            'platform_summary': {
                'total_platforms': len(seen_platforms),
                'platforms': list(seen_platforms),
                'total_reports': len(all_reports),
                'key_report_count': len(key_reports),
            }
        }
    })


@event_bp.route('/events/<int:event_id>/fakenews', methods=['GET'])
@login_required
def get_event_fakenews(event_id):
    """获取虚假文本检测结果"""
    event = db.session.get(Event, event_id)
    if not event:
        return jsonify({'success': False, 'message': '事件不存在'}), 404

    from nlp.fake_detect import detect_fake_news

    # 对每篇报道使用真正的虚假检测算法
    reports = EventReport.query.filter_by(event_id=event_id).all()
    fake_results = []
    scores = []

    for r in reports:
        result = detect_fake_news(
            text=(r.content or '') + ' ' + (r.title or ''),
            source_url=r.source_url or '',
            platform=r.platform or '',
            author=r.author or ''
        )
        scores.append(result['fake_probability'])
        fake_results.append({
            'report_id': r.id,
            'title': r.title,
            'fake_probability': result['fake_probability'],
            'verdict': result['verdict'],
            'reasons': result.get('reasons', []),
            'source': r.platform,
            'author': r.author
        })

    # 整体虚假风险 = 所有报道的平均虚假概率
    overall_score = round(sum(scores) / len(scores), 2) if scores else 0.0

    return jsonify({
        'success': True,
        'event_fake_score': overall_score,
        'reports': fake_results
    })


@event_bp.route('/events/search', methods=['GET'])
@login_required
def search_events():
    """搜索事件（支持历史事件和相似事件检索）"""
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({'success': False, 'message': '请输入搜索关键词'}), 400

    events = Event.query.filter(
        db.or_(
            Event.title.contains(q),
            Event.summary.contains(q),
            Event.cause.contains(q)
        )
    ).order_by(Event.heat_index.desc()).limit(20).all()

    return jsonify({
        'success': True,
        'events': [e.to_dict() for e in events],
        'query': q
    })
