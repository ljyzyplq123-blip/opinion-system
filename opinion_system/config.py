"""
系统配置文件
"""
import os
import json

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# 运行时LLM配置文件路径
LLM_CONFIG_FILE = os.path.join(BASE_DIR, 'llm_config.json')


def _load_llm_config():
    """从运行时配置文件加载LLM配置"""
    if os.path.exists(LLM_CONFIG_FILE):
        try:
            with open(LLM_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _get_llm_config(key, env_var, default):
    """按优先级获取LLM配置: 环境变量 > 运行时配置 > 默认值"""
    env_val = os.environ.get(env_var)
    if env_val:
        return env_val
    runtime = _load_llm_config()
    if key in runtime and runtime[key]:
        return runtime[key]
    return default


class Config:
    """基础配置"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'opinion-system-secret-key-2026'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(BASE_DIR, 'opinion.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    # 爬虫配置
    CRAWLER_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    CRAWLER_TIMEOUT = 10
    CRAWLER_MAX_PAGES = 50

    # NLP配置
    JIEBA_DICT_PATH = os.path.join(BASE_DIR, 'data', 'dict.txt')
    STOPWORDS_PATH = os.path.join(BASE_DIR, 'data', 'stopwords.txt')

    # 情感词典
    SENTIMENT_POS_PATH = os.path.join(BASE_DIR, 'data', 'positive_words.txt')
    SENTIMENT_NEG_PATH = os.path.join(BASE_DIR, 'data', 'negative_words.txt')

    # LLM配置 (优先级: 环境变量 > 运行时JSON配置 > 默认值)
    LLM_API_URL = _get_llm_config('api_url', 'LLM_API_URL',
                                  'https://api.deepseek.com/v1/chat/completions')
    LLM_API_KEY = _get_llm_config('api_key', 'LLM_API_KEY',
                                  'sk-your-deepseek-api-key')
    LLM_MODEL = _get_llm_config('model', 'LLM_MODEL', 'deepseek-chat')

    # 热点事件配置
    HOTSPOT_TIME_WINDOW_DAYS = 7
    HOTSPOT_MIN_REPORTS = 5
    HOTSPOT_DECAY_FACTOR = 0.9

    # 生命周期配置
    LIFECYCLE_GROWTH_THRESHOLD = 0.2
    LIFECYCLE_DECLINE_THRESHOLD = -0.1

    # 分页
    ITEMS_PER_PAGE = 20


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
