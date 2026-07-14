"""
演示数据生成器
生成逼真的中文舆情事件数据用于系统演示
"""
from datetime import datetime, timedelta
import random
import json
from models import db, User, Event, EventReport, EventTrend, EventKeyword, MonitoredSource, MonitoredKeyword


# ============================================================
# 预设事件模板
# ============================================================
EVENT_TEMPLATES = [
    {
        "title": "某市食品安全事件引发广泛关注",
        "summary": "多名市民在某知名连锁餐厅就餐后出现集体食物中毒症状，市市场监管部门已介入调查。事件在社交平台迅速发酵，引发公众对食品安全的担忧。",
        "location": "广东省广州市",
        "cause": "市民在某连锁餐厅就餐后出现呕吐、腹泻等食物中毒症状，初步调查显示可能与食材储存不当有关。",
        "involved": "广州市市场监管局、涉事餐饮企业、卫健委、消费者协会",
        "category": "社会",
        "risk_level": "高",
        "platform_weights": {"微博": 0.40, "今日头条": 0.25, "抖音": 0.20, "澎湃新闻": 0.15},
        "sentiment_profile": {"positive": 0.10, "negative": 0.65, "neutral": 0.25},
        "peak_day": 3,
        "lifecycle_preset": "高潮期"
    },
    {
        "title": "某科技巨头发布新一代AI大模型",
        "summary": "国内某科技巨头正式发布自研大语言模型，多项基准测试超越国际主流模型。该消息引发科技圈和投资界广泛讨论，相关概念股大幅上涨。",
        "location": "北京",
        "cause": "科技公司年度战略发布会正式推出自主研发的大语言模型产品，并宣布开源计划。",
        "involved": "科技公司CEO、工信部、AI行业专家、投资机构",
        "category": "科技",
        "risk_level": "低",
        "platform_weights": {"微博": 0.25, "知乎": 0.30, "今日头条": 0.20, "36氪": 0.15, "虎嗅": 0.10},
        "sentiment_profile": {"positive": 0.55, "negative": 0.10, "neutral": 0.35},
        "peak_day": 2,
        "lifecycle_preset": "成长期"
    },
    {
        "title": "某地暴雨洪涝灾害致多人受灾",
        "summary": "连日强降雨导致某省多地出现严重洪涝灾害，受灾人口超过百万。当地政府启动防汛一级应急响应，各方力量紧急投入抢险救灾工作。",
        "location": "河南省郑州市",
        "cause": "受台风外围环流影响，该地区遭遇百年一遇的极端强降雨天气，24小时降雨量突破历史极值。",
        "involved": "应急管理部、水利部、当地政府、解放军、红十字会、社会各界",
        "category": "社会",
        "risk_level": "高",
        "platform_weights": {"微博": 0.35, "人民日报": 0.20, "央视新闻": 0.20, "快手": 0.15, "抖音": 0.10},
        "sentiment_profile": {"positive": 0.30, "negative": 0.25, "neutral": 0.45},
        "peak_day": 2,
        "lifecycle_preset": "高潮期"
    },
    {
        "title": "知名艺人涉嫌违法事件持续发酵",
        "summary": "某知名艺人被举报涉嫌多项违法行为，品牌方陆续宣布解约。事件在粉丝群体中引发激烈争论，话题多次登上热搜榜首。",
        "location": "上海",
        "cause": "网友实名举报该艺人涉嫌偷税漏税及不当言论，相关部门已立案调查。",
        "involved": "涉事艺人、经纪公司、品牌合作方、税务部门、网信办",
        "category": "娱乐",
        "risk_level": "中",
        "platform_weights": {"微博": 0.55, "豆瓣": 0.15, "抖音": 0.15, "小红书": 0.10, "百度贴吧": 0.05},
        "sentiment_profile": {"positive": 0.15, "negative": 0.50, "neutral": 0.35},
        "peak_day": 4,
        "lifecycle_preset": "成长期"
    },
    {
        "title": "某高校学术不端事件调查结果公布",
        "summary": "某知名高校教师被举报学术论文造假，经校方调查认定存在严重学术不端行为。该事件在学术界和教育领域引发广泛反思。",
        "location": "湖北省武汉市",
        "cause": "匿名举报者向校方和学术期刊提交了详实的论文造假证据，涉及多篇高水平论文的数据篡改和图片重复使用。",
        "involved": "涉事教师、高校学术委员会、教育部、期刊编辑部、举报人",
        "category": "教育",
        "risk_level": "中",
        "platform_weights": {"知乎": 0.35, "微博": 0.25, "微信公众号": 0.20, "今日头条": 0.20},
        "sentiment_profile": {"positive": 0.20, "negative": 0.55, "neutral": 0.25},
        "peak_day": 5,
        "lifecycle_preset": "衰退期"
    },
    {
        "title": "某市出台楼市新政引发热议",
        "summary": "某一线城市住建部门发布房地产调控新政，全面取消限购政策并降低首付比例。新政在购房者、开发商和学者中引发了激烈讨论。",
        "location": "广东省深圳市",
        "cause": "为促进房地产市场平稳健康发展，该市住建局联合多部门出台了新一轮楼市调控优化政策。",
        "involved": "深圳市住建局、央行、各大银行、房地产开发商、购房者",
        "category": "财经",
        "risk_level": "中",
        "platform_weights": {"今日头条": 0.25, "微博": 0.20, "雪球": 0.20, "微信公众号": 0.20, "知乎": 0.15},
        "sentiment_profile": {"positive": 0.40, "negative": 0.20, "neutral": 0.40},
        "peak_day": 3,
        "lifecycle_preset": "成长期"
    },
    {
        "title": "某国际体育赛事中国队夺冠",
        "summary": "在某国际顶级体育赛事中，中国队创造历史性突破夺得冠军。全国各大媒体争相报道，全民庆祝氛围浓厚。",
        "location": "日本东京",
        "cause": "中国队在决赛中战胜强劲对手，打破该项目多年的国际垄断，实现历史性突破。",
        "involved": "中国代表队、国家体育总局、国际体育组织、赞助商",
        "category": "体育",
        "risk_level": "低",
        "platform_weights": {"微博": 0.30, "抖音": 0.25, "央视体育": 0.20, "虎扑": 0.15, "B站": 0.10},
        "sentiment_profile": {"positive": 0.75, "negative": 0.05, "neutral": 0.20},
        "peak_day": 2,
        "lifecycle_preset": "高潮期"
    },
    {
        "title": "新型疫苗研发取得重大突破",
        "summary": "国内某生物医药企业宣布其研发的新型mRNA疫苗III期临床试验结果优异，保护效力达到国际领先水平，获批紧急使用。",
        "location": "江苏省苏州市",
        "cause": "该企业在国际学术期刊发表III期临床试验结果，数据显示疫苗安全性和有效性均表现优异。",
        "involved": "国家药监局、卫健委、研发企业、临床试验机构、WHO",
        "category": "健康",
        "risk_level": "低",
        "platform_weights": {"微博": 0.20, "知乎": 0.25, "今日头条": 0.25, "丁香园": 0.15, "微信公众号": 0.15},
        "sentiment_profile": {"positive": 0.60, "negative": 0.08, "neutral": 0.32},
        "peak_day": 1,
        "lifecycle_preset": "成长期"
    },
    {
        "title": "某知名电商平台数据泄露事件",
        "summary": "安全研究人员发现某头部电商平台存在严重数据安全漏洞，数千万用户的个人信息疑似遭到泄露。平台方已紧急修复漏洞并启动内部调查。",
        "location": "浙江省杭州市",
        "cause": "白帽黑客在漏洞众测平台提交了该电商平台的数据库访问控制漏洞报告，平台确认后紧急修复。",
        "involved": "电商平台、网信办、公安部、信息安全公司、受影响的用户",
        "category": "科技",
        "risk_level": "高",
        "platform_weights": {"微博": 0.30, "知乎": 0.25, "今日头条": 0.20, "安全焦点": 0.15, "微信公众号": 0.10},
        "sentiment_profile": {"positive": 0.10, "negative": 0.60, "neutral": 0.30},
        "peak_day": 3,
        "lifecycle_preset": "成长期"
    },
    {
        "title": "某省全面推进教育改革引发争论",
        "summary": "某省教育厅发布基础教育综合改革方案，涉及中考改革、课后服务、教师轮岗等多项重大调整。方案在教师和家长群体中引发激烈争议。",
        "location": "浙江省",
        "cause": "省教育厅在广泛调研基础上制定了《基础教育综合改革实施方案》，向社会公开征求意见。",
        "involved": "省教育厅、学校、教师工会、家长委员会、教育学者",
        "category": "教育",
        "risk_level": "中",
        "platform_weights": {"微信公众号": 0.30, "微博": 0.25, "知乎": 0.20, "今日头条": 0.15, "抖音": 0.10},
        "sentiment_profile": {"positive": 0.30, "negative": 0.35, "neutral": 0.35},
        "peak_day": 4,
        "lifecycle_preset": "潜伏期"
    }
]

