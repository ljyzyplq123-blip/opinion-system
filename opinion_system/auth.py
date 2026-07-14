"""
用户认证模块
"""
from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/api/register', methods=['POST'])
def register():
    """用户注册"""
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    email = data.get('email', '').strip()

    # 验证
    if not username or len(username) < 2:
        return jsonify({'success': False, 'message': '用户名至少2个字符'}), 400
    if not password or len(password) < 6:
        return jsonify({'success': False, 'message': '密码至少6个字符'}), 400
    if not email or '@' not in email:
        return jsonify({'success': False, 'message': '请输入有效邮箱'}), 400

    # 检查重复
    if User.query.filter_by(username=username).first():
        return jsonify({'success': False, 'message': '用户名已存在'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'message': '邮箱已被注册'}), 400

    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify({'success': True, 'message': '注册成功，请登录'})


@auth_bp.route('/api/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    remember = data.get('remember', False)

    if not username or not password:
        return jsonify({'success': False, 'message': '请输入用户名和密码'}), 400

    user = User.query.filter_by(username=username).first()
    if user is None or not user.check_password(password):
        return jsonify({'success': False, 'message': '用户名或密码错误'}), 401

    login_user(user, remember=remember)
    return jsonify({
        'success': True,
        'message': '登录成功',
        'user': {'id': user.id, 'username': user.username, 'email': user.email}
    })


@auth_bp.route('/api/logout', methods=['POST'])
@login_required
def logout():
    """退出登录"""
    logout_user()
    return jsonify({'success': True, 'message': '已退出登录'})


@auth_bp.route('/api/user/info', methods=['GET'])
@login_required
def user_info():
    """获取当前用户信息"""
    return jsonify({
        'success': True,
        'user': {
            'id': current_user.id,
            'username': current_user.username,
            'email': current_user.email,
            'created_at': current_user.created_at.isoformat() if current_user.created_at else ''
        }
    })


# ==================== 页面路由 ====================

@auth_bp.route('/')
def index():
    """首页"""
    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard'))
    return redirect(url_for('auth.login_page'))


@auth_bp.route('/login')
def login_page():
    """登录页"""
    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard'))
    return render_template('login.html')


@auth_bp.route('/register')
def register_page():
    """注册页"""
    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard'))
    return render_template('register.html')


@auth_bp.route('/dashboard')
@login_required
def dashboard():
    """舆情看板"""
    return render_template('dashboard.html')


@auth_bp.route('/event/<int:event_id>')
@login_required
def event_detail(event_id):
    """事件详情页"""
    return render_template('event_detail.html', event_id=event_id)


@auth_bp.route('/qa')
@login_required
def qa_page():
    """智能问答页"""
    return render_template('qa.html')


@auth_bp.route('/profile')
@login_required
def profile():
    """个人中心"""
    return render_template('profile.html')


@auth_bp.route('/test')
@login_required
def test_page():
    """诊断页面"""
    return render_template('test.html')
