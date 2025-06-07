from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Item, ItemImage, ItemCategory, User, db
from utils import success_response, error_response, validate_required_fields, get_current_user, paginate_query, calculate_distance
from sqlalchemy import or_, and_

items_bp = Blueprint('items', __name__, url_prefix='/api/v1/items')

@items_bp.route('', methods=['POST'])
@jwt_required()
def create_item():
    """发布新物品"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data:
            return error_response("请求数据不能为空")
        
        # 验证必需字段
        required_fields = ['title', 'description', 'category_id', 'condition']
        validation_error = validate_required_fields(data, required_fields)
        if validation_error:
            return error_response(validation_error)
        
        title = data['title'].strip()
        description = data['description'].strip()
        category_id = data['category_id']
        condition = data['condition']
        image_urls = data.get('image_urls', [])
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        # 验证数据格式
        if len(title) < 1 or len(title) > 100:
            return error_response("物品标题长度必须在1-100个字符之间")
        
        if len(description) < 1 or len(description) > 1000:
            return error_response("物品描述长度必须在1-1000个字符之间")
        
        if condition not in ['new', 'like_new', 'used', 'worn']:
            return error_response("物品状态必须是: new, like_new, used, worn 之一")
        
        # 验证分类是否存在
        category = ItemCategory.query.get(category_id)
        if not category:
            return error_response("分类不存在")
        
        # 验证图片URL
        if not image_urls or len(image_urls) == 0:
            return error_response("至少需要上传一张图片")
        
        if len(image_urls) > 10:
            return error_response("最多只能上传10张图片")
        
        # 验证经纬度
        if latitude is not None and longitude is not None:
            try:
                latitude = float(latitude)
                longitude = float(longitude)
                if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
                    return error_response("经纬度范围不正确")
            except (ValueError, TypeError):
                return error_response("经纬度格式不正确")
        else:
            latitude = longitude = None
        
        # 创建物品
        item = Item(
            user_id=current_user_id,
            title=title,
            description=description,
            category_id=category_id,
            condition=condition,
            latitude=latitude,
            longitude=longitude
        )
        
        db.session.add(item)
        db.session.flush()  # 获取item_id
        
        # 添加图片
        for i, image_url in enumerate(image_urls):
            image = ItemImage(
                item_id=item.item_id,
                image_url=image_url.strip(),
                is_primary=(i == 0)  # 第一张图片设为主图
            )
            db.session.add(image)
        
        db.session.commit()
        
        return success_response(
            data={
                'item_id': item.item_id,
                'title': item.title,
                'status': item.status
            },
            message="物品发布成功",
            code=201
        )
        
    except Exception as e:
        db.session.rollback()
        return error_response(f"发布物品失败: {str(e)}", 500)

@items_bp.route('/<int:item_id>', methods=['GET'])
def get_item(item_id):
    """获取物品详情"""
    try:
        item = Item.query.get(item_id)
        if not item:
            return error_response("物品不存在", 404)
        
        # 获取当前用户（如果已登录）
        current_user = get_current_user()
        
        item_data = item.to_dict(include_images=True)
        
        # 如果当前用户已登录且有位置信息，计算距离
        if current_user and current_user.latitude and current_user.longitude and item.latitude and item.longitude:
            distance = calculate_distance(
                current_user.latitude, current_user.longitude,
                item.latitude, item.longitude
            )
            if distance is not None:
                item_data['distance'] = round(distance, 2)
        
        return success_response(
            data=item_data,
            message="获取物品详情成功"
        )
        
    except Exception as e:
        return error_response(f"获取物品详情失败: {str(e)}", 500)

@items_bp.route('', methods=['GET'])
def get_items():
    """获取物品列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        category_id = request.args.get('category_id', type=int)
        condition = request.args.get('condition')
        status = request.args.get('status', 'available')
        search = request.args.get('search', '').strip()
        user_id = request.args.get('user_id', type=int)
        nearby = request.args.get('nearby', type=bool)
        max_distance = request.args.get('max_distance', 10, type=float)  # 默认10公里
        
        query = Item.query
        
        # 状态筛选
        if status:
            query = query.filter(Item.status == status)
        
        # 分类筛选
        if category_id:
            query = query.filter(Item.category_id == category_id)
        
        # 新旧程度筛选
        if condition:
            query = query.filter(Item.condition == condition)
        
        # 用户筛选
        if user_id:
            query = query.filter(Item.user_id == user_id)
        
        # 搜索功能
        if search:
            query = query.filter(
                or_(
                    Item.title.contains(search),
                    Item.description.contains(search)
                )
            )
        
        # 附近物品筛选
        current_user = get_current_user()
        if nearby and current_user and current_user.latitude and current_user.longitude:
            # 这里简化处理，实际应用中可以使用空间索引优化
            query = query.filter(
                and_(
                    Item.latitude.isnot(None),
                    Item.longitude.isnot(None)
                )
            )
        
        # 排序
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')
        
        if sort_by == 'created_at':
            if sort_order == 'asc':
                query = query.order_by(Item.created_at.asc())
            else:
                query = query.order_by(Item.created_at.desc())
        elif sort_by == 'updated_at':
            if sort_order == 'asc':
                query = query.order_by(Item.updated_at.asc())
            else:
                query = query.order_by(Item.updated_at.desc())
        
        result = paginate_query(query, page, per_page)
        
        # 如果是附近物品搜索，计算距离并过滤
        if nearby and current_user and current_user.latitude and current_user.longitude:
            filtered_items = []
            for item_data in result['items']:
                item = Item.query.get(item_data['item_id'])
                if item.latitude and item.longitude:
                    distance = calculate_distance(
                        current_user.latitude, current_user.longitude,
                        item.latitude, item.longitude
                    )
                    if distance is not None and distance <= max_distance:
                        item_data['distance'] = round(distance, 2)
                        filtered_items.append(item_data)
            
            result['items'] = sorted(filtered_items, key=lambda x: x.get('distance', float('inf')))
            result['pagination']['total'] = len(filtered_items)
        
        return success_response(
            data=result,
            message="获取物品列表成功"
        )
        
    except Exception as e:
        return error_response(f"获取物品列表失败: {str(e)}", 500)

