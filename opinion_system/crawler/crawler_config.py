"""
爬虫认证配置文件
配置各平台的 Cookie、Token 等认证信息

使用方法:
1. 浏览器登录对应平台
2. F12 → Application → Cookies 复制需要的字段
3. 填入下方对应字段
4. 将 use_real 改为 true
"""
import json
import os

# 配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'crawler_config.json')

# 默认配置
DEFAULT_CONFIG = {
    # ============================================
    # 全局设置
    # ============================================
    "global": {
        "use_real_crawler": False,        # 总开关: 是否使用真实爬虫
        "fallback_to_simulated": True,    # 真实爬取失败时是否回退到模拟数据
        "request_delay": 2.0,             # 请求间隔(秒), 防止被封
        "max_retries": 3,                 # 最大重试次数
        "timeout": 15,                    # 请求超时(秒)
    },

    # ============================================
    # 微博热搜 (s.weibo.com)
    # 需要登录微博后获取 Cookie
    # ============================================
    "weibo": {
        "enabled": True,
        "use_real": False,               # 改为 true 启用真实爬取
        "cookies": {
            "SUB": "",                   # 微博登录凭证 (必须)
            "SUBP": "",                  # 可选
            "SINAGLOBAL": "",            # 可选
            "_s_tentry": "weibo.com",
        },
        "headers": {
            "Referer": "https://s.weibo.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        },
        "urls": {
            "hot_search": "https://s.weibo.com/top/summary",
            "topic_detail": "https://s.weibo.com/weibo?q={keyword}",
            "api_hot_band": "https://weibo.com/ajax/side/hotSearch"
        },
    },

    # ============================================
    # 百度热搜 (top.baidu.com)
    # 大部分页面无需登录
    # ============================================
    "baidu": {
        "enabled": True,
        "use_real": False,
        "cookies": {
            "BAIDUID": "",               # 可选，登录后获取更稳定
            "BDUSS": "",                 # 可选
        },
        "headers": {
            "Referer": "https://top.baidu.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        },
        "urls": {
            "hot_board": "https://top.baidu.com/board?tab=realtime",
            "api_board": "https://top.baidu.com/api/board?platform=wise&tab=realtime",
        },
    },

    # ============================================
    # 知乎热榜 (zhihu.com)
    # 需要登录获取 z_c0 token
    # ============================================
    "zhihu": {
        "enabled": True,
        "use_real": False,
        "cookies": {
            "z_c0": "",                  # 知乎登录 Token (必须)
            "d_c0": "",                  # 可选
        },
        "headers": {
            "Referer": "https://www.zhihu.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        },
        "urls": {
            "hot_list": "https://www.zhihu.com/hot",
            "api_hot": "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=50",
        },
    },

    # ============================================
    # 今日头条 (toutiao.com)
    # ============================================
    "toutiao": {
        "enabled": True,
        "use_real": False,
        "cookies": {},
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.toutiao.com/",
        },
        "urls": {
            "hot": "https://www.toutiao.com/hot-event/hot-board/",
            "api_hot": "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc",
        },
    },

    # ============================================
    # 澎湃新闻 (thepaper.cn)
    # ============================================
    "thepaper": {
        "enabled": True,
        "use_real": False,
        "cookies": {},
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        },
        "urls": {
            "hot": "https://www.thepaper.cn/",
            "api_load_more": "https://api.thepaper.cn/content/loadMore",
        },
    },

    # ============================================
    # B站热门 (bilibili.com)
    # ============================================
    "bilibili": {
        "enabled": False,
        "use_real": False,
        "cookies": {
            "SESSDATA": "",              # B站登录凭证 (可选)
        },
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.bilibili.com/",
        },
        "urls": {
            "popular": "https://api.bilibili.com/x/web-interface/popular?ps=50&pn=1",
        },
    },

    # ============================================
    # 抖音 (douyin.com) - 通过第三方或API
    # ============================================
    "douyin": {
        "enabled": False,
        "use_real": False,
        "cookies": {},
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        },
        "urls": {
            "hot": "https://www.douyin.com/hot",
        },
    },

    # ============================================
    # 代理/VPN配置 (可选)
    # ============================================
    "proxy": {
        "enabled": False,
        "http": "",
        "https": "",
    },
}


def load_config():
    """加载爬虫配置"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                # 深度合并
                merged = _deep_merge(DEFAULT_CONFIG, user_config)
                return merged
        except Exception as e:
            print(f"[CrawlerConfig] 加载配置文件失败: {e}, 使用默认配置")
    else:
        # 首次运行，创建默认配置文件
        save_config(DEFAULT_CONFIG)
        print(f"[CrawlerConfig] 已创建配置文件: {CONFIG_FILE}")
        print(f"[CrawlerConfig] 请编辑此文件，填入各平台的 Cookie/Token 后启用真实爬取")

    return DEFAULT_CONFIG.copy()


def save_config(config):
    """保存配置到文件"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[CrawlerConfig] 保存配置失败: {e}")
        return False


def update_platform_cookies(platform, cookies_dict):
    """
    更新指定平台的Cookie
    示例: update_platform_cookies('weibo', {'SUB': '你的SUB值'})
    """
    config = load_config()
    if platform in config:
        config[platform]['cookies'].update(cookies_dict)
        save_config(config)
        print(f"[CrawlerConfig] 已更新 {platform} 的 Cookie")
        return True
    return False


def _deep_merge(base, override):
    """深度合并两个字典"""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