# 平台搜索URL生成函数
def _generate_platform_url(platform_name, keyword=''):
    """根据平台名和关键词生成可用的搜索URL"""
    import urllib.parse
    kw = urllib.parse.quote(keyword or '')
    urls = {
        '微博': f'https://s.weibo.com/weibo?q={kw}',
        '今日头条': f'https://so.toutiao.com/search?keyword={kw}',
        '知乎': f'https://www.zhihu.com/search?type=content&q={kw}',
        '抖音': f'https://www.douyin.com/search/{kw}',
        '澎湃新闻': f'https://www.thepaper.cn/search?keyword={kw}',
        '央视新闻': f'https://search.cctv.com/search.php?qtext={kw}',
        '人民日报': f'https://www.people.com.cn/',
        '微信公众号': f'https://mp.weixin.qq.com/mp/search?search=1&query={kw}',
        '36氪': f'https://36kr.com/search/articles/{kw}',
        '虎嗅': f'https://www.huxiu.com/',
        'B站': f'https://search.bilibili.com/all?keyword={kw}',
        '小红书': f'https://www.xiaohongshu.com/search_result?keyword={kw}',
        '快手': f'https://www.kuaishou.com/search/video?searchKey={kw}',
        '豆瓣': f'https://www.douban.com/search?q={kw}',
        '百度贴吧': f'https://tieba.baidu.com/f?kw={kw}',
        '虎扑': f'https://bbs.hupu.com/',
        '丁香园': f'https://www.dxy.cn/',
        '雪球': f'https://xueqiu.com/',
    }
    return urls.get(platform_name, f'https://www.baidu.com/s?wd={kw}')


