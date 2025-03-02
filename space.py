#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, request, jsonify, g
from functools import wraps
import json
import os
import uuid
import datetime
import random
import string
from auth import login_required, read_spaces, write_spaces, read_users
from models import Space, SpaceMember, MemberRole

# 创建空间蓝图
space_bp = Blueprint('space', __name__)

# 生成随机邀请码
def generate_invite_code(length=8):
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

# 检查空间成员权限的装饰器
def member_required(role=None):
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(space_id, *args, **kwargs):
            # 获取当前用户ID
            user_id = g.user_id
            
            # 获取空间
            spaces = read_spaces()
            space = next((space for space in spaces if space['id'] == space_id), None)
            
            if not space:
                return jsonify({'error': '空间不存在'}), 404
            
            # 检查用户是否是空间成员
            is_member = False
            user_role = None
            
            for member in space['members']:
                if member['user_id'] == user_id:
                    is_member = True
                    user_role = member['role']
                    break
            
            if not is_member:
                return jsonify({'error': '您不是该空间的成员'}), 403
            
            # 如果指定了角色要求，检查用户角色
            
            if role and user_role != role and user_role != MemberRole.ADMIN:
                return jsonify({'error': f'需要{role}权限才能执行此操作'}), 403
            
            # 将空间ID和用户角色存储在g对象中
            g.space_id = space_id
            g.user_role = user_role
            
            return f(space_id, *args, **kwargs)
        
        return decorated_function
    
    return decorator

# 创建新空间
@space_bp.route('', methods=['POST'])
@login_required
def create_space():
    data = request.get_json()
    
    # 验证请求数据
    if not data or not all(key in data for key in ['name']):
        return jsonify({'error': '缺少必要的空间信息'}), 400
    
    # 获取当前用户ID
    user_id = g.user_id
    
    # 生成邀请码
    invite_code = generate_invite_code()
    
    # 创建新空间
    now = datetime.datetime.utcnow().isoformat()
    new_space = {
        'id': str(uuid.uuid4()),
        'name': data['name'],
        'description': data.get('description', ''),
        'creator_id': user_id,
        'members': [
            {
                'user_id': user_id,
                'role': MemberRole.ADMIN
            }
        ],
        'created_at': now,
        'updated_at': now,
        'invite_code': invite_code
    }
    
    # 保存空间
    spaces = read_spaces()
    spaces.append(new_space)
    write_spaces(spaces)
    
    # 添加成员的用户名
    space_with_usernames = new_space.copy()
    space_with_usernames['members'] = get_members_with_username(new_space['members'])
    
    # 返回新空间信息
    return jsonify(space_with_usernames), 201

# 通过邀请码加入空间
@space_bp.route('/join', methods=['POST'])
@login_required
def join_space():
    data = request.get_json()
    
    # 验证请求数据
    if not data or 'invite_code' not in data:
        return jsonify({'error': '缺少邀请码'}), 400
    
    invite_code = data['invite_code']
    
    # 获取当前用户ID
    user_id = g.user_id
    
    # 获取所有空间
    spaces = read_spaces()
    
    # 查找匹配邀请码的空间
    space_index = next((i for i, space in enumerate(spaces) if space.get('invite_code') == invite_code), None)
    
    if space_index is None:
        return jsonify({'error': '无效的邀请码'}), 404
    
    space = spaces[space_index]
    
    # 检查用户是否已经是成员
    if any(member['user_id'] == user_id for member in space['members']):
        return jsonify({'error': '您已经是该空间的成员'}), 400
    
    # 添加用户为成员（默认为打卡者角色）
    space['members'].append({
        'user_id': user_id,
        'role': MemberRole.SUBMITTER
    })
    
    space['updated_at'] = datetime.datetime.utcnow().isoformat()
    
    # 保存更新
    write_spaces(spaces)
    
    # 添加成员的用户名
    space_with_usernames = space.copy()
    space_with_usernames['members'] = get_members_with_username(space['members'])
    
    return jsonify(space_with_usernames), 200

# 获取用户的所有空间
@space_bp.route('', methods=['GET'])
@login_required
def get_user_spaces():
    # 获取当前用户ID
    user_id = g.user_id
    
    # 获取所有空间
    spaces = read_spaces()
    
    # 筛选出用户所在的空间
    user_spaces = []
    for space in spaces:
        for member in space['members']:
            if member['user_id'] == user_id:
                # 添加空间信息，包括成员的用户名
                space_with_usernames = space.copy()
                space_with_usernames['members'] = get_members_with_username(space['members'])
                user_spaces.append(space_with_usernames)
                break
    
    return jsonify(user_spaces)

# 获取空间详情
@space_bp.route('/<space_id>', methods=['GET'])
@member_required()
def get_space(space_id):
    # 获取空间
    spaces = read_spaces()
    space = next((space for space in spaces if space['id'] == space_id), None)
    
    # 添加成员的用户名
    space_with_usernames = space.copy()
    space_with_usernames['members'] = get_members_with_username(space['members'])
    
    return jsonify(space_with_usernames)

# 更新空间信息
@space_bp.route('/<space_id>', methods=['PUT'])
@member_required(MemberRole.ADMIN)
def update_space(space_id):
    data = request.get_json()
    
    # 验证请求数据
    if not data:
        return jsonify({'error': '缺少更新信息'}), 400
    
    # 获取空间
    spaces = read_spaces()
    space_index = next((i for i, space in enumerate(spaces) if space['id'] == space_id), None)
    
    if space_index is None:
        return jsonify({'error': '空间不存在'}), 404
    
    # 更新空间信息
    space = spaces[space_index]
    if 'name' in data:
        space['name'] = data['name']
    if 'description' in data:
        space['description'] = data['description']
    
    space['updated_at'] = datetime.datetime.utcnow().isoformat()
    
    # 保存更新
    write_spaces(spaces)
    
    # 添加成员的用户名
    space_with_usernames = space.copy()
    space_with_usernames['members'] = get_members_with_username(space['members'])
    
    return jsonify(space_with_usernames)

