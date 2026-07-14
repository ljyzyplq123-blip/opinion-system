"""
Auth API - 认证相关API（复用auth.py中的路由）
"""
from flask import Blueprint
from auth import auth_bp

api_auth_bp = Blueprint('api_auth', __name__)

# auth_bp已包含所有认证路由：
# POST /api/login
# POST /api/register
# POST /api/logout
# GET /api/user/info
