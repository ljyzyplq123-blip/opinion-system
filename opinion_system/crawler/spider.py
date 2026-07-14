"""
网页爬虫核心模块 v2.0
- 支持各平台 Cookie/Token 认证
- 真实 API 调用 + HTML 解析双模式
- 自动 fallback 到模拟数据
"""
import requests
from bs4 import BeautifulSoup
import re
import json
import time
import hashlib
import random
from datetime import datetime

from .crawler_config import load_config


class BaseCrawler:
    """爬虫基类 — 支持 Cookie 认证"""

    def __init__(self, platform_key, config=None):
        self.platform_key = platform_key
        self.config = config or load_config()
        self.platform_cfg = self.config.get(platform_key, {})
        self.global_cfg = self.config.get('global', {})
        self.proxy_cfg = self.config.get('proxy', {})

        self.session = requests.Session()

        # 请求头
        default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
        }
        # 合并平台自定义 headers
        platform_headers = self.platform_cfg.get('headers', {})
        default_headers.update(platform_headers)
        self.session.headers.update(default_headers)

        # Cookie
        cookies = self.platform_cfg.get('cookies', {})
        # 过滤空值
        valid_cookies = {k: v for k, v in cookies.items() if v}
        if valid_cookies:
            for key, value in valid_cookies.items():
                self.session.cookies.set(key, value)

        # 代理
        if self.proxy_cfg.get('enabled'):
            proxies = {}
            if self.proxy_cfg.get('http'):
                proxies['http'] = self.proxy_cfg['http']
            if self.proxy_cfg.get('https'):
                proxies['https'] = self.proxy_cfg['https']
            if proxies:
                self.session.proxies.update(proxies)

        # 请求参数
        self.timeout = self.global_cfg.get('timeout', 15)
        self.max_retries = self.global_cfg.get('max_retries', 3)
        self.request_delay = self.global_cfg.get('request_delay', 2.0)

    def _request(self, url, method='GET', **kwargs):
        """带重试的请求"""
        for attempt in range(self.max_retries):
            try:
                if method == 'GET':
                    resp = self.session.get(
                        url, timeout=self.timeout + attempt * 5, **kwargs
                    )
                else:
                    resp = self.session.post(
                        url, timeout=self.timeout + attempt * 5, **kwargs
                    )

                if resp.status_code == 200:
                    return resp
                elif resp.status_code == 403:
                    print(f"[{self.platform_key}] 403 被拦截，可能需要更新 Cookie")
                    return None
                elif resp.status_code == 429:
                    wait = (attempt + 1) * 5
                    print(f"[{self.platform_key}] 429 限流，等待 {wait}s...")
                    time.sleep(wait)
                else:
                    print(f"[{self.platform_key}] HTTP {resp.status_code}")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.request_delay)

            except requests.exceptions.Timeout:
                print(f"[{self.platform_key}] 请求超时 (尝试 {attempt+1}/{self.max_retries})")
            except requests.exceptions.ConnectionError:
                print(f"[{self.platform_key}] 连接失败 (尝试 {attempt+1}/{self.max_retries})")
            except Exception as e:
                print(f"[{self.platform_key}] 请求异常: {e}")

            if attempt < self.max_retries - 1:
                time.sleep(self.request_delay)

        return None

    def fetch_json(self, url, **kwargs):
        """获取 JSON 响应"""
        resp = self._request(url, **kwargs)
        if resp:
            try:
                resp.encoding = 'utf-8'
                return resp.json()
            except Exception as e:
                # 打印响应详情以便调试
                body_preview = resp.text[:200] if resp.text else '(empty body)'
                print(f"[{self.platform_key}] JSON解析失败: {e} | "
                      f"Content-Type={resp.headers.get('Content-Type', '?')} | "
                      f"body={body_preview}")
        return None

    def fetch_html(self, url, **kwargs):
        """获取并解析 HTML"""
        resp = self._request(url, **kwargs)
        if resp:
            try:
                resp.encoding = resp.apparent_encoding or 'utf-8'
                return BeautifulSoup(resp.text, 'lxml')
            except Exception as e:
                print(f"[{self.platform_key}] HTML 解析失败: {e}")
        return None

    @property
    def is_real_enabled(self):
        """是否启用真实爬取"""
        return (self.global_cfg.get('use_real_crawler', False) and
                self.platform_cfg.get('use_real', False) and
                self.platform_cfg.get('enabled', True))

    @property
    def has_auth(self):
        """是否有有效的认证信息"""
        cookies = self.platform_cfg.get('cookies', {})
        return any(v for v in cookies.values())


