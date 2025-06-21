from flask import Flask, render_template, redirect, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_migrate import Migrate
from config import DevelopmentConfig
from models import db
from utils import error_response
import os

# 导入蓝图
from auth import auth_bp
from items import items_bp
from categories import categories_bp
from requests import requests_bp
from reviews import reviews_bp
from messages import messages_bp
from statistics import statistics_bp


def create_app(config_class=DevelopmentConfig):
    """应用工厂函数"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # 初始化扩展
    db.init_app(app)
    jwt = JWTManager(app)
    CORS(app, origins=app.config['CORS_ORIGINS'])
    migrate = Migrate(app, db)
    
    # 创建上传目录
    upload_folder = app.config['UPLOAD_FOLDER']
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    
    # 注册蓝图
    app.register_blueprint(auth_bp)          # 用户认证相关API
    app.register_blueprint(items_bp)         # 物品管理API
    app.register_blueprint(categories_bp)    # 分类管理API
    app.register_blueprint(requests_bp)      # 交易请求API
    app.register_blueprint(reviews_bp)       # 评价管理API
    app.register_blueprint(messages_bp)      # 消息管理API
    app.register_blueprint(statistics_bp)    # 统计数据API

    
    # JWT错误处理
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return error_response("Token已过期，请重新登录", 401)
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return error_response("无效的Token", 401)
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return error_response("缺少访问Token", 401)
    
    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return error_response("Token已被撤销", 401)
    
    # 全局错误处理
    @app.errorhandler(400)
    def bad_request(error):
        return error_response("请求参数错误", 400)
    
    @app.errorhandler(404)
    def not_found(error):
        return error_response("请求的资源不存在", 404)
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        return error_response("请求方法不被允许", 405)
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return error_response("服务器内部错误", 500)
    
    # 健康检查端点
    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({
            'status': 'healthy',
            'message': '校园二手物品交易平台API服务正常运行',
            'version': '1.0.0'
        })
    
    # 图片上传端点
    @app.route('/api/v1/upload/image', methods=['POST'])
    def upload_image():
        """上传图片"""
        try:
            if 'image' not in request.files:
                return error_response("没有选择文件")
            
            file = request.files['image']
            if file.filename == '':
                return error_response("没有选择文件")
            
            from utils import save_uploaded_file
            image_url = save_uploaded_file(file, 'items')
            
            if image_url:
                return jsonify({
                    'success': True,
                    'message': '图片上传成功',
                    'data': {
                        'image_url': image_url
                    }
                })
            else:
                return error_response("文件格式不支持")
                
        except Exception as e:
            return error_response(f"上传失败: {str(e)}")
    
    # API根端点
    @app.route('/api/v1', methods=['GET'])
    def api_info():
        return jsonify({
            'name': '校园二手物品交易平台API',
            'version': '1.0.0',
            'description': '提供用户管理、物品管理、交易请求、评价系统等功能的RESTful API',
            'endpoints': {
                'auth': '/api/v1/users',
                'items': '/api/v1/items',
                'categories': '/api/v1/categories',
                'requests': '/api/v1/requests',
                'reviews': '/api/v1/reviews',
                'messages': '/api/v1/messages',
                'upload': '/api/v1/upload/image'
            }
        })
    
    # 后台管理系统路由
    @app.route('/login', methods=['GET'])
    def admin_login():
        """管理员登录页面"""
        return render_template('login.html')
    
    @app.route('/admin', methods=['GET'])
    def admin_dashboard():
        """后台管理主页面"""
        return render_template('admin.html')
    
    @app.route('/', methods=['GET'])
    def index():
        """首页重定向到管理后台"""
        return redirect('/admin')
    
    return app

# 创建应用实例
app = create_app()

if __name__ == '__main__':
    with app.app_context():
        # 创建数据库表
        db.create_all()
        print("数据库表创建完成")
        
        # 创建默认管理员用户（如果不存在）
        try:
            from models import User
            admin_user = User.query.filter_by(email='admin@example.com').first()
            if not admin_user:
                admin_user = User(
                    username='admin',
                    email='admin@example.com',
                    phone='13800000000',
                    address='管理员地址',
                    is_admin=True
                )
                admin_user.set_password('admin123')
                db.session.add(admin_user)
                db.session.commit()
                print("默认管理员用户创建完成")
                print("管理员账号: admin@example.com 或 admin")
                print("管理员密码: admin123")
            else:
                print("管理员用户已存在")
                print("管理员账号: admin@example.com 或 admin")
                print("管理员密码: admin123")
        except Exception as e:
            print(f"创建管理员用户时出错: {str(e)}")
            print("请检查数据库连接")
    
    print("\n=== 校园二手物品交易平台API服务 ===")
    print("服务地址: http://localhost:5000")
    print("API文档: http://localhost:5000/api/v1")
    print("健康检查: http://localhost:5000/health")
    print("=====================================\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
