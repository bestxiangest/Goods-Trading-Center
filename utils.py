import os
import uuid
from functools import wraps
from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from werkzeug.utils import secure_filename
from models import User, db
import math

def admin_required(f):
    """管理员权限装饰器"""
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user or not user.is_admin:
            return jsonify({
                'code': 403,
                'message': '需要管理员权限'
            }), 403
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """获取当前登录用户"""
    try:
        verify_jwt_in_request()
        current_user_id = get_jwt_identity()
        return User.query.get(current_user_id)
    except:
        return None

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