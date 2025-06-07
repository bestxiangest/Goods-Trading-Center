from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Message, User, db
from utils import success_response, error_response, validate_required_fields, paginate_query
from datetime import datetime
from sqlalchemy import and_, or_, func

messages_bp = Blueprint('messages', __name__, url_prefix='/api/v1/messages')

@messages_bp.route('', methods=['POST'])
@jwt_required()
def send_message():
    """发送消息"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data:
            return error_response("请求数据不能为空")
        
        # 验证必需字段
        required_fields = ['recipient_id', 'content']
        validation_error = validate_required_fields(data, required_fields)
        if validation_error:
            return error_response(validation_error)
        
        recipient_id = data['recipient_id']
        content = data['content'].strip()
        message_type = data.get('type', 'user_message')
        related_id = data.get('related_id')
        
        # 验证接收者
        if recipient_id == current_user_id:
            return error_response("不能给自己发送消息")
        
        recipient = User.query.get(recipient_id)
        if not recipient:
            return error_response("接收者不存在", 404)
        
        # 验证消息内容
        if not content:
            return error_response("消息内容不能为空")
        
        if len(content) > 1000:
            return error_response("消息内容长度不能超过1000个字符")
        
        # 验证消息类型
        valid_types = ['user_message', 'system_message', 'request_notification', 
                      'status_update', 'review_notification']
        if message_type not in valid_types:
            return error_response(f"消息类型必须是: {', '.join(valid_types)} 之一")
        
        # 创建消息
        new_message = Message(
            recipient_id=recipient_id,
            sender_id=current_user_id,
            type=message_type,
            content=content,
            related_id=related_id
        )
        
        db.session.add(new_message)
        db.session.commit()
        
        return success_response(
            data=new_message.to_dict(),
            message="消息发送成功",
            code=201
        )
        
    except Exception as e:
        db.session.rollback()
        return error_response(f"发送消息失败: {str(e)}", 500)

@messages_bp.route('', methods=['GET'])
@jwt_required()
def get_messages():
    """获取消息列表"""
    try:
        current_user_id = get_jwt_identity()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        message_type = request.args.get('type')
        is_read = request.args.get('is_read')
        conversation_with = request.args.get('conversation_with', type=int)
        
        query = Message.query.filter_by(recipient_id=current_user_id)
        
        # 消息类型筛选
        if message_type:
            query = query.filter(Message.type == message_type)
        
        # 已读状态筛选
        if is_read is not None:
            is_read_bool = is_read.lower() == 'true'
            query = query.filter(Message.is_read == is_read_bool)
        
        # 会话筛选（与特定用户的对话）
        if conversation_with:
            query = query.filter(Message.sender_id == conversation_with)
        
        query = query.order_by(Message.created_at.desc())
        
        result = paginate_query(query, page, per_page)
        
        # 为每条消息添加发送者信息
        for message_data in result['items']:
            message = Message.query.get(message_data['message_id'])
            if message.sender_id:
                sender = User.query.get(message.sender_id)
                message_data['sender'] = {
                    'user_id': sender.user_id,
                    'username': sender.username,
                    'avatar_url': sender.avatar_url
                }
            else:
                message_data['sender'] = None  # 系统消息
        
        return success_response(
            data=result,
            message="获取消息列表成功"
        )
        
    except Exception as e:
        return error_response(f"获取消息列表失败: {str(e)}", 500)

@messages_bp.route('/<int:message_id>', methods=['GET'])
@jwt_required()
def get_message(message_id):
    """获取消息详情"""
    try:
        current_user_id = get_jwt_identity()
        message = Message.query.get(message_id)
        
        if not message:
            return error_response("消息不存在", 404)
        
        # 检查权限（只有接收者或发送者可以查看）
        if message.recipient_id != current_user_id and message.sender_id != current_user_id:
            return error_response("无权限查看此消息", 403)
        
        message_data = message.to_dict()
        
        # 添加发送者和接收者信息
        if message.sender_id:
            sender = User.query.get(message.sender_id)
            message_data['sender'] = {
                'user_id': sender.user_id,
                'username': sender.username,
                'avatar_url': sender.avatar_url
            }
        else:
            message_data['sender'] = None  # 系统消息
        
        recipient = User.query.get(message.recipient_id)
        message_data['recipient'] = {
            'user_id': recipient.user_id,
            'username': recipient.username,
            'avatar_url': recipient.avatar_url
        }
        
        return success_response(
            data=message_data,
            message="获取消息详情成功"
        )
        
    except Exception as e:
        return error_response(f"获取消息详情失败: {str(e)}", 500)

@messages_bp.route('/<int:message_id>/read', methods=['PUT'])
@jwt_required()
def mark_message_read(message_id):
    """标记消息为已读"""
    try:
        current_user_id = get_jwt_identity()
        message = Message.query.get(message_id)
        
        if not message:
            return error_response("消息不存在", 404)
        
        # 检查权限（只有接收者可以标记为已读）
        if message.recipient_id != current_user_id:
            return error_response("只能标记自己收到的消息为已读", 403)
        
        if not message.is_read:
            message.is_read = True
            message.read_at = datetime.utcnow()
            db.session.commit()
        
        return success_response(
            data=message.to_dict(),
            message="消息已标记为已读"
        )
        
    except Exception as e:
        db.session.rollback()
        return error_response(f"标记消息已读失败: {str(e)}", 500)

@messages_bp.route('/batch/read', methods=['PUT'])
@jwt_required()
def mark_messages_read():
    """批量标记消息为已读"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data or 'message_ids' not in data:
            return error_response("请提供要标记的消息ID列表")
        
        message_ids = data['message_ids']
        
        if not isinstance(message_ids, list) or not message_ids:
            return error_response("消息ID列表不能为空")
        
        # 查询并更新消息
        messages = Message.query.filter(
            and_(
                Message.message_id.in_(message_ids),
                Message.recipient_id == current_user_id,
                Message.is_read == False
            )
        ).all()
        
        updated_count = 0
        for message in messages:
            message.is_read = True
            message.read_at = datetime.utcnow()
            updated_count += 1
        
        db.session.commit()
        
        return success_response(
            data={'updated_count': updated_count},
            message=f"成功标记{updated_count}条消息为已读"
        )
        
    except Exception as e:
        db.session.rollback()
        return error_response(f"批量标记消息已读失败: {str(e)}", 500)