class WeiboHotCrawler(BaseCrawler):
    """微博热搜爬虫 — 支持 API + HTML 双模式"""

    def __init__(self, config=None):
        super().__init__('weibo', config)
        self.urls = self.platform_cfg.get('urls', {})

    def crawl(self):
        """获取微博热搜"""
        results = []

        # 方式1: 通过 API (需要有效的 SUB cookie)
        api_url = self.urls.get('api_hot_band',
                                 'https://weibo.com/ajax/side/hotSearch')
        data = self.fetch_json(api_url, headers={
            'Referer': 'https://weibo.com/',
            'X-Requested-With': 'XMLHttpRequest',
        })
        if data and 'data' in data:
            realtime = data['data'].get('realtime', [])
            for item in realtime[:50]:
                word = item.get('word', '')
                if word:
                    results.append({
                        'title': word.strip(),
                        'url': f"https://s.weibo.com/weibo?q={word}",
                        'platform': '微博',
                        'heat': str(item.get('num', '')),
                        'rank': item.get('rank', 0),
                        'category': item.get('category', ''),
                        'crawl_time': datetime.utcnow().isoformat(),
                        'content_id': hashlib.md5(word.encode()).hexdigest()[:12],
                        'is_real': True,
                    })
            if results:
                print(f"[Weibo] API获取 {len(results)} 条热搜")
                return results

        # 方式2: HTML 解析
        hot_url = self.urls.get('hot_search', 'https://s.weibo.com/top/summary')
        soup = self.fetch_html(hot_url)
        if soup:
            items = soup.select('tr')
            for item in items:
                try:
                    title_elem = item.select_one('.td-02 a')
                    if not title_elem:
                        continue
                    title = title_elem.get_text(strip=True)
                    url = 'https://s.weibo.com' + title_elem.get('href', '')
                    heat_elem = item.select_one('.td-02 span')
                    heat = heat_elem.get_text(strip=True) if heat_elem else ''

                    results.append({
                        'title': title,
                        'url': url,
                        'platform': '微博',
                        'heat': heat,
                        'crawl_time': datetime.utcnow().isoformat(),
                        'content_id': hashlib.md5(url.encode()).hexdigest()[:12],
                        'is_real': True,
                    })
                except Exception as e:
                    print(f"[Weibo] HTML解析条目失败: {e}")

        if results:
            print(f"[Weibo] HTML获取 {len(results)} 条热搜")
        return results


