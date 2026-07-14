"""
爬虫管理 API
- 查看认证状态
- 配置 Cookie/Token
- 手动触发爬取
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required

crawler_api_bp = Blueprint('crawler_api', __name__)


@crawler_api_bp.route('/crawler/status', methods=['GET'])
@login_required
def crawler_status():
    """获取各平台认证状态"""
    from crawler.spider import CrawlerManager
    manager = CrawlerManager()
    status = manager.get_auth_status()

    global_cfg = manager.config.get('global', {})

    return jsonify({
        'success': True,
        'global': {
            'use_real_crawler': global_cfg.get('use_real_crawler', False),
            'fallback_to_simulated': global_cfg.get('fallback_to_simulated', True),
        },
        'platforms': status,
    })


@crawler_api_bp.route('/crawler/config', methods=['GET'])
@login_required
def get_crawler_config():
    """获取完整爬虫配置（敏感信息已脱敏）"""
    from crawler.crawler_config import load_config
    config = load_config()

    # 脱敏处理
    safe_config = _sanitize_config(config)
    return jsonify({
        'success': True,
        'config': safe_config,
    })


@crawler_api_bp.route('/crawler/config', methods=['POST'])
@login_required
def update_crawler_config():
    """更新爬虫配置"""
    from crawler.crawler_config import load_config, save_config

    data = request.get_json() or {}
    platform = data.get('platform', '').strip()
    updates = data.get('updates', {})

    if not platform:
        return jsonify({'success': False, 'message': '请指定平台'}), 400

    config = load_config()

    if platform == 'global':
        # 更新全局配置
        allowed_global_keys = ['use_real_crawler', 'fallback_to_simulated',
                               'request_delay', 'max_retries', 'timeout']
        for key in allowed_global_keys:
            if key in updates:
                config['global'][key] = updates[key]
    elif platform in config:
        # 更新平台配置
        if 'enabled' in updates:
            config[platform]['enabled'] = bool(updates['enabled'])
        if 'use_real' in updates:
            config[platform]['use_real'] = bool(updates['use_real'])
        if 'cookies' in updates:
            config[platform]['cookies'].update(updates['cookies'])
    else:
        return jsonify({'success': False, 'message': f'未知平台: {platform}'}), 400

    if save_config(config):
        return jsonify({
            'success': True,
            'message': f'已更新 {platform} 配置',
        })
    else:
        return jsonify({'success': False, 'message': '保存失败'}), 500


@crawler_api_bp.route('/crawler/refresh-events', methods=['POST'])
@login_required
def refresh_events():
    """一键用真实热搜数据替换所有事件"""
    import sys, os
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    script_path = os.path.join(base_dir, 'scripts', 'refresh_real_data.py')

    if not os.path.exists(script_path):
        return jsonify({'success': False, 'message': '刷新脚本不存在'}), 500

    # 运行刷新脚本
    import subprocess
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True, text=True, timeout=120,
            cwd=base_dir
        )
        output = result.stdout + '\n' + result.stderr

        # 提取结果
        if '完成' in output:
            # 找到事件数量
            import re
            match = re.search(r'创建 (\d+) 个', output)
            count = int(match.group(1)) if match else 0
            return jsonify({
                'success': True,
                'count': count,
                'message': f'已用真实热搜数据刷新，共 {count} 个事件',
                'log': output[-2000:],
            })
        else:
            return jsonify({
                'success': False,
                'message': '刷新过程中出现问题',
                'log': output[-2000:],
            }), 500
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'message': '刷新超时，请检查网络'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': f'刷新失败: {str(e)}'}), 500


@crawler_api_bp.route('/crawler/config/cookies/<platform>', methods=['POST'])
@login_required
def update_cookies(platform):
    """快捷更新指定平台的 Cookie"""
    from crawler.crawler_config import update_platform_cookies

    data = request.get_json() or {}
    cookies = data.get('cookies', {})

    if not cookies:
        return jsonify({'success': False, 'message': '请提供 Cookie 数据'}), 400

    success = update_platform_cookies(platform, cookies)
    if success:
        return jsonify({'success': True, 'message': f'已更新 {platform} 的 Cookie'})
    else:
        return jsonify({'success': False, 'message': f'平台 {platform} 不存在'}), 404


@crawler_api_bp.route('/crawler/run', methods=['POST'])
@login_required
def trigger_crawl():
    """手动触发爬取"""
    data = request.get_json() or {}
    platforms = data.get('platforms', None)  # None = 全部
    force_real = data.get('force_real', False)

    from crawler.spider import CrawlerManager
    manager = CrawlerManager()

    # 如果强制真实爬取，临时启用
    if force_real:
        manager.config['global']['use_real_crawler'] = True
        if platforms:
            for p in platforms:
                if p in manager.config:
                    manager.config[p]['use_real'] = True

    results = manager.crawl_all(platforms)

    return jsonify({
        'success': True,
        'count': len(results),
        'results': results[:100],  # 最多返回100条预览
        'message': f'爬取完成，共获取 {len(results)} 条数据',
    })


@crawler_api_bp.route('/crawler/auth-guide', methods=['GET'])
@login_required
def auth_guide():
    """获取各平台 Cookie 获取指南"""
    guides = {
        'weibo': {
            'platform': '微博热搜',
            'url': 'https://weibo.com',
            'steps': [
                '1. 浏览器打开 https://weibo.com 并登录',
                '2. 按 F12 打开开发者工具 → Application → Cookies',
                '3. 找到 weibo.com 域名下的 SUB 字段，复制完整值',
                '4. 在本系统填入 SUB 值即可',
            ],
            'required_cookies': ['SUB'],
            'optional_cookies': ['SUBP', 'SINAGLOBAL'],
            'note': 'SUB 是微博的核心登录凭证，有效期通常为1-3天',
        },
        'zhihu': {
            'platform': '知乎热榜',
            'url': 'https://www.zhihu.com',
            'steps': [
                '1. 浏览器打开 https://www.zhihu.com 并登录',
                '2. F12 → Application → Cookies → zhihu.com',
                '3. 找到 z_c0 字段，复制完整值',
                '4. 在本系统填入 z_c0 值',
            ],
            'required_cookies': ['z_c0'],
            'optional_cookies': ['d_c0'],
            'note': 'z_c0 是知乎的认证 token，登录后自动获取',
        },
        'baidu': {
            'platform': '百度热搜',
            'url': 'https://top.baidu.com',
            'steps': [
                '1. 百度热搜通常无需登录即可访问',
                '2. 如需更稳定访问，可在百度登录后获取 BAIDUID',
            ],
            'required_cookies': [],
            'optional_cookies': ['BAIDUID', 'BDUSS'],
            'note': '百度热搜 API 无需认证即可访问，建议优先使用',
        },
        'bilibili': {
            'platform': 'B站热门',
            'url': 'https://www.bilibili.com',
            'steps': [
                '1. 登录 B站后 F12 → Application → Cookies',
                '2. 复制 SESSDATA 字段值',
            ],
            'required_cookies': [],
            'optional_cookies': ['SESSDATA'],
            'note': 'B站热门 API 无需登录也可访问',
        },
    }

    return jsonify({
        'success': True,
        'guides': guides,
    })


def _sanitize_config(config):
    """脱敏配置中的敏感信息"""
    import copy
    safe = copy.deepcopy(config)

    for platform in safe:
        if platform == 'global' or platform == 'proxy':
            continue
        if isinstance(safe[platform], dict) and 'cookies' in safe[platform]:
            sanitized = {}
            for key, value in safe[platform]['cookies'].items():
                if value:
                    # 只显示前4个和后4个字符
                    if len(value) > 10:
                        sanitized[key] = value[:4] + '****' + value[-4:]
                    else:
                        sanitized[key] = '****'
                else:
                    sanitized[key] = ''
            safe[platform]['cookies'] = sanitized

    return safe
