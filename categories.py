from flask import Blueprint, request, jsonify
from models import ItemCategory, Item, db
from utils import success_response, error_response, validate_required_fields, paginate_query, admin_required
from sqlalchemy import func

categories_bp = Blueprint('categories', __name__, url_prefix='/api/v1/categories')

@categories_bp.route('', methods=['GET'])
def get_categories():
    """获取分类列表"""
    try:
        include_children = request.args.get('include_children', 'false').lower() == 'true'
        parent_id = request.args.get('parent_id', type=int)
        
        if parent_id is not None:
            # 获取指定父分类下的子分类
            categories = ItemCategory.query.filter_by(parent_id=parent_id).all()
        else:
            # 获取所有根分类
            categories = ItemCategory.query.filter_by(parent_id=None).all()
        
        categories_data = []
        for category in categories:
            category_data = category.to_dict(include_children=include_children)
            # 添加物品数量统计
            category_data['item_count'] = category.items.filter_by(status='available').count()
            categories_data.append(category_data)
        
        return success_response(
            data=categories_data,
            message="获取分类列表成功"
        )
        
    except Exception as e:
        return error_response(f"获取分类列表失败: {str(e)}", 500)

@categories_bp.route('/tree', methods=['GET'])
def get_categories_tree():
    """获取完整的分类树"""
    try:
        # 获取所有根分类
        root_categories = ItemCategory.query.filter_by(parent_id=None).all()
        
        def build_tree(category):
            """递归构建分类树"""
            category_data = category.to_dict()
            category_data['item_count'] = category.items.filter_by(status='available').count()
            
            children = category.children.all()
            if children:
                category_data['children'] = [build_tree(child) for child in children]
            else:
                category_data['children'] = []
            
            return category_data
        
        tree_data = [build_tree(category) for category in root_categories]
        
        return success_response(
            data=tree_data,
            message="获取分类树成功"
        )
        
    except Exception as e:
        return error_response(f"获取分类树失败: {str(e)}", 500)

@categories_bp.route('/<int:category_id>', methods=['GET'])
def get_category(category_id):
    """获取分类详情"""
    try:
        category = ItemCategory.query.get(category_id)
        if not category:
            return error_response("分类不存在", 404)
        
        category_data = category.to_dict(include_children=True)
        category_data['item_count'] = category.items.filter_by(status='available').count()
        
        # 获取父分类信息
        if category.parent:
            category_data['parent_name'] = category.parent.name
        
        return success_response(
            data=category_data,
            message="获取分类详情成功"
        )
        
    except Exception as e:
        return error_response(f"获取分类详情失败: {str(e)}", 500)

@categories_bp.route('', methods=['POST'])
def create_category():
    """创建新分类（管理员功能）"""
    try:
        data = request.get_json()
        if not data:
            return error_response("请求数据不能为空")
        
        # 验证必需字段
        required_fields = ['name']
        validation_error = validate_required_fields(data, required_fields)
        if validation_error:
            return error_response(validation_error)
        
        name = data['name'].strip()
        parent_id = data.get('parent_id')
        
        # 验证数据格式
        if len(name) < 1 or len(name) > 50:
            return error_response("分类名称长度必须在1-50个字符之间")
        
        # 检查同级分类名称是否重复
        existing_category = ItemCategory.query.filter_by(
            name=name,
            parent_id=parent_id
        ).first()
        if existing_category:
            return error_response("同级分类中已存在相同名称的分类")
        
        # 验证父分类是否存在
        if parent_id is not None:
            parent_category = ItemCategory.query.get(parent_id)
            if not parent_category:
                return error_response("父分类不存在")
        
        # 创建分类
        category = ItemCategory(
            name=name,
            parent_id=parent_id
        )
        
        db.session.add(category)
        db.session.commit()
        
        return success_response(
            data=category.to_dict(),
            message="分类创建成功",
            code=201
        )
        
    except Exception as e:
        db.session.rollback()
        return error_response(f"创建分类失败: {str(e)}", 500)