def _generate_report_content(template, platform, author, sentiment_bias=0):
    """生成单个报道内容"""
    titles_pool = [
        f"【关注】{template['title']}",
        f"最新进展：{template['title']}",
        f"深度分析：{template['title']}背后的真相",
        f"热议！{template['title']}引发全网讨论",
        f"{template['location']}发生重大事件：{template['title']}",
        f"专家解读：{template['title']}说明了什么？",
        f"持续关注：{template['title']}最新后续来了",
        f"独家：{template['title']}内幕揭秘",
    ]

    positive_snippets = [
        "这件事反映出相关部门反应迅速、处置得当，值得点赞。",
        "从目前情况来看，事态正在向好的方向发展。",
        "社会各界积极响应，展现了良好的互助精神。",
        "相关部门的及时回应有效遏制了谣言的传播。",
    ]

    negative_snippets = [
        "此事暴露出相关管理制度仍然存在较大漏洞。",
        "当事人/机构的态度令人失望，缺乏基本的社会责任感。",
        "类似事件一再发生，说明深层次问题并未得到解决。",
        "希望有关部门能真正重视起来，而不是走过场。",
    ]

    neutral_snippets = [
        "我们将持续关注此事的后续发展。",
        "目前各方信息仍在核实中，建议保持理性关注。",
        "事件仍在发展中，相关信息有待进一步确认。",
        f"截止目前，已有大量网友对此事发表看法。",
    ]

    # 根据情感倾向选择片段
    snippets = []
    if sentiment_bias > 0.2:
        snippets = random.sample(positive_snippets, min(2, len(positive_snippets)))
        snippets += random.sample(neutral_snippets, 1)
    elif sentiment_bias < -0.2:
        snippets = random.sample(negative_snippets, min(2, len(negative_snippets)))
        snippets += random.sample(neutral_snippets, 1)
    else:
        snippets = random.sample(neutral_snippets, min(2, len(neutral_snippets)))
        snippets += random.sample(positive_snippets + negative_snippets, 1)

    title = random.choice(titles_pool)
    content = f"{template['summary']}\n\n"
    content += f"事件发生地点：{template['location']}。"
    content += f"涉及方：{template['involved']}。\n\n"
    content += ' '.join(snippets)
    content += f"\n\n（来源：{platform} 作者：{author}）"

    return title, content


