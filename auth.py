from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from models import User, db
from utils import success_response, error_response, validate_required_fields, get_current_user
import re

auth_bp = Blueprint('auth', __name__, url_prefix='/api/v1/users')

def validate_email(email):
    """验证邮箱格式"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone):
    """验证手机号格式"""
    if not phone:
        return True  # 手机号可选
    pattern = r'^1[3-9]\d{9}$'
    return re.match(pattern, phone) is not None

@auth_bp.route('/register', methods=['POST'])
def register():
    """用户注册"""
    try:
        data = request.get_json()
        if not data:
            return error_response("请求数据不能为空")
        
        # 验证必需字段
        required_fields = ['username', 'password', 'email', 'address']
        validation_error = validate_required_fields(data, required_fields)
        if validation_error:
            return error_response(validation_error)
        
        username = data['username'].strip()
        password = data['password']
        email = data['email'].strip().lower()
        phone = data.get('phone', '').strip()
        address = data['address'].strip()
        
        # 验证数据格式
        if len(username) < 2 or len(username) > 20:
            return error_response("用户名长度必须在2-20个字符之间")
        
        if len(password) < 6 or len(password) > 20:
            return error_response("密码长度必须在6-20个字符之间")
        
        if not validate_email(email):
            return error_response("邮箱格式不正确")
        
        if phone and not validate_phone(phone):
            return error_response("手机号格式不正确")
        
        if len(address) < 5 or len(address) > 200:
            return error_response("地址长度必须在5-200个字符之间")
        
        # 检查用户名和邮箱是否已存在
        if User.query.filter_by(username=username).first():
            return error_response("用户名已存在")
        
        if User.query.filter_by(email=email).first():
            return error_response("邮箱已被注册")
        
        # 创建新用户
        user = User(
            username=username,
            email=email,
            phone=phone if phone else None,
            address=address
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        return success_response(
            data={
                'user_id': user.user_id,
                'username': user.username,
                'email': user.email
            },
            message="用户注册成功",
            code=201
        )
        
    except Exception as e:
        db.session.rollback()
        return error_response(f"注册失败: {str(e)}", 500)

@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    try:
        data = request.get_json()
        if not data:
            return error_response("请求数据不能为空")
        
        username_or_email = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username_or_email or not password:
            return error_response("用户名/邮箱和密码不能为空")
        
        # 查找用户（支持用户名或邮箱登录）
        user = User.query.filter(
            (User.username == username_or_email) | 
            (User.email == username_or_email.lower())
        ).first()
        
        if not user or not user.check_password(password):
            return error_response("用户名或密码错误", 401)
        
        # 生成JWT token
        access_token = create_access_token(identity=user.user_id)
        
        return success_response(
            data={
                'user_id': user.user_id,
                'username': user.username,
                'token': access_token,
                'is_admin': user.is_admin
            },
            message="登录成功"
        )
        
    except Exception as e:
        return error_response(f"登录失败: {str(e)}", 500)

@auth_bp.route('/admin/login', methods=['POST'])
def admin_login():
    """管理员登录"""
    try:
        data = request.get_json()
        if not data:
            return error_response("请求数据不能为空")
        
        username_or_email = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username_or_email or not password:
            return error_response("用户名/邮箱和密码不能为空")
        
        # 查找用户（支持用户名或邮箱登录）
        user = User.query.filter(
            (User.username == username_or_email) | 
            (User.email == username_or_email.lower())
        ).first()
        
        if not user or not user.check_password(password):
            return error_response("用户名或密码错误", 401)
        
        # 检查是否为管理员
        if not user.is_admin:
            return error_response("权限不足，仅限管理员登录", 403)
        
        return success_response(
            data={
                'user_id': user.user_id,
                'username': user.username,
                'is_admin': user.is_admin
            },
            message="管理员登录成功"
        )
        
    except Exception as e:
        return error_response(f"登录失败: {str(e)}", 500)

@auth_bp.route('/verify', methods=['GET'])
def verify_token():
    """简单验证（无token验证）"""
    try:
        # 简单返回成功，不做任何验证
        return success_response(
            data={
                'user_id': 1,
                'username': 'admin',
                'is_admin': True
            },
            message="验证成功"
        )
        
    except Exception as e:
        return error_response(f"验证失败: {str(e)}", 401)

@auth_bp.route('/me', methods=['GET'])
def get_current_user_info():
    """获取当前用户信息（简化版）"""
    try:
        # 简化版本，返回固定的管理员信息
        return success_response(
            data={
                'user_id': 1,
                'username': 'admin',
                'email': 'admin@qq.com',
                'is_admin': True
            },
            message="获取用户信息成功"
        )
        
    except Exception as e:
        return error_response(f"获取用户信息失败: {str(e)}", 500)

@auth_bp.route('/verify', methods=['GET'])
def verify_user():
    """验证用户身份（简化版）"""
    try:
        # 简化版本，直接返回管理员身份
        return success_response(
            data={
                'user_id': 1,
                'username': 'admin',
                'email': 'admin@qq.com',
                'is_admin': True
            },
            message="用户验证成功"
        )
        
    except Exception as e:
        return error_response(f"用户验证失败: {str(e)}", 500)

@auth_bp.route('/me', methods=['PUT'])
def update_current_user_info():
    """更新当前用户信息（简化版）"""
    try:
        # 简化版本，直接返回成功
        return success_response(
            data={
                'user_id': 1,
                'username': 'admin',
                'email': 'admin@qq.com',
                'is_admin': True
            },
            message="用户信息更新成功"
        )
        
    except Exception as e:
        return error_response(f"更新用户信息失败: {str(e)}", 500)

@auth_bp.route('/<int:user_id>', methods=['GET'])
def get_user_info(user_id):
    """获取指定用户的公开信息"""
    print(f"调用获取用户信息接口,用户为：{user_id}")
    try:
        user = User.query.get(user_id)
        if not user:
            return error_response("用户不存在", 404)
        
        # 获取当前登录用户（如果有）
        current_user = get_current_user()
        include_sensitive = current_user and (current_user.user_id == user_id or current_user.is_admin)
        
        # 添加用户统计信息
        # user_data = user.to_dict(include_sensitive=include_sensitive)
        user_data = user.to_dict(include_sensitive=True)# 直接获取敏感数据
        
        # 发布物品数量
        user_data['items_count'] = user.items.count()
        
        # 交易次数（已完成的请求数量）
        from models import Request
        completed_requests = Request.query.filter(
            ((Request.requester_id == user_id) | (Request.item.has(user_id=user_id))) &
            (Request.status == 'completed')
        ).count()
        user_data['transactions_count'] = completed_requests
        
        # 最后登录时间（暂时使用注册时间，因为没有last_login字段）
        user_data['last_login'] = user.created_at.isoformat() if user.created_at else None
        
        return success_response(
            data=user_data,
            message="获取用户信息成功"
        )
        
    except Exception as e:
        return error_response(f"获取用户信息失败: {str(e)}", 500)

@auth_bp.route('', methods=['GET'])
def get_all_users():
    """获取所有用户列表（管理员功能）"""
    try:
        # 检查是否为管理员
        current_user = get_current_user()
        if not current_user or not current_user.is_admin:
            return error_response("需要管理员权限", 403)
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '').strip()
        
        query = User.query
        
        # 搜索功能
        if search:
            query = query.filter(
                (User.username.contains(search)) |
                (User.email.contains(search))
            )
        
        query = query.order_by(User.created_at.desc())
        
        # 手动分页处理，避免使用可能有问题的paginate_query
        try:
            page = max(1, page)
            per_page = min(max(1, per_page), 100)
            
            total = query.count()
            users = query.offset((page - 1) * per_page).limit(per_page).all()
            
            # 转换用户数据
            user_list = []
            for user in users:
                try:
                    user_data = user.to_dict(include_sensitive=True)
                    # 安全地获取关联数据计数
                    try:
                        user_data['items_count'] = user.items.count()
                    except Exception:
                        user_data['items_count'] = 0
                    
                    try:
                        user_data['requests_count'] = user.requests.count()
                    except Exception:
                        user_data['requests_count'] = 0
                    
                    # 添加交易次数统计
                    try:
                        from models import Request
                        completed_requests = Request.query.filter(
                            ((Request.requester_id == user.user_id) | (Request.item.has(user_id=user.user_id))) &
                            (Request.status == 'completed')
                        ).count()
                        user_data['transactions_count'] = completed_requests
                    except Exception:
                        user_data['transactions_count'] = 0
                    
                    # 添加最后登录时间
                    user_data['last_login'] = user.created_at.isoformat() if user.created_at else None
                    
                    user_list.append(user_data)
                except Exception as e:
                    # 如果单个用户数据转换失败，跳过该用户
                    print(f"转换用户数据失败 (user_id: {user.user_id}): {str(e)}")
                    continue
            
            # 计算分页信息
            pages = (total + per_page - 1) // per_page
            
            result = {
                'items': user_list,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': pages,
                    'has_prev': page > 1,
                    'has_next': page < pages
                }
            }
            
            return success_response(
                data=result,
                message="获取用户列表成功"
            )
            
        except Exception as db_error:
            print(f"数据库查询错误: {str(db_error)}")
            return error_response(f"数据库查询失败: {str(db_error)}", 500)
        
    except Exception as e:
        print(f"获取用户列表失败: {str(e)}")
        return error_response(f"获取用户列表失败: {str(e)}", 500)

@auth_bp.route('/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """删除用户（管理员功能）"""
    import traceback
    print(f"开始删除用户，用户ID: {user_id}")
    try:
        # 检查是否为管理员
        current_user = get_current_user()
        print(f"当前用户: {current_user.username if current_user else 'None'}")
        if not current_user or not current_user.is_admin:
            return error_response("需要管理员权限", 403)
        
        # 查找要删除的用户
        user = User.query.get(user_id)
        if not user:
            return error_response("用户不存在", 404)
        
        # 不能删除管理员用户
        if user.is_admin:
            return error_response("不能删除管理员用户", 400)
        
        # 不能删除自己
        if user.user_id == current_user.user_id:
            return error_response("不能删除自己的账户", 400)
        
        # 检查用户是否有未完成的交易
        from models import Request, Item
        # 查询用户作为请求者的未完成交易
        requester_pending = Request.query.filter(
            (Request.requester_id == user_id) &
            (Request.status.in_(['pending', 'accepted']))
        ).count()
        
        # 查询用户作为物品拥有者的未完成交易
        owner_pending = Request.query.join(Item).filter(
            (Item.user_id == user_id) &
            (Request.status.in_(['pending', 'accepted']))
        ).count()
        
        pending_requests = requester_pending + owner_pending
        
        if pending_requests > 0:
            print(f"用户 {user.username} 还有未完成的交易")
            return error_response("该用户还有未完成的交易，无法删除", 400)
        
        # 删除用户相关数据
        try:
            # 删除用户的物品
            from models import Item
            user_items = Item.query.filter_by(user_id=user_id).all()
            for item in user_items:
                db.session.delete(item)
            
            # 删除用户的评价
            from models import Review
            user_reviews = Review.query.filter(
                (Review.reviewer_id == user_id) | (Review.reviewee_id == user_id)
            ).all()
            for review in user_reviews:
                db.session.delete(review)
            
            # 删除用户的消息
            from models import Message
            user_messages = Message.query.filter(
                (Message.sender_id == user_id) | (Message.recipient_id == user_id)
            ).all()
            for message in user_messages:
                db.session.delete(message)
            
            # 删除用户作为请求者的请求
            requester_requests = Request.query.filter_by(requester_id=user_id).all()
            for request in requester_requests:
                db.session.delete(request)
            
            # 删除用户作为物品拥有者收到的请求
            owner_requests = Request.query.join(Item).filter(Item.user_id == user_id).all()
            for request in owner_requests:
                db.session.delete(request)
            
            # 最后删除用户
            db.session.delete(user)
            db.session.commit()
            
            return success_response(
                message=f"用户 {user.username} 已成功删除"
            )
            
        except Exception as delete_error:
            db.session.rollback()
            print(f"删除用户数据时出错: {str(delete_error)}")
            print(f"错误堆栈: {traceback.format_exc()}")
            return error_response(f"删除用户数据时出错: {str(delete_error)}", 500)
        
    except Exception as e:
        db.session.rollback()
        print(f"删除用户失败: {str(e)}")
        print(f"错误堆栈: {traceback.format_exc()}")
        return error_response(f"删除用户失败: {str(e)}", 500)