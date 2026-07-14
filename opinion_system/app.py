"""
Flask主应用入口
"""
import os
import time
import threading
from flask import Flask
from flask_login import LoginManager
from flask_cors import CORS
from config import config
from models import db, User

# 自动刷新间隔（秒），默认30分钟
AUTO_REFRESH_INTERVAL = int(os.environ.get('REFRESH_INTERVAL', '1800'))


def create_app(config_name=None):
    """应用工厂函数"""
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # 初始化扩展
    db.init_app(app)
    CORS(app, supports_credentials=True)

    # 登录管理器
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login_page'
    login_manager.login_message = '请先登录'

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # 注册蓝图
    from auth import auth_bp
    app.register_blueprint(auth_bp)

    from api.auth_api import api_auth_bp
    app.register_blueprint(api_auth_bp, url_prefix='/api')

    from api.event_api import event_bp
    app.register_blueprint(event_bp, url_prefix='/api')

    from api.dashboard_api import dashboard_bp
    app.register_blueprint(dashboard_bp, url_prefix='/api')

    from api.qa_api import qa_bp
    app.register_blueprint(qa_bp, url_prefix='/api')

    from api.user_api import user_bp
    app.register_blueprint(user_bp, url_prefix='/api')

    from api.crawler_api import crawler_api_bp
    app.register_blueprint(crawler_api_bp, url_prefix='/api')

    # 创建数据库表 + 启动时自动爬取真实数据
    with app.app_context():
        db.create_all()
        _auto_refresh_on_startup(app)

    # 启动后台定时刷新线程
    _start_background_refresh(app)

    # 注册调度器状态 API
    from flask import jsonify

    @app.route('/api/scheduler/status')
    def scheduler_status():
        return jsonify({
            'success': True,
            'interval_seconds': AUTO_REFRESH_INTERVAL,
            'interval_minutes': AUTO_REFRESH_INTERVAL / 60,
            'message': f'每 {AUTO_REFRESH_INTERVAL / 60:.0f} 分钟自动刷新一次',
        })

    return app


def _auto_refresh_on_startup(app):
    """
    启动时自动用真实热搜数据初始化/刷新数据库
    - 首次启动（无用户）：爬取真实数据
    - 后续启动：如果距上次刷新超过2小时，自动刷新
    """
    from datetime import datetime, timedelta
    from models import User, Event

    with app.app_context():
        user_count = User.query.first()
        if user_count is None:
            print("[Startup] 首次启动，开始爬取真实热搜数据...")
            _do_refresh(app, is_initial=True)
            return

        # 检查上次刷新时间（通过最新事件的创建时间判断）
        latest_event = Event.query.order_by(Event.created_at.desc()).first()
        if latest_event and latest_event.created_at:
            hours_since = (datetime.utcnow() - latest_event.created_at).total_seconds() / 3600
            if hours_since < 2:
                print(f"[Startup] 数据较新（{hours_since:.1f}小时前），跳过自动刷新")
                return

        print("[Startup] 数据需要更新，自动爬取真实热搜数据...")
        _do_refresh(app, is_initial=False)


