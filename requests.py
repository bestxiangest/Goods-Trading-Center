from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Request, Item, User, Message, db
from utils import success_response, error_response, validate_required_fields, paginate_query
from datetime import datetime

requests_bp = Blueprint('requests', __name__, url_prefix='/api/v1/requests')

def create_notification_message(recipient_id, sender_id, message_type, related_id, content):
    """创建通知消息"""
    message = Message(
        recipient_id=recipient_id,
        sender_id=sender_id,
        type=message_type,
        related_id=related_id,
        content=content
    )
    db.session.add(message)

@requests_bp.route('', methods=['POST'])
@jwt_required()
def create_request():
    """发起交换请求"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data:
            return error_response("请求数据不能为空")
        
        # 验证必需字段
        required_fields = ['item_id']
        validation_error = validate_required_fields(data, required_fields)
        if validation_error:
            return error_response(validation_error)
        
        item_id = data['item_id']
        message_content = data.get('message', '').strip()
        
        # 验证物品是否存在
        item = Item.query.get(item_id)
        if not item:
            return error_response("物品不存在", 404)
        
        # 检查物品状态
        if item.status != 'available':
            return error_response("该物品当前不可交易")
        
        # 检查是否是自己的物品
        if item.user_id == current_user_id:
            return error_response("不能请求自己发布的物品")
        
        # 检查是否已经发起过请求
        existing_request = Request.query.filter_by(
            item_id=item_id,
            requester_id=current_user_id,
            status='pending'
        ).first()
        
        if existing_request:
            return error_response("您已经对该物品发起过请求，请等待处理")
        
        # 验证消息长度
        if len(message_content) > 200:
            return error_response("附言长度不能超过200个字符")
        
        # 创建请求
        new_request = Request(
            item_id=item_id,
            requester_id=current_user_id,
            message=message_content if message_content else None
        )
        
        db.session.add(new_request)
        db.session.flush()  # 获取request_id
        
        # 创建通知消息给物品所有者
        notification_content = f"您有一条新的物品请求：{item.title}"
        if message_content:
            notification_content += f"\n附言：{message_content}"
        
        create_notification_message(
            recipient_id=item.user_id,
            sender_id=current_user_id,
            message_type='request_notification',
            related_id=new_request.request_id,
            content=notification_content
        )
        
        db.session.commit()
        
        return success_response(
            data=new_request.to_dict(),
            message="请求发送成功",
            code=201
        )
        
    except Exception as e:
        db.session.rollback()
        return error_response(f"发送请求失败: {str(e)}", 500)

@requests_bp.route('/<int:request_id>', methods=['GET'])
@jwt_required()
def get_request(request_id):
    """获取请求详情"""
    try:
        current_user_id = get_jwt_identity()
        req = Request.query.get(request_id)
        
        if not req:
            return error_response("请求不存在", 404)
        
        # 检查权限（只有请求者、物品所有者或管理员可以查看）
        current_user = User.query.get(current_user_id)
        if (req.requester_id != current_user_id and 
            req.item.user_id != current_user_id and 
            not current_user.is_admin):
            return error_response("无权限查看此请求", 403)
        
        request_data = req.to_dict()
        
        # 添加物品详细信息
        request_data['item'] = req.item.to_dict(include_images=True)
        
        return success_response(
            data=request_data,
            message="获取请求详情成功"
        )
        
    except Exception as e:
        return error_response(f"获取请求详情失败: {str(e)}", 500)

@requests_bp.route('', methods=['GET'])
@jwt_required()
def get_requests():
    """获取请求列表"""
    try:
        current_user_id = get_jwt_identity()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status')
        request_type = request.args.get('type')  # 'sent' 或 'received'
        
        query = Request.query
        
        # 根据类型筛选
        if request_type == 'sent':
            # 我发送的请求
            query = query.filter(Request.requester_id == current_user_id)
        elif request_type == 'received':
            # 我收到的请求
            query = query.join(Item).filter(Item.user_id == current_user_id)
        else:
            # 所有相关的请求
            query = query.filter(
                (Request.requester_id == current_user_id) |
                (Request.item.has(user_id=current_user_id))
            )
        
        # 状态筛选
        if status:
            query = query.filter(Request.status == status)
        
        query = query.order_by(Request.created_at.desc())
        
        result = paginate_query(query, page, per_page)
        
        # 为每个请求添加物品信息
        for request_data in result['items']:
            req = Request.query.get(request_data['request_id'])
            request_data['item'] = req.item.to_dict(include_images=False)
        
        return success_response(
            data=result,
            message="获取请求列表成功"
        )
        
    except Exception as e:
        return error_response(f"获取请求列表失败: {str(e)}", 500)

@requests_bp.route('/<int:request_id>/status', methods=['PUT'])
@jwt_required()
def update_request_status(request_id):
    """更新请求状态"""
    try:
        current_user_id = get_jwt_identity()
        req = Request.query.get(request_id)
        
        if not req:
            return error_response("请求不存在", 404)
        
        data = request.get_json()
        if not data or 'status' not in data:
            return error_response("请提供新的状态")
        
        new_status = data['status']
        
        if new_status not in ['accepted', 'rejected', 'cancelled']:
            return error_response("状态必须是: accepted, rejected, cancelled 之一")
        
        # 检查权限
        if new_status in ['accepted', 'rejected']:
            # 只有物品所有者可以接受或拒绝请求
            if req.item.user_id != current_user_id:
                return error_response("只有物品所有者可以接受或拒绝请求", 403)
        elif new_status == 'cancelled':
            # 只有请求者可以取消请求
            if req.requester_id != current_user_id:
                return error_response("只有请求者可以取消请求", 403)
        
        # 检查当前状态
        if req.status != 'pending':
            return error_response("只能修改待处理状态的请求")
        
        # 更新请求状态
        req.status = new_status
        req.updated_at = datetime.utcnow()
        
        # 根据状态更新物品状态
        if new_status == 'accepted':
            req.item.status = 'reserved'
            
            # 拒绝该物品的其他待处理请求
            other_requests = Request.query.filter(
                Request.item_id == req.item_id,
                Request.request_id != request_id,
                Request.status == 'pending'
            ).all()
            
            for other_req in other_requests:
                other_req.status = 'rejected'
                # 通知其他请求者
                create_notification_message(
                    recipient_id=other_req.requester_id,
                    sender_id=None,  # 系统消息
                    message_type='status_update',
                    related_id=other_req.request_id,
                    content=f"很抱歉，您对物品