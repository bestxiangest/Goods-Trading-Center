# 校园二手物品交易平台 - 后端API服务

这是一个基于Flask框架开发的校园二手物品交易平台后端API服务，提供完整的用户管理、物品管理、交易请求、评价系统和消息通知功能。

## 功能特性

### 核心功能
- **用户管理**: 用户注册、登录、个人信息管理
- **物品管理**: 物品发布、编辑、删除、搜索、分类
- **交易系统**: 交易请求、状态管理、交易完成
- **评价系统**: 用户互评、信誉度计算
- **消息通知**: 实时消息、系统通知
- **分类管理**: 物品分类的层级管理

### 技术特性
- RESTful API设计
- JWT身份认证
- 数据库迁移支持
- 文件上传处理
- 跨域资源共享(CORS)
- 完善的错误处理
- 数据验证和安全防护

## 技术栈

- **框架**: Flask 2.x
- **数据库**: MySQL 8.0+
- **ORM**: SQLAlchemy
- **身份认证**: Flask-JWT-Extended
- **数据库迁移**: Flask-Migrate
- **跨域处理**: Flask-CORS
- **密码加密**: Werkzeug
- **图像处理**: Pillow

## 项目结构

```
Goods Trading Center/
├── app.py                 # 主应用文件
├── config.py             # 配置文件
├── models.py             # 数据模型
├── utils.py              # 工具函数
├── auth.py               # 用户认证蓝图
├── items.py              # 物品管理蓝图
├── categories.py         # 分类管理蓝图
├── requests.py           # 交易请求蓝图
├── reviews.py            # 评价系统蓝图
├── messages.py           # 消息系统蓝图
├── requirements.txt      # 依赖包列表
├── .env                  # 环境变量配置
├── README.md             # 项目说明
└── uploads/              # 文件上传目录
```

## 快速开始

### 1. 环境准备

确保您的系统已安装：
- Python 3.8+
- MySQL 8.0+
- pip包管理器

### 2. 克隆项目

```bash
git clone <repository-url>
cd "Goods Trading Center"
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 数据库配置

1. 创建MySQL数据库：
```sql
CREATE DATABASE goods_trading_center CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

2. 修改`.env`文件中的数据库配置：
```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=your_username
DB_PASSWORD=your_password
DB_NAME=goods_trading_center
```

### 5. 初始化数据库

```bash
# 初始化数据库迁移
flask db init

# 生成迁移文件
flask db migrate -m "Initial migration"

# 应用迁移
flask db upgrade
```

或者直接运行应用（会自动创建表）：
```bash
python app.py
```

### 6. 运行应用

```bash
python app.py
```

应用将在 `http://localhost:5000` 启动。

## API文档

### 基础信息

- **基础URL**: `http://localhost:5000/api/v1`
- **认证方式**: JWT Bearer Token
- **数据格式**: JSON

### 主要端点

#### 用户管理 (`/api/v1/users`)
- `POST /register` - 用户注册
- `POST /login` - 用户登录
- `GET /me` - 获取当前用户信息
- `PUT /me` - 更新当前用户信息
- `GET /{user_id}` - 获取指定用户信息

#### 物品管理 (`/api/v1/items`)
- `GET /` - 获取物品列表
- `POST /` - 发布新物品
- `GET /{item_id}` - 获取物品详情
- `PUT /{item_id}` - 更新物品信息
- `DELETE /{item_id}` - 删除物品
- `GET /my` - 获取我的物品

#### 分类管理 (`/api/v1/categories`)
- `GET /` - 获取分类列表
- `GET /tree` - 获取分类树
- `POST /` - 创建分类（管理员）
- `PUT /{category_id}` - 更新分类（管理员）
- `DELETE /{category_id}` - 删除分类（管理员）

#### 交易请求 (`/api/v1/requests`)
- `GET /` - 获取请求列表
- `POST /` - 发起交易请求
- `GET /{request_id}` - 获取请求详情
- `PUT /{request_id}/status` - 更新请求状态
- `PUT /{request_id}/complete` - 完成交易

#### 评价系统 (`/api/v1/reviews`)
- `GET /` - 获取评价列表
- `POST /` - 创建评价
- `GET /{review_id}` - 获取评价详情
- `GET /user/{user_id}/statistics` - 获取用户评价统计

