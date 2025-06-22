#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户认证功能测试文件

这个文件演示了如何使用改进后的 get_current_user() 函数
以及相关的认证辅助函数。
"""

from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token
from utils import get_current_user, get_current_user_id, is_authenticated, admin_required
from models import User, db
from config import Config

def test_get_current_user():
    """
    测试 get_current_user() 函数的功能
    
    这个函数演示了在不同情况下 get_current_user() 的行为：
    1. 有有效JWT token时 - 返回真实用户对象
    2. 没有JWT token时 - 返回MockUser对象（兼容性）
    3. JWT token无效时 - 返回MockUser对象
    """
    print("=== 测试 get_current_user() 函数 ===")
    
    # 情况1：没有JWT token（模拟未登录状态）
    print("\n1. 未登录状态：")
    user = get_current_user()
    print(f"用户类型: {type(user).__name__}")
    print(f"用户ID: {user.user_id}")
    print(f"用户名: {user.username}")
    print(f"是否管理员: {user.is_admin}")
    
    # 情况2：检查认证状态
    print("\n2. 认证状态检查：")
    print(f"是否已认证: {is_authenticated()}")
    print(f"当前用户ID: {get_current_user_id()}")

def create_test_route(app):
    """
    创建测试路由来演示认证功能
    """
    
    @app.route('/test/current-user', methods=['GET'])
    def test_current_user_route():
        """测试获取当前用户信息的路由"""
        user = get_current_user()
        
        return jsonify({
            'success': True,
            'data': {
                'user_type': type(user).__name__,
                'user_id': user.user_id,
                'username': user.username,
                'is_admin': user.is_admin,
                'is_authenticated': is_authenticated(),
                'current_user_id': get_current_user_id()
            }
        })
    
    @app.route('/test/admin-only', methods=['GET'])
    @admin_required
    def test_admin_route():
        """测试管理员权限的路由"""
        user = get_current_user()
        return jsonify({
            'success': True,
            'message': '管理员权限验证成功',
            'admin_user': {
                'user_id': user.user_id,
                'username': user.username,
                'is_admin': user.is_admin
            }
        })
    
    @app.route('/test/login-demo', methods=['POST'])
    def test_login_demo():
        """演示登录并获取token的过程"""
        data = request.get_json()
        username = data.get('username')
        
        # 查找用户（这里简化处理）
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({
                'success': False,
                'message': '用户不存在'
            }), 404
        
        # 创建JWT token
        access_token = create_access_token(identity=user.user_id)
        
        return jsonify({
            'success': True,
            'message': '登录成功',
            'data': {
                'user_id': user.user_id,
                'username': user.username,
                'token': access_token
            }
        })

def usage_examples():
    """
    使用示例和最佳实践
    """
    print("\n=== 使用示例 ===")
    
    print("\n1. 在API路由中使用：")
    print("""
    @app.route('/api/my-items', methods=['GET'])
    def get_my_items():
        # 获取当前用户
        current_user = get_current_user()
        
        # 检查是否为真实用户（非MockUser）
        if isinstance(current_user, User):
            # 用户已登录，返回其物品
            items = Item.query.filter_by(owner_id=current_user.user_id).all()
            return success_response([item.to_dict() for item in items])
        else:
            # 用户未登录
            return error_response('请先登录', 401)
    """)
    
    print("\n2. 检查用户权限：")
    print("""
    @app.route('/api/admin/users', methods=['GET'])
    def get_all_users():
        current_user = get_current_user()
        
        # 检查管理员权限
        if not (isinstance(current_user, User) and current_user.is_admin):
            return error_response('需要管理员权限', 403)
        
        # 管理员操作...
        users = User.query.all()
        return success_response([user.to_dict() for user in users])
    """)
    
    print("\n3. 使用辅助函数：")
    print("""
    # 检查是否已认证
    if is_authenticated():
        user_id = get_current_user_id()
        print(f'当前用户ID: {user_id}')
    
    # 获取用户对象
    user = get_current_user()
    if isinstance(user, User):
        print(f'真实用户: {user.username}')
    else:
        print('未登录用户（MockUser）')
    """)

if __name__ == '__main__':
    print("用户认证功能测试")
    print("==================")
    
    # 运行测试
    test_get_current_user()
    
    # 显示使用示例
    usage_examples()
    
    print("\n=== 测试完成 ===")
    print("\n注意事项：")
    print("1. get_current_user() 现在会尝试从JWT token获取真实用户")
    print("2. 如果没有有效token，会返回MockUser对象保持兼容性")
    print("3. 使用 isinstance(user, User) 来检查是否为真实用户")
    print("4. admin_required 装饰器现在会验证JWT token和管理员权限")
    print("5. 新增了 is_authenticated() 和 get_current_user_id() 辅助函数")