@messages_bp.route('/conversations', methods=['GET'])
@jwt_required()
def get_conversations():
    """获取会话列表"""
    try:
        current_user_id = get_jwt_identity()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # 获取与当前用户有消息往来的所有用户
        # 子查询：获取每个会话的最新消息
        latest_messages = db.session.query(
            func.max(Message.message_id).label('latest_message_id')
        ).filter(
            or_(
                Message.recipient_id == current_user_id,
                Message.sender_id == current_user_id
            )
        ).group_by(
            func.case(
                [(Message.recipient_id == current_user_id, Message.sender_id)],
                else_=Message.recipient_id
            )
        ).subquery()
        
        # 获取最新消息的详细信息
        conversations_query = db.session.query(Message).filter(
            Message.message_id.in_(
                db.session.query(latest_messages.c.latest_message_id)
            )
        ).order_by(Message.created_at.desc())
        
        # 分页
        total = conversations_query.count()
        conversations = conversations_query.offset((page - 1) * per_page).limit(per_page).all()
        
        conversations_data = []
        for message in conversations:
            # 确定对话对象
            if message.recipient_id == current_user_id:
                other_user_id = message.sender_id
            else:
                other_user_id = message.recipient_id
            
            if other_user_id:  # 排除系统消息
                other_user = User.query.get(other_user_id)
                
                # 计算未读消息数
                unread_count = Message.query.filter(
                    and_(
                        Message.recipient_id == current_user_id,
                        Message.sender_id == other_user_id,
                        Message.is_read == False
                    )
                ).count()
                
                conversation_data = {
                    'user': {
                        'user_id': other_user.user_id,
                        'username': other_user.username,
                        'avatar_url': other_user.avatar_url
                    },
                    'latest_message': message.to_dict(),
                    'unread_count': unread_count
                }
                conversations_data.append(conversation_data)
        
        result = {
            'items': conversations_data,
            'total': len(conversations_data),
            'page': page,
            'per_page': per_page,
            'pages': (len(conversations_data) + per_page - 1) // per_page
        }
        
        return success_response(
            data=result,
            message="获取会话列表成功"
        )
        
    except Exception as e:
        return error_response(f"获取会话列表失败: {str(e)}", 500)

