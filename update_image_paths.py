#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新数据库中的图片路径，将uploads/文件名改为uploads/items/文件名
"""

import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from models import db, ItemImage

def create_app():
    """创建Flask应用"""
    app = Flask(__name__)
    
    # 数据库配置
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "goods_trading.db")}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    return app

def update_image_paths():
    """更新图片路径"""
    app = create_app()
    
    with app.app_context():
        try:
            # 查找所有需要更新的图片记录
            images_to_update = ItemImage.query.filter(
                ItemImage.image_url.like('uploads/%')
            ).filter(
                ~ItemImage.image_url.like('uploads/items/%')
            ).all()
            
            print(f"找到 {len(images_to_update)} 条需要更新的图片记录")
            
            updated_count = 0
            for image in images_to_update:
                old_path = image.image_url
                # 提取文件名
                filename = os.path.basename(old_path)
                # 构建新路径
                new_path = f"uploads/items/{filename}"
                
                print(f"更新: {old_path} -> {new_path}")
                
                # 更新数据库记录
                image.image_url = new_path
                updated_count += 1
            
            # 提交更改
            db.session.commit()
            print(f"成功更新了 {updated_count} 条图片路径记录")
            
        except Exception as e:
            print(f"更新过程中出现错误: {e}")
            db.session.rollback()
            return False
    
    return True

if __name__ == '__main__':
    print("开始更新图片路径...")
    success = update_image_paths()
    if success:
        print("图片路径更新完成！")
    else:
        print("图片路径更新失败！")
        sys.exit(1)