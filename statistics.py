from flask import Blueprint, request, jsonify
from models import User, Item, Request, Review, Message, ItemCategory, db
from utils import success_response, error_response, get_current_user
from sqlalchemy import func, and_
from datetime import datetime, timedelta

statistics_bp = Blueprint('statistics', __name__, url_prefix='/api/v1')

@statistics_bp.route('/users/count', methods=['GET'])
def get_users_count():
    """获取用户总数"""
    try:
        count = User.query.count()
        return success_response(
            data={'count': count},
            message="获取用户总数成功"
        )
    except Exception as e:
        return error_response(f"获取用户总数失败: {str(e)}", 500)

@statistics_bp.route('/items/count', methods=['GET'])
def get_items_count():
    """获取物品总数"""
    try:
        count = Item.query.count()
        return success_response(
            data={'count': count},
            message="获取物品总数成功"
        )
    except Exception as e:
        return error_response(f"获取物品总数失败: {str(e)}", 500)

@statistics_bp.route('/requests/count', methods=['GET'])
def get_requests_count():
    """获取交易请求数量"""
    try:
        status = request.args.get('status')
        query = Request.query
        
        if status:
            query = query.filter(Request.status == status)
        
        count = query.count()
        return success_response(
            data={'count': count},
            message="获取交易请求数量成功"
        )
    except Exception as e:
        return error_response(f"获取交易请求数量失败: {str(e)}", 500)

@statistics_bp.route('/reviews/count', methods=['GET'])
def get_reviews_count():
    """获取评价总数"""
    try:
        count = Review.query.count()
        return success_response(
            data={'count': count},
            message="获取评价总数成功"
        )
    except Exception as e:
        return error_response(f"获取评价总数失败: {str(e)}", 500)

@statistics_bp.route('/messages/count', methods=['GET'])
def get_messages_count():
    """获取消息总数"""
    try:
        count = Message.query.count()
        return success_response(
            data={'count': count},
            message="获取消息总数成功"
        )
    except Exception as e:
        return error_response(f"获取消息总数失败: {str(e)}", 500)

@statistics_bp.route('/statistics/today', methods=['GET'])
def get_today_statistics():
    """获取今日统计数据"""
    try:
        
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        
        # 今日新增用户
        new_users = User.query.filter(
            func.date(User.created_at) == today
        ).count()
        
        # 今日新增物品
        new_items = Item.query.filter(
            func.date(Item.created_at) == today
        ).count()
        
        # 今日新增交易请求
        new_requests = Request.query.filter(
            func.date(Request.created_at) == today
        ).count()
        
        # 今日新增评价
        new_reviews = Review.query.filter(
            func.date(Review.created_at) == today
        ).count()
        
        return success_response(
            data={
                'new_users': new_users,
                'new_items': new_items,
                'new_requests': new_requests,
                'new_reviews': new_reviews
            },
            message="获取今日统计数据成功"
        )
    except Exception as e:
        return error_response(f"获取今日统计数据失败: {str(e)}", 500)

@statistics_bp.route('/statistics/user-registration-trend', methods=['GET'])
def get_user_registration_trend():
    """获取用户注册趋势"""
    try:
        
        # 获取最近7天的注册数据
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=6)
        
        trend_data = []
        current_date = start_date
        
        while current_date <= end_date:
            count = User.query.filter(
                func.date(User.created_at) == current_date
            ).count()
            
            trend_data.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'count': count
            })
            
            current_date += timedelta(days=1)
        
        return success_response(
            data=trend_data,
            message="获取用户注册趋势成功"
        )
    except Exception as e:
        return error_response(f"获取用户注册趋势失败: {str(e)}", 500)

@statistics_bp.route('/statistics/item-category-distribution', methods=['GET'])
def get_item_category_distribution():
    """获取物品分类分布"""
    try:
        
        # 获取分类分布数据
        distribution = db.session.query(
            ItemCategory.name,
            func.count(Item.item_id).label('count')
        ).outerjoin(Item, ItemCategory.category_id == Item.category_id)\
         .group_by(ItemCategory.category_id, ItemCategory.name)\
         .all()
        
        distribution_data = [
            {
                'category': category_name,
                'count': count
            }
            for category_name, count in distribution
        ]
        
        return success_response(
            data=distribution_data,
            message="获取物品分类分布成功"
        )
    except Exception as e:
        return error_response(f"获取物品分类分布失败: {str(e)}", 500)

@statistics_bp.route('/statistics/request-status-distribution', methods=['GET'])
def get_request_status_distribution():
    """获取交易请求状态分布"""
    try:
        
        # 获取状态分布数据
        distribution = db.session.query(
            Request.status,
            func.count(Request.request_id).label('count')
        ).group_by(Request.status).all()
        
        status_names = {
            'pending': '待处理',
            'accepted': '已接受',
            'rejected': '已拒绝',
            'completed': '已完成',
            'cancelled': '已取消'
        }
        
        distribution_data = [
            {
                'status': status_names.get(status, status),
                'count': count
            }
            for status, count in distribution
        ]
        
        return success_response(
            data=distribution_data,
            message="获取交易请求状态分布成功"
        )
    except Exception as e:
        return error_response(f"获取交易请求状态分布失败: {str(e)}", 500)