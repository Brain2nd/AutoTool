#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
白名单数据迁移脚本

功能：
- 将现有的文件白名单数据迁移到数据库
- 支持批量迁移多个模块
- 提供备份和恢复功能
- 验证迁移完整性

支持的模块：
- larkbusiness: 飞书商务模块（唯一支持的模块）
"""

import asyncio
import sys
import os
import pathlib
import shutil
from datetime import datetime
from typing import Dict, List, Any

# 添加项目根目录到路径
current_dir = pathlib.Path(__file__).parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from whitelist_db_tool import WhitelistDBTool


class WhitelistMigrationTool:
    """白名单数据迁移工具"""
    
    def __init__(self):
        """初始化迁移工具"""
        self.whitelist_db_tool = None
        self.project_root = project_root
        
        # 模块到文件路径的映射（只支持larkbusiness）
        self.module_file_mapping = {
            'larkbusiness': 'task/larkbusiness/whitelist/whitelist.txt'
        }
        
        # 备份目录
        self.backup_dir = self.project_root / "tool" / "db" / "whitelist_backups"
        
    async def initialize(self):
        """初始化数据库连接"""
        try:
            self.whitelist_db_tool = WhitelistDBTool()
            success = await self.whitelist_db_tool.connect()
            if success:
                print("✅ 数据库连接成功")
                return True
            else:
                print("❌ 数据库连接失败")
                return False
        except Exception as e:
            print(f"❌ 初始化数据库连接失败: {e}")
            return False
    
    async def close(self):
        """关闭数据库连接"""
        if self.whitelist_db_tool:
            await self.whitelist_db_tool.close()
    
    def create_backup_directory(self):
        """创建备份目录"""
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_session_dir = self.backup_dir / f"migration_{timestamp}"
            backup_session_dir.mkdir(exist_ok=True)
            return backup_session_dir
        except Exception as e:
            print(f"❌ 创建备份目录失败: {e}")
            return None
    
    def read_whitelist_file(self, file_path: pathlib.Path) -> List[str]:
        """
        读取白名单文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            List[str]: 白名单项目列表
        """
        try:
            if not file_path.exists():
                print(f"⚠️ 白名单文件不存在: {file_path}")
                return []
            
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 过滤注释和空行
            whitelist_items = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    whitelist_items.append(line)
            
            print(f"📖 读取文件 {file_path.name}: {len(whitelist_items)} 个项目")
            return whitelist_items
            
        except Exception as e:
            print(f"❌ 读取文件失败 {file_path}: {e}")
            return []
    
    def backup_file(self, file_path: pathlib.Path, backup_dir: pathlib.Path) -> bool:
        """
        备份文件
        
        Args:
            file_path: 源文件路径
            backup_dir: 备份目录
            
        Returns:
            bool: 备份是否成功
        """
        try:
            if not file_path.exists():
                return True  # 文件不存在，无需备份
            
            # 构建备份文件名
            relative_path = file_path.relative_to(self.project_root)
            backup_file_path = backup_dir / relative_path
            
            # 确保备份目录存在
            backup_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 复制文件
            shutil.copy2(file_path, backup_file_path)
            print(f"💾 已备份: {relative_path} -> {backup_file_path.relative_to(backup_dir)}")
            return True
            
        except Exception as e:
            print(f"❌ 备份文件失败 {file_path}: {e}")
            return False
    
    async def migrate_module_whitelist(self, module: str, backup_dir: pathlib.Path = None) -> Dict[str, Any]:
        """
        迁移单个模块的白名单
        
        Args:
            module: 模块名称
            backup_dir: 备份目录
            
        Returns:
            Dict: 迁移结果
        """
        result = {
            'module': module,
            'success': False,
            'file_exists': False,
            'items_count': 0,
            'migrated_count': 0,
            'message': ''
        }
        
        try:
            # 检查模块是否支持
            if module not in self.module_file_mapping:
                result['message'] = f"不支持的模块: {module}"
                return result
            
            # 获取文件路径
            file_path = self.project_root / self.module_file_mapping[module]
            
            # 检查文件是否存在
            if not file_path.exists():
                result['message'] = f"白名单文件不存在: {file_path}"
                return result
            
            result['file_exists'] = True
            
            # 备份文件
            if backup_dir:
                backup_success = self.backup_file(file_path, backup_dir)
                if not backup_success:
                    result['message'] = "备份失败"
                    return result
            
            # 读取白名单文件
            whitelist_items = self.read_whitelist_file(file_path)
            result['items_count'] = len(whitelist_items)
            
            if not whitelist_items:
                result['success'] = True
                result['message'] = "文件为空，无需迁移"
                return result
            
            # 迁移到数据库
            migrate_result = await self.whitelist_db_tool.replace_whitelist(
                module,
                whitelist_items,
                f'文件迁移到数据库 - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
            )
            
            if migrate_result.get('success'):
                result['success'] = True
                result['migrated_count'] = migrate_result.get('added', 0)
                result['message'] = f"成功迁移 {result['migrated_count']} 个项目"
                
                # 创建迁移标记文件
                marker_file = file_path.with_suffix('.txt.migrated')
                with open(marker_file, 'w', encoding='utf-8') as f:
                    f.write(f"# 迁移标记文件\n")
                    f.write(f"# 原文件: {file_path.name}\n")
                    f.write(f"# 迁移时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"# 迁移项目数: {result['migrated_count']}\n")
                    f.write(f"# 目标模块: {module}\n")
                
                print(f"✅ {module} 模块迁移成功: {result['migrated_count']} 个项目")
            else:
                result['message'] = f"数据库操作失败: {migrate_result.get('message')}"
            
            return result
            
        except Exception as e:
            result['message'] = f"迁移过程出错: {str(e)}"
            print(f"❌ 迁移 {module} 模块时出错: {e}")
            return result
    
    async def migrate_all_modules(self, create_backup: bool = True) -> Dict[str, Any]:
        """
        迁移所有模块的白名单
        
        Args:
            create_backup: 是否创建备份
            
        Returns:
            Dict: 迁移总结果
        """
        print("🚀 开始批量迁移所有模块的白名单数据...")
        
        # 创建备份目录
        backup_dir = None
        if create_backup:
            backup_dir = self.create_backup_directory()
            if not backup_dir:
                return {
                    'success': False,
                    'message': '创建备份目录失败'
                }
        
        # 迁移结果汇总
        migration_summary = {
            'success': True,
            'total_modules': len(self.module_file_mapping),
            'processed_modules': 0,
            'successful_migrations': 0,
            'total_items': 0,
            'total_migrated': 0,
            'module_results': {},
            'backup_dir': str(backup_dir) if backup_dir else None,
            'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 逐个迁移模块
        for module in self.module_file_mapping.keys():
            print(f"\n📦 正在迁移模块: {module}")
            
            module_result = await self.migrate_module_whitelist(module, backup_dir)
            migration_summary['module_results'][module] = module_result
            migration_summary['processed_modules'] += 1
            
            if module_result['success']:
                migration_summary['successful_migrations'] += 1
                migration_summary['total_items'] += module_result['items_count']
                migration_summary['total_migrated'] += module_result['migrated_count']
            else:
                print(f"❌ {module} 迁移失败: {module_result['message']}")
        
        # 完成时间
        migration_summary['end_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 打印总结
        print(f"\n🎯 迁移完成总结:")
        print(f"   总模块数: {migration_summary['total_modules']}")
        print(f"   成功迁移: {migration_summary['successful_migrations']}")
        print(f"   总项目数: {migration_summary['total_items']}")
        print(f"   迁移项目: {migration_summary['total_migrated']}")
        
        if backup_dir:
            print(f"   备份目录: {backup_dir}")
        
        # 生成迁移报告
        if backup_dir:
            report_file = backup_dir / "migration_report.txt"
            await self.generate_migration_report(migration_summary, report_file)
        
        return migration_summary
    
    async def generate_migration_report(self, summary: Dict[str, Any], report_file: pathlib.Path):
        """
        生成迁移报告
        
        Args:
            summary: 迁移总结
            report_file: 报告文件路径
        """
        try:
            report_content = [
                "# 白名单数据迁移报告",
                f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "",
                "## 迁移总结",
                f"开始时间: {summary['start_time']}",
                f"结束时间: {summary['end_time']}",
                f"总模块数: {summary['total_modules']}",
                f"成功迁移: {summary['successful_migrations']}",
                f"总项目数: {summary['total_items']}",
                f"迁移项目: {summary['total_migrated']}",
                "",
                "## 模块详情"
            ]
            
            for module, result in summary['module_results'].items():
                report_content.extend([
                    f"",
                    f"### {module}",
                    f"状态: {'成功' if result['success'] else '失败'}",
                    f"文件存在: {'是' if result['file_exists'] else '否'}",
                    f"项目数量: {result['items_count']}",
                    f"迁移数量: {result['migrated_count']}",
                    f"消息: {result['message']}"
                ])
            
            # 写入报告
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(report_content))
            
            print(f"📊 迁移报告已生成: {report_file}")
            
        except Exception as e:
            print(f"❌ 生成迁移报告失败: {e}")
    
    async def verify_migration(self, module: str = None) -> Dict[str, Any]:
        """
        验证迁移完整性
        
        Args:
            module: 要验证的模块，None表示验证所有模块
            
        Returns:
            Dict: 验证结果
        """
        verification_results = {}
        
        modules_to_verify = [module] if module else list(self.module_file_mapping.keys())
        
        for mod in modules_to_verify:
            try:
                # 读取文件数据
                file_path = self.project_root / self.module_file_mapping[mod]
                file_items = self.read_whitelist_file(file_path) if file_path.exists() else []
                
                # 读取数据库数据
                db_items = await self.whitelist_db_tool.get_whitelist_names(mod)
                
                # 比较数据
                file_set = set(file_items)
                db_set = set(db_items)
                
                verification_results[mod] = {
                    'file_exists': file_path.exists(),
                    'file_count': len(file_items),
                    'db_count': len(db_items),
                    'matches': file_set == db_set,
                    'missing_in_db': list(file_set - db_set),
                    'extra_in_db': list(db_set - file_set)
                }
                
                status = "✅ 完全匹配" if verification_results[mod]['matches'] else "❌ 数据不匹配"
                print(f"{status} {mod}: 文件{len(file_items)}项 vs 数据库{len(db_items)}项")
                
            except Exception as e:
                verification_results[mod] = {
                    'error': str(e)
                }
                print(f"❌ 验证 {mod} 时出错: {e}")
        
        return verification_results
    
    async def rollback_migration(self, module: str, backup_dir: pathlib.Path) -> bool:
        """
        回滚迁移（从数据库删除数据，恢复文件）
        
        Args:
            module: 模块名称
            backup_dir: 备份目录
            
        Returns:
            bool: 回滚是否成功
        """
        try:
            print(f"🔄 开始回滚模块 {module}...")
            
            # 从数据库删除数据
            current_items = await self.whitelist_db_tool.get_whitelist_names(module)
            if current_items:
                result = await self.whitelist_db_tool.batch_remove_whitelist(module, current_items)
                if not result.get('success'):
                    print(f"❌ 从数据库删除数据失败: {result.get('message')}")
                    return False
            
            # 恢复备份文件
            backup_file_path = backup_dir / self.module_file_mapping[module]
            target_file_path = self.project_root / self.module_file_mapping[module]
            
            if backup_file_path.exists():
                # 确保目标目录存在
                target_file_path.parent.mkdir(parents=True, exist_ok=True)
                
                # 恢复文件
                shutil.copy2(backup_file_path, target_file_path)
                print(f"✅ 已恢复文件: {target_file_path}")
                
                # 删除迁移标记文件
                marker_file = target_file_path.with_suffix('.txt.migrated')
                if marker_file.exists():
                    marker_file.unlink()
                    print(f"🗑️ 已删除迁移标记文件: {marker_file}")
            
            print(f"✅ {module} 模块回滚成功")
            return True
            
        except Exception as e:
            print(f"❌ 回滚 {module} 模块失败: {e}")
            return False


async def main():
    """主函数"""
    migration_tool = WhitelistMigrationTool()
    
    try:
        # 初始化
        if not await migration_tool.initialize():
            return
        
        print("🎯 AutoOOIN 白名单数据迁移工具")
        print("=" * 50)
        
        # 执行迁移
        result = await migration_tool.migrate_all_modules(create_backup=True)
        
        if result['success']:
            print(f"\n🎉 迁移完成！")
            print(f"成功迁移 {result['successful_migrations']}/{result['total_modules']} 个模块")
            print(f"总计迁移 {result['total_migrated']} 个白名单项目")
            
            # 验证迁移
            print("\n🔍 验证迁移完整性...")
            verification = await migration_tool.verify_migration()
            
            all_match = all(v.get('matches', False) for v in verification.values() if 'error' not in v)
            if all_match:
                print("✅ 所有模块验证通过")
            else:
                print("⚠️ 部分模块验证失败，请检查迁移报告")
        else:
            print(f"\n❌ 迁移失败: {result.get('message')}")
    
    finally:
        await migration_tool.close()


if __name__ == "__main__":
    asyncio.run(main()) 