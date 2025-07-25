#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
白名单日志查看器

功能：
- 查看最近的白名单操作日志
- 按操作类型过滤日志
- 按时间范围查看日志
- 统计操作成功率
"""

import sys
import re
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any

# 添加项目根目录到路径
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

from ..db.whitelist_logger import whitelist_logger

class WhitelistLogViewer:
    """白名单日志查看器"""
    
    def __init__(self):
        self.logger = whitelist_logger
        self.log_file = Path(self.logger.get_log_file_path())
    
    def get_logs(self, lines: int = 100) -> List[str]:
        """获取日志行"""
        if not self.log_file.exists():
            print(f"❌ 日志文件不存在: {self.log_file}")
            return []
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                return all_lines[-lines:] if len(all_lines) > lines else all_lines
        except Exception as e:
            print(f"❌ 读取日志文件失败: {e}")
            return []
    
    def parse_log_line(self, line: str) -> Dict[str, Any]:
        """解析日志行"""
        # 日志格式: 2025-07-14 14:52:48 |     INFO | 消息内容
        pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \|\s*(\w+)\s*\| (.+)'
        match = re.match(pattern, line.strip())
        
        if match:
            timestamp_str, level, message = match.groups()
            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            
            # 提取操作类型
            operation_type = "unknown"
            if "🚀 开始操作:" in message:
                operation_type = "operation_start"
            elif "✅ 操作成功:" in message:
                operation_type = "operation_success"
            elif "❌ 操作失败:" in message:
                operation_type = "operation_failure"
            elif "🔗 数据库连接尝试" in message:
                operation_type = "database_connect"
            elif "📋 开始加载白名单" in message:
                operation_type = "whitelist_load"
            elif "💾 开始保存白名单" in message:
                operation_type = "whitelist_save"
            elif "🔄 开始同步白名单" in message:
                operation_type = "whitelist_sync"
            elif "🌐 Web请求开始" in message:
                operation_type = "web_request"
            elif "🔍 数据验证:" in message:
                operation_type = "data_verification"
            
            return {
                'timestamp': timestamp,
                'level': level,
                'message': message,
                'operation_type': operation_type,
                'raw_line': line.strip()
            }
        
        return {
            'timestamp': None,
            'level': 'UNKNOWN',
            'message': line.strip(),
            'operation_type': 'unknown',
            'raw_line': line.strip()
        }
    
    def filter_logs(self, logs: List[str], 
                   operation_type: str = None,
                   level: str = None,
                   hours: int = None) -> List[Dict[str, Any]]:
        """过滤日志"""
        parsed_logs = [self.parse_log_line(line) for line in logs]
        filtered_logs = []
        
        # 时间过滤
        if hours:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            parsed_logs = [log for log in parsed_logs 
                          if log['timestamp'] and log['timestamp'] >= cutoff_time]
        
        # 操作类型过滤
        if operation_type:
            parsed_logs = [log for log in parsed_logs 
                          if operation_type in log['operation_type']]
        
        # 级别过滤
        if level:
            parsed_logs = [log for log in parsed_logs 
                          if log['level'].upper() == level.upper()]
        
        return parsed_logs
    
    def show_recent_logs(self, lines: int = 50):
        """显示最近的日志"""
        print(f"📋 最近 {lines} 行白名单操作日志:")
        print("=" * 80)
        
        logs = self.get_logs(lines)
        if not logs:
            print("❌ 没有找到日志记录")
            return
        
        for i, line in enumerate(logs, 1):
            parsed = self.parse_log_line(line)
            
            # 添加颜色标识
            level_color = {
                'INFO': '🔵',
                'WARNING': '🟡', 
                'ERROR': '🔴',
                'DEBUG': '⚪'
            }.get(parsed['level'], '⚫')
            
            operation_emoji = {
                'operation_start': '🚀',
                'operation_success': '✅',
                'operation_failure': '❌',
                'database_connect': '🔗',
                'whitelist_load': '📋',
                'whitelist_save': '💾',
                'whitelist_sync': '🔄',
                'web_request': '🌐',
                'data_verification': '🔍'
            }.get(parsed['operation_type'], '📝')
            
            print(f"{i:3d}. {level_color} {operation_emoji} {parsed['raw_line']}")
    
    def show_operation_summary(self, hours: int = 24):
        """显示操作统计摘要"""
        print(f"📊 最近 {hours} 小时白名单操作统计:")
        print("=" * 60)
        
        logs = self.get_logs(1000)  # 获取更多日志用于统计
        filtered_logs = self.filter_logs(logs, hours=hours)
        
        if not filtered_logs:
            print("❌ 没有找到指定时间范围内的日志记录")
            return
        
        # 统计各种操作
        stats = {
            'total': len(filtered_logs),
            'by_level': {},
            'by_operation': {},
            'success_rate': {}
        }
        
        success_count = 0
        failure_count = 0
        
        for log in filtered_logs:
            # 按级别统计
            level = log['level']
            stats['by_level'][level] = stats['by_level'].get(level, 0) + 1
            
            # 按操作类型统计
            op_type = log['operation_type']
            stats['by_operation'][op_type] = stats['by_operation'].get(op_type, 0) + 1
            
            # 成功率统计
            if '✅' in log['message'] or 'success' in log['message'].lower():
                success_count += 1
            elif '❌' in log['message'] or 'failure' in log['message'].lower():
                failure_count += 1
        
        # 显示统计结果
        print(f"📈 总操作数: {stats['total']}")
        print(f"✅ 成功操作: {success_count}")
        print(f"❌ 失败操作: {failure_count}")
        if success_count + failure_count > 0:
            success_rate = success_count / (success_count + failure_count) * 100
            print(f"📊 成功率: {success_rate:.1f}%")
        
        print(f"\n📋 按级别统计:")
        for level, count in sorted(stats['by_level'].items()):
            emoji = {'INFO': '🔵', 'WARNING': '🟡', 'ERROR': '🔴', 'DEBUG': '⚪'}.get(level, '⚫')
            print(f"   {emoji} {level}: {count}")
        
        print(f"\n🔧 按操作类型统计:")
        for op_type, count in sorted(stats['by_operation'].items()):
            emoji = {
                'operation_start': '🚀', 'operation_success': '✅', 'operation_failure': '❌',
                'database_connect': '🔗', 'whitelist_load': '📋', 'whitelist_save': '💾',
                'whitelist_sync': '🔄', 'web_request': '🌐', 'data_verification': '🔍'
            }.get(op_type, '📝')
            print(f"   {emoji} {op_type}: {count}")
    
    def show_errors_only(self, hours: int = 24):
        """只显示错误日志"""
        print(f"🔴 最近 {hours} 小时的错误日志:")
        print("=" * 60)
        
        logs = self.get_logs(1000)
        error_logs = self.filter_logs(logs, level='ERROR', hours=hours)
        
        if not error_logs:
            print("✅ 没有发现错误日志！")
            return
        
        for i, log in enumerate(error_logs, 1):
            print(f"{i:3d}. {log['timestamp'].strftime('%H:%M:%S')} | {log['message']}")
    
    def show_database_operations(self, hours: int = 24):
        """显示数据库相关操作"""
        print(f"🔗 最近 {hours} 小时的数据库操作:")
        print("=" * 60)
        
        logs = self.get_logs(1000)
        db_logs = self.filter_logs(logs, operation_type='database', hours=hours)
        
        if not db_logs:
            print("❌ 没有找到数据库操作日志")
            return
        
        for i, log in enumerate(db_logs, 1):
            print(f"{i:3d}. {log['timestamp'].strftime('%H:%M:%S')} | {log['message']}")
    
    def show_web_requests(self, hours: int = 24):
        """显示Web请求"""
        print(f"🌐 最近 {hours} 小时的Web请求:")
        print("=" * 60)
        
        logs = self.get_logs(1000)
        web_logs = self.filter_logs(logs, operation_type='web', hours=hours)
        
        if not web_logs:
            print("❌ 没有找到Web请求日志")
            return
        
        for i, log in enumerate(web_logs, 1):
            print(f"{i:3d}. {log['timestamp'].strftime('%H:%M:%S')} | {log['message']}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='白名单日志查看器')
    parser.add_argument('--lines', '-l', type=int, default=50, help='显示的日志行数 (默认: 50)')
    parser.add_argument('--hours', '-t', type=int, help='时间范围(小时)')
    parser.add_argument('--summary', '-s', action='store_true', help='显示操作统计摘要')
    parser.add_argument('--errors', '-e', action='store_true', help='只显示错误日志')
    parser.add_argument('--database', '-d', action='store_true', help='显示数据库操作')
    parser.add_argument('--web', '-w', action='store_true', help='显示Web请求')
    
    args = parser.parse_args()
    
    viewer = WhitelistLogViewer()
    
    print("🔍 AutoOOIN 白名单日志查看器")
    print(f"📁 日志文件: {viewer.log_file}")
    print("=" * 80)
    
    if args.summary:
        viewer.show_operation_summary(args.hours or 24)
    elif args.errors:
        viewer.show_errors_only(args.hours or 24)
    elif args.database:
        viewer.show_database_operations(args.hours or 24)
    elif args.web:
        viewer.show_web_requests(args.hours or 24)
    else:
        viewer.show_recent_logs(args.lines)
    
    print("\n💡 使用提示:")
    print("   python tool/db/view_whitelist_logs.py --summary    # 查看统计摘要")
    print("   python tool/db/view_whitelist_logs.py --errors     # 查看错误日志")
    print("   python tool/db/view_whitelist_logs.py --database   # 查看数据库操作")
    print("   python tool/db/view_whitelist_logs.py --web        # 查看Web请求")
    print("   python tool/db/view_whitelist_logs.py -l 100       # 查看最近100行日志")
    print("   python tool/db/view_whitelist_logs.py -t 1         # 查看最近1小时日志")

if __name__ == "__main__":
    main() 