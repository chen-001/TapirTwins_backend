#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 数据模型定义

# 用户模型
class User:
    def __init__(self, id, username, password_hash, email, created_at, updated_at):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.email = email
        self.created_at = created_at
        self.updated_at = updated_at
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @staticmethod
    def from_dict(data):
        return User(
            id=data.get('id'),
            username=data.get('username'),
            password_hash=data.get('password_hash'),
            email=data.get('email'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )

# 空间成员角色枚举
class MemberRole:
    SUBMITTER = "submitter"  # 打卡者
    APPROVER = "approver"    # 审批者
    ADMIN = "admin"          # 管理员（创建者）

# 空间成员模型
class SpaceMember:
    def __init__(self, user_id, role):
        self.user_id = user_id
        self.role = role
    
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'role': self.role
        }
    
    @staticmethod
    def from_dict(data):
        return SpaceMember(
            user_id=data.get('user_id'),
            role=data.get('role')
        )

# 空间模型
class Space:
    def __init__(self, id, name, description, creator_id, members, created_at, updated_at, invite_code=None):
        self.id = id
        self.name = name
        self.description = description
        self.creator_id = creator_id
        self.members = members  # 成员列表，包含用户ID和角色（打卡者/审批者）
        self.created_at = created_at
        self.updated_at = updated_at
        self.invite_code = invite_code  # 邀请码
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'creator_id': self.creator_id,
            'members': [member.to_dict() for member in self.members],
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'invite_code': self.invite_code
        }
    
    @staticmethod
    def from_dict(data):
        return Space(
            id=data.get('id'),
            name=data.get('name'),
            description=data.get('description'),
            creator_id=data.get('creator_id'),
            members=[SpaceMember.from_dict(member) for member in data.get('members', [])],
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
            invite_code=data.get('invite_code')
        )

# 扩展任务模型
class Task:
    def __init__(self, id, space_id, title, description, due_date, created_at, updated_at, 
                 completed_today, required_images, status="pending", submitter_id=None, 
                 approver_id=None, missed_dates=None):
        self.id = id
        self.space_id = space_id
        self.title = title
        self.description = description
        self.due_date = due_date
        self.created_at = created_at
        self.updated_at = updated_at
        self.completed_today = completed_today
        self.required_images = required_images
        self.status = status  # pending, submitted, approved, rejected
        self.submitter_id = submitter_id  # 打卡者ID
        self.approver_id = approver_id    # 审批者ID
        self.missed_dates = missed_dates or []  # 缺卡日期列表
    
    def to_dict(self):
        return {
            'id': self.id,
            'space_id': self.space_id,
            'title': self.title,
            'description': self.description,
            'due_date': self.due_date,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'completed_today': self.completed_today,
            'required_images': self.required_images,
            'status': self.status,
            'submitter_id': self.submitter_id,
            'approver_id': self.approver_id,
            'missed_dates': self.missed_dates
        }
    
    @staticmethod
    def from_dict(data):
        return Task(
            id=data.get('id'),
            space_id=data.get('space_id'),
            title=data.get('title'),
            description=data.get('description'),
            due_date=data.get('due_date'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
            completed_today=data.get('completed_today', False),
            required_images=data.get('required_images', 0),
            status=data.get('status', 'pending'),
            submitter_id=data.get('submitter_id'),
            approver_id=data.get('approver_id'),
            missed_dates=data.get('missed_dates', [])
        )

# 扩展任务记录模型
class TaskRecord:
    def __init__(self, id, task_id, date, created_at, images, submitter_id, 
                 status="submitted", approver_id=None, approved_at=None, 
                 rejection_reason=None, space_id=None):
        self.id = id
        self.task_id = task_id
        self.date = date
        self.created_at = created_at
        self.images = images
        self.submitter_id = submitter_id
        self.status = status  # submitted, approved, rejected
        self.approver_id = approver_id
        self.approved_at = approved_at
        self.rejection_reason = rejection_reason
        self.space_id = space_id
    
    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'date': self.date,
            'created_at': self.created_at,
            'images': self.images,
            'submitter_id': self.submitter_id,
            'status': self.status,
            'approver_id': self.approver_id,
            'approved_at': self.approved_at,
            'rejection_reason': self.rejection_reason,
            'space_id': self.space_id
        }
    
    @staticmethod
    def from_dict(data):
        return TaskRecord(
            id=data.get('id'),
            task_id=data.get('task_id'),
            date=data.get('date'),
            created_at=data.get('created_at'),
            images=data.get('images', []),
            submitter_id=data.get('submitter_id'),
            status=data.get('status', 'submitted'),
            approver_id=data.get('approver_id'),
            approved_at=data.get('approved_at'),
            rejection_reason=data.get('rejection_reason'),
            space_id=data.get('space_id')
        )

# 梦境模型扩展
class Dream:
    def __init__(self, id, title, content, date, created_at, updated_at=None, space_id=None, user_id=None):
        self.id = id
        self.title = title
        self.content = content
        self.date = date
        self.created_at = created_at
        self.updated_at = updated_at
        self.space_id = space_id  # 新增：空间ID
        self.user_id = user_id    # 新增：用户ID
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'date': self.date,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'space_id': self.space_id,
            'user_id': self.user_id
        }
    
    @staticmethod
    def from_dict(data):
        return Dream(
            id=data.get('id'),
            title=data.get('title'),
            content=data.get('content'),
            date=data.get('date'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
            space_id=data.get('space_id'),
            user_id=data.get('user_id')
        )
