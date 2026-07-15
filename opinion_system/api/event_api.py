"""
Event API - 事件详情
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required
from models import db, Event, EventReport, EventKeyword, EventTrend

event_bp = Blueprint('event', __name__)


def _fmt_iso(iso_str):
    """将 ISO 时间字符串转为人类可读格式 'YYYY-MM-DD HH:MM'"""
    if not iso_str:
        return ''
    try:
        # 处理各种ISO格式: '2025-07-10T12:30:00', '2025-07-10T12:30:00.123456'
        s = iso_str.replace('T', ' ').split('.')[0].split('+')[0].split('Z')[0]
        # 截取到分钟
        if len(s) >= 16:
            return s[:16]
        return s
    except Exception:
        return iso_str


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


@event_bp.route('/events/<int:event_id>/wordcloud', methods=['GET'])
@login_required
def get_event_wordcloud(event_id):
    """生成服务端词云图（参照 weibo_wordcloud 方案）"""
    from nlp.wordcloud_gen import generate_wordcloud

    keywords = EventKeyword.query.filter_by(event_id=event_id).order_by(
        EventKeyword.weight.desc()).limit(50).all()

    if not keywords:
        return jsonify({'success': False, 'message': '无关键词数据'}), 404

    kw_list = [{'keyword': k.keyword, 'weight': k.weight} for k in keywords]

    try:
        shape = request.args.get('shape', 'cloud')
        palette = request.args.get('palette', 'vivid')
        b64_img = generate_wordcloud(kw_list, mask_shape=shape, palette=palette)
        return jsonify({'success': True, 'image': b64_img})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


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
        pub_time = r.publish_time
        node = {
            'id': r.id,
            'name': r.platform,
            'label': r.author or r.platform,
            'type': r.node_type or ('origin' if r.is_original else 'normal'),
            'is_key': r.is_key_node,
            'is_origin': r.is_original,
            'time': pub_time.isoformat() if pub_time else '',
            'formatted_time': pub_time.strftime('%Y-%m-%d %H:%M') if pub_time else '',
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

    # 提取溯源中的关键节点信息，并融入图谱 nodes
    trace_nodes_from_data = []
    if trace_data:
        initial = trace_data.get('initial_source', {})
        if initial:
            init_time = initial.get('time', '')
            init_formatted = initial.get('formatted_time', '') or _fmt_iso(init_time)
            tn = {
                'id': 'trace_initial',
                'name': initial.get('platform', '未知'),
                'label': initial.get('author', '信息首发'),
                'type': 'origin',
                'time': init_time,
                'formatted_time': init_formatted,
                'description': initial.get('description', ''),
                'symbolSize': 35,
            }
            trace_nodes_from_data.append(tn)
            nodes.insert(0, tn)  # 放在最前面

        for i, kn in enumerate(trace_data.get('key_nodes', [])):
            kn_type = kn.get('type', 'key')
            # 统一 type 名称以匹配前端分类
            if kn_type == 'official_media':
                kn_type = 'official'
            kn_time = kn.get('time', '')
            kn_formatted = kn.get('formatted_time', '') or _fmt_iso(kn_time)
            tn = {
                'id': f"trace_kn_{i}_{kn.get('platform','')}",
                'name': kn.get('platform', ''),
                'label': kn.get('author', kn.get('description', '关键节点')),
                'type': kn_type,
                'time': kn_time,
                'formatted_time': kn_formatted,
                'description': kn.get('description', ''),
                'symbolSize': 25 if kn_type == 'official' else 22,
            }
            trace_nodes_from_data.append(tn)
            nodes.append(tn)  # 追加到图谱节点

    # 按时间顺序重建边：形成传播链
    # 对 trace 节点按时间排序，构建链式边
    trace_nodes_sorted = sorted(
        [n for n in nodes if str(n['id']).startswith('trace_')],
        key=lambda n: n.get('time', '')
    )
    for i in range(len(trace_nodes_sorted) - 1):
        edges.insert(0, {
            'source': trace_nodes_sorted[i]['id'],
            'target': trace_nodes_sorted[i + 1]['id'],
            'label': '→',
            'lineStyle': {'color': '#667eea', 'width': 2, 'curveness': 0.1},
        })

    # 将 trace 节点也连到对应的 EventReport 节点
    for tn in trace_nodes_sorted:
        matching_reports = [
            r for r in all_reports
            if r.platform == tn.get('name') and r.publish_time
        ]
        if matching_reports:
            closest = min(
                matching_reports,
                key=lambda r: abs((r.publish_time - datetime.fromisoformat(tn['time'])).total_seconds())
                if tn.get('time') and r.publish_time else 999999
            )
            if closest.id != tn['id']:
                edges.append({
                    'source': tn['id'],
                    'target': closest.id,
                    'label': '详情',
                    'lineStyle': {'color': '#ddd', 'type': 'dashed'},
                })

    # 构建传播链 (供前端水平时间线)
    propagation_chain = trace_data.get('propagation_timeline', []) if trace_data else []

    # 统计 — 使用 v2 propagation metrics
    metrics = trace_data.get('propagation_metrics', {})
    platform_summary = trace_data.get('platform_summary', {})

    stats = {
        'total_platforms': platform_summary.get('total_platforms', len(seen_platforms)),
        'platforms': platform_summary.get('platforms', list(seen_platforms)),
        'total_reports': len(all_reports),
        'key_report_count': platform_summary.get('key_report_count', len(key_reports)),
        'official_report_count': platform_summary.get('official_report_count',
            len([r for r in all_reports if getattr(r, 'node_type', '') == 'official'])),
        'influencer_report_count': platform_summary.get('vip_report_count',
            len([r for r in all_reports if getattr(r, 'node_type', '') == 'vip_repost'])),
        'first_response_time': metrics.get('first_response_time', 'N/A'),
        'first_response_delta': metrics.get('first_response_delta', ''),
        'propagation_span': metrics.get('propagation_span', ''),
        'propagation_depth': metrics.get('propagation_depth', 1),
        'platform_detail': platform_summary.get('platform_detail', {}),
    }

    return jsonify({
        'success': True,
        'trace': {
            'nodes': nodes,
            'edges': edges,
            'trace_data': trace_data,
            'propagation_chain': propagation_chain,
            'stats': stats,
        }
    })


@event_bp.route('/events/<int:event_id>/content-analysis', methods=['GET'])
@login_required
def get_event_content_analysis(event_id):
    """内容分析：正文提取 + 分词 + 特征表示"""
    from nlp.content_analyzer import analyze_document, extract_features_from_documents

    reports = EventReport.query.filter_by(
        event_id=event_id
    ).order_by(EventReport.publish_time).all()

    if not reports:
        return jsonify({'success': False, 'message': '无报道数据'}), 404

    # 分析每篇报道
    report_analyses = []
    all_contents = []

    for r in reports[:10]:  # 最多分析10篇
        content = r.content or ''
        if len(content) < 20:
            continue

        analysis = analyze_document(content, is_html=False)
        all_contents.append(content)

        report_analyses.append({
            'id': r.id,
            'title': r.title,
            'platform': r.platform,
            'author': r.author,
            'word_count': analysis['word_count'],
            'keywords': analysis['keywords'][:8],
            'features': analysis['features'],
        })

    # 聚合特征
    agg_features = extract_features_from_documents(all_contents)

    return jsonify({
        'success': True,
        'report_analyses': report_analyses,
        'aggregated': agg_features,
        'report_count': len(report_analyses),
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
