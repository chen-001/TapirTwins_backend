#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os

# 获取数据文件路径
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
dreams_file = os.path.join(data_dir, 'dreams.json')
interpretations_file = os.path.join(data_dir, 'dream_interpretations.json')

# 读取梦境数据
with open(dreams_file, 'r') as f:
    dreams = json.load(f)

# 读取解梦数据
with open(interpretations_file, 'r') as f:
    interpretations = json.load(f)

print(f'梦境总数: {len(dreams)}')
print(f'解梦总数: {len(interpretations)}')

# 检查相同内容的梦境是否有不同的ID
titles = {}
for dream in dreams:
    title = dream.get('title')
    content = dream.get('content')
    key = (title, content)
    if key not in titles:
        titles[key] = []
    titles[key].append(dream.get('id'))

print("\n相同内容的梦境检查:")
found_duplicates = False
for key, ids in titles.items():
    if len(ids) > 1:
        found_duplicates = True
        print(f'发现内容相同但ID不同的梦境: {key[0]} - {key[1][:20]}... IDs: {ids}')

if not found_duplicates:
    print("没有发现内容相同但ID不同的梦境。")

# 检查每个解梦对应的梦境
print("\n解梦与梦境的对应关系:")
dream_ids = {dream.get('id'): (dream.get('title'), dream.get('content')) for dream in dreams}
for interp in interpretations:
    dream_id = interp.get('dream_id')
    if dream_id in dream_ids:
        print(f"解梦ID: {interp.get('id')[:8]}... 梦境ID: {dream_id[:8]}... 梦境: {dream_ids[dream_id][0]}")
    else:
        print(f"警告：解梦ID: {interp.get('id')} 引用了不存在的梦境ID: {dream_id}") 