from flask import Blueprint, request, jsonify
from models import Request, Item, User, Message, db
from utils import success_response, error_response, validate_required_fields, paginate_query
from datetime import datetime
from sqlalchemy import and_, or_

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
def create_request():
    """创建交易请求"""
    try:
        # 使用固定的管理员用户ID
        current_user_id = 1
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
def get_request(request_id):
    """获取交易请求详情"""
    try:
        # 使用固定的管理员用户ID
        current_user_id = 1
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
def get_requests():
    """获取交易请求列表"""
    try:
        # 使用固定的管理员用户ID
        current_user_id = 1
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status')
        request_type = request.args.get('type')  # 'sent' 或 'received'
        
        # 手动分页处理，避免使用可能有问题的paginate方法
        try:
            page = max(1, page)
            per_page = min(max(1, per_page), 100)
            
            # 构建查询
            query = Request.query
            
            # 根据类型筛选
            if request_type == 'sent':
                # 我发送的请求
                query = query.filter(Request.requester_id == current_user_id)
            elif request_type == 'received':
                # 我收到的请求 - 需要join Item表
                query = query.join(Item).filter(Item.user_id == current_user_id)
            # 管理员可以查看所有请求，不做额外筛选
            
            # 状态筛选
            if status:
                query = query.filter(Request.status == status)
            
            query = query.order_by(Request.created_at.desc())
            
            # 手动分页
            total = query.count()
            requests = query.offset((page - 1) * per_page).limit(per_page).all()
            
            # 转换数据格式，添加物品所有者信息
            requests_data = []
            for req in requests:
                try:
                    req_dict = req.to_dict()
                    # 安全地添加物品所有者用户名
                    try:
                        req_dict['owner_username'] = req.item.owner.username if req.item and req.item.owner else None
                    except Exception:
                        req_dict['owner_username'] = None
                    requests_data.append(req_dict)
                except Exception as e:
                    # 如果单个请求数据转换失败，跳过该请求
                    print(f"转换请求数据失败 (request_id: {req.request_id}): {str(e)}")
                    continue
            
            # 计算分页信息
            pages = (total + per_page - 1) // per_page
            
            result = {
                'requests': requests_data,
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
                message="获取请求列表成功"
            )
            
        except Exception as db_error:
            print(f"数据库查询错误: {str(db_error)}")
            return error_response(f"数据库查询失败: {str(db_error)}", 500)
        
    except Exception as e:
        print(f"获取请求列表失败: {str(e)}")
        return error_response(f"获取请求列表失败: {str(e)}", 500)

@requests_bp.route('/<int:request_id>/status', methods=['PUT'])
def update_request_status(request_id):
    """更新交易请求状态"""
    try:
        # 使用固定的管理员用户ID
        current_user_id = 1
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
                    content=f"很抱歉，您对物品'{req.item.title}'的请求已被拒绝，该物品已被其他用户预定。"
                )
        
        # 创建通知消息给请求者
        if new_status == 'accepted':
            notification_content = f"恭喜！您对物品'{req.item.title}'的请求已被接受。"
            recipient_id = req.requester_id
        elif new_status == 'rejected':
            notification_content = f"很抱歉，您对物品'{req.item.title}'的请求已被拒绝。"
            recipient_id = req.requester_id
        else:  # cancelled
            notification_content = f"用户取消了对物品'{req.item.title}'的请求。"
            recipient_id = req.item.user_id
        
        create_notification_message(
            recipient_id=recipient_id,
            sender_id=current_user_id,
            message_type='status_update',
            related_id=request_id,
            content=notification_content
        )
        
        db.session.commit()
        
        return success_response(
            data=req.to_dict(),
            message="请求状态更新成功"
        )
        
    except Exception as e:
        db.session.rollback()
        return error_response(f"更新请求状态失败: {str(e)}", 500)

@requests_bp.route('/<int:request_id>/complete', methods=['PUT'])
def complete_request(request_id):
    """完成交易请求"""
    try:
        # 使用固定的管理员用户ID
        current_user_id = 1
        req = Request.query.get(request_id)
        
        if not req:
            return error_response("请求不存在", 404)
        
        # 检查请求状态
        if req.status != 'accepted':
            return error_response("只能完成已接受的请求")
        
        # 检查权限（交易双方都可以标记完成）
        if current_user_id not in [req.requester_id, req.item.user_id]:
            return error_response("只有交易双方可以完成交易", 403)
        
        # 更新请求和物品状态
        req.status = 'completed'
        req.item.status = 'sold'
        req.updated_at = datetime.utcnow()
        
        # 确定通知对象
        if current_user_id == req.requester_id:
            recipient_id = req.item.user_id
        else:
            recipient_id = req.requester_id
        
        notification_content = f"物品'{req.item.title}'的交易已完成！请为对方评价。"
        
        create_notification_message(
            recipient_id=recipient_id,
            sender_id=current_user_id,
            message_type='status_update',
            related_id=request_id,
            content=notification_content
        )
        
        db.session.commit()
        
        return success_response(
            data=req.to_dict(),
            message="交易完成"
        )
        
    except Exception as e:
        db.session.rollback()
        return error_response(f"完成交易失败: {str(e)}", 500)