@items_bp.route('/<int:item_id>', methods=['PUT'])
@jwt_required()
def update_item(item_id):
    """更新物品信息"""
    try:
        current_user_id = get_jwt_identity()
        item = Item.query.get(item_id)
        
        if not item:
            return error_response("物品不存在", 404)
        
        # 检查权限（只有物品所有者或管理员可以修改）
        current_user = User.query.get(current_user_id)
        if item.user_id != current_user_id and not current_user.is_admin:
            return error_response("无权限修改此物品", 403)
        
        data = request.get_json()
        if not data:
            return error_response("请求数据不能为空")
        
        # 更新标题
        if 'title' in data:
            title = data['title'].strip()
            if len(title) < 1 or len(title) > 100:
                return error_response("物品标题长度必须在1-100个字符之间")
            item.title = title
        
        # 更新描述
        if 'description' in data:
            description = data['description'].strip()
            if len(description) < 1 or len(description) > 1000:
                return error_response("物品描述长度必须在1-1000个字符之间")
            item.description = description
        
        # 更新分类
        if 'category_id' in data:
            category = ItemCategory.query.get(data['category_id'])
            if not category:
                return error_response("分类不存在")
            item.category_id = data['category_id']
        
        # 更新状态
        if 'status' in data:
            if data['status'] not in ['available', 'reserved', 'completed', 'cancelled']:
                return error_response("物品状态必须是: available, reserved, completed, cancelled 之一")
            item.status = data['status']
        
        # 更新新旧程度
        if 'condition' in data:
            if data['condition'] not in ['new', 'like_new', 'used', 'worn']:
                return error_response("物品状态必须是: new, like_new, used, worn 之一")
            item.condition = data['condition']
        
        # 更新地理位置
        if 'latitude' in data and 'longitude' in data:
            try:
                if data['latitude'] is not None and data['longitude'] is not None:
                    latitude = float(data['latitude'])
                    longitude = float(data['longitude'])
                    if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
                        return error_response("经纬度范围不正确")
                    item.latitude = latitude
                    item.longitude = longitude
                else:
                    item.latitude = None
                    item.longitude = None
            except (ValueError, TypeError):
                return error_response("经纬度格式不正确")
        
        # 更新图片
        if 'image_urls' in data:
            image_urls = data['image_urls']
            if not image_urls or len(image_urls) == 0:
                return error_response("至少需要一张图片")
            
            if len(image_urls) > 10:
                return error_response("最多只能上传10张图片")
            
            # 删除原有图片
            ItemImage.query.filter_by(item_id=item_id).delete()
            
            # 添加新图片
            for i, image_url in enumerate(image_urls):
                image = ItemImage(
                    item_id=item_id,
                    image_url=image_url.strip(),
                    is_primary=(i == 0)
                )
                db.session.add(image)
        
        db.session.commit()
        
        return success_response(
            data=item.to_dict(include_images=True),
            message="物品信息更新成功"
        )
        
    except Exception as e:
        db.session.rollback()
        return error_response(f"更新物品信息失败: {str(e)}", 500)

@items_bp.route('/<int:item_id>', methods=['DELETE'])
@jwt_required()
def delete_item(item_id):
    """删除物品"""
    try:
        current_user_id = get_jwt_identity()
        item = Item.query.get(item_id)
        
        if not item:
            return error_response("物品不存在", 404)
        
        # 检查权限（只有物品所有者或管理员可以删除）
        current_user = User.query.get(current_user_id)
        if item.user_id != current_user_id and not current_user.is_admin:
            return error_response("无权限删除此物品", 403)
        
        # 检查是否有未完成的请求
        from models import Request
        pending_requests = Request.query.filter_by(
            item_id=item_id,
            status='pending'
        ).count()
        
        if pending_requests > 0:
            return error_response("该物品还有待处理的请求，无法删除")
        
        db.session.delete(item)
        db.session.commit()
        
        return success_response(
            message="物品删除成功",
            code=204
        )
        
    except Exception as e:
        db.session.rollback()
        return error_response(f"删除物品失败: {str(e)}", 500)

@items_bp.route('/my', methods=['GET'])
@jwt_required()
def get_my_items():
    """获取当前用户发布的物品"""
    try:
        current_user_id = get_jwt_identity()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status')
        
        query = Item.query.filter_by(user_id=current_user_id)
        
        if status:
            query = query.filter(Item.status == status)
        
        query = query.order_by(Item.created_at.desc())
        
        result = paginate_query(query, page, per_page)
        
        return success_response(
            data=result,
            message="获取我的物品成功"
        )
        
    except Exception as e:
        return error_response(f"获取我的物品失败: {str(e)}", 500)