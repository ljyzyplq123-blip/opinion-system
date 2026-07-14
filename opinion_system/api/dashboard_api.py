"""
Dashboard API - 舆情看板
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required
from models import db, Event

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard', methods=['GET'])
@login_required
def get_dashboard():
    """获取看板事件列表"""
    sort_by = request.args.get('sort', 'heat')  # heat / time
    category = request.args.get('category', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    query = Event.query

    if category:
        query = query.filter_by(category=category)

    if sort_by == 'time':
        query = query.order_by(Event.event_time.desc())
    else:
        query = query.order_by(Event.heat_index.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    events = pagination.items

    return jsonify({
        'success': True,
        'events': [e.to_dict() for e in events],
        'total': pagination.total,
        'page': page,
        'pages': pagination.pages,
        'has_next': pagination.has_next
    })


@dashboard_bp.route('/dashboard/stats', methods=['GET'])
@login_required
def get_stats():
    """获取看板统计数据"""
    total_events = Event.query.count()
    total_reports = db.session.query(db.func.sum(Event.report_count)).scalar() or 0
    high_risk = Event.query.filter_by(risk_level='高').count()
    today_events = Event.query.filter(
        db.func.date(Event.created_at) == db.func.date('now')
    ).count()

    # 分类统计
    categories = db.session.query(
        Event.category, db.func.count(Event.id)
    ).group_by(Event.category).all()

    # 各生命周期分布
    lifecycle_stats = db.session.query(
        Event.lifecycle_stage, db.func.count(Event.id)
    ).group_by(Event.lifecycle_stage).all()

    return jsonify({
        'success': True,
        'stats': {
            'total_events': total_events,
            'total_reports': total_reports,
            'high_risk_count': high_risk,
            'today_events': today_events,
            'categories': [{'name': c[0], 'count': c[1]} for c in categories],
            'lifecycle': [{'stage': l[0], 'count': l[1]} for l in lifecycle_stats]
        }
    })


@dashboard_bp.route('/dashboard/hotspots', methods=['GET'])
@login_required
def get_hotspots():
    """获取实时热点（top事件）"""
    limit = request.args.get('limit', 10, type=int)
    events = Event.query.order_by(Event.heat_index.desc()).limit(limit).all()
    return jsonify({
        'success': True,
        'hotspots': [e.to_dict() for e in events]
    })
