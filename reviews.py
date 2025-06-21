from flask import Blueprint, request, jsonify
from models import Review, Request, User, Message, db
from utils import success_response, error_response, validate_required_fields, paginate_query, update_user_reputation
from datetime import datetime
from sqlalchemy import func, or_

reviews_bp = Blueprint('reviews', __name__, url_prefix='/api/v1/reviews')

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

@reviews_bp.route('', methods=['POST'])
def create_review():
    """创建评价"""
    try:
        # 使用固定的管理员用户ID
        current_user_id = 1
        data = request.get_json()
        
        if not data:
            return error_response("请求数据不能为空")
        
        # 验证必需字段
        required_fields = ['request_id', 'rating']
        validation_error = validate_required_fields(data, required_fields)
        if validation_error:
            return error_response(validation_error)
        
        request_id = data['request_id']
        rating = data['rating']
        comment = data.get('comment', '').strip()
        
        # 验证评分范围
        if not isinstance(rating, int) or rating < 1 or rating > 5:
            return error_response("评分必须是1-5之间的整数")
        
        # 验证评论长度
        if len(comment) > 500:
            return error_response("评论长度不能超过500个字符")
        
        # 验证请求是否存在
        req = Request.query.get(request_id)
        if not req:
            return error_response("请求不存在", 404)
        
        # 检查请求状态
        if req.status != 'completed':
            return error_response("只能对已完成的交易进行评价")
        
        # 检查评价权限（只有交易双方可以评价）
        if current_user_id not in [req.requester_id, req.item.user_id]:
            return error_response("只有交易双方可以进行评价", 403)
        
        # 确定被评价者
        if current_user_id == req.requester_id:
            reviewed_user_id = req.item.user_id
        else:
            reviewed_user_id = req.requester_id
        
        # 检查是否已经评价过
        existing_review = Review.query.filter_by(
            request_id=request_id,
            reviewer_id=current_user_id,
            reviewee_id=reviewed_user_id
        ).first()
        
        if existing_review:
            return error_response("您已经对此交易进行过评价")
        
        # 创建评价
        new_review = Review(
            request_id=request_id,
            reviewer_id=current_user_id,
            reviewee_id=reviewed_user_id,
            rating=rating,
            comment=comment if comment else None
        )
        
        db.session.add(new_review)
        db.session.flush()  # 获取review_id
        
        # 更新被评价用户的信誉度
        update_user_reputation(reviewed_user_id)
        
        # 创建通知消息
        reviewed_user = User.query.get(reviewed_user_id)
        notification_content = f"您收到了一条新的评价（{rating}星）"
        if comment:
            notification_content += f"：{comment[:50]}{'...' if len(comment) > 50 else ''}"
        
        create_notification_message(
            recipient_id=reviewed_user_id,
            sender_id=current_user_id,
            message_type='review_notification',
            related_id=new_review.review_id,
            content=notification_content
        )
        
        db.session.commit()
        
        return success_response(
            data=new_review.to_dict(),
            message="评价提交成功",
            code=201
        )
        
    except Exception as e:
        db.session.rollback()
        return error_response(f"提交评价失败: {str(e)}", 500)

@reviews_bp.route('/<int:review_id>', methods=['GET'])
def get_review(review_id):
    """获取评价详情"""
    try:
        review = Review.query.get(review_id)
        
        if not review:
            return error_response("评价不存在", 404)
        
        return success_response(
            data=review.to_dict(),
            message="获取评价详情成功"
        )
        
    except Exception as e:
        return error_response(f"获取评价详情失败: {str(e)}", 500)

