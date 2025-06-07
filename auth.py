from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
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

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user_info():
    """获取当前用户信息"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return error_response("用户不存在", 404)
        
        return success_response(
            data=user.to_dict(include_sensitive=True),
            message="获取用户信息成功"
        )
        
    except Exception as e:
        return error_response(f"获取用户信息失败: {str(e)}", 500)

@auth_bp.route('/me', methods=['PUT'])
@jwt_required()
def update_current_user_info():
    """更新当前用户信息"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return error_response("用户不存在", 404)
        
        data = request.get_json()
        if not data:
            return error_response("请求数据不能为空")
        
        # 更新用户名
        if 'username' in data:
            new_username = data['username'].strip()
            if len(new_username) < 2 or len(new_username) > 20:
                return error_response("用户名长度必须在2-20个字符之间")
            
            # 检查用户名是否已被其他用户使用
            existing_user = User.query.filter(
                User.username == new_username,
                User.user_id != current_user_id
            ).first()
            if existing_user:
                return error_response("用户名已存在")
            
            user.username = new_username
        
        # 更新邮箱
        if 'email' in data:
            new_email = data['email'].strip().lower()
            if not validate_email(new_email):
                return error_response("邮箱格式不正确")
            
            # 检查邮箱是否已被其他用户使用
            existing_user = User.query.filter(
                User.email == new_email,
                User.user_id != current_user_id
            ).first()
            if existing_user:
                return error_response("邮箱已被注册")
            
            user.email = new_email
        
        # 更新手机号
        if 'phone' in data:
            new_phone = data['phone'].strip() if data['phone'] else None
            if new_phone and not validate_phone(new_phone):
                return error_response("手机号格式不正确")
            user.phone = new_phone
        
        # 更新地址
        if 'address' in data:
            new_address = data['address'].strip()
            if len(new_address) < 5 or len(new_address) > 200:
                return error_response("地址长度必须在5-200个字符之间")
            user.address = new_address
        
        # 更新地理位置
        if 'latitude' in data and 'longitude' in data:
            try:
                user.latitude = float(data['latitude']) if data['latitude'] else None
                user.longitude = float(data['longitude']) if data['longitude'] else None
            except (ValueError, TypeError):
                return error_response("经纬度格式不正确")
        
        db.session.commit()
        
        return success_response(
            data=user.to_dict(include_sensitive=True),
            message="用户信息更新成功"
        )
        
    except Exception as e:
        db.session.rollback()
        return error_response(f"更新用户信息失败: {str(e)}", 500)

@auth_bp.route('/<int:user_id>', methods=['GET'])
def get_user_info(user_id):
    """获取指定用户的公开信息"""
    try:
        user = User.query.get(user_id)
        if not user:
            return error_response("用户不存在", 404)
        
        # 获取当前登录用户（如果有）
        current_user = get_current_user()
        include_sensitive = current_user and (current_user.user_id == user_id or current_user.is_admin)
        
        # 添加用户发布的物品数量
        user_data = user.to_dict(include_sensitive=include_sensitive)
        user_data['item_count'] = user.items.filter_by(status='available').count()
        
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
        
        from utils import paginate_query
        result = paginate_query(query, page, per_page)
        
        # 为每个用户添加额外信息
        for user_data in result['items']:
            user = User.query.get(user_data['user_id'])
            user_data['item_count'] = user.items.count()
            user_data['request_count'] = user.requests.count()
        
        return success_response(
            data=result,
            message="获取用户列表成功"
        )
        
    except Exception as e:
        return error_response(f"获取用户列表失败: {str(e)}", 500)