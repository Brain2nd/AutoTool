#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
修复project_root引用问题
"""

import os
import re

def fix_project_root_references():
    """修复project_root变量引用问题"""
    
    files_to_fix = [
        "task_whl/larkbusiness/auto_ooin_lark.py",
        "task_whl/influencertool/batch_update_levels.py", 
        "task_whl/influencertool/update_price_range.py",
        "task_whl/influencertool/referesh_table_ALL.py",
        "task_whl/influencertool/update_product_category.py",
    ]
    
    for file_path in files_to_fix:
        if not os.path.exists(file_path):
            continue
            
        print(f"修复文件: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 修复项目根目录获取
        content = re.sub(
            r'project_root = current_file_path\.parents\[\d+\].*?\n',
            'config_base_path = current_file_path.parents[2]  # 配置文件基础路径\n',
            content
        )
        
        # 修复feishu-config.ini路径
        content = content.replace(
            'feishu_config_path = project_root / "feishu-config.ini"',
            'feishu_config_path = config_base_path / "feishu-config.ini"'
        )
        
        # 修复其他project_root引用
        content = content.replace('project_root /', 'config_base_path /')
        content = content.replace('project_root/', 'config_base_path/')
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    # 修复asyncbusiness中的引用
    async_files = [
        "task_whl/asyncbusiness/function/config.py",
        "task_whl/asyncbusiness/function/monitor.py", 
        "task_whl/asyncbusiness/function/db_handler.py"
    ]
    
    for file_path in async_files:
        if not os.path.exists(file_path):
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 删除多余的sys.path代码
        lines = content.split('\n')
        cleaned_lines = []
        skip_next = False
        
        for line in lines:
            if 'project_root = os.path.dirname' in line:
                # 跳过project_root定义和后续的sys.path代码
                skip_next = True
                continue
            elif skip_next and ('sys.path.insert' in line or 'if project_root not in' in line):
                continue
            else:
                skip_next = False
                cleaned_lines.append(line)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(cleaned_lines))

if __name__ == "__main__":
    fix_project_root_references()
    print("✅ project_root引用修复完成") 