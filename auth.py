#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import request, jsonify, g, Blueprint
from functools import wraps
import json
import os
import uuid
import datetime
import hashlib
import jwt
import re

# 配置
SECRET_KEY = "tapir_twins_secret_key"  # 实际应用中应该使用环境变量存储
TOKEN_EXPIRATION = 24 * 60 * 60  # 24小时

# 数据文件路径
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
SPACES_FILE = os.path.join(DATA_DIR, 'spaces.json')

# 确保数据目录存在
os.makedirs(DATA_DIR, exist_ok=True)

# 初始化用户数据文件
def init_users_file():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)

# 初始化空间数据文件
def init_spaces_file():
    if not os.path.exists(SPACES_FILE):
        with open(SPACES_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)

# 读取用户数据
def read_users():
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

# 写入用户数据
def write_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

# 读取空间数据
def read_spaces():
    try:
        with open(SPACES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

# 写入空间数据
def write_spaces(spaces):
    with open(SPACES_FILE, 'w', encoding='utf-8') as f:
        json.dump(spaces, f, ensure_ascii=False, indent=2)

# 密码哈希
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# 验证密码
def verify_password(stored_hash, password):
    return stored_hash == hash_password(password)

# 生成JWT令牌
def generate_token(user_id):
    payload = {
        'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=TOKEN_EXPIRATION),
        'iat': datetime.datetime.utcnow(),
        'sub': user_id
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

# 验证JWT令牌
def verify_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload['sub']
    except jwt.ExpiredSignatureError:
        return None  # 令牌已过期
    except jwt.InvalidTokenError:
        return None  # 无效令牌

# 验证邮箱格式
def is_valid_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

# 验证用户名格式
def is_valid_username(username):
    # 用户名长度3-20，允许字母、数字、下划线和汉字
    pattern = r'^[\w\u4e00-\u9fa5]{3,20}$'
    return re.match(pattern, username) is not None

# 验证密码强度
def is_valid_password(password):
    # 密码长度至少8位
    return len(password) >= 8

# 登录装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': '未授权访问'}), 401
        
        token = auth_header.split(' ')[1]
        user_id = verify_token(token)
        
        if not user_id:
            return jsonify({'error': '无效或过期的令牌'}), 401
        
        # 将用户ID存储在g对象中，以便在视图函数中使用
        g.user_id = user_id
        
        return f(*args, **kwargs)
    
    return decorated_function

# 创建认证蓝图
auth_bp = Blueprint('auth', __name__)

# 用户注册
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    # 验证请求数据
    if not data or not all(key in data for key in ['username', 'password', 'email']):
        return jsonify({'error': '缺少必要的注册信息'}), 400
    
    username = data['username']
    password = data['password']
    email = data['email']
    
    # 验证用户名格式
    if not is_valid_username(username):
        return jsonify({'error': '用户名格式不正确（3-20个字符，允许字母、数字、下划线和汉字）'}), 400
    
    # 验证密码强度
    if not is_valid_password(password):
        return jsonify({'error': '密码强度不足（至少8位）'}), 400
    
    # 验证邮箱格式
    if not is_valid_email(email):
        return jsonify({'error': '邮箱格式不正确'}), 400
    
    # 检查用户名和邮箱是否已存在
    users = read_users()
    if any(user['username'] == username for user in users):
        return jsonify({'error': '用户名已存在'}), 400
    
    if any(user['email'] == email for user in users):
        return jsonify({'error': '邮箱已注册'}), 400
    
    # 创建新用户
    now = datetime.datetime.utcnow().isoformat()
    new_user = {
        'id': str(uuid.uuid4()),
        'username': username,
        'password_hash': hash_password(password),
        'email': email,
        'created_at': now,
        'updated_at': now
    }
    
    # 保存用户
    users.append(new_user)
    write_users(users)
    
    # 生成令牌
    token = generate_token(new_user['id'])
    
    # 返回用户信息和令牌
    return jsonify({
        'user': {
            'id': new_user['id'],
            'username': new_user['username'],
            'email': new_user['email']
        },
        'token': token
    }), 201

# 用户登录
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    # 验证请求数据
    if not data or not all(key in data for key in ['username', 'password']):
        return jsonify({'error': '缺少用户名或密码'}), 400
    
    username = data['username']
    password = data['password']
    
    # 查找用户
    users = read_users()
    user = next((user for user in users if user['username'] == username), None)
    
    # 验证用户和密码
    if not user or not verify_password(user['password_hash'], password):
        return jsonify({'error': '用户名或密码错误'}), 401
    
    # 生成令牌
    token = generate_token(user['id'])
    
    # 返回用户信息和令牌
    return jsonify({
        'user': {
            'id': user['id'],
            'username': user['username'],
            'email': user['email']
        },
        'token': token
    })

# 获取当前用户信息
@auth_bp.route('/me', methods=['GET'])
@login_required
def get_current_user():
    # 从g对象中获取用户ID
    user_id = g.user_id
    
    # 查找用户
    users = read_users()
    user = next((user for user in users if user['id'] == user_id), None)
    
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    
    # 返回用户信息
    return jsonify({
        'user': {
            'id': user['id'],
            'username': user['username'],
            'email': user['email']
        }
    })

# 初始化
init_users_file()
init_spaces_file()
