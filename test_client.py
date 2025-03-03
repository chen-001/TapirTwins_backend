#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import uuid
import datetime

# 模拟数据目录和文件
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
dreams_file = os.path.join(data_dir, 'dreams.json')

# 读取现有梦境数据
with open(dreams_file, 'r') as f:
    dreams = json.load(f)

# 显示当前梦境总数
print(f"当前梦境总数: {len(dreams)}")

# 准备测试数据 - 两个用户的相同梦境内容
test_dream = {
    'title': '测试梦境',
    'content': '这是一个用于测试相同梦境ID的梦境内容',
    'date': datetime.datetime.now().strftime('%Y-%m-%d')
}

# 模拟修改前的代码逻辑（每次生成新ID）
user1_dream = test_dream.copy()
user1_dream['id'] = str(uuid.uuid4())
user1_dream['user_id'] = 'user1'
user1_dream['created_at'] = datetime.datetime.now().isoformat()

user2_dream = test_dream.copy()
user2_dream['id'] = str(uuid.uuid4())
user2_dream['user_id'] = 'user2'
user2_dream['created_at'] = datetime.datetime.now().isoformat()

print("\n修改前的逻辑 - 每次生成新ID:")
print(f"用户1的梦境ID: {user1_dream['id']}")
print(f"用户2的梦境ID: {user2_dream['id']}")
print(f"ID是否相同: {user1_dream['id'] == user2_dream['id']}")

# 模拟修改后的代码逻辑
def find_existing_dream(dreams, title, content):
    for dream in dreams:
        if dream.get('title') == title and dream.get('content') == content:
            return dream
    return None

def add_dream_new_logic(dreams, title, content, user_id):
    existing_dream = find_existing_dream(dreams, title, content)
    
    if existing_dream:
        new_id = existing_dream['id']
    else:
        new_id = str(uuid.uuid4())
    
    new_dream = {
        'id': new_id,
        'title': title,
        'content': content,
        'user_id': user_id,
        'created_at': datetime.datetime.now().isoformat(),
        'date': datetime.datetime.now().strftime('%Y-%m-%d')
    }
    
    duplicate = next((d for d in dreams if d.get('user_id') == user_id 
                     and d.get('title') == title and d.get('content') == content), None)
    
    if not duplicate:
        dreams.append(new_dream)
    
    return new_dream

# 使用新逻辑测试（模拟两个用户依次添加相同内容梦境）
test_dreams = []  # 新的测试数据集

user1_dream_new = add_dream_new_logic(test_dreams, test_dream['title'], test_dream['content'], 'user1')
user2_dream_new = add_dream_new_logic(test_dreams, test_dream['title'], test_dream['content'], 'user2')

print("\n修改后的逻辑 - 相同内容使用相同ID:")
print(f"用户1的梦境ID: {user1_dream_new['id']}")
print(f"用户2的梦境ID: {user2_dream_new['id']}")
print(f"ID是否相同: {user1_dream_new['id'] == user2_dream_new['id']}")
print(f"测试数据集中的梦境数量: {len(test_dreams)}")

print("\n测试完成，未修改实际数据。") 