@reviews_bp.route('', methods=['GET'])
def get_reviews():
    """获取评价列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        user_id = request.args.get('user_id', type=int)
        rating = request.args.get('rating', type=int)
        review_type = request.args.get('type')  # 'given' 或 'received'
        
        # 使用固定的管理员用户ID
        current_user_id = 1
        
        query = Review.query
        
        # 用户筛选
        if user_id:
            if review_type == 'given':
                # 该用户给出的评价
                query = query.filter(Review.reviewer_id == user_id)
            elif review_type == 'received':
                # 该用户收到的评价
                query = query.filter(Review.reviewee_id == user_id)
            else:
                # 该用户相关的所有评价
                query = query.filter(
                    or_(Review.reviewer_id == user_id, Review.reviewee_id == user_id)
                )
        # 管理员可以查看所有评价，不做额外筛选
        
        # 评分筛选
        if rating and 1 <= rating <= 5:
            query = query.filter(Review.rating == rating)
        
        query = query.order_by(Review.created_at.desc())
        
        result = paginate_query(query, page, per_page)
        
        return success_response(
            data={
                'reviews': result['items'],
                'pagination': result['pagination']
            },
            message="获取评价列表成功"
        )
        
    except Exception as e:
        return error_response(f"获取评价列表失败: {str(e)}", 500)

@reviews_bp.route('/user/<int:user_id>/statistics', methods=['GET'])
def get_user_review_statistics(user_id):
    """获取用户评价统计"""
    try:
        # 验证用户是否存在
        user = User.query.get(user_id)
        if not user:
            return error_response("用户不存在", 404)
        
        # 收到的评价统计
        received_reviews = Review.query.filter_by(reviewee_id=user_id)
        received_count = received_reviews.count()
        
        if received_count > 0:
            # 计算平均评分
            avg_rating = db.session.query(func.avg(Review.rating)).filter_by(reviewee_id=user_id).scalar()
            avg_rating = round(float(avg_rating), 2) if avg_rating else 0
            
            # 各星级评价数量
            rating_distribution = {}
            for i in range(1, 6):
                count = received_reviews.filter_by(rating=i).count()
                rating_distribution[str(i)] = count
        else:
            avg_rating = 0
            rating_distribution = {str(i): 0 for i in range(1, 6)}
        
        # 给出的评价统计
        given_count = Review.query.filter_by(reviewer_id=user_id).count()
        
        # 最近的评价
        recent_reviews = Review.query.filter_by(reviewee_id=user_id)\
            .order_by(Review.created_at.desc())\
            .limit(5)\
            .all()
        
        recent_reviews_data = [review.to_dict() for review in recent_reviews]
        
        return success_response(
            data={
                'user_id': user_id,
                'received': {
                    'total_count': received_count,
                    'average_rating': avg_rating,
                    'rating_distribution': rating_distribution
                },
                'given': {
                    'total_count': given_count
                },
                'recent_reviews': recent_reviews_data
            },
            message="获取用户评价统计成功"
        )
        
    except Exception as e:
        return error_response(f"获取用户评价统计失败: {str(e)}", 500)

@reviews_bp.route('/request/<int:request_id>', methods=['GET'])
def get_request_reviews(request_id):
    """获取特定请求的评价"""
    try:
        # 使用固定的管理员用户ID
        current_user_id = 1
        
        # 验证请求是否存在
        req = Request.query.get(request_id)
        if not req:
            return error_response("请求不存在", 404)
        
        # 检查权限（只有交易双方可以查看）
        if current_user_id not in [req.requester_id, req.item.user_id]:
            return error_response("无权限查看此请求的评价", 403)
        
        # 获取该请求的所有评价
        reviews = Review.query.filter_by(request_id=request_id).all()
        
        reviews_data = []
        for review in reviews:
            review_data = review.to_dict()
            # 添加评价者和被评价者信息
            reviewer = User.query.get(review.reviewer_id)
            reviewed_user = User.query.get(review.reviewee_id)
            
            review_data['reviewer'] = {
                'user_id': reviewer.user_id,
                'username': reviewer.username
            }
            review_data['reviewed_user'] = {
                'user_id': reviewed_user.user_id,
                'username': reviewed_user.username
            }
            
            reviews_data.append(review_data)
        
        # 检查当前用户是否可以评价
        can_review = False
        if req.status == 'completed':
            # 检查当前用户是否已经评价过
            if current_user_id == req.requester_id:
                reviewed_user_id = req.item.user_id
            else:
                reviewed_user_id = req.requester_id
            
            existing_review = Review.query.filter_by(
                request_id=request_id,
                reviewer_id=current_user_id,
                reviewee_id=reviewed_user_id
            ).first()
            
            can_review = not existing_review
        
        return success_response(
            data={
                'request_id': request_id,
                'reviews': reviews_data,
                'can_review': can_review
            },
            message="获取请求评价成功"
        )
        
    except Exception as e:
        return error_response(f"获取请求评价失败: {str(e)}", 500)

@reviews_bp.route('/<int:review_id>', methods=['PUT'])
def update_review(review_id):
    """更新评价（仅限评价者在24小时内修改）"""
    try:
        # 使用固定的管理员用户ID
        current_user_id = 1
        review = Review.query.get(review_id)
        
        if not review:
            return error_response("评价不存在", 404)
        
        # 检查权限
        if review.reviewer_id != current_user_id:
            return error_response("只能修改自己的评价", 403)
        
        # 检查时间限制（24小时内可修改）
        from datetime import timedelta
        if datetime.utcnow() - review.created_at > timedelta(hours=24):
            return error_response("评价发布超过24小时后不能修改")
        
        data = request.get_json()
        if not data:
            return error_response("请求数据不能为空")
        
        # 更新评分
        if 'rating' in data:
            rating = data['rating']
            if not isinstance(rating, int) or rating < 1 or rating > 5:
                return error_response("评分必须是1-5之间的整数")
            review.rating = rating
        
        # 更新评论
        if 'comment' in data:
            comment = data['comment'].strip() if data['comment'] else None
            if comment and len(comment) > 500:
                return error_response("评论长度不能超过500个字符")
            review.comment = comment
        
        review.updated_at = datetime.utcnow()
        
        # 重新计算被评价用户的信誉度
        update_user_reputation(review.reviewee_id)
        
        db.session.commit()
        
        return success_response(
            data=review.to_dict(),
            message="评价更新成功"
        )
        
    except Exception as e:
        db.session.rollback()
        return error_response(f"更新评价失败: {str(e)}", 500)

@reviews_bp.route('/<int:review_id>', methods=['DELETE'])
def delete_review(review_id):
    """删除评价（仅限管理员或评价者在1小时内删除）"""
    try:
        # 使用固定的管理员用户ID
        current_user_id = 1
        current_user = User.query.get(current_user_id)
        review = Review.query.get(review_id)
        
        if not review:
            return error_response("评价不存在", 404)
        
        # 检查权限
        if not current_user.is_admin and review.reviewer_id != current_user_id:
            return error_response("无权限删除此评价", 403)
        
        # 非管理员检查时间限制（1小时内可删除）
        if not current_user.is_admin:
            from datetime import timedelta
            if datetime.utcnow() - review.created_at > timedelta(hours=1):
                return error_response("评价发布超过1小时后不能删除")
        
        reviewed_user_id = review.reviewee_id
        
        db.session.delete(review)
        
        # 重新计算被评价用户的信誉度
        update_user_reputation(reviewed_user_id)
        
        db.session.commit()
        
        return success_response(
            message="评价删除成功"
        )
        
    except Exception as e:
        db.session.rollback()
        return error_response(f"删除评价失败: {str(e)}", 500)