@categories_bp.route('/<int:category_id>', methods=['PUT'])
def update_category(category_id):
    """更新分类信息（管理员功能）"""
    try:
        category = ItemCategory.query.get(category_id)
        if not category:
            return error_response("分类不存在", 404)
        
        data = request.get_json()
        if not data:
            return error_response("请求数据不能为空")
        
        # 更新分类名称
        if 'name' in data:
            name = data['name'].strip()
            if len(name) < 1 or len(name) > 50:
                return error_response("分类名称长度必须在1-50个字符之间")
            
            # 检查同级分类名称是否重复
            existing_category = ItemCategory.query.filter(
                ItemCategory.name == name,
                ItemCategory.parent_id == category.parent_id,
                ItemCategory.category_id != category_id
            ).first()
            if existing_category:
                return error_response("同级分类中已存在相同名称的分类")
            
            category.name = name
        
        # 更新父分类
        if 'parent_id' in data:
            new_parent_id = data['parent_id']
            
            # 防止循环引用
            if new_parent_id is not None:
                # 检查新父分类是否存在
                new_parent = ItemCategory.query.get(new_parent_id)
                if not new_parent:
                    return error_response("父分类不存在")
                
                # 检查是否会形成循环引用
                def check_circular_reference(parent_id, target_id):
                    if parent_id == target_id:
                        return True
                    parent = ItemCategory.query.get(parent_id)
                    if parent and parent.parent_id:
                        return check_circular_reference(parent.parent_id, target_id)
                    return False
                
                if check_circular_reference(new_parent_id, category_id):
                    return error_response("不能将分类设置为其子分类的父分类")
            
            category.parent_id = new_parent_id
        
        db.session.commit()
        
        return success_response(
            data=category.to_dict(),
            message="分类更新成功"
        )
        
    except Exception as e:
        db.session.rollback()
        return error_response(f"更新分类失败: {str(e)}", 500)

@categories_bp.route('/<int:category_id>', methods=['DELETE'])
def delete_category(category_id):
    """删除分类（管理员功能）"""
    try:
        category = ItemCategory.query.get(category_id)
        if not category:
            return error_response("分类不存在", 404)
        
        # 检查是否有子分类
        children_count = category.children.count()
        if children_count > 0:
            return error_response("该分类下还有子分类，无法删除")
        
        # 检查是否有物品使用此分类
        items_count = category.items.count()
        if items_count > 0:
            return error_response("该分类下还有物品，无法删除")
        
        db.session.delete(category)
        db.session.commit()
        
        return success_response(
            message="分类删除成功",
            code=204
        )
        
    except Exception as e:
        db.session.rollback()
        return error_response(f"删除分类失败: {str(e)}", 500)

@categories_bp.route('/search', methods=['GET'])
def search_categories():
    """搜索分类"""
    try:
        keyword = request.args.get('keyword', '').strip()
        if not keyword:
            return error_response("搜索关键词不能为空")
        
        categories = ItemCategory.query.filter(
            ItemCategory.name.contains(keyword)
        ).all()
        
        categories_data = []
        for category in categories:
            category_data = category.to_dict()
            category_data['item_count'] = category.items.filter_by(status='available').count()
            
            # 添加完整路径
            path = []
            current = category
            while current:
                path.insert(0, current.name)
                current = current.parent
            category_data['full_path'] = ' > '.join(path)
            
            categories_data.append(category_data)
        
        return success_response(
            data=categories_data,
            message="搜索分类成功"
        )
        
    except Exception as e:
        return error_response(f"搜索分类失败: {str(e)}", 500)

@categories_bp.route('/popular', methods=['GET'])
def get_popular_categories():
    """获取热门分类"""
    try:
        limit = request.args.get('limit', 10, type=int)
        limit = min(limit, 50)  # 限制最大数量
        
        # 查询有物品的分类，按物品数量排序
        from sqlalchemy import func
        from models import Item
        
        popular_categories = db.session.query(
            ItemCategory,
            func.count(Item.item_id).label('item_count')
        ).join(
            Item, ItemCategory.category_id == Item.category_id
        ).filter(
            Item.status == 'available'
        ).group_by(
            ItemCategory.category_id
        ).order_by(
            func.count(Item.item_id).desc()
        ).limit(limit).all()
        
        categories_data = []
        for category, item_count in popular_categories:
            category_data = category.to_dict()
            category_data['item_count'] = item_count
            categories_data.append(category_data)
        
        return success_response(
            data=categories_data,
            message="获取热门分类成功"
        )
        
    except Exception as e:
        return error_response(f"获取热门分类失败: {str(e)}", 500)