class BaiduHotCrawler(BaseCrawler):
    """百度热搜爬虫 — 优先使用 API"""

    def __init__(self, config=None):
        super().__init__('baidu', config)
        self.urls = self.platform_cfg.get('urls', {})

    def crawl(self):
        results = []

        hot_url = self.urls.get('hot_board',
                                 'https://top.baidu.com/board?tab=realtime')

        # 方式1: 从 HTML s-data 提取（数据最完整，含 hotScore/desc）
        resp = self._request(hot_url)
        if resp:
            match = re.search(r'<!--s-data:(.*?)-->', resp.text, re.DOTALL)
            if match:
                try:
                    sdata = json.loads(match.group(1))
                    cards = sdata.get('data', {}).get('cards', [])
                    for card in cards:
                        items = card.get('content', [])
                        # 兼容嵌套格式
                        if (len(items) == 1 and isinstance(items[0], dict)
                                and 'content' in items[0] and isinstance(items[0]['content'], list)):
                            items = items[0]['content']
                        for item in items[:30]:
                            word = item.get('word', '') or item.get('query', '')
                            if word:
                                results.append({
                                    'title': word.strip(),
                                    'url': item.get('appUrl', '') or item.get('url', '') or f"https://www.baidu.com/s?wd={word}",
                                    'platform': '百度热搜',
                                    'heat': str(item.get('hotScore', '')),
                                    'rank': item.get('index', ''),
                                    'desc': item.get('desc', ''),
                                    'crawl_time': datetime.utcnow().isoformat(),
                                    'content_id': hashlib.md5(word.encode()).hexdigest()[:12],
                                    'is_real': True,
                                })
                    if results:
                        print(f"[Baidu] s-data获取 {len(results)} 条热搜")
                        return results
                except Exception as e:
                    print(f"[Baidu] s-data解析失败: {e}")

        # 方式2: API fallback
        api_url = self.urls.get('api_board',
                                 'https://top.baidu.com/api/board?platform=wise&tab=realtime')
        data = self.fetch_json(api_url, headers={
            'Referer': 'https://top.baidu.com/',
        })
        if data and 'data' in data:
            cards = data['data'].get('cards', [])
            for card in cards:
                items = card.get('content', [])
                if (len(items) == 1 and isinstance(items[0], dict)
                        and 'content' in items[0] and isinstance(items[0]['content'], list)):
                    items = items[0]['content']
                for item in items[:30]:
                    word = item.get('word', '') or item.get('query', '')
                    if word:
                        results.append({
                            'title': word.strip(),
                            'url': item.get('url', '') or f"https://www.baidu.com/s?wd={word}",
                            'platform': '百度热搜',
                            'heat': str(item.get('hotScore', '')),
                            'rank': item.get('index', ''),
                            'desc': item.get('desc', ''),
                            'crawl_time': datetime.utcnow().isoformat(),
                            'content_id': hashlib.md5(word.encode()).hexdigest()[:12],
                            'is_real': True,
                        })
            if results:
                print(f"[Baidu] API获取 {len(results)} 条热搜")
                return results

        # 方式3: HTML CSS选择器解析
        soup = self.fetch_html(hot_url)
        if soup:
            items = soup.select('.category-wrap_iQLoo')
            if not items:
                items = soup.select('[class*="category-wrap"]')
            for item in items:
                try:
                    title_elem = item.select_one('.c-single-text-ellipsis')
                    if not title_elem:
                        title_elem = item.select_one('[class*="text-ellipsis"]') or item.select_one('a')
                    if not title_elem:
                        continue
                    title = title_elem.get_text(strip=True)
                    heat_elem = item.select_one('.hot-index_1Bl1a') or item.select_one('[class*="hot-index"]')
                    heat = heat_elem.get_text(strip=True) if heat_elem else ''
                    if title:
                        results.append({
                            'title': title,
                            'url': f"https://www.baidu.com/s?wd={title}",
                            'platform': '百度热搜',
                            'heat': heat,
                            'crawl_time': datetime.utcnow().isoformat(),
                            'content_id': hashlib.md5(title.encode()).hexdigest()[:12],
                            'is_real': True,
                        })
                except Exception as e:
                    print(f"[Baidu] HTML解析条目失败: {e}")

        if results:
            print(f"[Baidu] HTML获取 {len(results)} 条热搜")
        return results


