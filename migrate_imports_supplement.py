#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
补充迁移脚本
修正遗漏的导入语句
"""

import os
import re
import pathlib
from typing import List, Dict, Tuple

def find_python_files(directory: str) -> List[str]:
    """查找所有Python文件"""
    python_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py') and not file.endswith('.backup'):
                python_files.append(os.path.join(root, file))
    return python_files

def backup_file(file_path: str) -> str:
    """备份文件"""
    backup_path = file_path + '.backup2'
    with open(file_path, 'r', encoding='utf-8') as src:
        with open(backup_path, 'w', encoding='utf-8') as dst:
            dst.write(src.read())
    return backup_path

def update_remaining_imports(content: str) -> Tuple[str, List[str]]:
    """更新剩余的导入语句"""
    changes = []
    
    # 补充导入映射规则
    import_mappings = {
        # 遗漏的导入
        r'from tool\.lark\.list import (.+)': r'from lark.list import \1',
        r'from tool\.browser\.function\.connect_to_chrome import (.+)': r'from browser.function.connect_to_chrome import \1',
        r'from tool\.browser\.function\.find_elements_by_class import (.+)': r'from browser.function.find_elements_by_class import \1',
        r'from tool\.browser\.function\.(.+) import (.+)': r'from browser.function.\1 import \2',
        r'from tool\.volcengine\.ttsTool import (.+)': r'from volcengine.ttsTool import \1',
        r'from tool\.ppadb\.test\.(.+) import (.+)': r'from ppadb.test.\1 import \2',
        
        # 完整模块导入
        r'import tool\.lark\.list': r'import lark.list',
        r'import tool\.browser\.function\.(.+)': r'import browser.function.\1',
        r'import tool\.volcengine\.ttsTool': r'import volcengine.ttsTool',
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

def process_file(file_path: str) -> Dict[str, any]:
    """处理单个文件"""
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
        backup_path = backup_file(file_path)
        
        # 更新导入语句
        updated_content, changes = update_remaining_imports(original_content)
        
        # 如果有变化，写入文件
        if changes:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            return {
                'status': 'updated',
                'message': f'已更新 {len(changes)} 个导入语句',
                'changes': changes,
                'backup': backup_path
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
    
    print("🔧 开始补充迁移遗漏的导入语句...")
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
        
        # 跳过某些文件
        if any(skip in relative_path for skip in ['README', 'test_whl_', '__pycache__']):
            continue
            
        result = process_file(file_path)
        
        if result['status'] == 'updated':
            updated_files += 1
            total_changes += len(result['changes'])
            print(f"[{i}/{total_files}] 更新: {relative_path}")
            print(f"  ✅ {result['message']}")
            for change in result['changes']:
                print(change)
                
        elif result['status'] == 'error':
            error_files += 1
            print(f"[{i}/{total_files}] 错误: {relative_path}")
            print(f"  ❌ {result['message']}")
    
    # 输出统计结果
    print("\n" + "=" * 80)
    print("📊 补充迁移统计:")
    print(f"  📁 处理文件: {total_files}")
    print(f"  ✅ 更新文件: {updated_files}")
    print(f"  ❌ 错误文件: {error_files}")
    print(f"  🔄 总修改数: {total_changes}")
    
    if updated_files > 0:
        print(f"\n🎉 补充完成！更新了 {updated_files} 个文件，共 {total_changes} 处导入语句！")
    else:
        print("\n✅ 没有找到需要补充的导入语句！")

if __name__ == "__main__":
    main() 