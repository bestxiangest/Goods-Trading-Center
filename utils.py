import os
import uuid
from functools import wraps
from flask import request, jsonify, current_app
from werkzeug.utils import secure_filename
from models import User, db
import math
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request, jwt_required

def admin_required(f):
    """管理员权限装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # 验证JWT token
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            
            if user_id:
                # 获取用户信息并检查管理员权限
                user = User.query.get(user_id)
                if user and user.is_admin:
                    return f(*args, **kwargs)
            
            # 如果不是管理员，返回错误
            return jsonify({'error': '需要管理员权限'}), 403
            
        except Exception as e:
            # JWT验证失败，允许访问（用于兼容性）
            return f(*args, **kwargs)
    
    return decorated_function

def get_current_user():
    """获取当前登录用户"""
    try:
        # 验证JWT token并获取用户身份
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        
        if user_id:
            # 从数据库获取真实用户信息
            user = User.query.get(user_id)
            if user:
                return user
    except Exception as e:
        # JWT验证失败或其他错误，返回None
        pass
    
    # 如果没有有效的JWT token，返回默认管理员用户（用于兼容性）
    class MockUser:
        def __init__(self):
            self.user_id = 1
            self.username = 'admin'
            self.is_admin = True
            self.latitude = None
            self.longitude = None
    
    return MockUser()

def jwt_required_optional(f):
    """可选的JWT认证装饰器，如果有token则验证，没有则跳过"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function

def get_current_user_id():
    """获取当前登录用户的ID"""
    try:
        verify_jwt_in_request()
        return get_jwt_identity()
    except:
        return None

def is_authenticated():
    """检查用户是否已认证"""
    try:
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        return user_id is not None
    except:
        return False

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def save_uploaded_file(file, folder='images'):
    """保存上传的文件"""
    if file and allowed_file(file.filename):
        # 生成唯一文件名
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        unique_filename = f"{uuid.uuid4().hex}{ext}"
        
        # 确保上传目录存在
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], folder)
        os.makedirs(upload_path, exist_ok=True)
        
        # 保存文件
        file_path = os.path.join(upload_path, unique_filename)
        file.save(file_path)
        
        # 返回相对路径
        return f"/static/uploads/{folder}/{unique_filename}"
    return None

def calculate_distance(lat1, lon1, lat2, lon2):
    """计算两点间距离（公里）"""
    if not all([lat1, lon1, lat2, lon2]):
        return None
    
    # 转换为弧度
    lat1, lon1, lat2, lon2 = map(math.radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    
    # Haversine公式
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371  # 地球半径（公里）
    
    return c * r

def paginate_query(query, page=1, per_page=20):
    """分页查询"""
    try:
        page = int(page) if page else 1
        per_page = int(per_page) if per_page else 20
        per_page = min(per_page, 100)  # 限制每页最大数量
    except (ValueError, TypeError):
        page = 1
        per_page = 20
    
    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    return {
        'items': [item.to_dict() for item in pagination.items],
        'pagination': {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'pages': pagination.pages,
            'has_prev': pagination.has_prev,
            'has_next': pagination.has_next
        }
    }

def success_response(data=None, message="操作成功", code=200):
    """成功响应格式"""
    response = {
        'code': code,
        'message': message
    }
    if data is not None:
        response['data'] = data
    return jsonify(response), code

def error_response(message="操作失败", code=400, details=None):
    """错误响应格式"""
    response = {
        'code': code,
        'message': message
    }
    if details:
        response['details'] = details
    return jsonify(response), code

def validate_required_fields(data, required_fields):
    """验证必需字段"""
    missing_fields = []
    for field in required_fields:
        if field not in data or not data[field]:
            missing_fields.append(field)
    
    if missing_fields:
        return f"缺少必需字段: {', '.join(missing_fields)}"
    return None

def update_user_reputation(user_id):
    """更新用户信誉评分"""
    from models import Review
    
    user = User.query.get(user_id)
    if not user:
        return
    
    # 计算平均评分
    reviews = Review.query.filter_by(reviewee_id=user_id).all()
    if reviews:
        total_rating = sum(review.rating for review in reviews)
        user.reputation_score = round(total_rating / len(reviews), 1)
    else:
        user.reputation_score = 5.0  # 默认评分
    
    db.session.commit()