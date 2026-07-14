"""
User API - 个人中心（管理监控源和关键词）
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, MonitoredSource, MonitoredKeyword

user_bp = Blueprint('user', __name__)


# ==================== 监控源管理 ====================

@user_bp.route('/user/sources', methods=['GET'])
@login_required
def get_sources():
    """获取用户监控源列表"""
    sources = MonitoredSource.query.filter_by(
        user_id=current_user.id).order_by(MonitoredSource.created_at.desc()).all()
    return jsonify({
        'success': True,
        'sources': [s.to_dict() for s in sources]
    })


@user_bp.route('/user/sources', methods=['POST'])
@login_required
def add_source():
    """添加监控源"""
    data = request.get_json() or {}
    name = data.get('platform_name', '').strip()
    url = data.get('platform_url', '').strip()
    source_type = data.get('source_type', 'news').strip()

    if not name or not url:
        return jsonify({'success': False, 'message': '请填写平台名称和URL'}), 400

    source = MonitoredSource(
        user_id=current_user.id,
        platform_name=name,
        platform_url=url,
        source_type=source_type
    )
    db.session.add(source)
    db.session.commit()

    return jsonify({'success': True, 'source': source.to_dict(),
                    'message': '添加成功'})


@user_bp.route('/user/sources/<int:source_id>', methods=['PUT'])
@login_required
def update_source(source_id):
    """更新监控源"""
    source = MonitoredSource.query.filter_by(
        id=source_id, user_id=current_user.id).first()
    if not source:
        return jsonify({'success': False, 'message': '记录不存在'}), 404

    data = request.get_json() or {}
    if 'is_active' in data:
        source.is_active = data['is_active']
    if 'platform_name' in data:
        source.platform_name = data['platform_name']
    if 'platform_url' in data:
        source.platform_url = data['platform_url']

    db.session.commit()
    return jsonify({'success': True, 'source': source.to_dict(),
                    'message': '更新成功'})


@user_bp.route('/user/sources/<int:source_id>', methods=['DELETE'])
@login_required
def delete_source(source_id):
    """删除监控源"""
    source = MonitoredSource.query.filter_by(
        id=source_id, user_id=current_user.id).first()
    if not source:
        return jsonify({'success': False, 'message': '记录不存在'}), 404

    db.session.delete(source)
    db.session.commit()
    return jsonify({'success': True, 'message': '已删除'})


# ==================== 关键词管理 ====================

@user_bp.route('/user/keywords', methods=['GET'])
@login_required
def get_keywords():
    """获取用户关键词列表"""
    keywords = MonitoredKeyword.query.filter_by(
        user_id=current_user.id).order_by(MonitoredKeyword.created_at.desc()).all()
    return jsonify({
        'success': True,
        'keywords': [k.to_dict() for k in keywords]
    })


@user_bp.route('/user/keywords', methods=['POST'])
@login_required
def add_keyword():
    """添加关键词"""
    data = request.get_json() or {}
    keyword = data.get('keyword', '').strip()
    category = data.get('category', 'general').strip()

    if not keyword:
        return jsonify({'success': False, 'message': '请输入关键词'}), 400

    # 避免重复
    existing = MonitoredKeyword.query.filter_by(
        user_id=current_user.id, keyword=keyword).first()
    if existing:
        return jsonify({'success': False, 'message': '关键词已存在'}), 400

    kw = MonitoredKeyword(
        user_id=current_user.id,
        keyword=keyword,
        category=category
    )
    db.session.add(kw)
    db.session.commit()

    return jsonify({'success': True, 'keyword': kw.to_dict(),
                    'message': '添加成功'})


@user_bp.route('/user/keywords/<int:kw_id>', methods=['DELETE'])
@login_required
def delete_keyword(kw_id):
    """删除关键词"""
    kw = MonitoredKeyword.query.filter_by(
        id=kw_id, user_id=current_user.id).first()
    if not kw:
        return jsonify({'success': False, 'message': '记录不存在'}), 404

    db.session.delete(kw)
    db.session.commit()
    return jsonify({'success': True, 'message': '已删除'})


# ==================== LLM 配置管理 ====================

import os
import json

LLM_CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), 'llm_config.json')

# LLM 预设模板
LLM_PRESETS = {
    'deepseek': {
        'name': 'DeepSeek V3',
        'api_url': 'https://api.deepseek.com/v1/chat/completions',
        'model': 'deepseek-chat',
        'description': 'DeepSeek 大语言模型，性价比极高',
    },
    'deepseek-r1': {
        'name': 'DeepSeek R1',
        'api_url': 'https://api.deepseek.com/v1/chat/completions',
        'model': 'deepseek-reasoner',
        'description': 'DeepSeek 推理模型，擅长深度分析',
    },
    'openai': {
        'name': 'OpenAI GPT',
        'api_url': 'https://api.openai.com/v1/chat/completions',
        'model': 'gpt-4o',
        'description': 'OpenAI 最新模型',
    },
    'custom': {
        'name': '自定义',
        'api_url': '',
        'model': '',
        'description': '兼容 OpenAI API 格式的其他服务',
    },
}


@user_bp.route('/user/llm-config', methods=['GET'])
@login_required
def get_llm_config():
    """获取当前LLM配置（掩码显示API Key）"""
    from config import _load_llm_config
    cfg = _load_llm_config()

    # 如果JSON没有配置，使用config.py的默认值
    if not cfg:
        from config import Config
        cfg = {
            'api_url': Config.LLM_API_URL,
            'api_key': Config.LLM_API_KEY,
            'model': Config.LLM_MODEL,
        }

    # 掩码API Key
    key = cfg.get('api_key', '')
    masked = ''
    if key and len(key) > 8:
        masked = key[:4] + '****' + key[-4:]
    elif key:
        masked = '****'

    return jsonify({
        'success': True,
        'config': {
            'api_url': cfg.get('api_url', ''),
            'api_key': key,
            'api_key_masked': masked,
            'model': cfg.get('model', ''),
        },
        'presets': LLM_PRESETS,
    })


@user_bp.route('/user/llm-config', methods=['POST'])
@login_required
def update_llm_config():
    """更新LLM配置"""
    data = request.get_json() or {}
    api_url = data.get('api_url', '').strip()
    api_key = data.get('api_key', '').strip()
    model = data.get('model', '').strip()

    if not api_url:
        return jsonify({'success': False, 'message': '请输入API地址'}), 400
    if not api_key:
        return jsonify({'success': False, 'message': '请输入API Key'}), 400
    if not model:
        return jsonify({'success': False, 'message': '请输入模型名称'}), 400

    cfg = {
        'api_url': api_url,
        'api_key': api_key,
        'model': model,
    }

    try:
        with open(LLM_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        return jsonify({'success': True, 'message': 'LLM配置已保存，下次问答生效'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'保存失败: {str(e)}'}), 500


@user_bp.route('/user/llm-config/test', methods=['POST'])
@login_required
def test_llm_config():
    """测试LLM连接"""
    data = request.get_json() or {}
    api_url = data.get('api_url', '').strip()
    api_key = data.get('api_key', '').strip()
    model = data.get('model', '').strip()

    if not api_url or not api_key or not model:
        return jsonify({'success': False, 'message': '请填写完整的配置'}), 400

    import requests
    try:
        resp = requests.post(
            api_url,
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            json={
                'model': model,
                'messages': [{'role': 'user', 'content': '你好，请回复"连接成功"'}],
                'max_tokens': 50,
            },
            timeout=30,
        )
        if resp.status_code == 200:
            result = resp.json()
            reply = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            return jsonify({
                'success': True,
                'message': f'连接成功！模型回复: {reply[:100]}',
            })
        else:
            body = resp.text[:300]
            return jsonify({
                'success': False,
                'message': f'HTTP {resp.status_code}: {body}',
            })
    except requests.exceptions.Timeout:
        return jsonify({'success': False, 'message': '连接超时，请检查API地址是否正确'})
    except requests.exceptions.ConnectionError:
        return jsonify({'success': False, 'message': '无法连接，请检查API地址和网络'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'测试失败: {str(e)}'})
