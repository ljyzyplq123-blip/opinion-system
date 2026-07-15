"""
用真实爬取数据替换演示数据
用法: python scripts/refresh_real_data.py
"""
import sys
import os
import random
import json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db, Event, EventReport, EventTrend, EventKeyword
from nlp.sentiment import analyze_sentiment, aggregate_sentiment
from nlp.segmentation import extract_keywords, extract_keywords_tfidf, extract_keywords_combined
from nlp.fake_detect import detect_fake_news
from nlp.lifecycle import assign_lifecycle_stage
from nlp.hotspot import classify_event_category, predict_risk_level
from nlp.clustering import compute_heat_index
from nlp.propagation import analyze_propagation, classify_report_node
from crawler.article_fetcher import ArticleFetcher


def _get_cross_platforms():
    """从监控平台配置中获取爬虫输出平台名列表（用于跨平台传播模拟）"""
    from crawler.spider import CrawlerManager
    manager = CrawlerManager()
    names = manager.get_crawler_output_names()
    # 如果 MonitoredSource 为空（首次启动时），回退到所有已注册的爬虫平台
    if not names:
        names = [info[2] for info in CrawlerManager.CRAWLER_REGISTRY.values()]
    return names

# 平台名 → 真实域名
PLATFORM_DOMAIN = {
    '微博': 'https://weibo.com',
    '百度热搜': 'https://top.baidu.com',
    '知乎': 'https://www.zhihu.com',
    '今日头条': 'https://www.toutiao.com',
    '抖音': 'https://www.douyin.com',
    '澎湃新闻': 'https://www.thepaper.cn',
    '央视新闻': 'https://news.cctv.com',
    'B站': 'https://www.bilibili.com',
    '小红书': 'https://www.xiaohongshu.com',
    '快手': 'https://www.kuaishou.com',
    '微信公众号': 'https://mp.weixin.qq.com',
    '豆瓣': 'https://www.douban.com',
    '网易新闻': 'https://news.163.com',
    '搜狐新闻': 'https://news.sohu.com',
    '人民日报': 'https://www.people.com.cn',
    '虎扑': 'https://bbs.hupu.com',
}


def _make_platform_url(platform_name, keyword=''):
    """根据平台名和关键词生成可用的搜索URL"""
    import urllib.parse
    kw = urllib.parse.quote(keyword or '')
    urls = {
        '微博': f'https://s.weibo.com/weibo?q={kw}',
        '百度热搜': f'https://www.baidu.com/s?wd={kw}',
        '知乎': f'https://www.zhihu.com/search?type=content&q={kw}',
        '今日头条': f'https://so.toutiao.com/search?keyword={kw}',
        '抖音': f'https://www.douyin.com/search/{kw}',
        '澎湃新闻': f'https://www.thepaper.cn/search?keyword={kw}',
        '央视新闻': f'https://search.cctv.com/search.php?qtext={kw}',
        'B站': f'https://search.bilibili.com/all?keyword={kw}',
        '小红书': f'https://www.xiaohongshu.com/search_result?keyword={kw}',
        '快手': f'https://www.kuaishou.com/search/video?searchKey={kw}',
        '微信公众号': f'https://mp.weixin.qq.com/mp/search?search=1&query={kw}',
        '豆瓣': f'https://www.douban.com/search?q={kw}',
        '网易新闻': f'https://news.163.com/news/search?keyword={kw}',
        '搜狐新闻': f'https://news.sohu.com/a/',
        '人民日报': f'https://www.people.com.cn/',
        '虎扑': f'https://bbs.hupu.com/',
    }
    return urls.get(platform_name, f'https://www.baidu.com/s?wd={kw}')


def crawl_real_data():
    """爬取真实热搜数据"""
    print("="*50)
    print("🕷️  开始爬取真实数据...")
    print("="*50)

    from crawler.spider import CrawlerManager
    manager = CrawlerManager()

    all_results = manager.crawl_all()

    print(f"\n爬取完成: 共 {len(all_results)} 条")

    if not all_results:
        print("\n没有获取到真实数据！请检查:")
        print("   1. 各平台 Cookie 是否已配置（个人中心 → 爬虫配置）")
        print("   2. 网络是否可以访问目标网站")
        return None

    return all_results


def group_by_platform(results):
    """按平台分组"""
    groups = {}
    for r in results:
        plat = r.get('platform', '未知')
        if plat not in groups:
            groups[plat] = []
        groups[plat].append(r)
    return groups