# 邀请用户加入空间
@space_bp.route('/<space_id>/members', methods=['POST'])
@member_required(MemberRole.ADMIN)
def invite_member(space_id):
    data = request.get_json()
    
    # 验证请求数据
    if not data or not all(key in data for key in ['username', 'role']):
        return jsonify({'error': '缺少必要的邀请信息'}), 400
    
    username = data['username']
    role = data['role']
    
    # 验证角色
    if role not in [MemberRole.SUBMITTER, MemberRole.APPROVER]:
        return jsonify({'error': '无效的角色'}), 400
    
    # 查找用户
    users = read_users()
    user = next((user for user in users if user['username'] == username), None)
    
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    
    # 获取空间
    spaces = read_spaces()
    space_index = next((i for i, space in enumerate(spaces) if space['id'] == space_id), None)
    
    if space_index is None:
        return jsonify({'error': '空间不存在'}), 404
    
    # 检查用户是否已经是成员
    space = spaces[space_index]
    if any(member['user_id'] == user['id'] for member in space['members']):
        return jsonify({'error': '用户已经是该空间的成员'}), 400
    
    # 添加新成员
    space['members'].append({
        'user_id': user['id'],
        'role': role
    })
    
    space['updated_at'] = datetime.datetime.utcnow().isoformat()
    
    # 保存更新
    write_spaces(spaces)
    
    # 添加成员的用户名
    space_with_usernames = space.copy()
    space_with_usernames['members'] = get_members_with_username(space['members'])
    
    return jsonify(space_with_usernames)

# 移除空间成员
@space_bp.route('/<space_id>/members/<user_id>', methods=['DELETE'])
@member_required(MemberRole.ADMIN)
def remove_member(space_id, user_id):
    # 获取空间
    spaces = read_spaces()
    space_index = next((i for i, space in enumerate(spaces) if space['id'] == space_id), None)
    
    if space_index is None:
        return jsonify({'error': '空间不存在'}), 404
    
    # 检查要移除的用户是否是成员
    space = spaces[space_index]
    member_index = next((i for i, member in enumerate(space['members']) if member['user_id'] == user_id), None)
    
    if member_index is None:
        return jsonify({'error': '用户不是该空间的成员'}), 404
    
    # 不能移除创建者
    if user_id == space['creator_id']:
        return jsonify({'error': '不能移除空间创建者'}), 400
    
    # 移除成员
    space['members'].pop(member_index)
    space['updated_at'] = datetime.datetime.utcnow().isoformat()
    
    # 保存更新
    write_spaces(spaces)
    
    # 添加成员的用户名
    space_with_usernames = space.copy()
    space_with_usernames['members'] = get_members_with_username(space['members'])
    
    return jsonify(space_with_usernames)

# 更新成员角色
@space_bp.route('/<space_id>/members/<user_id>', methods=['PUT'])
@member_required(MemberRole.ADMIN)
def update_member_role(space_id, user_id):
    data = request.get_json()
    
    # 验证请求数据
    if not data or 'role' not in data:
        return jsonify({'error': '缺少角色信息'}), 400
    
    role = data['role']
    
    # 验证角色
    if role not in [MemberRole.SUBMITTER, MemberRole.APPROVER]:
        return jsonify({'error': '无效的角色'}), 400
    
    # 获取空间
    spaces = read_spaces()
    space_index = next((i for i, space in enumerate(spaces) if space['id'] == space_id), None)
    
    if space_index is None:
        return jsonify({'error': '空间不存在'}), 404
    
    # 检查要更新的用户是否是成员
    space = spaces[space_index]
    member_index = next((i for i, member in enumerate(space['members']) if member['user_id'] == user_id), None)
    
    if member_index is None:
        return jsonify({'error': '用户不是该空间的成员'}), 404
    
    # 不能更改创建者的角色
    if user_id == space['creator_id']:
        return jsonify({'error': '不能更改空间创建者的角色'}), 400
    
    # 更新角色
    space['members'][member_index]['role'] = role
    space['updated_at'] = datetime.datetime.utcnow().isoformat()
    
    # 保存更新
    write_spaces(spaces)
    
    # 添加成员的用户名
    space_with_usernames = space.copy()
    space_with_usernames['members'] = get_members_with_username(space['members'])
    
    return jsonify(space_with_usernames)

# 删除空间
@space_bp.route('/<space_id>', methods=['DELETE'])
@member_required(MemberRole.ADMIN)
def delete_space(space_id):
    # 获取当前用户ID
    user_id = g.user_id
    
    # 获取空间
    spaces = read_spaces()
    space_index = next((i for i, space in enumerate(spaces) if space['id'] == space_id), None)
    
    if space_index is None:
        return jsonify({'error': '空间不存在'}), 404
    
    # 只有创建者可以删除空间
    space = spaces[space_index]
    if space['creator_id'] != user_id:
        return jsonify({'error': '只有空间创建者可以删除空间'}), 403
    
    # 删除空间
    spaces.pop(space_index)
    
    # 保存更新
    write_spaces(spaces)
    
    return jsonify({'message': '空间已删除'})

# 辅助函数：获取带有用户名的成员列表
def get_members_with_username(members):
    users = read_users()
    members_with_username = []
    
    for member in members:
        user = next((user for user in users if user['id'] == member['user_id']), None)
        if user:
            member_with_username = member.copy()
            member_with_username['username'] = user['username']
            members_with_username.append(member_with_username)
    
    return members_with_username