@requests_bp.route('/statistics', methods=['GET'])
def get_request_statistics():
    """获取交易请求统计"""
    try:
        # 使用固定的管理员用户ID
        current_user_id = 1
        
        # 我发送的请求统计
        sent_stats = {
            'total': Request.query.filter_by(requester_id=current_user_id).count(),
            'pending': Request.query.filter_by(requester_id=current_user_id, status='pending').count(),
            'accepted': Request.query.filter_by(requester_id=current_user_id, status='accepted').count(),
            'rejected': Request.query.filter_by(requester_id=current_user_id, status='rejected').count(),
            'cancelled': Request.query.filter_by(requester_id=current_user_id, status='cancelled').count(),
            'completed': Request.query.filter_by(requester_id=current_user_id, status='completed').count()
        }
        
        # 我收到的请求统计
        from sqlalchemy import and_
        received_stats = {
            'total': Request.query.join(Item).filter(Item.user_id == current_user_id).count(),
            'pending': Request.query.join(Item).filter(
                and_(Item.user_id == current_user_id, Request.status == 'pending')
            ).count(),
            'accepted': Request.query.join(Item).filter(
                and_(Item.user_id == current_user_id, Request.status == 'accepted')
            ).count(),
            'rejected': Request.query.join(Item).filter(
                and_(Item.user_id == current_user_id, Request.status == 'rejected')
            ).count(),
            'cancelled': Request.query.join(Item).filter(
                and_(Item.user_id == current_user_id, Request.status == 'cancelled')
            ).count(),
            'completed': Request.query.join(Item).filter(
                and_(Item.user_id == current_user_id, Request.status == 'completed')
            ).count()
        }
        
        return success_response(
            data={
                'sent': sent_stats,
                'received': received_stats
            },
            message="获取请求统计成功"
        )
        
    except Exception as e:
        return error_response(f"获取请求统计失败: {str(e)}", 500)


@requests_bp.route('/admin', methods=['POST'])
def admin_create_request():
    """管理员创建交易请求"""
    try:
        data = request.get_json()
        
        if not data:
            return error_response("请求数据不能为空")
        
        # 验证必需字段
        required_fields = ['item_id', 'requester_id']
        validation_error = validate_required_fields(data, required_fields)
        if validation_error:
            return error_response(validation_error)
        
        item_id = data['item_id']
        requester_id = data['requester_id']
        message_content = data.get('message', '').strip()
        status = data.get('status', 'pending')
        
        # 验证物品是否存在
        item = Item.query.get(item_id)
        if not item:
            return error_response("物品不存在", 404)
        
        # 验证请求者是否存在
        requester = User.query.get(requester_id)
        if not requester:
            return error_response("请求者不存在", 404)
        
        # 检查是否已存在相同的请求
        existing_request = Request.query.filter_by(
            item_id=item_id,
            requester_id=requester_id,
            status='pending'
        ).first()
        
        if existing_request:
            return error_response("该用户已对此物品发起过待处理的交易请求")
        
        # 创建新的交易请求
        new_request = Request(
            item_id=item_id,
            requester_id=requester_id,
            message=message_content if message_content else None,
            status=status
        )
        
        db.session.add(new_request)
        db.session.commit()
        
        # 创建通知消息
        if status == 'pending':
            create_notification_message(
                recipient_id=item.user_id,
                sender_id=requester_id,
                message_type='request',
                related_id=new_request.request_id,
                content=f"用户 {requester.username} 请求交易您的物品 \"{item.title}\""
            )
        
        db.session.commit()
        
        return success_response(
            data=new_request.to_dict(),
            message="交易请求创建成功"
        )
        
    except Exception as e:
        db.session.rollback()
        return error_response(f"创建交易请求失败: {str(e)}", 500)