class ZhihuHotCrawler(BaseCrawler):
    """知乎热榜爬虫 — API 需要 z_c0 token"""

    def __init__(self, config=None):
        super().__init__('zhihu', config)
        self.urls = self.platform_cfg.get('urls', {})

    def crawl(self):
        results = []

        # 方式1: API (需要 z_c0)
        api_url = self.urls.get('api_hot',
                                 'https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=50')
        data = self.fetch_json(api_url, headers={
            'Referer': 'https://www.zhihu.com/hot',
            'x-requested-with': 'fetch',
        })
        if data and 'data' in data:
            for item in data['data'][:50]:
                target = item.get('target', {})
                title = target.get('title', '')
                if title:
                    qid = target.get('id', '')
                    url = f"https://www.zhihu.com/question/{qid}" if qid else ''
                    # 新版API: 数据直接在 target 下，不再嵌套在 metrics 中
                    answer_count = target.get('answer_count', 0)
                    follower_count = target.get('follower_count', 0)
                    comment_count = target.get('comment_count', 0)
                    heat = str(target.get('detail_text', '') or item.get('detail_text', ''))
                    results.append({
                        'title': title.strip(),
                        'url': url,
                        'platform': '知乎',
                        'heat': heat,
                        'answer_count': answer_count,
                        'follower_count': follower_count,
                        'comment_count': comment_count,
                        'crawl_time': datetime.utcnow().isoformat(),
                        'content_id': hashlib.md5(title.encode()).hexdigest()[:12],
                        'is_real': True,
                    })
            if results:
                print(f"[Zhihu] API获取 {len(results)} 条热搜")
                return results

        # 方式2: HTML 解析 — 从 __INITIAL_STATE__ 提取
        hot_url = self.urls.get('hot_list', 'https://www.zhihu.com/hot')
        resp = self._request(hot_url)
        if resp:
            match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', resp.text, re.DOTALL)
            if match:
                try:
                    state = json.loads(match.group(1))
                    hot_list = state.get('topstory', {}).get('hotList', [])
                    for item in hot_list[:50]:
                        target = item.get('target', {})
                        title = target.get('title', '') or target.get('titleArea', {}).get('text', '')
                        if title:
                            qid = target.get('id', '')
                            url = f"https://www.zhihu.com/question/{qid}" if qid else ''
                            results.append({
                                'title': title.strip(),
                                'url': url,
                                'platform': '知乎',
                                'heat': str(item.get('detail_text', '')),
                                'answer_count': target.get('answer_count', 0),
                                'follower_count': target.get('follower_count', 0),
                                'crawl_time': datetime.utcnow().isoformat(),
                                'content_id': hashlib.md5(title.encode()).hexdigest()[:12],
                                'is_real': True,
                            })
                    if results:
                        print(f"[Zhihu] HTML __INITIAL_STATE__ 获取 {len(results)} 条热搜")
                        return results
                except Exception as e:
                    print(f"[Zhihu] __INITIAL_STATE__ 解析失败: {e}")

        # 方式3: HTML CSS选择器解析
        soup = self.fetch_html(hot_url)
        if soup:
            items = soup.select('.HotItem')
            if not items:
                items = soup.select('[class*="HotItem"]')
            for item in items:
                try:
                    title_elem = item.select_one('.HotItem-title')
                    if not title_elem:
                        title_elem = item.select_one('[class*="HotItem-title"]') or item.select_one('h2 a')
                    if not title_elem:
                        continue
                    title = title_elem.get_text(strip=True)
                    url = item.select_one('a')
                    href = url.get('href', '') if url else ''
                    if href and not href.startswith('http'):
                        href = 'https://www.zhihu.com' + href
                    metrics_elem = item.select_one('.HotItem-metrics')
                    metrics = metrics_elem.get_text(strip=True) if metrics_elem else ''

                    results.append({
                        'title': title,
                        'url': href,
                        'platform': '知乎',
                        'heat': metrics,
                        'crawl_time': datetime.utcnow().isoformat(),
                        'content_id': hashlib.md5(title.encode()).hexdigest()[:12],
                        'is_real': True,
                    })
                except Exception as e:
                    print(f"[Zhihu] HTML解析条目失败: {e}")

        if results:
            print(f"[Zhihu] HTML获取 {len(results)} 条热搜")
        return results


