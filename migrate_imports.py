#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
导入语句迁移脚本
将 task_whl 目录中的 tool.* 导入语句修改为直接导入whl包中的模块
"""

import os
import re
import pathlib
from typing import List, Dict, Tuple

def find_python_files(directory: str) -> List[str]:
    """
    递归查找所有Python文件
    
    Args:
        directory: 目录路径
        
    Returns:
        Python文件路径列表
    """
    python_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    return python_files

def backup_file(file_path: str) -> str:
    """
    备份文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        备份文件路径
    """
    backup_path = file_path + '.backup'
    with open(file_path, 'r', encoding='utf-8') as src:
        with open(backup_path, 'w', encoding='utf-8') as dst:
            dst.write(src.read())
    return backup_path

def update_imports(content: str) -> Tuple[str, List[str]]:
    """
    更新导入语句
    
    Args:
        content: 文件内容
        
    Returns:
        (更新后的内容, 修改列表)
    """
    changes = []
    
    # 定义导入映射规则
    import_mappings = {
        # 基础模块导入
        r'from tool\.browser\.browsertool import (.+)': r'from browser.browsertool import \1',
        r'from tool\.chat\.postgreschattool import (.+)': r'from chat.postgreschattool import \1',
        r'from tool\.db\.postgrestool import (.+)': r'from db.postgrestool import \1',
        r'from tool\.cache\.postgrescachetool import (.+)': r'from cache.postgrescachetool import \1',
        r'from tool\.wx\.AsyncWxTool import (.+)': r'from wx.AsyncWxTool import \1',
        r'from tool\.rag\.ragtool import (.+)': r'from rag.ragtool import \1',
        r'from tool\.ppadb\.ppadbtool import (.+)': r'from ppadb.ppadbtool import \1',
        r'from tool\.db\.SCAdatabaseTool import (.+)': r'from db.SCAdatabaseTool import \1',
        r'from tool\.db\.whitelist_db_tool import (.+)': r'from db.whitelist_db_tool import \1',
        r'from tool\.lark\.lark import (.+)': r'from lark.lark import \1',
        r'from tool\.browser\.chrome_launcher import (.+)': r'from browser.chrome_launcher import \1',
        r'from tool\.volcengine\.volcenginetool import (.+)': r'from volcengine.volcenginetool import \1',
        
        # 完整模块导入
        r'import tool\.browser\.browsertool': r'import browser.browsertool',
        r'import tool\.chat\.postgreschattool': r'import chat.postgreschattool',
        r'import tool\.db\.postgrestool': r'import db.postgrestool',
        r'import tool\.cache\.postgrescachetool': r'import cache.postgrescachetool',
        r'import tool\.wx\.AsyncWxTool': r'import wx.AsyncWxTool',
        r'import tool\.rag\.ragtool': r'import rag.ragtool',
        r'import tool\.ppadb\.ppadbtool': r'import ppadb.ppadbtool',
        
        # 子模块导入
        r'from tool\.browser\.function import (.+)': r'from browser.function import \1',
        r'from tool\.chat\.config import (.+)': r'from chat.config import \1',
        r'from tool\.chat\.template import (.+)': r'from chat.template import \1',
    }
    
    updated_content = content
    
    # 应用所有映射规则
    for old_pattern, new_pattern in import_mappings.items():
        matches = list(re.finditer(old_pattern, updated_content))
        if matches:
            for match in matches:
                old_line = match.group(0)
                new_line = re.sub(old_pattern, new_pattern, old_line)
                changes.append(f"  {old_line} -> {new_line}")
            updated_content = re.sub(old_pattern, new_pattern, updated_content)
    
    return updated_content, changes

def process_file(file_path: str, create_backup: bool = True) -> Dict[str, any]:
    """
    处理单个文件
    
    Args:
        file_path: 文件路径
        create_backup: 是否创建备份
        
    Returns:
        处理结果字典
    """
    try:
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # 检查是否包含tool导入
        if 'from tool.' not in original_content and 'import tool.' not in original_content:
            return {
                'status': 'skipped',
                'message': '没有tool导入语句',
                'changes': []
            }
        
        # 创建备份
        if create_backup:
            backup_path = backup_file(file_path)
        
        # 更新导入语句
        updated_content, changes = update_imports(original_content)
        
        # 如果有变化，写入文件
        if changes:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            return {
                'status': 'updated',
                'message': f'已更新 {len(changes)} 个导入语句',
                'changes': changes,
                'backup': backup_path if create_backup else None
            }
        else:
            return {
                'status': 'no_changes',
                'message': '没有需要更新的导入语句',
                'changes': []
            }
            
    except Exception as e:
        return {
            'status': 'error',
            'message': f'处理文件时出错: {str(e)}',
            'changes': []
        }

def main():
    """主函数"""
    task_whl_dir = "/Users/tangzhengzheng/Desktop/Code/AutoOOIN/task_whl"
    
    print("🚀 开始迁移task_whl目录中的导入语句...")
    print(f"📂 目标目录: {task_whl_dir}")
    print("=" * 80)
    
    # 查找所有Python文件
    python_files = find_python_files(task_whl_dir)
    print(f"📋 找到 {len(python_files)} 个Python文件")
    
    # 统计信息
    total_files = len(python_files)
    updated_files = 0
    skipped_files = 0
    error_files = 0
    total_changes = 0
    
    # 处理每个文件
    for i, file_path in enumerate(python_files, 1):
        relative_path = os.path.relpath(file_path, task_whl_dir)
        print(f"\n[{i}/{total_files}] 处理文件: {relative_path}")
        
        result = process_file(file_path)
        
        if result['status'] == 'updated':
            updated_files += 1
            total_changes += len(result['changes'])
            print(f"  ✅ {result['message']}")
            for change in result['changes']:
                print(change)
            if result.get('backup'):
                print(f"  💾 备份文件: {os.path.basename(result['backup'])}")
                
        elif result['status'] == 'skipped':
            skipped_files += 1
            print(f"  ⏭️  {result['message']}")
            
        elif result['status'] == 'no_changes':
            skipped_files += 1
            print(f"  ⚠️  {result['message']}")
            
        elif result['status'] == 'error':
            error_files += 1
            print(f"  ❌ {result['message']}")
    
    # 输出统计结果
    print("\n" + "=" * 80)
    print("📊 迁移完成统计:")
    print(f"  📁 总文件数: {total_files}")
    print(f"  ✅ 更新文件: {updated_files}")
    print(f"  ⏭️  跳过文件: {skipped_files}")
    print(f"  ❌ 错误文件: {error_files}")
    print(f"  🔄 总修改数: {total_changes}")
    
    if updated_files > 0:
        print(f"\n🎉 成功更新 {updated_files} 个文件，共 {total_changes} 处导入语句！")
        print("💡 所有原文件已备份，后缀为 .backup")
        print("🚀 现在可以使用新的conda环境运行task_whl中的脚本了！")
    else:
        print("\n ℹ️ 没有文件需要更新。")

if __name__ == "__main__":
    main() 