@requests_bp.route('/<int:request_id>/admin', methods=['PUT'])
def admin_update_request(request_id):
    """管理员更新交易请求"""
    try:
        data = request.get_json()
        
        if not data:
            return error_response("请求数据不能为空")
        
        # 查找请求
        req = Request.query.get(request_id)
        if not req:
            return error_response("交易请求不存在", 404)
        
        # 更新字段
        if 'message' in data:
            req.message = data['message']
        
        if 'status' in data:
            old_status = req.status
            new_status = data['status']
            
            # 验证状态值
            valid_statuses = ['pending', 'accepted', 'rejected', 'cancelled', 'completed']
            if new_status not in valid_statuses:
                return error_response(f"无效的状态值: {new_status}")
            
            req.status = new_status
            req.updated_at = datetime.utcnow()
            
            # 如果状态发生变化，创建通知
            if old_status != new_status:
                if new_status == 'accepted':
                    # 检查物品是否存在
                    if not req.item:
                        return error_response("关联的物品不存在", 404)
                    
                    # 更新物品状态为预留
                    req.item.status = 'reserved'
                    
                    # 通知请求者
                    create_notification_message(
                        recipient_id=req.requester_id,
                        sender_id=req.item.user_id,
                        message_type='status_update',
                        related_id=req.request_id,
                        content=f"您对物品 \"{req.item.title}\" 的交易请求已被接受"
                    )
                    
                    # 拒绝其他待处理的请求
                    other_requests = Request.query.filter(
                        Request.item_id == req.item_id,
                        Request.request_id != req.request_id,
                        Request.status == 'pending'
                    ).all()
                    
                    for other_req in other_requests:
                        other_req.status = 'rejected'
                        other_req.updated_at = datetime.utcnow()
                        
                        # 通知被拒绝的请求者
                        create_notification_message(
                            recipient_id=other_req.requester_id,
                            sender_id=req.item.user_id,
                            message_type='status_update',
                            related_id=other_req.request_id,
                            content=f"您对物品 \"{req.item.title}\" 的交易请求已被拒绝"
                        )
                
                elif new_status == 'rejected':
                    # 检查物品是否存在
                    if not req.item:
                        return error_response("关联的物品不存在", 404)
                    
                    # 通知请求者
                    create_notification_message(
                        recipient_id=req.requester_id,
                        sender_id=req.item.user_id,
                        message_type='status_update',
                        related_id=req.request_id,
                        content=f"您对物品 \"{req.item.title}\" 的交易请求已被拒绝"
                    )
                
                elif new_status == 'completed':
                    # 检查物品是否存在
                    if not req.item:
                        return error_response("关联的物品不存在", 404)
                    
                    # 更新物品状态
                    req.item.status = 'completed'
                    
                    # 通知双方
                    # 获取用户信息
                    item_owner = User.query.get(req.item.user_id)
                    requester = User.query.get(req.requester_id)
                    
                    if item_owner and requester:
                        create_notification_message(
                            recipient_id=req.requester_id,
                            sender_id=req.item.user_id,
                            message_type='status_update',
                            related_id=req.request_id,
                            content=f"您与 {item_owner.username} 的物品 \"{req.item.title}\" 交易已完成"
                        )
                        
                        create_notification_message(
                            recipient_id=req.item.user_id,
                            sender_id=req.requester_id,
                            message_type='status_update',
                            related_id=req.request_id,
                            content=f"您与 {requester.username} 的物品 \"{req.item.title}\" 交易已完成"
                        )
        
        db.session.commit()
        
        return success_response(
            data=req.to_dict(),
            message="交易请求更新成功"
        )
        
    except Exception as e:
        db.session.rollback()
        print(f"Admin update request error: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return error_response(f"更新交易请求失败: {str(e)}", 500)

@requests_bp.route('/<int:request_id>', methods=['DELETE'])
def admin_delete_request(request_id):
    """管理员删除交易请求"""
    try:
        # 查找请求
        req = Request.query.get(request_id)
        if not req:
            return error_response("交易请求不存在", 404)
        
        # 删除相关的通知消息
        Message.query.filter_by(related_id=request_id, type='request').delete()
        Message.query.filter_by(related_id=request_id, type='request_accepted').delete()
        Message.query.filter_by(related_id=request_id, type='request_rejected').delete()
        Message.query.filter_by(related_id=request_id, type='request_completed').delete()
        
        # 删除请求
        db.session.delete(req)
        db.session.commit()
        
        return success_response(
            message="交易请求删除成功"
        )
        
    except Exception as e:
        db.session.rollback()
        return error_response(f"删除交易请求失败: {str(e)}", 500)