import os
from datetime import timedelta
from dotenv import load_dotenv

# 加载环境变量 (Load Environment Variables)
# load_dotenv() 会读取项目根目录下的一个叫 .env 的文件。

load_dotenv()
# 基础配置类 (Base Config Class)
# 创建一个叫 Config 的基础类，所有环境通用的配置都放在这里。
# 其他特定环境的配置类可以继承它，并覆盖或添加自己的配置。
class Config:
    """基础配置类"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # ----------------- 数据库配置 (Database Configuration) -----------------
    # 数据库配置 - 使用MySQL数据库
    DB_HOST = os.environ.get('DB_HOST') or 'localhost'
    DB_PORT = os.environ.get('DB_PORT') or '3306'
    DB_USER = os.environ.get('DB_USER') or 'root'
    DB_PASSWORD = os.environ.get('DB_PASSWORD') or 'zzn20041031'
    DB_NAME = os.environ.get('DB_NAME') or 'secondhand_trading_platform'
    
    # SQLALCHEMY_DATABASE_URI 是 Flask-SQLAlchemy 扩展用来连接数据库的字符串。
    # 它的格式是：'数据库类型+驱动://用户名:密码@地址:端口/数据库名?参数'
    # `charset=utf8mb4` 是为了支持中文字符和 emoji。
    basedir = os.path.abspath(os.path.dirname(__file__))
    # SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{os.path.join(basedir, "goods_trading.db")}'
    # 如果需要使用MySQL，请取消注释下面一行并注释上面一行
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4'
    # 关闭一个Flask-SQLAlchemy的追踪功能，可以节省系统资源。
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # 数据库连接池的一些高级选项，用于优化性能和稳定性。
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,# 每次从连接池取连接前，先测试一下连接是否有效。
        'pool_recycle': 300,# 连接在被回收前可以存活的最长时间（秒）。
        'pool_timeout': 20,
        'max_overflow': 0
    }
    # ----------------- JWT 配置 (JWT Configuration) -----------------
    # JWT (JSON Web Token) 是我们用来做用户登录认证的。
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-string'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # ----------------- 文件上传配置 (File Upload Configuration) -----------------
    # UPLOAD_FOLDER 定义了用户上传的文件（比如商品图片）应该保存在服务器的哪个位置。
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    
    # ----------------- CORS 配置 (CORS Configuration) -----------------
    # CORS_ORIGINS 是一个列表，里面包含了允许访问我们后端API的前端服务器地址。
    CORS_ORIGINS = [
        'http://localhost:3000', 'http://127.0.0.1:3000',
        'http://localhost:5000', 'http://127.0.0.1:5000'
    ]

# 特定环境配置类 (Environment-specific Configs)
# 这些类都继承自上面的 Config 基类，所以它们拥有所有基础配置，
# 并且可以定义自己独有的或覆盖掉基础的配置。
class DevelopmentConfig(Config):
    """开发环境配置"""
    # 开启调试模式，这样代码改动后服务器会自动重启，并且出错时会显示详细信息。
    DEBUG = True
    
class ProductionConfig(Config):
    """生产（线上）环境配置"""
    # 线上环境必须关闭调试模式！
    DEBUG = False
    
class TestingConfig(Config):
    """测试环境配置"""
    # 在测试时，我们通常会用一个专门的测试数据库，以免污染开发或生产数据。
    TESTING = True
    DB_NAME = 'secondhand_trading_platform_test'
    SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{Config.DB_USER}:{Config.DB_PASSWORD}@{Config.DB_HOST}:{Config.DB_PORT}/{DB_NAME}?charset=utf8mb4'
    

# 配置字典 (Config Dictionary)
# 创建一个字典，方便我们根据一个字符串（'development', 'production'等）来选择使用哪个配置类。
# 在 app.py 中，我们默认使用了 DevelopmentConfig。
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}