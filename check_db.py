#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pymysql
from config import DevelopmentConfig

def check_mysql_connection():
    """检查MySQL数据库连接和表结构"""
    try:
        # 从配置中获取数据库连接信息
        config = DevelopmentConfig()
        
        # 解析数据库URI
        db_uri = config.SQLALCHEMY_DATABASE_URI
        print(f"数据库连接URI: {db_uri}")
        
        # 连接数据库
        connection = pymysql.connect(
            host=config.DB_HOST,
            port=int(config.DB_PORT),
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME,
            charset='utf8mb4'
        )
        
        print(f"✅ 成功连接到MySQL数据库: {config.DB_NAME}")
        
        # 查看表结构
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES;")
            tables = cursor.fetchall()
            
            if tables:
                print(f"\n📋 数据库中的表 ({len(tables)}个):")
                for table in tables:
                    print(f"  - {table[0]}")
                    
                # 查看每个表的结构
                for table in tables:
                    table_name = table[0]
                    cursor.execute(f"DESCRIBE {table_name};")
                    columns = cursor.fetchall()
                    print(f"\n🔍 表 '{table_name}' 的结构:")
                    for col in columns:
                        print(f"  {col[0]} - {col[1]} - {col[2]} - {col[3]}")
            else:
                print("\n⚠️  数据库中没有表")
        
        connection.close()
        print("\n✅ 数据库连接测试完成")
        
    except Exception as e:
        print(f"❌ 数据库连接失败: {str(e)}")
        return False
    
    return True

if __name__ == '__main__':
    check_mysql_connection()