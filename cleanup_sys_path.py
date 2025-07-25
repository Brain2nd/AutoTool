#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
清理sys.path脚本
删除task_whl目录中所有多余的sys.path.append代码
因为使用whl包后，这些代码都是多余的
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
    backup_path = file_path + '.backup_cleanup'
    with open(file_path, 'r', encoding='utf-8') as src:
        with open(backup_path, 'w', encoding='utf-8') as dst:
            dst.write(src.read())
    return backup_path

def clean_sys_path_code(content: str) -> Tuple[str, List[str]]:
    """清理sys.path相关代码"""
    changes = []
    lines = content.split('\n')
    cleaned_lines = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # 检查是否是sys.path相关的代码块
        if any(pattern in stripped for pattern in [
            'current_dir = pathlib.Path(__file__).parent',
            'project_root = current_dir.parent',
            'sys.path.append(str(project_root))',
            'sys.path.append(str(root_dir))',
            'sys.path.insert(0, str(project_root))',
            'sys.path.insert(0, str(root_dir))',
            'if str(project_root) not in sys.path:',
            'if str(root_dir) not in sys.path:'
        ]):
            # 检查是否是完整的代码块
            if 'current_dir = pathlib.Path(__file__).parent' in stripped:
                # 找到一个完整的sys.path代码块，跳过整个块
                block_lines = []
                block_start = i
                
                # 收集整个代码块
                while i < len(lines):
                    block_lines.append(lines[i])
                    if 'sys.path.append' in lines[i] or 'sys.path.insert' in lines[i]:
                        i += 1
                        break
                    i += 1
                
                # 记录删除的代码块
                changes.append(f"删除sys.path代码块 (行 {block_start+1}-{i}):")
                for block_line in block_lines:
                    if block_line.strip():
                        changes.append(f"  - {block_line}")
                
                continue
            
            elif any(pattern in stripped for pattern in [
                'sys.path.append',
                'sys.path.insert',
                'if str(project_root) not in sys.path:',
                'if str(root_dir) not in sys.path:'
            ]):
                # 单独的sys.path语句
                changes.append(f"删除 (行 {i+1}): {line}")
                i += 1
                continue
            
            elif 'project_root = ' in stripped and ('parent' in stripped or 'dirname' in stripped):
                # 项目根目录定义语句
                changes.append(f"删除 (行 {i+1}): {line}")
                i += 1
                continue
        
        # 保留其他代码
        cleaned_lines.append(line)
        i += 1
    
    # 清理多余的空行
    final_lines = []
    prev_empty = False
    for line in cleaned_lines:
        if line.strip() == '':
            if not prev_empty:
                final_lines.append(line)
            prev_empty = True
        else:
            final_lines.append(line)
            prev_empty = False
    
    return '\n'.join(final_lines), changes

def process_file(file_path: str) -> Dict[str, any]:
    """处理单个文件"""
    try:
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # 检查是否包含sys.path相关代码
        if 'sys.path' not in original_content:
            return {
                'status': 'skipped',
                'message': '没有sys.path代码',
                'changes': []
            }
        
        # 创建备份
        backup_path = backup_file(file_path)
        
        # 清理代码
        cleaned_content, changes = clean_sys_path_code(original_content)
        
        # 如果有变化，写入文件
        if changes:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)
            
            return {
                'status': 'cleaned',
                'message': f'清理了 {len(changes)} 处sys.path代码',
                'changes': changes,
                'backup': backup_path
            }
        else:
            return {
                'status': 'no_changes',
                'message': '没有需要清理的sys.path代码',
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
    
    print("🧹 开始清理task_whl目录中的sys.path代码...")
    print("📝 原因：使用whl包后，这些代码都是多余的，甚至有害")
    print(f"📂 目标目录: {task_whl_dir}")
    print("=" * 80)
    
    # 查找所有Python文件
    python_files = find_python_files(task_whl_dir)
    print(f"📋 找到 {len(python_files)} 个Python文件")
    
    # 统计信息
    total_files = len(python_files)
    cleaned_files = 0
    skipped_files = 0
    error_files = 0
    total_changes = 0
    
    # 处理每个文件
    for i, file_path in enumerate(python_files, 1):
        relative_path = os.path.relpath(file_path, task_whl_dir)
        
        # 跳过某些文件
        if any(skip in relative_path for skip in ['README', 'test_whl_', '__pycache__', 'MIGRATION']):
            continue
            
        result = process_file(file_path)
        
        if result['status'] == 'cleaned':
            cleaned_files += 1
            total_changes += len(result['changes'])
            print(f"[{i}/{total_files}] 清理: {relative_path}")
            print(f"  ✅ {result['message']}")
            # 只显示前3个变化，避免输出过长
            for change in result['changes'][:3]:
                print(f"    {change}")
            if len(result['changes']) > 3:
                print(f"    ... 还有 {len(result['changes'])-3} 处修改")
                
        elif result['status'] == 'skipped':
            skipped_files += 1
            
        elif result['status'] == 'error':
            error_files += 1
            print(f"[{i}/{total_files}] 错误: {relative_path}")
            print(f"  ❌ {result['message']}")
    
    # 输出统计结果
    print("\n" + "=" * 80)
    print("📊 清理完成统计:")
    print(f"  📁 处理文件: {total_files}")
    print(f"  🧹 清理文件: {cleaned_files}")
    print(f"  ⏭️  跳过文件: {skipped_files}")
    print(f"  ❌ 错误文件: {error_files}")
    print(f"  🗑️  删除代码: {total_changes} 处")
    
    if cleaned_files > 0:
        print(f"\n🎉 清理完成！处理了 {cleaned_files} 个文件，删除了 {total_changes} 处多余代码！")
        print("💡 现在task_whl完全独立，不再依赖项目根目录")
        print("🔒 源码保护更加彻底，用户无法通过sys.path访问原始代码")
    else:
        print("\n✅ 没有找到需要清理的sys.path代码！")

if __name__ == "__main__":
    main() 