@messages_bp.route('/conversation/<int:user_id>', methods=['GET'])
@jwt_required()
def get_conversation_messages(user_id):
    """获取与特定用户的对话消息"""
    try:
        current_user_id = get_jwt_identity()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        # 验证用户是否存在
        other_user = User.query.get(user_id)
        if not other_user:
            return error_response("用户不存在", 404)
        
        # 获取双方的消息
        query = Message.query.filter(
            or_(
                and_(Message.sender_id == current_user_id, Message.recipient_id == user_id),
                and_(Message.sender_id == user_id, Message.recipient_id == current_user_id)
            )
        ).order_by(Message.created_at.desc())
        
        result = paginate_query(query, page, per_page)
        
        # 标记来自对方的未读消息为已读
        unread_messages = Message.query.filter(
            and_(
                Message.sender_id == user_id,
                Message.recipient_id == current_user_id,
                Message.is_read == False
            )
        ).all()
        
        for message in unread_messages:
            message.is_read = True
            message.read_at = datetime.utcnow()
        
        if unread_messages:
            db.session.commit()
        
        return success_response(
            data=result,
            message="获取对话消息成功"
        )
        
    except Exception as e:
        db.session.rollback()
        return error_response(f"获取对话消息失败: {str(e)}", 500)

@messages_bp.route('/<int:message_id>', methods=['DELETE'])
@jwt_required()
def delete_message(message_id):
    """删除消息"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        message = Message.query.get(message_id)
        
        if not message:
            return error_response("消息不存在", 404)
        
        # 检查权限（接收者、发送者或管理员可以删除）
        if (message.recipient_id != current_user_id and 
            message.sender_id != current_user_id and 
            not current_user.is_admin):
            return error_response("无权限删除此消息", 403)
        
        db.session.delete(message)
        db.session.commit()
        
        return success_response(
            message="消息删除成功"
        )
        
    except Exception as e:
        db.session.rollback()
        return error_response(f"删除消息失败: {str(e)}", 500)

@messages_bp.route('/statistics', methods=['GET'])
@jwt_required()
def get_message_statistics():
    """获取消息统计信息"""
    try:
        current_user_id = get_jwt_identity()
        
        # 收到的消息统计
        received_total = Message.query.filter_by(recipient_id=current_user_id).count()
        received_unread = Message.query.filter_by(
            recipient_id=current_user_id, 
            is_read=False
        ).count()
        
        # 发送的消息统计
        sent_total = Message.query.filter_by(sender_id=current_user_id).count()
        
        # 按类型统计未读消息
        unread_by_type = {}
        message_types = ['user_message', 'system_message', 'request_notification', 
                        'status_update', 'review_notification']
        
        for msg_type in message_types:
            count = Message.query.filter_by(
                recipient_id=current_user_id,
                type=msg_type,
                is_read=False
            ).count()
            unread_by_type[msg_type] = count
        
        return success_response(
            data={
                'received': {
                    'total': received_total,
                    'unread': received_unread
                },
                'sent': {
                    'total': sent_total
                },
                'unread_by_type': unread_by_type
            },
            message="获取消息统计成功"
        )
        
    except Exception as e:
        return error_response(f"获取消息统计失败: {str(e)}", 500)