#### 消息系统 (`/api/v1/messages`)
- `GET /` - 获取消息列表
- `POST /` - 发送消息
- `GET /conversations` - 获取会话列表
- `PUT /{message_id}/read` - 标记消息已读

### 认证说明

大部分API需要JWT认证，请在请求头中包含：
```
Authorization: Bearer <your-jwt-token>
```

获取Token的方式：
1. 用户注册或登录成功后会返回`access_token`
2. 将Token添加到后续请求的Authorization头中

## 默认管理员账号

首次运行应用时会自动创建默认管理员账号：
- **邮箱**: admin@example.com
- **密码**: admin123

**注意**: 生产环境中请及时修改默认密码！

## 配置说明

### 环境变量配置 (`.env`)

```env
# 数据库配置
DB_HOST=localhost          # 数据库主机
DB_PORT=3306              # 数据库端口
DB_USER=root              # 数据库用户名
DB_PASSWORD=password      # 数据库密码
DB_NAME=goods_trading_center  # 数据库名

# 安全配置
SECRET_KEY=your-secret-key        # Flask密钥
JWT_SECRET_KEY=your-jwt-secret     # JWT密钥

# 文件上传配置
UPLOAD_FOLDER=uploads             # 上传目录
MAX_CONTENT_LENGTH=16777216       # 最大文件大小(16MB)

# CORS配置
CORS_ORIGINS=http://localhost:3000  # 允许的前端域名
```

### 配置类说明

- `DevelopmentConfig`: 开发环境配置
- `ProductionConfig`: 生产环境配置
- `TestingConfig`: 测试环境配置

## 数据库设计

### 主要数据表

1. **用户表 (user)**
   - 用户基本信息、认证信息、信誉度等

2. **物品分类表 (item_category)**
   - 支持层级分类结构

3. **物品表 (item)**
   - 物品详细信息、状态、位置等

4. **物品图片表 (item_image)**
   - 物品多图片支持

5. **交易请求表 (request)**
   - 交易请求状态管理

6. **评价表 (review)**
   - 用户互评系统

7. **消息表 (message)**
   - 消息通知系统

## 开发指南

### 添加新的API端点

1. 在相应的蓝图文件中添加路由函数
2. 使用`@jwt_required()`装饰器进行认证
3. 使用工具函数进行数据验证和响应格式化
4. 添加适当的错误处理

### 数据库迁移

```bash
# 生成迁移文件
flask db migrate -m "描述变更内容"

# 应用迁移
flask db upgrade

# 回滚迁移
flask db downgrade
```

### 测试API

推荐使用Postman或类似工具测试API：

1. 首先调用注册或登录接口获取Token
2. 在后续请求中添加Authorization头
3. 根据API文档发送正确格式的请求

## 部署说明

### 生产环境部署

1. **环境配置**
   ```bash
   export FLASK_ENV=production
   ```

2. **安全配置**
   - 修改`.env`中的密钥
   - 配置HTTPS
   - 设置防火墙规则

3. **数据库配置**
   - 使用生产级MySQL配置
   - 配置数据库连接池
   - 设置备份策略

4. **Web服务器**
   - 使用Gunicorn + Nginx
   - 配置负载均衡
   - 设置日志记录

### Docker部署

```dockerfile
# Dockerfile示例
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["python", "app.py"]
```

## 常见问题

### Q: 数据库连接失败
A: 检查MySQL服务是否启动，数据库配置是否正确

### Q: JWT Token过期
A: 重新登录获取新的Token，或实现Token刷新机制

### Q: 文件上传失败
A: 检查上传目录权限，文件大小是否超限

### Q: CORS错误
A: 检查前端域名是否在CORS_ORIGINS配置中

## 贡献指南

1. Fork项目
2. 创建功能分支
3. 提交变更
4. 发起Pull Request

## 许可证

本项目采用MIT许可证，详见LICENSE文件。

## 联系方式

如有问题或建议，请通过以下方式联系：
- 邮箱: [your-email@example.com]
- 项目地址: [repository-url]

---

**注意**: 这是一个教学项目，仅供学习和参考使用。在生产环境中使用前，请进行充分的安全评估和测试。