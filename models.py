from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from enum import Enum

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'user'
    
    user_id = db.Column(db.Integer, primary_key=True, comment='用户ID')
    username = db.Column(db.String(20), unique=True, nullable=False, comment='用户名，唯一')
    password_hash = db.Column(db.String(128), nullable=False, comment='密码哈希值')
    email = db.Column(db.String(50), unique=True, nullable=False, comment='邮箱，唯一')
    phone = db.Column(db.String(15), comment='手机号，可选')
    address = db.Column(db.String(200), nullable=True, comment='街道级地址')
    latitude = db.Column(db.Numeric(9, 6), comment='用户注册地址的纬度')
    longitude = db.Column(db.Numeric(9, 6), comment='用户注册地址的经度')
    reputation_score = db.Column(db.Float, default=5.0, comment='信誉评分，范围1.0-5.0')
    is_admin = db.Column(db.Boolean, default=False, comment='是否为管理员')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='用户注册时间')
    
    # 关系
    items = db.relationship('Item', backref='owner', lazy='dynamic', cascade='all, delete-orphan')
    requests = db.relationship('Request', backref='requester', lazy='dynamic', cascade='all, delete-orphan')
    reviews_given = db.relationship('Review', foreign_keys='Review.reviewer_id', backref='reviewer', lazy='dynamic')
    reviews_received = db.relationship('Review', foreign_keys='Review.reviewee_id', backref='reviewee', lazy='dynamic')
    messages_received = db.relationship('Message', foreign_keys='Message.recipient_id', backref='recipient', lazy='dynamic')
    messages_sent = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy='dynamic')
    
    def set_password(self, password):
        """设置密码哈希"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """验证密码"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self, include_sensitive=False):
        """转换为字典"""
        data = {
            'user_id': self.user_id,
            'username': self.username,
            'email': self.email if include_sensitive else None,
            'phone': self.phone if include_sensitive else None,
            'address': self.address if include_sensitive else None,
            'latitude': float(self.latitude) if self.latitude else None,
            'longitude': float(self.longitude) if self.longitude else None,
            'reputation_score': self.reputation_score,
            'is_admin': self.is_admin if include_sensitive else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        return {k: v for k, v in data.items() if v is not None}

class ItemCategory(db.Model):
    __tablename__ = 'item_category'
    
    category_id = db.Column(db.Integer, primary_key=True, comment='分类ID')
    name = db.Column(db.String(50), nullable=False, comment='分类名称')
    parent_id = db.Column(db.Integer, db.ForeignKey('item_category.category_id'), comment='父分类ID')
    
    # 关系
    children = db.relationship('ItemCategory', backref=db.backref('parent', remote_side=[category_id]), lazy='dynamic')
    items = db.relationship('Item', backref='category', lazy='dynamic')
    
    def to_dict(self, include_children=False):
        """转换为字典"""
        data = {
            'category_id': self.category_id,
            'name': self.name,
            'parent_id': self.parent_id
        }
        if include_children:
            data['children'] = [child.to_dict() for child in self.children]
        return data

class Item(db.Model):
    __tablename__ = 'item'
    
    item_id = db.Column(db.Integer, primary_key=True, comment='物品ID')
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False, comment='发布者ID')
    title = db.Column(db.String(100), nullable=False, comment='物品标题')
    description = db.Column(db.Text, nullable=False, comment='物品详细描述')
    category_id = db.Column(db.Integer, db.ForeignKey('item_category.category_id'), nullable=False, comment='分类ID')
    status = db.Column(db.Enum('available', 'reserved', 'completed', 'cancelled', name='item_status'), 
                      nullable=False, default='available', comment='物品状态')
    condition = db.Column(db.Enum('new', 'like_new', 'used', 'worn', name='item_condition'), 
                         nullable=False, comment='新旧程度')
    latitude = db.Column(db.Numeric(9, 6), comment='物品发布地点的纬度')
    longitude = db.Column(db.Numeric(9, 6), comment='物品发布地点的经度')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='物品发布时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='物品信息最后更新时间')
    
    # 关系
    images = db.relationship('ItemImage', backref='item', lazy='dynamic', cascade='all, delete-orphan')
    requests = db.relationship('Request', backref='item', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self, include_images=True):
        """转换为字典"""
        data = {
            'item_id': self.item_id,
            'user_id': self.user_id,
            'title': self.title,
            'description': self.description,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else None,
            'status': self.status,
            'condition': self.condition,
            'latitude': float(self.latitude) if self.latitude else None,
            'longitude': float(self.longitude) if self.longitude else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'owner_username': self.owner.username if self.owner else None
        }
        if include_images:
            data['images'] = [img.to_dict() for img in self.images]
        return data

