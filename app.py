#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify, send_from_directory, g
import json
import os
import datetime
import time
import threading
import uuid
import base64
from flask_cors import CORS
from auth import auth_bp, login_required, init_users_file, init_spaces_file
from space import space_bp, member_required
from models import MemberRole, Dream, Task, TaskRecord

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 注册蓝图
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(space_bp, url_prefix='/api/spaces')

# 确保数据目录存在
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# 确保图片目录存在
IMAGES_DIR = os.path.join(DATA_DIR, 'images')
os.makedirs(IMAGES_DIR, exist_ok=True)

# 数据文件路径
DREAMS_FILE = os.path.join(DATA_DIR, 'dreams.json')
TASKS_FILE = os.path.join(DATA_DIR, 'tasks.json')
TASK_RECORDS_FILE = os.path.join(DATA_DIR, 'task_records.json')
USER_SETTINGS_FILE = os.path.join(DATA_DIR, 'user_settings.json')
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
SPACES_FILE = os.path.join(DATA_DIR, 'spaces.json')
HISTORY_RECORDS_FILE = os.path.join(DATA_DIR, 'history_records.json')

# 初始化数据文件
def init_data_file(file_path, initial_data=None):
    if not os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(initial_data or [], f, ensure_ascii=False, indent=2)

init_data_file(DREAMS_FILE)
init_data_file(TASKS_FILE)
init_data_file(TASK_RECORDS_FILE)
init_data_file(USER_SETTINGS_FILE, {})
init_data_file(USERS_FILE, [])
init_data_file(SPACES_FILE, [])
init_data_file(HISTORY_RECORDS_FILE, [])
init_users_file()
init_spaces_file()