def _generate_propagation_data(template, reports):
    """生成传播溯源数据"""
    trace_data = {
        "initial_source": {
            "platform": random.choice(["微博", "抖音", "快手", "微信公众号"]),
            "author": random.choice(["普通网友爆料", "当事人发布", "现场群众拍摄", "匿名投稿"]),
            "time": (datetime.utcnow() - timedelta(hours=random.randint(24, 72))).isoformat(),
            "description": f"事件最早由网友在社交平台发布，随后被其他用户广泛转发"
        },
        "key_nodes": [
            {
                "type": "big_v",
                "platform": "微博",
                "author": random.choice(["财经大V", "社会评论员", "知名博主", "行业专家"]),
                "followers": random.randint(100000, 5000000),
                "time": (datetime.utcnow() - timedelta(hours=random.randint(12, 48))).isoformat(),
                "description": "大V转发后讨论量激增，话题迅速升温"
            },
            {
                "type": "official_media",
                "platform": random.choice(["人民日报", "央视新闻", "澎湃新闻", "新华社"]),
                "author": "官方媒体",
                "time": (datetime.utcnow() - timedelta(hours=random.randint(6, 24))).isoformat(),
                "description": "主流媒体跟进报道，事件进入公众视野"
            },
        ]
    }
    return json.dumps(trace_data, ensure_ascii=False)


def generate_sentiment_scores(template, bias=0):
    """生成带偏移的情感得分"""
    profile = template['sentiment_profile']
    base = random.random() * 0.4 - 0.2 + bias  # -0.2 到 0.2 基础
    if random.random() < profile['positive']:
        return round(0.5 + random.random() * 0.5, 2)  # 0.5-1.0
    elif random.random() < profile['positive'] + profile['negative']:
        return round(-0.5 - random.random() * 0.5, 2)  # -1.0--0.5
    else:
        return round(random.random() * 0.4 - 0.2, 2)  # -0.2-0.2