class ItemImage(db.Model):
    __tablename__ = 'item_image'
    
    image_id = db.Column(db.Integer, primary_key=True, comment='图片ID')
    item_id = db.Column(db.Integer, db.ForeignKey('item.item_id'), nullable=False, comment='所属物品ID')
    image_url = db.Column(db.String(255), nullable=False, comment='图片存储路径')
    is_primary = db.Column(db.Boolean, default=False, comment='是否为主图')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='图片上传时间')
    
    def to_dict(self):
        """转换为字典"""
        return {
            'image_id': self.image_id,
            'item_id': self.item_id,
            'image_url': self.image_url,
            'is_primary': self.is_primary,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Request(db.Model):
    __tablename__ = 'request'
    
    request_id = db.Column(db.Integer, primary_key=True, comment='请求ID')
    item_id = db.Column(db.Integer, db.ForeignKey('item.item_id'), nullable=False, comment='目标物品ID')
    requester_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False, comment='请求者ID')
    message = db.Column(db.String(200), comment='附言')
    status = db.Column(db.Enum('pending', 'accepted', 'rejected', 'cancelled', name='request_status'), 
                      nullable=False, default='pending', comment='请求状态')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='请求时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='请求状态最后更新时间')
    
    # 关系
    review = db.relationship('Review', backref='request', uselist=False, cascade='all, delete-orphan')
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.request_id,
            'request_id': self.request_id,
            'item_id': self.item_id,
            'item_title': self.item.title if self.item else None,
            'requester_id': self.requester_id,
            'requester_username': self.requester.username if self.requester else None,
            'message': self.message,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Review(db.Model):
    __tablename__ = 'review'
    
    review_id = db.Column(db.Integer, primary_key=True, comment='评价ID')
    request_id = db.Column(db.Integer, db.ForeignKey('request.request_id'), unique=True, nullable=False, comment='关联的请求ID')
    reviewer_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False, comment='评价人ID')
    reviewee_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False, comment='被评价人ID')
    rating = db.Column(db.SmallInteger, nullable=False, comment='评分（1-5分）')
    comment = db.Column(db.String(200), comment='文字评价')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='评价时间')
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.review_id,
            'review_id': self.review_id,
            'request_id': self.request_id,
            'reviewer_id': self.reviewer_id,
            'reviewer_username': self.reviewer.username if self.reviewer else None,
            'reviewee_id': self.reviewee_id,
            'reviewee_username': self.reviewee.username if self.reviewee else None,
            'rating': self.rating,
            'comment': self.comment,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Message(db.Model):
    __tablename__ = 'message'
    
    message_id = db.Column(db.Integer, primary_key=True, comment='消息ID')
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False, comment='消息接收者ID')
    sender_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), comment='消息发送者ID')
    type = db.Column(db.Enum('request_notification', 'status_update', 'system_announcement', 'chat_message', name='message_type'), 
                    nullable=False, comment='消息类型')
    related_id = db.Column(db.Integer, comment='关联的业务ID')
    content = db.Column(db.Text, nullable=False, comment='消息内容')
    is_read = db.Column(db.Boolean, default=False, comment='是否已读')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='消息创建时间')
    
    def to_dict(self):
        """转换为字典"""
        return {
            'message_id': self.message_id,
            'recipient_id': self.recipient_id,
            'sender_id': self.sender_id,
            'sender_username': self.sender.username if self.sender else 'System',
            'type': self.type,
            'related_id': self.related_id,
            'content': self.content,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }