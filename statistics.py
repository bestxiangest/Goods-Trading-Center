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

@statistics_bp.route('/today', methods=['GET'])
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

@statistics_bp.route('/user-registration-trend', methods=['GET'])
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

@statistics_bp.route('/item-category-distribution', methods=['GET'])
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

@statistics_bp.route('/request-status-distribution', methods=['GET'])
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

@statistics_bp.route('/user-reputation-distribution', methods=['GET'])
def get_user_reputation_distribution():
    """获取用户信誉分布"""
    try:
        # 定义信誉评分区间
        reputation_ranges = [
            (1.0, 2.0, '1.0-2.0'),
            (2.0, 3.0, '2.0-3.0'),
            (3.0, 4.0, '3.0-4.0'),
            (4.0, 5.0, '4.0-5.0'),
            (5.0, 5.1, '5.0')
        ]
        
        ranges = []
        counts = []
        for min_score, max_score, label in reputation_ranges:
            if max_score == 5.1:  # 处理5.0的特殊情况
                count = User.query.filter(User.reputation_score == 5.0).count()
            else:
                count = User.query.filter(
                    and_(User.reputation_score >= min_score, User.reputation_score < max_score)
                ).count()
            
            ranges.append(label)
            counts.append(count)
        
        return success_response(
            data={
                'ranges': ranges,
                'counts': counts
            },
            message="获取用户信誉分布成功"
        )
    except Exception as e:
        return error_response(f"获取用户信誉分布失败: {str(e)}", 500)

@statistics_bp.route('/monthly-transaction-trend', methods=['GET'])
def get_monthly_transaction_trend():
    """获取月度交易趋势"""
    try:
        # 获取最近12个月的数据
        end_date = datetime.now().date()
        start_date = end_date.replace(day=1) - timedelta(days=365)
        
        # 按月统计不同状态的交易请求
        completed_data = db.session.query(
            func.date_format(Request.created_at, '%Y-%m').label('month'),
            func.count(Request.request_id).label('count')
        ).filter(
            and_(
                Request.status == 'completed',
                Request.created_at >= start_date
            )
        ).group_by(
            func.date_format(Request.created_at, '%Y-%m')
        ).all()
        
        pending_data = db.session.query(
            func.date_format(Request.created_at, '%Y-%m').label('month'),
            func.count(Request.request_id).label('count')
        ).filter(
            and_(
                Request.status == 'pending',
                Request.created_at >= start_date
            )
        ).group_by(
            func.date_format(Request.created_at, '%Y-%m')
        ).all()
        
        cancelled_data = db.session.query(
            func.date_format(Request.created_at, '%Y-%m').label('month'),
            func.count(Request.request_id).label('count')
        ).filter(
            and_(
                Request.status == 'cancelled',
                Request.created_at >= start_date
            )
        ).group_by(
            func.date_format(Request.created_at, '%Y-%m')
        ).all()
        
        # 获取所有月份
        all_months = set()
        for month, _ in completed_data + pending_data + cancelled_data:
            all_months.add(month)
        
        months = sorted(list(all_months))
        
        # 创建字典便于查找
        completed_dict = {month: count for month, count in completed_data}
        pending_dict = {month: count for month, count in pending_data}
        cancelled_dict = {month: count for month, count in cancelled_data}
        
        # 构建返回数据
        completed_counts = [completed_dict.get(month, 0) for month in months]
        pending_counts = [pending_dict.get(month, 0) for month in months]
        cancelled_counts = [cancelled_dict.get(month, 0) for month in months]
        
        return success_response(
            data={
                'months': months,
                'completed': completed_counts,
                'pending': pending_counts,
                'cancelled': cancelled_counts
            },
            message="获取月度交易趋势成功"
        )
    except Exception as e:
        return error_response(f"获取月度交易趋势失败: {str(e)}", 500)

@statistics_bp.route('/item-condition-distribution', methods=['GET'])
def get_item_condition_distribution():
    """获取物品新旧程度分布"""
    try:
        distribution = db.session.query(
            Item.condition,
            func.count(Item.item_id).label('count')
        ).group_by(Item.condition).all()
        
        condition_names = {
            'new': '全新',
            'like_new': '几乎全新',
            'used': '二手',
            'worn': '有磨损'
        }
        
        conditions = []
        counts = []
        for condition, count in distribution:
            conditions.append(condition_names.get(condition, condition))
            counts.append(count)
        
        return success_response(
            data={
                'conditions': conditions,
                'counts': counts
            },
            message="获取物品新旧程度分布成功"
        )
    except Exception as e:
        return error_response(f"获取物品新旧程度分布失败: {str(e)}", 500)

@statistics_bp.route('/daily-activity', methods=['GET'])
def get_daily_activity():
    """获取最近7天的活跃度统计"""
    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=6)
        
        dates = []
        new_users_data = []
        new_items_data = []
        new_requests_data = []
        current_date = start_date
        
        while current_date <= end_date:
            # 统计当天的各种活动
            new_users = User.query.filter(
                func.date(User.created_at) == current_date
            ).count()
            
            new_items = Item.query.filter(
                func.date(Item.created_at) == current_date
            ).count()
            
            new_requests = Request.query.filter(
                func.date(Request.created_at) == current_date
            ).count()
            
            dates.append(current_date.strftime('%Y-%m-%d'))
            new_users_data.append(new_users)
            new_items_data.append(new_items)
            new_requests_data.append(new_requests)
            
            current_date += timedelta(days=1)
        
        return success_response(
            data={
                'dates': dates,
                'new_users': new_users_data,
                'new_items': new_items_data,
                'new_requests': new_requests_data
            },
            message="获取每日活跃度统计成功"
        )
    except Exception as e:
        return error_response(f"获取每日活跃度统计失败: {str(e)}", 500)