def _do_refresh(app, is_initial=False):
    """执行真实数据爬取和入库"""
    import sys, os, random, json
    from datetime import datetime, timedelta
    from models import db, User, Event, EventReport, EventTrend, EventKeyword
    from nlp.sentiment import analyze_sentiment, aggregate_sentiment
    from nlp.segmentation import extract_keywords
    from nlp.fake_detect import detect_fake_news
    from nlp.hotspot import classify_event_category, predict_risk_level
    from nlp.lifecycle import assign_lifecycle_stage

    # 导入爬虫管理器和工具函数
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from crawler.spider import CrawlerManager
    from scripts.refresh_real_data import (
        _get_cross_platforms, _make_platform_url, _generate_report_content,
        _generate_trend_data, group_by_platform
    )

    with app.app_context():
        # 1. 爬取真实数据
        print("[Startup] 正在爬取各平台热搜...")
        manager = CrawlerManager()
        all_results = manager.crawl_all()

        if not all_results:
            print("[Startup] 爬取失败，未获取到数据")
            return

        real_results = all_results  # CrawlerManager now always returns real data
        print(f"[Startup] 爬取到 {len(real_results)} 条热搜")

        # 2. 清空旧事件数据
        print("[Startup] 清除旧数据...")
        EventTrend.query.delete()
        EventKeyword.query.delete()
        EventReport.query.delete()
        Event.query.delete()
        db.session.commit()

        # 3. 按平台分组
        groups = group_by_platform(real_results)
        now = datetime.utcnow()
        events_created = 0

        for platform, items in groups.items():
            for idx, item in enumerate(items[:20]):
                title = item.get('title', '').strip()
                desc = item.get('desc', '')
                if not title:
                    continue

                content = _generate_report_content(title, desc, platform)
                sentiment_result = analyze_sentiment(content)
                keywords_raw = extract_keywords(content, topk=15)
                fake_result = detect_fake_news(content, '', platform)
                category = classify_event_category(title + desc)

                rank = item.get('rank', idx) or idx
                heat_score = max(30, 99 - (rank * 2)) + random.uniform(-5, 5)
                heat_score = min(99, max(30, heat_score))
                event_time = now - timedelta(hours=random.randint(0, 48))

                event = Event(
                    title=title,
                    summary=desc or f"「{title}」引发全网热议，各大平台持续关注中。",
                    event_time=event_time,
                    location='全国',
                    cause=desc or f'{platform}热搜话题',
                    involved='社会各界',
                    heat_index=round(heat_score, 2),
                    category=category,
                    lifecycle_stage=assign_lifecycle_stage(heat_score, 1, str(event_time)),
                    risk_level=predict_risk_level(
                        {'category': category, 'negative_ratio': sentiment_result['negative_ratio']},
                        [{'publish_time': event_time.isoformat(), 'platform': platform}]
                    ),
                    report_count=1,
                    positive_ratio=round(sentiment_result['positive_ratio'], 2),
                    negative_ratio=round(sentiment_result['negative_ratio'], 2),
                    neutral_ratio=round(sentiment_result['neutral_ratio'], 2),
                    fake_news_score=fake_result['fake_probability'],
                    source_trace=json.dumps({
                        'initial_source': {
                            'platform': platform,
                            'url': item.get('url', ''),
                            'time': event_time.isoformat(),
                        }
                    }, ensure_ascii=False),
                )
                db.session.add(event)
                db.session.flush()

                # 原始报道
                report = EventReport(
                    event_id=event.id, title=title, content=content,
                    source_url=item.get('url', ''),
                    platform=platform, publish_time=event_time,
                    author='实时热搜', sentiment_score=sentiment_result['score'],
                    is_original=True, is_key_node=True, node_type='origin',
                )
                db.session.add(report)

                # 跨平台报道
                cross_platforms = _get_cross_platforms()
                other_platforms = [p for p in cross_platforms if p != platform]
                extra_reports = 0
                for extra_plat in random.sample(other_platforms, min(3, len(other_platforms))):
                    extra_time = event_time + timedelta(hours=random.randint(1, 12))
                    extra_title = f"[{extra_plat}转载] {title}"
                    extra_content = f"【{extra_plat}】{title}。{desc}此消息已在全网多平台引发热议。"
                    extra_sent = analyze_sentiment(extra_content)
                    is_key = random.random() < 0.4
                    extra_report = EventReport(
                        event_id=event.id, title=extra_title, content=extra_content,
                        source_url=_make_platform_url(extra_plat, title),
                        platform=extra_plat, publish_time=extra_time,
                        author=f'{extra_plat}平台', sentiment_score=extra_sent['score'],
                        is_original=False, is_key_node=is_key,
                        node_type=random.choice(['vip_repost', 'official']) if is_key else 'normal',
                    )
                    db.session.add(extra_report)
                    extra_reports += 1

                total_reports = 1 + extra_reports
                event.report_count = total_reports

                # 情感聚合
                all_scores = [sentiment_result] + [analyze_sentiment(f"[{p}] {title}") for p in random.sample(other_platforms, min(3, len(other_platforms)))]
                agg = aggregate_sentiment(all_scores)
                event.positive_ratio = round(agg['positive'], 2)
                event.negative_ratio = round(agg['negative'], 2)
                event.neutral_ratio = round(agg['neutral'], 2)

                # 丰富 source_trace
                event.source_trace = json.dumps({
                    'initial_source': {
                        'platform': platform,
                        'url': item.get('url', ''),
                        'time': event_time.isoformat(),
                        'description': f'事件最早由{platform}热搜话题引爆'
                    },
                    'key_nodes': [
                        {'type': 'origin', 'platform': platform, 'time': event_time.isoformat(),
                         'description': f'{platform}首发热搜'}
                    ] + [
                        {'type': 'cross_platform', 'platform': p,
                         'time': (event_time + timedelta(hours=random.randint(1, 12))).isoformat(),
                         'description': f'{p}平台跟进报道'}
                        for p in random.sample(other_platforms, min(2, len(other_platforms)))
                    ]
                }, ensure_ascii=False)

                # 关键词
                for kw in keywords_raw[:15]:
                    db.session.add(EventKeyword(
                        event_id=event.id, keyword=kw['keyword'], weight=kw['weight']
                    ))

                # 趋势数据
                _generate_trend_data(event.id, now, event)
                events_created += 1

        # 确保有演示用户
        if User.query.first() is None:
            demo_user = User(username='admin', email='admin@opinion.com')
            demo_user.set_password('admin123')
            db.session.add(demo_user)

        db.session.commit()
        print(f"[Startup] 成功创建 {events_created} 个真实舆情事件")


def _start_background_refresh(app):
    """启动后台定时刷新线程"""
    interval_min = AUTO_REFRESH_INTERVAL / 60
    print(f"[Scheduler] 后台自动刷新已启动，每 {interval_min:.0f} 分钟爬取一次热搜数据")

    def _refresh_loop():
        # 首次启动已刷新过，先等待一个间隔
        time.sleep(AUTO_REFRESH_INTERVAL)
        while True:
            try:
                print(f"[Scheduler] 定时刷新开始...")
                with app.app_context():
                    _do_refresh(app, is_initial=False)
                print(f"[Scheduler] 定时刷新完成，下次刷新: {interval_min:.0f} 分钟后")
            except Exception as e:
                print(f"[Scheduler] 刷新异常: {e}")
            time.sleep(AUTO_REFRESH_INTERVAL)

    t = threading.Thread(target=_refresh_loop, daemon=True, name='auto-refresh')
    t.start()


if __name__ == '__main__':
    application = create_app()
    application.run(host='0.0.0.0', port=5000, debug=True)
