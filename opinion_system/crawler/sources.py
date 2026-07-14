"""
新闻源配置
定义主流新闻网站和社交平台的爬取配置
"""

# 新闻源配置列表
NEWS_SOURCES = [
    {
        'name': '微博热搜',
        'url': 'https://s.weibo.com/top/summary',
        'type': 'social',
        'enabled': True,
        'weight': 0.40,
        'description': '新浪微博实时热搜榜',
        'crawler_class': 'WeiboHotCrawler',
    },
    {
        'name': '百度热搜',
        'url': 'https://top.baidu.com/board?tab=realtime',
        'type': 'news',
        'enabled': True,
        'weight': 0.35,
        'description': '百度实时热搜',
        'crawler_class': 'BaiduHotCrawler',
    },
    {
        'name': '知乎热榜',
        'url': 'https://www.zhihu.com/hot',
        'type': 'social',
        'enabled': True,
        'weight': 0.25,
        'description': '知乎社区热榜',
        'crawler_class': 'ZhihuHotCrawler',
    },
    {
        'name': '今日头条',
        'url': 'https://www.toutiao.com',
        'type': 'news',
        'enabled': True,
        'weight': 0.30,
        'description': '今日头条推荐频道',
        'crawler_class': 'ToutiaoCrawler',
    },
    {
        'name': '澎湃新闻',
        'url': 'https://www.thepaper.cn',
        'type': 'news',
        'enabled': True,
        'weight': 0.30,
        'description': '澎湃新闻热点',
        'crawler_class': 'NewsCrawler',
    },
    {
        'name': '抖音热点',
        'url': 'https://www.douyin.com',
        'type': 'social',
        'enabled': False,
        'weight': 0.35,
        'description': '抖音热门话题',
        'crawler_class': 'DouyinCrawler',
    },
    {
        'name': 'B站热门',
        'url': 'https://www.bilibili.com/v/popular/all',
        'type': 'social',
        'enabled': False,
        'weight': 0.20,
        'description': 'B站热门视频',
        'crawler_class': 'BilibiliCrawler',
    },
    {
        'name': '央视新闻',
        'url': 'https://news.cctv.com',
        'type': 'news',
        'enabled': True,
        'weight': 0.50,
        'description': '央视网新闻频道',
        'crawler_class': 'NewsCrawler',
    },
    {
        'name': '36氪',
        'url': 'https://36kr.com',
        'type': 'news',
        'enabled': True,
        'weight': 0.15,
        'description': '36氪科技资讯',
        'crawler_class': 'NewsCrawler',
    },
    {
        'name': '快手',
        'url': 'https://www.kuaishou.com',
        'type': 'social',
        'enabled': False,
        'weight': 0.25,
        'description': '快手热门',
        'crawler_class': 'KuaishouCrawler',
    },
]


def get_enabled_sources():
    """获取已启用的新闻源"""
    return [s for s in NEWS_SOURCES if s['enabled']]


def get_sources_by_type(source_type):
    """按类型获取新闻源"""
    return [s for s in NEWS_SOURCES if s['type'] == source_type]


def get_source_names():
    """获取所有新闻源名称"""
    return [s['name'] for s in NEWS_SOURCES]
