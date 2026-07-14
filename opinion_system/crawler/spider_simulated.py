"""
模拟爬虫 — 真实数据不可用时的 fallback
生成逼真的中文热点数据
"""
import hashlib
import random
from datetime import datetime


class SimulatedCrawler:
    """模拟爬虫"""

    SIMULATED_SOURCES = [
        {'name': '微博热搜', 'url': 'https://weibo.com', 'type': 'social'},
        {'name': '百度热搜', 'url': 'https://top.baidu.com', 'type': 'news'},
        {'name': '知乎热榜', 'url': 'https://www.zhihu.com', 'type': 'social'},
        {'name': '今日头条', 'url': 'https://www.toutiao.com', 'type': 'news'},
        {'name': '抖音热点', 'url': 'https://www.douyin.com', 'type': 'social'},
        {'name': '澎湃新闻', 'url': 'https://www.thepaper.cn', 'type': 'news'},
        {'name': '央视新闻', 'url': 'https://news.cctv.com', 'type': 'news'},
        {'name': 'B站热门', 'url': 'https://www.bilibili.com', 'type': 'social'},
    ]

    # 更丰富的模拟话题
    SIMULATED_TOPICS = [
        # 社会
        {"title": "多地发布高温红色预警", "cat": "社会", "desc": "多地气温突破40℃"},
        {"title": "某市地铁故障致大面积延误", "cat": "社会", "desc": "早高峰出行受阻"},
        {"title": "警方破获特大网络诈骗案", "cat": "社会", "desc": "涉案金额超5亿元"},
        {"title": "某地山体滑坡致道路中断", "cat": "社会", "desc": "无人员伤亡报告"},
        {"title": "快递新规实施首月效果显著", "cat": "社会", "desc": "送货上门率大幅提升"},
        # 科技
        {"title": "国产芯片取得重大突破", "cat": "科技", "desc": "良品率大幅提升"},
        {"title": "AI大模型通过图灵测试", "cat": "科技", "desc": "引发行业震动"},
        {"title": "6G研发进入关键阶段", "cat": "科技", "desc": "预计2030年商用"},
        {"title": "某手机品牌发布折叠屏新品", "cat": "科技", "desc": "售价创新低"},
        {"title": "量子计算商用化提速", "cat": "科技", "desc": "多领域应用落地"},
        # 财经
        {"title": "央行宣布降准释放流动性", "cat": "财经", "desc": "支持实体经济发展"},
        {"title": "A股成交额突破2万亿", "cat": "财经", "desc": "券商板块集体大涨"},
        {"title": "跨境电商出口额创新高", "cat": "财经", "desc": "同比增长35%"},
        {"title": "数字人民币试点扩围", "cat": "财经", "desc": "覆盖更多消费场景"},
        {"title": "新能源汽车渗透率超50%", "cat": "财经", "desc": "行业拐点已至"},
        # 娱乐
        {"title": "某热门电影票房破50亿", "cat": "娱乐", "desc": "观众口碑持续发酵"},
        {"title": "知名歌手宣布巡回演唱会", "cat": "娱乐", "desc": "票价引发粉丝热议"},
        {"title": "某综艺节目争议性淘汰", "cat": "娱乐", "desc": "评委决定引发不满"},
        {"title": "电竞中国队亚运夺金", "cat": "娱乐", "desc": "创造历史最佳战绩"},
        {"title": "某演员获国际电影节大奖", "cat": "娱乐", "desc": "为中国电影争光"},
        # 体育
        {"title": "中国女排世联赛夺冠", "cat": "体育", "desc": "3-0横扫对手"},
        {"title": "马拉松赛事报名人数破纪录", "cat": "体育", "desc": "全民健身热情高涨"},
        {"title": "NBA选秀中国球员入选", "cat": "体育", "desc": "首轮被选中"},
        # 健康
        {"title": "新型流感疫苗获批上市", "cat": "健康", "desc": "保护率超90%"},
        {"title": "中医药治疗获国际认可", "cat": "健康", "desc": "WHO推荐使用"},
        {"title": "青少年近视率首次下降", "cat": "健康", "desc": "双减政策效果显现"},
        # 教育
        {"title": "高考改革方案征求意见", "cat": "教育", "desc": "拟增加综合素质评价"},
        {"title": "考研报名人数出现下降", "cat": "教育", "desc": "就业导向更趋明显"},
        {"title": "职业教育法修订通过", "cat": "教育", "desc": "职教地位大幅提升"},
    ]

    def crawl_all(self):
        """模拟爬取所有数据源"""
        results = []
        for source in self.SIMULATED_SOURCES:
            items = self._generate_items(source)
            results.extend(items)
        return results

    def crawl_source(self, source_name):
        """模拟爬取特定数据源"""
        source = next(
            (s for s in self.SIMULATED_SOURCES if s['name'] == source_name),
            self.SIMULATED_SOURCES[0]
        )
        return self._generate_items(source)

    def _generate_items(self, source):
        """生成模拟爬取条目"""
        items = []
        num = random.randint(8, 20)
        used_topics = set()

        for i in range(num):
            # 选择未使用的话题
            available = [t for t in self.SIMULATED_TOPICS
                         if t['title'] not in used_topics]
            if not available:
                available = self.SIMULATED_TOPICS
            topic = random.choice(available)
            used_topics.add(topic['title'])

            heat = random.randint(100000, 9999999)
            items.append({
                'title': topic['title'],
                'url': f"{source['url']}/article/{random.randint(10000, 999999)}",
                'platform': source['name'],
                'source_type': source['type'],
                'category': topic['cat'],
                'desc': topic['desc'],
                'heat': f"{heat}",
                'comment_count': random.randint(100, 50000),
                'repost_count': random.randint(50, 10000),
                'crawl_time': datetime.utcnow().isoformat(),
                'content_id': hashlib.md5(
                    f"{source['name']}{topic['title']}{i}".encode()
                ).hexdigest()[:12],
                'content': self._generate_article_content(topic),
                'is_real': False,
            })

        return items

    def _generate_article_content(self, topic):
        """生成模拟文章内容"""
        paragraphs = [
            f"关于「{topic['title']}」的最新动态，引起了社会各界的广泛关注。",
            f"据相关部门透露，{topic['desc']}，这一消息迅速在网络上传播。",
            "业内专家对此发表了专业意见，认为这一发展具有重要意义。",
            "从数据上看，这一趋势在近期表现尤为明显。",
            "多位受访者表示，这将对行业未来产生深远影响。",
            f"{topic['cat']}领域的从业者纷纷表达了各自的观点和见解。",
            "社会各界对此反应不一，支持者和谨慎者各有其充分理由。",
            "业内人士指出，需要更多时间和数据来评估其长期影响。",
            "各大媒体对此进行了广泛报道，相关话题阅读量持续攀升。",
        ]
        return '\n'.join(random.sample(paragraphs, min(5, len(paragraphs))))