class ToutiaoHotCrawler(BaseCrawler):
    """今日头条热点爬虫"""

    def __init__(self, config=None):
        super().__init__('toutiao', config)
        self.urls = self.platform_cfg.get('urls', {})

    def crawl(self):
        results = []

        # 方式1: 直接请求JSON API (接口已改为返回纯JSON)
        api_url = self.urls.get('api_hot',
                                 'https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc')
        data = self.fetch_json(api_url, headers={
            'Referer': 'https://www.toutiao.com/',
        })
        if data and 'data' in data and isinstance(data['data'], list):
            for item in data['data'][:50]:
                title = item.get('Title', '') or item.get('title', '')
                if title:
                    cluster_id = item.get('ClusterId', '') or item.get('ClusterIdStr', '')
                    results.append({
                        'title': title.strip(),
                        'url': item.get('Url', '') or f"https://www.toutiao.com/trending/{cluster_id}",
                        'platform': '今日头条',
                        'heat': str(item.get('HotValue', '')),
                        'label': item.get('Label', ''),
                        'label_desc': item.get('LabelDesc', ''),
                        'crawl_time': datetime.utcnow().isoformat(),
                        'content_id': hashlib.md5(title.encode()).hexdigest()[:12],
                        'is_real': True,
                    })
            if results:
                print(f"[Toutiao] JSON API获取 {len(results)} 条热搜")
                return results

        # 方式2: HTML fallback（尝试从SSR数据提取）
        resp = self._request(api_url)
        if resp:
            text = resp.text
            # 尝试 SSR hydrated data
            match = re.search(r'window\._SSR_HYDRATED_DATA\s*=\s*({.+?});?\s*</script>',
                              text, re.DOTALL)
            if match:
                try:
                    raw = match.group(1).rstrip(';').strip()
                    jdata = json.loads(raw)
                    board = _find_key(jdata, 'hotBoard')
                    if board:
                        for item in board[:50]:
                            title = item.get('Title', '') or item.get('title', '')
                            if title:
                                results.append({
                                    'title': title.strip(),
                                    'url': f"https://www.toutiao.com/trending/{item.get('ClusterId', '')}",
                                    'platform': '今日头条',
                                    'heat': str(item.get('HotValue', '')),
                                    'crawl_time': datetime.utcnow().isoformat(),
                                    'content_id': hashlib.md5(title.encode()).hexdigest()[:12],
                                    'is_real': True,
                                })
                        if results:
                            print(f"[Toutiao] SSR数据获取 {len(results)} 条热搜")
                            return results
                except Exception as e:
                    print(f"[Toutiao] SSR解析失败: {e}")

            # 尝试直接匹配JSON数据
            json_match = re.search(r'\{[^}]*"ClusterId"[^}]*\}', text)
            if json_match:
                try:
                    # 找数组
                    arr_match = re.search(r'\{"data":\s*(\[.*?\])\s*[,}]', text, re.DOTALL)
                    if arr_match:
                        arr_data = json.loads(arr_match.group(1))
                        for item in arr_data[:50]:
                            title = item.get('Title', '') or item.get('title', '')
                            if title:
                                results.append({
                                    'title': title.strip(),
                                    'url': item.get('Url', '') or f"https://www.toutiao.com/trending/{item.get('ClusterId', '')}",
                                    'platform': '今日头条',
                                    'heat': str(item.get('HotValue', '')),
                                    'crawl_time': datetime.utcnow().isoformat(),
                                    'content_id': hashlib.md5(title.encode()).hexdigest()[:12],
                                    'is_real': True,
                                })
                        if results:
                            print(f"[Toutiao] JSON正则提取 {len(results)} 条热搜")
                            return results
                except Exception as e:
                    print(f"[Toutiao] JSON正则解析失败: {e}")

        return results


class BilibiliPopularCrawler(BaseCrawler):
    """B站热门爬虫 — API 调用"""

    def __init__(self, config=None):
        super().__init__('bilibili', config)
        self.urls = self.platform_cfg.get('urls', {})

    def crawl(self):
        results = []
        api_url = self.urls.get('popular',
                                 'https://api.bilibili.com/x/web-interface/popular?ps=50&pn=1')
        data = self.fetch_json(api_url, headers={
            'Referer': 'https://www.bilibili.com/',
        })
        if data and data.get('code') == 0:
            for item in data['data'].get('list', [])[:50]:
                title = item.get('title', '')
                if title:
                    results.append({
                        'title': title.strip(),
                        'url': f"https://www.bilibili.com/video/{item.get('bvid', '')}",
                        'platform': 'B站',
                        'heat': str(item.get('stat', {}).get('view', '')),
                        'crawl_time': datetime.utcnow().isoformat(),
                        'content_id': hashlib.md5(title.encode()).hexdigest()[:12],
                        'is_real': True,
                    })
            if results:
                print(f"[Bilibili] 获取 {len(results)} 条热门")
        return results


def _find_key(obj, key):
    """递归查找 JSON 中的指定 key"""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            result = _find_key(v, key)
            if result is not None:
                return result
    elif isinstance(obj, list):
        for item in obj:
            result = _find_key(item, key)
            if result is not None:
                return result
    return None


# ============================================================
# 爬虫管理器
# ============================================================

