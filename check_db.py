#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os

def check_database():
    db_path = 'goods_trading.db'
    if not os.path.exists(db_path):
        print(f"数据库文件 {db_path} 不存在")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 获取所有表名
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print("数据库中的表:")
    for table in tables:
        print(f"- {table[0]}")
    
    # 检查是否有图片相关的表
    for table in tables:
        table_name = table[0]
        if 'image' in table_name.lower():
            print(f"\n表 {table_name} 的结构:")
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            for col in columns:
                print(f"  {col[1]} ({col[2]})")
            
            # 查看表中的数据
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 5;")
            rows = cursor.fetchall()
            print(f"\n表 {table_name} 中的前5条数据:")
            for row in rows:
                print(f"  {row}")
    
    conn.close()

if __name__ == '__main__':
    check_database()