def init_demo_data(app):
    """初始化演示数据"""
    from models import User, Event, EventReport, EventTrend, EventKeyword
    from nlp.sentiment import analyze_sentiment, aggregate_sentiment
    from nlp.segmentation import extract_keywords
    from nlp.fake_detect import detect_fake_news

    with app.app_context():
        # 检查是否已有数据
        if User.query.first() is not None:
            print("[Demo] 数据库已有数据，跳过初始化")
            return

        print("[Demo] 开始初始化演示数据...")

        # ==================== 创建演示用户 ====================
        demo_user = User(username='admin', email='admin@opinion.com')
        demo_user.set_password('admin123')
        db.session.add(demo_user)

        demo_user2 = User(username='analyst', email='analyst@opinion.com')
        demo_user2.set_password('analyst123')
        db.session.add(demo_user2)
        db.session.flush()

        # ==================== 创建默认监控源 ====================
        default_sources = [
            MonitoredSource(user_id=demo_user.id, platform_name='微博热搜',
                            platform_url='https://weibo.com/top/summary',
                            source_type='social'),
            MonitoredSource(user_id=demo_user.id, platform_name='百度热搜',
                            platform_url='https://top.baidu.com/board',
                            source_type='news'),
            MonitoredSource(user_id=demo_user.id, platform_name='知乎热榜',
                            platform_url='https://www.zhihu.com/hot',
                            source_type='social'),
            MonitoredSource(user_id=demo_user.id, platform_name='今日头条',
                            platform_url='https://www.toutiao.com',
                            source_type='news'),
        ]
        for s in default_sources:
            db.session.add(s)

        # ==================== 创建默认关键词 ====================
        default_keywords = [
            MonitoredKeyword(user_id=demo_user.id, keyword='食品安全', category='社会'),
            MonitoredKeyword(user_id=demo_user.id, keyword='AI', category='科技'),
            MonitoredKeyword(user_id=demo_user.id, keyword='数据安全', category='科技'),
            MonitoredKeyword(user_id=demo_user.id, keyword='自然灾害', category='社会'),
            MonitoredKeyword(user_id=demo_user.id, keyword='教育', category='教育'),
            MonitoredKeyword(user_id=demo_user.id, keyword='楼市', category='财经'),
            MonitoredKeyword(user_id=demo_user.id, keyword='疫苗', category='健康'),
        ]
        for k in default_keywords:
            db.session.add(k)
        db.session.flush()

        # ==================== 创建事件和报道数据 ====================
        now = datetime.utcnow()
        event_ids = []

        for t_idx, template in enumerate(EVENT_TEMPLATES):
            # 创建事件
            peak_day = template['peak_day']
            event_time = now - timedelta(days=random.randint(3, 14))

            event = Event(
                title=template['title'],
                summary=template['summary'],
                event_time=event_time,
                location=template['location'],
                cause=template['cause'],
                involved=template['involved'],
                heat_index=round(random.uniform(60, 99), 2),
                category=template['category'],
                lifecycle_stage=template['lifecycle_preset'],
                risk_level=template['risk_level'],
                report_count=0,
                positive_ratio=template['sentiment_profile']['positive'],
                negative_ratio=template['sentiment_profile']['negative'],
                neutral_ratio=template['sentiment_profile']['neutral'],
            )
            db.session.add(event)
            db.session.flush()
            event_ids.append(event.id)

            # 为事件创建报道（20-35篇）
            num_reports = random.randint(20, 35)
            # 按平台权重分配报道
            platforms = list(template.get('platform_weights', {}).keys())
            platform_weights = list(template.get('platform_weights', {}).values())
            if not platforms:
                platforms = [p['name'] for p in random.sample(PLATFORMS, 5)]
                platform_weights = [1.0 / len(platforms)] * len(platforms)

            # 归一化权重
            total_w = sum(platform_weights)
            platform_weights = [w / total_w for w in platform_weights]

            reports_data = []
            sentiments_results = []

            for r_idx in range(num_reports):
                # 按权重选择平台
                plat_idx = random.choices(range(len(platforms)), weights=platform_weights, k=1)[0]
                platform_name = platforms[plat_idx]

                # 时间分布：按照事件生命周期曲线
                days_ago = random.randint(0, 10)
                hours_ago = random.randint(0, 23)
                report_time = now - timedelta(days=days_ago, hours=hours_ago)

                # 生成情感得分
                sentiment_score = generate_sentiment_scores(template)

                # 生成报道内容
                title, content = _generate_report_content(
                    template, platform_name,
                    f"{random.choice(['资深记者', '特约评论员', '媒体编辑', '热心网友'])}-{chr(65+r_idx)}",
                    sentiment_score
                )

                # 对报道进行情感分析
                sent_result = analyze_sentiment(content)
                sentiments_results.append(sent_result)

                # 虚假检测
                fake_result = detect_fake_news(content, '', platform_name)

                # 设置关键节点
                is_key = r_idx < 3 or random.random() < 0.15
                node_type = ''
                if r_idx == 0:
                    node_type = 'origin'
                elif r_idx == 1 and random.random() > 0.5:
                    node_type = 'vip_repost'
                elif r_idx == 2 and random.random() > 0.5:
                    node_type = 'official'

                report = EventReport(
                    event_id=event.id,
                    title=title,
                    content=content,
                    source_url=_generate_platform_url(platform_name, title),
                    platform=platform_name,
                    publish_time=report_time,
                    author=f"{random.choice(['资深记者', '特约评论员', '媒体编辑', '热心网友'])}-{chr(65+r_idx)}",
                    sentiment_score=sentiment_score,
                    is_original=(r_idx == 0),
                    is_key_node=is_key,
                    node_type=node_type
                )
                db.session.add(report)
                reports_data.append({
                    'title': title,
                    'content': content,
                    'publish_time': report_time,
                    'sentiment_score': sentiment_score,
                    'platform': platform_name
                })

            # 汇总情感分析
            agg_sentiment = aggregate_sentiment(sentiments_results)
            event.positive_ratio = agg_sentiment['positive']
            event.negative_ratio = agg_sentiment['negative']
            event.neutral_ratio = agg_sentiment['neutral']
            event.report_count = num_reports

            # 生成传播溯源数据
            event.source_trace = _generate_propagation_data(template, reports_data)

            # 计算热度指数
            from nlp.clustering import compute_heat_index
            heat = compute_heat_index(reports_data, 7, 0.9)
            event.heat_index = round(heat * 10 + random.uniform(30, 70), 2)
            if event.heat_index > 99:
                event.heat_index = round(random.uniform(85, 99), 2)

            # 虚假检测评分
            fake_scores = []
            for r in reports_data:
                result = detect_fake_news(r['content'], '', r['platform'])
                fake_scores.append(result['fake_probability'])
            event.fake_news_score = round(sum(fake_scores) / len(fake_scores), 2) if fake_scores else 0.1

            # ==================== 创建趋势数据 ====================
            for day_offset in range(10, -1, -1):
                trend_date = (now - timedelta(days=day_offset)).date()

                # 模拟生命周期曲线
                days_since_start = 10 - day_offset
                if days_since_start <= 1:
                    count = random.randint(0, 3)
                elif days_since_start <= peak_day:
                    count = random.randint(3, 15)
                elif days_since_start == peak_day + 1:
                    count = random.randint(15, 25)
                elif days_since_start <= peak_day + 3:
                    count = random.randint(8, 18)
                else:
                    count = random.randint(1, 8)

                # 按情感比例分配
                pos_c = int(count * event.positive_ratio)
                neg_c = int(count * event.negative_ratio)
                neu_c = max(0, count - pos_c - neg_c)

                key_node = ''
                if days_since_start == 0:
                    key_node = '事件首次被报道'
                elif days_since_start == peak_day:
                    key_node = '官方媒体介入报道'
                elif days_since_start == peak_day + 1:
                    key_node = '多位大V转发讨论'

                trend = EventTrend(
                    event_id=event.id,
                    date=trend_date,
                    report_count=count,
                    key_node=key_node,
                    positive_count=pos_c,
                    negative_count=neg_c,
                    neutral_count=neu_c
                )
                db.session.add(trend)

            # ==================== 提取关键词 ====================
            # 合并所有报道内容
            all_content = ' '.join([r['content'] for r in reports_data])
            keywords = extract_keywords(all_content, topk=20)

            for kw in keywords:
                event_keyword = EventKeyword(
                    event_id=event.id,
                    keyword=kw['keyword'],
                    weight=kw['weight']
                )
                db.session.add(event_keyword)

        db.session.commit()
        print(f"[Demo] 演示数据初始化完成! 创建了 {len(EVENT_TEMPLATES)} 个事件, "
              f"用户: admin/admin123, analyst/analyst123")


if __name__ == '__main__':
    from app import create_app
    app = create_app()
    print("数据初始化完成!")