class CrawlerManager:
    """
    爬虫管理器
    - 始终使用真实爬取（本系统仅支持真实数据）
    - 爬取平台从用户监控平台配置（MonitoredSource）动态读取
    - 结果去重合并
    """

    # 注册的爬虫：key → (CrawlerClass, 配置显示名, 爬虫输出平台名)
    CRAWLER_REGISTRY = {
        'weibo': (WeiboHotCrawler, '微博热搜', '微博'),
        'baidu': (BaiduHotCrawler, '百度热搜', '百度热搜'),
        'zhihu': (ZhihuHotCrawler, '知乎热榜', '知乎'),
        'toutiao': (ToutiaoHotCrawler, '今日头条', '今日头条'),
        'bilibili': (BilibiliPopularCrawler, 'B站热门', 'B站'),
    }

    # 监控平台名称 → 爬虫 key 的映射（用于匹配 MonitoredSource）
    PLATFORM_NAME_MAP = {
        '微博热搜': 'weibo',
        '微博': 'weibo',
        '百度热搜': 'baidu',
        '百度': 'baidu',
        '知乎热榜': 'zhihu',
        '知乎': 'zhihu',
        '今日头条': 'toutiao',
        '头条': 'toutiao',
        'B站热门': 'bilibili',
        'B站': 'bilibili',
        'bilibili': 'bilibili',
    }

    def get_crawler_output_names(self):
        """获取所有活跃监控平台对应的爬虫输出名称（用于跨平台传播）"""
        keys, _ = self._resolve_platforms()
        return [self.CRAWLER_REGISTRY[k][2] for k in keys]

    def __init__(self, config=None):
        self.config = config or load_config()
        self.global_cfg = self.config.get('global', {})

    def _resolve_platforms(self, platform_names=None):
        """
        将平台名称列表解析为爬虫 key 列表。
        如果未指定，从 MonitoredSource 读取所有活跃的监控平台。
        """
        if platform_names is None:
            try:
                from models import MonitoredSource
                sources = MonitoredSource.query.filter_by(is_active=True).all()
                platform_names = list(set(s.platform_name for s in sources))
            except Exception:
                # 数据库未就绪时回退到所有注册平台
                return list(self.CRAWLER_REGISTRY.keys()), [
                    info[2] for info in self.CRAWLER_REGISTRY.values()]

        keys = []
        names = []
        seen = set()
        for pname in platform_names:
            key = self.PLATFORM_NAME_MAP.get(pname)
            if key and key not in seen:
                keys.append(key)
                names.append(self.CRAWLER_REGISTRY[key][2])  # 爬虫输出平台名
                seen.add(key)
        return keys, names

    def crawl_all(self, platform_names=None):
        """爬取监控平台配置中的平台（仅真实数据）"""
        all_results = []

        keys, names = self._resolve_platforms(platform_names)
        if not keys:
            print("[Manager] 没有匹配到任何可爬取的监控平台")
            return []

        for key in keys:
            platform_cfg = self.config.get(key, {})
            if not platform_cfg.get('enabled', True):
                print(f"[Manager] 跳过未启用的平台: {key}")
                continue

            results = self._crawl_platform(key)
            if results:
                all_results.extend(results)

            # 请求间隔
            delay = self.global_cfg.get('request_delay', 2.0)
            if delay > 0:
                time.sleep(delay * random.uniform(0.5, 1.5))

        # 去重
        unique = self._deduplicate(all_results)
        print(f"[Manager] 总计: {len(unique)} 条去重后数据 (原始: {len(all_results)})")
        return unique

    def get_monitored_platform_names(self):
        """获取当前活跃的监控平台名称列表（用于跨平台传播模拟）"""
        try:
            from models import MonitoredSource
            sources = MonitoredSource.query.filter_by(is_active=True).all()
            return list(set(s.platform_name for s in sources))
        except Exception:
            return [info[1] for info in self.CRAWLER_REGISTRY.values()]

    def _crawl_platform(self, key):
        """爬取单个平台（始终真实爬取）"""
        cls, display_name, output_name = self.CRAWLER_REGISTRY[key]
        platform_cfg = self.config.get(key, {})

        print(f"[Manager] 真实爬取: {display_name}")
        try:
            crawler = cls(self.config)
            results = crawler.crawl()
            if results:
                return results
            print(f"[Manager] {display_name} 真实爬取返回空（请检查Cookie配置）")
        except Exception as e:
            print(f"[Manager] {display_name} 真实爬取异常: {e}")

        return []

    def _deduplicate(self, results):
        """去重"""
        seen = set()
        unique = []
        for r in results:
            cid = r.get('content_id', '')
            if cid not in seen:
                seen.add(cid)
                unique.append(r)
        return unique

    def get_auth_status(self):
        """获取各平台认证状态"""
        status = {}
        for key, (cls, display_name, output_name) in self.CRAWLER_REGISTRY.items():
            platform_cfg = self.config.get(key, {})
            cookies = platform_cfg.get('cookies', {})
            has_auth = any(v for v in cookies.values())

            status[key] = {
                'name': display_name,
                'enabled': platform_cfg.get('enabled', True),
                'has_auth': has_auth,
                'auth_fields': [k for k, v in cookies.items() if v],
            }
        return status