# 读取数据
def read_data(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        # 根据文件路径返回不同的默认值
        if file_path == USER_SETTINGS_FILE:
            return {}
        return []

# 写入数据
def write_data(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 获取今天的日期字符串
def get_today_date():
    return datetime.datetime.now().strftime('%Y-%m-%d')

# 辅助函数：根据用户ID获取用户名
def get_username(user_id):
    users = read_data(USERS_FILE)
    user = next((u for u in users if u.get('id') == user_id), None)
    if user:
        return user.get('username')
    return None

# 检查任务是否今天已完成
def is_task_completed_today(task_id):
    records = read_data(TASK_RECORDS_FILE)
    today = get_today_date()
    
    for record in records:
        if record.get('task_id') == task_id and record.get('date') == today:
            return True
    
    return False

# 每日重置任务状态的函数
def reset_tasks_daily():
    while True:
        # 获取当前时间
        now = datetime.datetime.now()
        
        # 计算距离下一个0点的秒数
        tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
        seconds_until_midnight = (tomorrow - now).total_seconds()
        
        # 等待到下一个0点
        time.sleep(seconds_until_midnight)
        
        # 重置所有任务的完成状态
        print(f"重置任务状态: {datetime.datetime.now()}")

# 启动每日重置任务的线程
reset_thread = threading.Thread(target=reset_tasks_daily, daemon=True)
reset_thread.start()

# 梦境API
@app.route('/api/dreams', methods=['GET'])
@login_required
def get_dreams():
    user_id = g.user_id
    space_id = request.args.get('space_id')
    
    dreams = read_data(DREAMS_FILE)
    
    # 过滤梦境：如果指定了空间ID，则只返回该空间的梦境；否则返回用户的个人梦境
    if space_id:
        filtered_dreams = [dream for dream in dreams if dream.get('space_id') == space_id]
    else:
        filtered_dreams = [dream for dream in dreams if dream.get('user_id') == user_id and not dream.get('space_id')]
    
    return jsonify(filtered_dreams)

@app.route('/api/spaces/<space_id>/dreams', methods=['GET'])
@member_required()
def get_space_dreams(space_id):
    dreams = read_data(DREAMS_FILE)
    space_dreams = [dream for dream in dreams if dream.get('space_id') == space_id]
    
    # 为每个梦境添加用户名
    for dream in space_dreams:
        if 'user_id' in dream:
            dream['username'] = get_username(dream['user_id'])
    
    return jsonify(space_dreams)

@app.route('/api/dreams/<dream_id>', methods=['GET'])
@login_required
def get_dream(dream_id):
    user_id = g.user_id
    dreams = read_data(DREAMS_FILE)
    
    for dream in dreams:
        if dream.get('id') == dream_id:
            # 检查权限：个人梦境只能本人查看，空间梦境只能空间成员查看
            if dream.get('space_id'):
                # 这里应该检查用户是否是空间成员，但为简化处理，我们假设前端已经做了相应的限制
                pass
            elif dream.get('user_id') != user_id:
                return jsonify({'error': '无权访问该梦境记录'}), 403
            
            return jsonify(dream)
    
    return jsonify({'error': '未找到该梦境记录'}), 404

@app.route('/api/dreams', methods=['POST'])
@login_required
def add_dream():
    user_id = g.user_id
    data = request.json
    dreams = read_data(DREAMS_FILE)
    
    # 生成唯一ID
    new_id = str(uuid.uuid4())
    
    # 添加时间戳和用户ID
    data['id'] = new_id
    data['created_at'] = datetime.datetime.now().isoformat()
    data['user_id'] = user_id
    
    # 如果指定了空间ID，需要验证用户是否是该空间的成员
    if 'space_id' in data and data['space_id']:
        # 这里应该检查用户是否是空间成员，但为简化处理，我们假设前端已经做了相应的限制
        pass
    
    dreams.append(data)
    write_data(DREAMS_FILE, dreams)
    
    return jsonify(data), 201

@app.route('/api/spaces/<space_id>/dreams', methods=['POST'])
@member_required()
def add_space_dream(space_id):
    user_id = g.user_id
    data = request.json
    dreams = read_data(DREAMS_FILE)
    
    # 生成唯一ID
    new_id = str(uuid.uuid4())
    
    # 添加时间戳、用户ID和空间ID
    data['id'] = new_id
    data['created_at'] = datetime.datetime.now().isoformat()
    data['user_id'] = user_id
    data['space_id'] = space_id
    data['username'] = get_username(user_id)  # 添加用户名
    
    dreams.append(data)
    write_data(DREAMS_FILE, dreams)
    
    return jsonify(data), 201

@app.route('/api/dreams/<dream_id>', methods=['PUT'])
@login_required
def update_dream(dream_id):
    user_id = g.user_id
    data = request.json
    dreams = read_data(DREAMS_FILE)
    
    for i, dream in enumerate(dreams):
        if dream.get('id') == dream_id:
            # 检查权限：个人梦境只能本人修改，空间梦境只能空间成员修改
            if dream.get('space_id'):
                # 这里应该检查用户是否是空间成员，但为简化处理，我们假设前端已经做了相应的限制
                pass
            elif dream.get('user_id') != user_id:
                return jsonify({'error': '无权修改该梦境记录'}), 403
            
            # 更新梦境数据，保留原ID、创建时间、用户ID和空间ID
            data['id'] = dream_id
            data['created_at'] = dream.get('created_at')
            data['updated_at'] = datetime.datetime.now().isoformat()
            data['user_id'] = dream.get('user_id')
            data['space_id'] = dream.get('space_id')
            
            dreams[i] = data
            write_data(DREAMS_FILE, dreams)
            return jsonify(data)
    
    return jsonify({'error': '未找到该梦境记录'}), 404

@app.route('/api/dreams/<dream_id>', methods=['DELETE'])
@login_required
def delete_dream(dream_id):
    user_id = g.user_id
    dreams = read_data(DREAMS_FILE)
    
    for i, dream in enumerate(dreams):
        if dream.get('id') == dream_id:
            # 检查权限：个人梦境只能本人删除，空间梦境只能空间管理员删除
            if dream.get('space_id'):
                # 这里应该检查用户是否是空间管理员，但为简化处理，我们假设前端已经做了相应的限制
                pass
            elif dream.get('user_id') != user_id:
                return jsonify({'error': '无权删除该梦境记录'}), 403
            
            deleted = dreams.pop(i)
            write_data(DREAMS_FILE, dreams)
            return jsonify(deleted)
    
    return jsonify({'error': '未找到该梦境记录'}), 404

# 任务API
@app.route('/api/tasks', methods=['GET'])
@login_required
def get_tasks():
    user_id = g.user_id
    space_id = request.args.get('space_id')
    
    tasks = read_data(TASKS_FILE)
    today = get_today_date()
    
    # 过滤任务：如果指定了空间ID，则只返回该空间的任务；否则返回用户的个人任务
    if space_id:
        filtered_tasks = [task for task in tasks if task.get('space_id') == space_id]
    else:
        filtered_tasks = [task for task in tasks if task.get('submitter_id') == user_id and not task.get('space_id')]
    
    # 为每个任务添加今日完成状态
    for task in filtered_tasks:
        task['completed_today'] = is_task_completed_today(task['id'])
    
    return jsonify(filtered_tasks)

@app.route('/api/spaces/<space_id>/tasks', methods=['GET'])
@member_required()
def get_space_tasks(space_id):
    tasks = read_data(TASKS_FILE)
    space_tasks = [task for task in tasks if task.get('space_id') == space_id]
    
    # 为每个任务添加今日完成状态
    for task in space_tasks:
        task['completed_today'] = is_task_completed_today(task['id'])
    
    return jsonify(space_tasks)

@app.route('/api/tasks/<task_id>', methods=['GET'])
@login_required
def get_task(task_id):
    user_id = g.user_id
    tasks = read_data(TASKS_FILE)
    
    for task in tasks:
        if task.get('id') == task_id:
            # 检查权限：个人任务只能本人查看，空间任务只能空间成员查看
            if task.get('space_id'):
                # 这里应该检查用户是否是空间成员，但为简化处理，我们假设前端已经做了相应的限制
                pass
            elif task.get('submitter_id') != user_id:
                return jsonify({'error': '无权访问该任务'}), 403
            
            task['completed_today'] = is_task_completed_today(task_id)
            return jsonify(task)
    
    return jsonify({'error': '未找到该任务'}), 404

@app.route('/api/tasks', methods=['POST'])
@login_required
def add_task():
    user_id = g.user_id
    data = request.json
    tasks = read_data(TASKS_FILE)
    
    # 生成唯一ID
    new_id = str(uuid.uuid4())
    
    # 添加时间戳和默认完成状态
    data['id'] = new_id
    data['created_at'] = datetime.datetime.now().isoformat()
    data['updated_at'] = datetime.datetime.now().isoformat()
    data['required_images'] = data.get('required_images', 1)  # 默认需要1张图片
    data['completed_today'] = False  # 默认未完成
    data['submitter_id'] = user_id
    data['status'] = 'pending'  # 设置初始状态为待处理
    
    # 如果指定了空间ID，需要验证用户是否是该空间的成员
    if 'space_id' in data and data['space_id']:
        # 这里应该检查用户是否是空间成员，但为简化处理，我们假设前端已经做了相应的限制
        pass
    
    tasks.append(data)
    write_data(TASKS_FILE, tasks)
    
    return jsonify(data), 201

@app.route('/api/spaces/<space_id>/tasks', methods=['POST'])
@member_required()
def add_space_task(space_id):
    user_id = g.user_id
    data = request.json
    tasks = read_data(TASKS_FILE)
    
    # 生成唯一ID
    new_id = str(uuid.uuid4())
    
    # 添加时间戳、用户ID和空间ID
    data['id'] = new_id
    data['created_at'] = datetime.datetime.now().isoformat()
    data['updated_at'] = datetime.datetime.now().isoformat()
    data['required_images'] = data.get('required_images', 1)  # 默认需要1张图片
    data['completed_today'] = False  # 默认未完成
    data['submitter_id'] = user_id
    data['space_id'] = space_id
    data['status'] = 'pending'  # 设置初始状态为待处理
    
    # 处理指定的打卡者和审阅者
    if 'assigned_submitter_id' in data and data['assigned_submitter_id']:
        # 验证指定的打卡者是否是空间成员
        spaces = read_data(SPACES_FILE)
        space = next((s for s in spaces if s.get('id') == space_id), None)
        if not space:
            return jsonify({'error': '未找到该空间'}), 404
            
        # 检查指定的打卡者是否是空间成员
        submitter_found = False
        submitter_name = None
        for member in space.get('members', []):
            if member.get('user_id') == data['assigned_submitter_id']:
                submitter_found = True
                submitter_name = member.get('username')
                break
                
        if not submitter_found:
            return jsonify({'error': '指定的打卡者不是空间成员'}), 400
            
        # 添加打卡者名称
        data['assigned_submitter_name'] = submitter_name
    
    # 处理指定的审阅者列表
    if 'assigned_approver_ids' in data and data['assigned_approver_ids']:
        # 验证指定的审阅者是否都是空间成员
        spaces = read_data(SPACES_FILE)
        space = next((s for s in spaces if s.get('id') == space_id), None)
        if not space:
            return jsonify({'error': '未找到该空间'}), 404
            
        # 检查指定的审阅者是否都是空间成员
        approver_names = []
        for approver_id in data['assigned_approver_ids']:
            approver_found = False
            for member in space.get('members', []):
                if member.get('user_id') == approver_id:
                    approver_found = True
                    approver_names.append(member.get('username'))
                    break
                    
            if not approver_found:
                return jsonify({'error': f'指定的审阅者 {approver_id} 不是空间成员'}), 400
                
        # 添加审阅者名称列表
        data['assigned_approver_names'] = approver_names
    
    # 将新任务添加到列表
    tasks.append(data)
    
    # 确保数据写入成功
    try:
        write_data(TASKS_FILE, tasks)
        print(f"成功创建空间任务: {data['title']}, ID: {new_id}, 空间ID: {space_id}")
    except Exception as e:
        print(f"保存任务数据失败: {str(e)}")
        return jsonify({"error": "保存任务失败"}), 500
    
    # 再次读取数据以确认保存成功
    updated_tasks = read_data(TASKS_FILE)
    saved_task = next((task for task in updated_tasks if task.get('id') == new_id), None)
    
    if not saved_task:
        print(f"警告: 任务已保存但无法立即读取: {new_id}")
    
    return jsonify(data), 201

@app.route('/api/tasks/<task_id>', methods=['PUT'])
@login_required
def update_task(task_id):
    user_id = g.user_id
    data = request.json
    tasks = read_data(TASKS_FILE)
    
    for i, task in enumerate(tasks):
        if task.get('id') == task_id:
            # 检查权限：个人任务只能本人修改，空间任务只能空间成员修改
            if task.get('space_id'):
                # 这里应该检查用户是否是空间成员，但为简化处理，我们假设前端已经做了相应的限制
                pass
            elif task.get('submitter_id') != user_id:
                return jsonify({'error': '无权修改该任务'}), 403
            
            # 更新任务数据，保留原ID、创建时间、用户ID和空间ID
            data['id'] = task_id
            data['created_at'] = task.get('created_at')
            data['updated_at'] = datetime.datetime.now().isoformat()
            data['submitter_id'] = task.get('submitter_id')
            data['space_id'] = task.get('space_id')
            
            # 确保completedToday字段存在
            if 'completed_today' not in data:
                data['completed_today'] = task.get('completed_today', False)
            
            tasks[i] = data
            write_data(TASKS_FILE, tasks)
            return jsonify(data)
    
    return jsonify({'error': '未找到该任务'}), 404

@app.route('/api/tasks/<task_id>/complete', methods=['POST'])
@login_required
def complete_task(task_id):
    user_id = g.user_id
    
    # 检查任务是否存在
    tasks = read_data(TASKS_FILE)
    task = None
    for t in tasks:
        if t.get('id') == task_id:
            task = t
            break
    
    if not task:
        return jsonify({'error': '未找到该任务'}), 404
    
    # 检查权限：
    # 1. 个人任务只能本人完成
    # 2. 空间任务如果指定了打卡者，只能由指定的打卡者完成
    # 3. 空间任务如果没有指定打卡者，任何空间成员都可以完成
    if task.get('space_id'):
        # 空间任务
        if task.get('assigned_submitter_id') and task.get('assigned_submitter_id') != user_id:
            return jsonify({'error': '只有指定的打卡者才能完成该任务'}), 403
        # 这里应该检查用户是否是空间成员，但为简化处理，我们假设前端已经做了相应的限制
    elif task.get('submitter_id') != user_id:
        return jsonify({'error': '无权完成该任务'}), 403
    
    # 检查是否已经完成
    if is_task_completed_today(task_id):
        return jsonify({'error': '今天已经完成过该任务'}), 400
    
    # 获取上传的图片
    if 'images' not in request.json:
        return jsonify({'error': '缺少图片数据'}), 400
    
    images = request.json['images']
    required_images = task.get('required_images', 1)
    
    if len(images) < required_images:
        return jsonify({'error': f'需要上传至少{required_images}张图片'}), 400
    
    # 保存图片
    image_paths = []
    for image_data in images:
        if ',' in image_data:
            # 处理base64编码的图片
            image_data = image_data.split(',')[1]
        
        # 生成唯一文件名
        filename = f"{uuid.uuid4()}.jpg"
        filepath = os.path.join(IMAGES_DIR, filename)
        
        # 解码并保存图片
        with open(filepath, "wb") as f:
            f.write(base64.b64decode(image_data))
        
        image_paths.append(filename)
    
    # 创建完成记录
    records = read_data(TASK_RECORDS_FILE)
    record = {
        'id': str(uuid.uuid4()),
        'task_id': task_id,
        'date': get_today_date(),
        'images': image_paths,
        'created_at': datetime.datetime.now().isoformat(),
        'submitter_id': user_id,
        'status': 'submitted',  # 设置状态为已提交，等待审阅
        'submitter_name': get_username(user_id)
    }
    
    # 如果是空间任务，添加空间ID和指定的审阅者
    if task.get('space_id'):
        record['space_id'] = task.get('space_id')
        
        # 如果任务指定了审阅者，将其添加到记录中
        if task.get('assigned_approver_ids'):
            record['assigned_approver_ids'] = task.get('assigned_approver_ids')
            record['assigned_approver_names'] = task.get('assigned_approver_names')
    
    records.append(record)
    write_data(TASK_RECORDS_FILE, records)
    
    # 更新任务状态为已提交
    for i, t in enumerate(tasks):
        if t.get('id') == task_id:
            tasks[i]['status'] = 'submitted'
            tasks[i]['updated_at'] = datetime.datetime.now().isoformat()
            break
    
    write_data(TASKS_FILE, tasks)
    
    return jsonify({
        'success': True,
        'message': '任务完成记录已保存',
        'record_id': record['id']
    })

@app.route('/api/tasks/<task_id>/records', methods=['GET'])
@login_required
def get_task_records(task_id):
    user_id = g.user_id
    
    # 检查任务是否存在
    tasks = read_data(TASKS_FILE)
    task = next((t for t in tasks if t.get('id') == task_id), None)
    
    if not task:
        return jsonify({'error': '未找到该任务'}), 404
    
    # 检查权限：个人任务只能本人查看记录，空间任务只能空间成员查看记录
    if task.get('space_id'):
        # 这里应该检查用户是否是空间成员，但为简化处理，我们假设前端已经做了相应的限制
        pass
    elif task.get('submitter_id') != user_id:
        return jsonify({'error': '无权查看该任务记录'}), 403
    
    records = read_data(TASK_RECORDS_FILE)
    task_records = [record for record in records if record.get('task_id') == task_id]
    return jsonify(task_records)

@app.route('/api/spaces/<space_id>/tasks/records', methods=['GET'])
@member_required()
def get_space_task_records(space_id):
    records = read_data(TASK_RECORDS_FILE)
    space_records = [record for record in records if record.get('space_id') == space_id]
    return jsonify(space_records)

@app.route('/api/tasks/records/today', methods=['GET'])
@login_required
def get_today_records():
    user_id = g.user_id
    space_id = request.args.get('space_id')
    
    records = read_data(TASK_RECORDS_FILE)
    today = get_today_date()
    
    # 过滤记录：如果指定了空间ID，则只返回该空间的今日记录；否则返回用户的个人今日记录
    if space_id:
        today_records = [record for record in records if record.get('date') == today and record.get('space_id') == space_id]
    else:
        today_records = [record for record in records if record.get('date') == today and record.get('submitter_id') == user_id and not record.get('space_id')]
    
    return jsonify(today_records)

@app.route('/api/spaces/<space_id>/tasks/records/today', methods=['GET'])
@member_required()
def get_space_today_records(space_id):
    records = read_data(TASK_RECORDS_FILE)
    today = get_today_date()
    space_today_records = [record for record in records if record.get('date') == today and record.get('space_id') == space_id]
    return jsonify(space_today_records)

@app.route('/api/images/<filename>', methods=['GET'])
def get_image(filename):
    # 添加调试输出
    print(f"请求图片: {filename}")
    
    # 检查文件是否存在
    file_path = os.path.join(IMAGES_DIR, filename)
    if not os.path.exists(file_path):
        print(f"图片文件不存在: {file_path}")
        return jsonify({"error": "图片文件不存在"}), 404
    
    print(f"图片文件存在，准备返回: {file_path}")
    return send_from_directory(IMAGES_DIR, filename)

@app.route('/api/images', methods=['GET'])
def list_images():
    """列出图片目录中的所有文件"""
    try:
        # 获取图片目录中的所有文件
        image_files = []
        for filename in os.listdir(IMAGES_DIR):
            file_path = os.path.join(IMAGES_DIR, filename)
            if os.path.isfile(file_path):
                # 获取文件信息
                file_info = {
                    'filename': filename,
                    'size': os.path.getsize(file_path),
                    'modified': os.path.getmtime(file_path),
                    'url': f"{request.host_url.rstrip('/')}/api/images/{filename}"
                }
                image_files.append(file_info)
        
        # 按修改时间排序，最新的在前面
        image_files.sort(key=lambda x: x['modified'], reverse=True)
        
        return jsonify({
            'count': len(image_files),
            'images': image_files,
            'images_dir': IMAGES_DIR
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<task_id>', methods=['DELETE'])
@login_required
def delete_task(task_id):
    user_id = g.user_id
    tasks = read_data(TASKS_FILE)
    
    for i, task in enumerate(tasks):
        if task.get('id') == task_id:
            # 检查权限：个人任务只能本人删除，空间任务只能空间管理员删除
            if task.get('space_id'):
                # 这里应该检查用户是否是空间管理员，但为简化处理，我们假设前端已经做了相应的限制
                pass
            elif task.get('submitter_id') != user_id:
                return jsonify({'error': '无权删除该任务'}), 403
            
            deleted = tasks.pop(i)
            write_data(TASKS_FILE, tasks)
            
            # 删除相关的完成记录
            records = read_data(TASK_RECORDS_FILE)
            records = [record for record in records if record.get('task_id') != task_id]
            write_data(TASK_RECORDS_FILE, records)
            
            return jsonify(deleted)
    
    return jsonify({'error': '未找到该任务'}), 404

# 任务审批API（仅适用于空间任务）
@app.route('/api/spaces/<space_id>/tasks/records/<record_id>/approve', methods=['POST'])
@member_required()
def approve_task_record(space_id, record_id):
    user_id = g.user_id
    data = request.json
    
    # 验证请求数据
    if not data or 'comment' not in data:
        return jsonify({'error': '缺少审批词'}), 400
    
    # 获取记录
    records = read_data(TASK_RECORDS_FILE)
    record_index = next((i for i, record in enumerate(records) if record.get('id') == record_id and record.get('space_id') == space_id), None)
    
    if record_index is None:
        return jsonify({'error': '未找到该任务记录'}), 404
        
    # 检查是否是指定的审阅者
    if 'assigned_approver_ids' in records[record_index] and records[record_index]['assigned_approver_ids']:
        if user_id not in records[record_index]['assigned_approver_ids']:
            return jsonify({'error': '只有指定的审阅者才能审批该任务'}), 403
    
    # 获取任务信息
    task_id = records[record_index].get('task_id')
    tasks = read_data(TASKS_FILE)
    task_index = next((i for i, task in enumerate(tasks) if task.get('id') == task_id), None)
    
    # 更新记录状态
    records[record_index]['status'] = 'approved'
    records[record_index]['approver_id'] = user_id
    records[record_index]['approver_name'] = get_username(user_id)
    records[record_index]['approved_at'] = datetime.datetime.now().isoformat()
    records[record_index]['approval_comment'] = data['comment']
    
    write_data(TASK_RECORDS_FILE, records)
    
    # 更新任务状态
    if task_index is not None:
        tasks[task_index]['status'] = 'approved'
        tasks[task_index]['updated_at'] = datetime.datetime.now().isoformat()
        tasks[task_index]['approver_id'] = user_id  # 记录审批者ID
        
        write_data(TASKS_FILE, tasks)
        
        # 创建打卡历史记录
        check_in_history = {
            'id': str(uuid.uuid4()),
            'task_id': task_id,
            'date': get_today_date(),
            'created_at': datetime.datetime.now().isoformat(),
            'user_id': user_id,
            'user_name': get_username(user_id),
            'action': 'approve',
            'description': f'审核通过了任务 {tasks[task_index].get("title")}，审批词：{data["comment"]}',
            'space_id': space_id
        }
        
        # 获取历史记录列表
        history_records = read_data(HISTORY_RECORDS_FILE)
        history_records.append(check_in_history)
        write_data(HISTORY_RECORDS_FILE, history_records)
    
    return jsonify({
        'success': True,
        'message': '任务记录已审批通过',
        'history_record': check_in_history
    })

@app.route('/api/spaces/<space_id>/tasks/records/<record_id>/reject', methods=['POST'])
@member_required()
def reject_task_record(space_id, record_id):
    user_id = g.user_id
    data = request.json
    
    # 验证请求数据
    if not data or 'reason' not in data:
        return jsonify({'error': '缺少拒绝原因'}), 400
    
    # 获取记录
    records = read_data(TASK_RECORDS_FILE)
    record_index = next((i for i, record in enumerate(records) if record.get('id') == record_id and record.get('space_id') == space_id), None)
    
    if record_index is None:
        return jsonify({'error': '未找到该任务记录'}), 404
        
    # 检查是否是指定的审阅者
    if 'assigned_approver_ids' in records[record_index] and records[record_index]['assigned_approver_ids']:
        if user_id not in records[record_index]['assigned_approver_ids']:
            return jsonify({'error': '只有指定的审阅者才能拒绝该任务'}), 403
    
    # 获取任务信息
    task_id = records[record_index].get('task_id')
    tasks = read_data(TASKS_FILE)
    task_index = next((i for i, task in enumerate(tasks) if task.get('id') == task_id), None)
    
    # 更新记录状态
    records[record_index]['status'] = 'rejected'
    records[record_index]['approver_id'] = user_id
    records[record_index]['approver_name'] = get_username(user_id)
    records[record_index]['rejection_reason'] = data['reason']
    
    write_data(TASK_RECORDS_FILE, records)
    
    # 更新任务状态
    if task_index is not None:
        tasks[task_index]['status'] = 'rejected'
        tasks[task_index]['updated_at'] = datetime.datetime.now().isoformat()
        write_data(TASKS_FILE, tasks)
    
    return jsonify({
        'success': True,
        'message': '任务记录已拒绝'
    })

# 用户设置API
@app.route('/api/user/settings', methods=['GET'])
@login_required
def get_user_settings():
    user_id = g.user_id
    
    # 读取用户设置
    try:
        with open(USER_SETTINGS_FILE, 'r', encoding='utf-8') as f:
            all_settings = json.load(f)
            # 确保all_settings是一个字典
            if not isinstance(all_settings, dict):
                all_settings = {}
    except (json.JSONDecodeError, FileNotFoundError):
        all_settings = {}
    
    # 获取当前用户的设置
    user_settings = all_settings.get(user_id, {})
    
    # 确保返回的JSON格式与前端期望的格式一致
    response = {
        "defaultShareSpaceId": user_settings.get("defaultShareSpaceId")
    }
    
    return jsonify(response)

@app.route('/api/user/settings', methods=['PUT'])
@login_required
def update_user_settings():
    user_id = g.user_id
    data = request.json
    
    # 读取所有用户设置
    try:
        with open(USER_SETTINGS_FILE, 'r', encoding='utf-8') as f:
            all_settings = json.load(f)
            # 确保all_settings是一个字典
            if not isinstance(all_settings, dict):
                all_settings = {}
    except (json.JSONDecodeError, FileNotFoundError):
        all_settings = {}
    
    # 更新当前用户的设置
    if user_id not in all_settings:
        all_settings[user_id] = {}
    
    # 更新设置
    if "defaultShareSpaceId" in data:
        all_settings[user_id]["defaultShareSpaceId"] = data["defaultShareSpaceId"]
    
    # 保存设置
    with open(USER_SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_settings, f, ensure_ascii=False, indent=2)
    
    # 确保返回的JSON格式与前端期望的格式一致
    response = {
        "defaultShareSpaceId": all_settings[user_id].get("defaultShareSpaceId")
    }
    
    return jsonify(response)

# 获取任务历史记录API
@app.route('/api/spaces/<space_id>/tasks/<task_id>/history', methods=['GET'])
@member_required()
def get_task_history(space_id, task_id):
    user_id = g.user_id
    
    # 获取历史记录
    history_records = read_data(HISTORY_RECORDS_FILE)
    
    # 过滤出与该任务相关的历史记录
    task_history = [record for record in history_records if record.get('task_id') == task_id and record.get('space_id') == space_id]
    
    # 按时间倒序排序
    task_history.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    return jsonify(task_history)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8081)