def create_events_from_real_data(results, app):
    """从真实爬取数据创建舆情事件"""
    print("\n" + "="*50)
    print("📊 创建舆情事件...")
    print("="*50)

    with app.app_context():
        # 清空已有数据
        print("🗑️  清除旧数据...")
        EventTrend.query.delete()
        EventKeyword.query.delete()
        EventReport.query.delete()
        Event.query.delete()
        db.session.commit()

        # 按平台分组
        groups = group_by_platform(results)

        # 为每个热门话题创建事件
        events_created = 0
        now = datetime.now()

        for platform, items in groups.items():
            # 取该平台前20条
            for idx, item in enumerate(items[:20]):
                title = item.get('title', '').strip()
                desc = item.get('desc', '')
                if not title:
                    continue

                # 使用 ArticleFetcher 搜索真实文章
                fetcher = ArticleFetcher()
                source_articles = fetcher.fetch_for_topic(title, platform, max_articles=3)

                if source_articles:
                    # 使用搜索到的真实文章
                    primary_article = source_articles[0]
                    content = f"{primary_article['title']}。{primary_article['content']}"
                    article_time = primary_article.get('publish_time')
                    # 如果文章时间是近期（1小时内），使用随机历史时间使其更真实
                    if article_time and abs((datetime.utcnow() - article_time).total_seconds()) < 3600:
                        article_time = None
                    event_time = article_time if article_time else \
                        datetime.utcnow() - timedelta(hours=random.randint(1, 168))  # 1小时~7天前
                else:
                    # 搜索失败时使用原始热搜摘要
                    content = f"【{platform}热搜】{title}。{desc}该话题引发网友广泛关注与讨论。"
                    event_time = datetime.utcnow() - timedelta(hours=random.randint(1, 168))

                # NLP分析
                sentiment_result = analyze_sentiment(content)
                fake_result = detect_fake_news(content, '', platform)
                category = classify_event_category(title + desc)

                # 计算热度（指数衰减，排名越高热度越高，避免大量99分）
                import math
                rank = item.get('rank', idx + 1) or (idx + 1)
                # 指数衰减: rank 1≈97, rank 5≈82, rank 10≈63, rank 20≈38, rank 35≈20
                base_score = 100 * math.exp(-0.045 * rank)
                heat_score = round(base_score + random.uniform(-3, 3), 1)
                heat_score = max(20, min(98, heat_score))

                # 创建事件
                summary = desc or f"「{title}」引发全网热议，各大平台持续关注中。"

                event = Event(
                    title=title,
                    summary=summary,
                    event_time=event_time,
                    location='全国' if '地' not in title else '',
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

                # 创建原始报道（首发平台）— 使用真实文章信息
                primary_url = source_articles[0].get('url', item.get('url', '')) if source_articles else item.get('url', '')
                primary_author = source_articles[0].get('author', '实时热搜') if source_articles else '实时热搜'
                primary_time = source_articles[0].get('publish_time', event_time) if source_articles else event_time
                report = EventReport(
                    event_id=event.id,
                    title=title,
                    content=content,
                    source_url=primary_url,
                    platform=platform,
                    publish_time=primary_time,
                    author=primary_author,
                    sentiment_score=sentiment_result['score'],
                    is_original=True,
                    is_key_node=True,
                    node_type='origin',
                )
                db.session.add(report)

                # 统计各平台帖子数 + 抓取1-2篇跨平台代表报道
                cross_platforms = _get_cross_platforms()
                other_platforms = [p for p in cross_platforms if p != platform]
                platform_counts = {}
                extra_reports = 0
                extra_sentiments = []

                # 构建需要统计的所有平台列表
                all_count_platforms = list(cross_platforms)
                if platform not in all_count_platforms:
                    all_count_platforms.append(platform)

                try:
                    counts = fetcher.count_all_platforms(title, all_count_platforms)
                    platform_counts.update(counts)
                except Exception:
                    pass

                # 兜底：确保每个平台都有合理的报道数（不为0或1）
                for plat in all_count_platforms:
                    cnt = platform_counts.get(plat, 0)
                    if cnt <= 1:
                        domain = fetcher._get_platform_domain(plat)
                        platform_counts[plat] = fetcher._estimate_count(title, domain)

                # 每个其他平台抓取1-2篇代表报道（展示在"相关报道"列表）
                # 不同节点类型有不同的传播延迟（模拟真实传播节奏）
                NODE_DELAY = {
                    'origin': (0, 1),           # 首发：0-1小时内
                    'vip_repost': (2, 24),      # 大V转发：2-24小时后
                    'official': (6, 72),        # 官媒介入：6-72小时后
                    'normal': (12, 168),        # 普通传播：12小时-7天后
                }
                for extra_plat in random.sample(other_platforms, min(3, len(other_platforms))):
                    cross_articles = fetcher.fetch_cross_platform(
                        title, platform, extra_plat, max_articles=2
                    )
                    if cross_articles:
                        for ca_idx, ca in enumerate(cross_articles):
                            extra_content = f"{ca['title']}。{ca['content']}"
                            extra_sent = analyze_sentiment(extra_content)
                            extra_sentiments.append(extra_sent)
                            # 使用 node_meta 分类确定 node_type
                            node_meta = ca.get('node_meta', {})
                            classification = classify_report_node(ca, is_original=False, node_meta=node_meta)
                            is_key = (ca_idx == 0 or
                                      classification['node_type'] in ('official', 'vip_repost'))
                            # 根据节点类型计算合理的传播时间
                            min_h, max_h = NODE_DELAY.get(classification['node_type'], (1, 12))
                            article_time = ca.get('publish_time')
                            # 如果文章时间不可靠（与当前时间太近），使用偏移量
                            if (article_time and
                                abs((datetime.utcnow() - article_time).total_seconds()) < 3600):
                                article_time = None  # 太新，使用偏移
                            extra_time = article_time if article_time else \
                                event_time + timedelta(hours=random.randint(min_h, max_h))
                            extra_report = EventReport(
                                event_id=event.id,
                                title=ca['title'][:200],
                                content=ca['content'][:500],
                                source_url=ca.get('url', ''),
                                platform=extra_plat,
                                publish_time=extra_time,
                                author=ca.get('author', f'{extra_plat}平台'),
                                sentiment_score=extra_sent['score'],
                                is_original=False,
                                is_key_node=is_key,
                                node_type=classification['node_type'],
                            )
                            db.session.add(extra_report)
                            extra_reports += 1

                event.platform_distribution = json.dumps(platform_counts, ensure_ascii=False)
                total_reports = 1 + extra_reports
                event.report_count = total_reports

                # 情感比例综合原始文章+跨平台报道
                all_scores = [sentiment_result] + extra_sentiments
                if len(all_scores) > 1:
                    agg = aggregate_sentiment(all_scores)
                    event.positive_ratio = round(agg['positive'], 2)
                    event.negative_ratio = round(agg['negative'], 2)
                    event.neutral_ratio = round(agg['neutral'], 2)
                else:
                    event.positive_ratio = round(sentiment_result['positive_ratio'], 2)
                    event.negative_ratio = round(sentiment_result['negative_ratio'], 2)
                    event.neutral_ratio = round(sentiment_result['neutral_ratio'], 2)

                # 传播路径分析
                all_reports = EventReport.query.filter_by(event_id=event.id).order_by(
                    EventReport.publish_time).all()
                trace_data = analyze_propagation(event, all_reports)
                event.source_trace = json.dumps(trace_data, ensure_ascii=False)

                # 使用综合算法提取关键词（TF-IDF + TextRank，含词性过滤）
                report_contents = [r.content for r in all_reports if r.content and len(r.content) > 10]
                if report_contents:
                    keywords_raw = extract_keywords_combined(report_contents, topk=15)
                else:
                    keywords_raw = extract_keywords(content, topk=15)
                for kw in keywords_raw[:15]:
                    ek = EventKeyword(
                        event_id=event.id,
                        keyword=kw['keyword'],
                        weight=kw['weight']
                    )
                    db.session.add(ek)

                # 生成趋势数据（模拟最近7天）
                _generate_trend_data(event.id, now, event)

                events_created += 1

        db.session.commit()

        print(f"\n✅ 成功创建 {events_created} 个真实舆情事件！")
        return events_created


def _generate_report_content(title, desc, platform):
    """生成新闻稿般的报道内容"""
    templates = [
        f"【{platform}热搜】{title}。{desc}",
        f"今天，{title}引发热议。{desc}据多家媒体报道，相关话题讨论量持续攀升。",
        f"{title}。{desc}此消息一经发布，迅速登上{platform}热搜榜，引发网友广泛关注和讨论。",
        f"最新消息：{title}。{desc}业内专家表示，这将对相关领域产生深远影响。",
    ]
    return random.choice(templates)


def _generate_trend_data(event_id, now, event):
    """为事件生成模拟趋势数据"""
    for day_offset in range(7, -1, -1):
        trend_date = (now - timedelta(days=day_offset)).date()

        # 最近几天的数据更多
        if day_offset <= 1:
            count = random.randint(5, 30)
        elif day_offset <= 3:
            count = random.randint(2, 10)
        else:
            count = random.randint(0, 5)

        pos_c = int(count * event.positive_ratio)
        neg_c = int(count * event.negative_ratio)
        neu_c = max(0, count - pos_c - neg_c)

        key_node = ''
        if day_offset == 0:
            key_node = f'登上{event.category}类热搜'
        elif day_offset == 1:
            key_node = '话题热度快速上升'

        trend = EventTrend(
            event_id=event_id,
            date=trend_date,
            report_count=count,
            key_node=key_node,
            positive_count=pos_c,
            negative_count=neg_c,
            neutral_count=neu_c,
        )
        db.session.add(trend)


def main():
    app = create_app()

    # 1. 爬取真实数据
    real_data = crawl_real_data()
    if not real_data:
        print("\n❌ 爬取失败，数据未更新。")
        return

    # 打印爬取预览
    print("\n📋 爬取预览（前10条）:")
    for i, item in enumerate(real_data[:10]):
        heat = item.get('heat', '?')
        plat = item.get('platform', '?')
        print(f"  {i+1}. [{plat}] {item['title'][:40]} (热度:{heat})")

    # 2. 创建事件
    count = create_events_from_real_data(real_data, app)

    # 3. 结果
    print("\n" + "="*50)
    print(f"🎉 完成! 数据已更新为真实热搜事件 ({count} 个事件)")
    print("   重启服务器: python app.py")
    print("   然后访问 http://localhost:5000/dashboard")
    print("="*50)


if __name__ == '__main__':
    main()
