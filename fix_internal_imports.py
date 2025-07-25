#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
修复内部导入脚本
将task_whl目录中的 from task.* 导入改为相对导入
"""

import os
import re
from typing import List, Tuple

def find_python_files(directory: str) -> List[str]:
    """查找所有Python文件"""
    python_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py') and not file.endswith('.backup'):
                python_files.append(os.path.join(root, file))
    return python_files

def fix_internal_imports(content: str, file_path: str) -> Tuple[str, List[str]]:
    """修复内部导入"""
    changes = []
    lines = content.split('\n')
    fixed_lines = []
    
    # 确定当前文件所在的模块路径
    if 'task_whl/' in file_path:
        base_path = file_path.split('task_whl/')[1]
        current_module = os.path.dirname(base_path).replace('/', '.')
    else:
        current_module = ""
    
    for line in lines:
        original_line = line
        
        # 处理不同类型的内部导入
        if 'from task.' in line:
            # 从 task_whl 目录开始的导入
            if 'from task.asyncbusiness.function import' in line:
                # asyncbusiness的function导入
                if 'asyncbusiness' in file_path:
                    fixed_line = line.replace('from task.asyncbusiness.function import', 'from .function import')
                else:
                    fixed_line = line.replace('from task.asyncbusiness.function import', 'from asyncbusiness.function import')
                    
            elif 'from task.macwx.function' in line:
                # macwx的function导入
                if 'macwx' in file_path:
                    # 如果在macwx目录内，使用相对导入
                    if '/function/' in file_path:
                        # 在function子目录内，导入其他function模块
                        fixed_line = re.sub(r'from task\.macwx\.function\.(\w+) import', r'from .\1 import', line)
                    else:
                        # 在macwx根目录，导入function模块
                        fixed_line = re.sub(r'from task\.macwx\.function\.(\w+) import', r'from .function.\1 import', line)
                        fixed_line = re.sub(r'from task\.macwx\.function import', r'from .function import', fixed_line)
                else:
                    # 从外部导入macwx
                    fixed_line = line.replace('from task.macwx.function', 'from macwx.function')
                    
            elif 'from task.larkbusiness.newfunction' in line:
                # larkbusiness的newfunction导入
                if 'larkbusiness' in file_path:
                    if '/newfunction/' in file_path:
                        # 在newfunction子目录内
                        fixed_line = re.sub(r'from task\.larkbusiness\.newfunction\.(\w+) import', r'from .\1 import', line)
                    else:
                        # 在larkbusiness根目录
                        fixed_line = re.sub(r'from task\.larkbusiness\.newfunction\.(\w+) import', r'from .newfunction.\1 import', line)
                else:
                    # 从外部导入
                    fixed_line = line.replace('from task.larkbusiness.newfunction', 'from larkbusiness.newfunction')
                    
            elif 'from task.hr.function' in line:
                # hr的function导入
                if 'hr' in file_path:
                    if '/function/' in file_path:
                        # 在function子目录内
                        fixed_line = re.sub(r'from task\.hr\.function\.(\w+) import', r'from .\1 import', line)
                    else:
                        # 在hr根目录
                        fixed_line = re.sub(r'from task\.hr\.function\.(\w+) import', r'from .function.\1 import', line)
                else:
                    # 从外部导入
                    fixed_line = line.replace('from task.hr.function', 'from hr.function')
                    
            elif 'from task.macwx.chat_item import' in line:
                # 同级模块导入
                if 'macwx' in file_path and '/function/' not in file_path:
                    fixed_line = line.replace('from task.macwx.chat_item import', 'from .chat_item import')
                else:
                    fixed_line = line.replace('from task.macwx.chat_item import', 'from macwx.chat_item import')
                    
            else:
                # 其他task导入，简单替换
                fixed_line = re.sub(r'from task\.(\w+)', r'from \1', line)
                
            if fixed_line != original_line:
                changes.append(f"修复导入: {original_line.strip()} -> {fixed_line.strip()}")
                line = fixed_line
        
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines), changes

def process_file(file_path: str) -> dict:
    """处理单个文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'from task.' not in content:
            return {'status': 'skipped', 'changes': []}
        
        # 备份
        backup_path = file_path + '.backup_imports'
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 修复导入
        fixed_content, changes = fix_internal_imports(content, file_path)
        
        if changes:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            return {
                'status': 'fixed',
                'changes': changes,
                'backup': backup_path
            }
        else:
            return {'status': 'no_changes', 'changes': []}
            
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e),
            'changes': []
        }

def main():
    """主函数"""
    task_whl_dir = "/Users/tangzhengzheng/Desktop/Code/AutoOOIN/task_whl"
    
    print("🔧 开始修复task_whl中的内部导入...")
    print(f"📂 目标目录: {task_whl_dir}")
    print("=" * 60)
    
    python_files = find_python_files(task_whl_dir)
    print(f"📋 找到 {len(python_files)} 个Python文件")
    
    fixed_files = 0
    total_changes = 0
    
    for file_path in python_files:
        relative_path = os.path.relpath(file_path, task_whl_dir)
        
        # 跳过某些文件
        if any(skip in relative_path for skip in ['README', 'test_whl_', '__pycache__']):
            continue
            
        result = process_file(file_path)
        
        if result['status'] == 'fixed':
            fixed_files += 1
            total_changes += len(result['changes'])
            print(f"✅ 修复: {relative_path}")
            for change in result['changes'][:3]:  # 只显示前3个变化
                print(f"    {change}")
            if len(result['changes']) > 3:
                print(f"    ... 还有 {len(result['changes'])-3} 处修改")
                
        elif result['status'] == 'error':
            print(f"❌ 错误: {relative_path} - {result['message']}")
    
    print("\n" + "=" * 60)
    print("📊 修复完成:")
    print(f"  🔧 修复文件: {fixed_files}")
    print(f"  📝 总修改数: {total_changes}")
    
    if fixed_files > 0:
        print(f"\n🎉 成功修复 {fixed_files} 个文件的内部导入！")
        print("💡 现在task_whl中的内部导入已规范化")
    else:
        print("\n✅ 没有找到需要修复的内部导入")

if __name__ == "__main__":
    main() 