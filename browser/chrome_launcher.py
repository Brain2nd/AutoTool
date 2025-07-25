#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Chrome 启动器 - 简化版

只管理端口和存储文件夹，去除复杂配置
"""

import os
import sys
import time
import subprocess
import platform
import requests
import argparse
import signal
import psutil

# Windows兼容的Task配置 - 持久化数据目录
from pathlib import Path

def get_persistent_data_dir(task_name, port):
    """获取持久化的数据目录路径（Windows兼容）"""
    if platform.system() == 'Windows':
        # Windows：使用AppData/Local目录
        return str(Path.home() / 'AppData' / 'Local' / f'chrome-{task_name}')
    else:
        # macOS/Linux：使用用户主目录下的隐藏文件夹
        return str(Path.home() / '.AutoOOIN_Chrome_Data' / f'{task_name}-{port}')

TASK_CONFIGS = {
    'influencertool': {'port': 9223, 'data_dir': get_persistent_data_dir('influencertool', 9223)},
    'hr': {'port': 9224, 'data_dir': get_persistent_data_dir('hr', 9224)},
    'larkbusiness': {'port': 9222, 'data_dir': get_persistent_data_dir('larkbusiness', 9222)},
    'sca': {'port': 9225, 'data_dir': get_persistent_data_dir('sca', 9225)},
    'macwx': {'port': 9226, 'data_dir': get_persistent_data_dir('macwx', 9226)},
    'asyncbusiness': {'port': 9227, 'data_dir': get_persistent_data_dir('asyncbusiness', 9227)}
}

def find_chrome_path():
    """查找Chrome可执行文件路径"""
    system = platform.system()
    
    if system == "Darwin":  # macOS
        paths = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
    elif system == "Windows":
        paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        ]
    else:  # Linux
        paths = ["/usr/bin/google-chrome", "/usr/bin/chromium-browser"]
    
    for path in paths:
        if os.path.exists(path):
            return path
    return None

def is_chrome_running(port):
    """检查指定端口的Chrome是否运行"""
    try:
        response = requests.get(f"http://localhost:{port}/json/version", timeout=2)
        return response.status_code == 200
    except:
        return False

def launch_chrome(port, data_dir):
    """启动Chrome（Windows兼容版本）"""
    chrome_path = find_chrome_path()
    if not chrome_path:
        print("❌ 找不到Chrome")
        return False

    # 检查是否已运行
    if is_chrome_running(port):
        print(f"✅ 端口 {port} 的Chrome已运行")
        print(f"📁 数据目录: {data_dir}")
        return True

    # 创建数据目录（带权限检查）
    try:
        os.makedirs(data_dir, exist_ok=True)
        print(f"📁 使用数据目录: {data_dir}")
        
        # 检查数据目录是否可写
        test_file = os.path.join(data_dir, '.write_test')
        try:
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            print(f"✅ 数据目录可写入")
        except Exception as e:
            print(f"⚠️ 数据目录权限问题: {e}")
            
    except Exception as e:
        print(f"❌ 创建数据目录失败: {e}")
        return False

    # Windows兼容的启动命令
    cmd = [
        chrome_path,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={data_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-timer-throttling",  # 防止后台节流
        "--disable-renderer-backgrounding",       # 防止渲染器后台化
        "--disable-backgrounding-occluded-windows"  # 防止窗口遮挡时后台化
    ]

    try:
        # Windows兼容性处理
        if platform.system() == 'Windows':
            print("🪟 Windows系统检测 - 使用兼容模式启动")
            # Windows下使用CREATE_NEW_PROCESS_GROUP
            process = subprocess.Popen(
                cmd,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:
            print("🍎 macOS/Linux系统检测 - 使用标准模式启动")
            # 其他系统使用start_new_session
            process = subprocess.Popen(
                cmd, 
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        
        # 等待启动（Windows需要更长时间）
        max_retries = 15 if platform.system() == 'Windows' else 10
        print(f"⏳ 等待Chrome启动中（最多 {max_retries} 秒）...")
        
        for i in range(max_retries):
            if is_chrome_running(port):
                print(f"✅ Chrome启动成功！")
                print(f"🔗 调试端口: {port}")
                print(f"💾 数据保存位置: {data_dir}")
                print(f"🔄 重启后登录状态将保持")
                return True
            time.sleep(1)
            if i % 5 == 4:  # 每5秒显示一次进度
                print(f"⏳ 仍在等待... ({i+1}/{max_retries})")
        
        print(f"❌ Chrome启动超时，端口: {port}")
        return False
    except Exception as e:
        print(f"❌ 启动Chrome出错: {e}")
        return False

def launch_task(task_name):
    """启动指定task的Chrome"""
    if task_name not in TASK_CONFIGS:
        print(f"❌ 未找到task: {task_name}")
        print(f"可用task: {list(TASK_CONFIGS.keys())}")
        return False
    
    config = TASK_CONFIGS[task_name]
    print(f"🚀 启动 {task_name} - 端口: {config['port']}")
    
    return launch_chrome(config['port'], config['data_dir'])

def show_status():
    """显示所有实例状态（包含数据目录信息）"""
    print("📊 Chrome实例状态及数据持久化信息")
    print("=" * 80)
    
    all_running = True
    for task, config in TASK_CONFIGS.items():
        port = config['port']
        data_dir = config['data_dir']
        status = "🟢 运行中" if is_chrome_running(port) else "🔴 未运行"
        
        # 检查数据目录状态
        if os.path.exists(data_dir):
            # 计算数据目录大小
            try:
                dir_size = sum(os.path.getsize(os.path.join(dirpath, filename))
                              for dirpath, dirnames, filenames in os.walk(data_dir)
                              for filename in filenames)
                size_mb = dir_size / (1024 * 1024)
                dir_status = f"📁 存在 ({size_mb:.1f}MB)"
            except:
                dir_status = "📁 存在"
        else:
            dir_status = "📂 未创建"
        
        print(f"{task:15} | 端口: {port:4} | {status:8} | {dir_status}")
        print(f"{'':15} | 数据: {data_dir}")
        print("-" * 80)
        
        if not is_chrome_running(port):
            all_running = False
    
    print("=" * 80)
    if all_running:
        print("✅ 所有Chrome实例都在运行")
    else:
        print("⚠️ 部分Chrome实例未运行")
    
    print("\n💡 数据持久化说明:")
    if platform.system() == 'Windows':
        print("🪟 Windows系统：数据保存在 C:/Users/{用户名}/AppData/Local/chrome-{任务名}/")
    else:
        print("🍎 macOS/Linux系统：数据保存在 ~/.AutoOOIN_Chrome_Data/{任务名}-{端口}/")
    print("🔄 重启系统后，您的登录状态、书签、设置都会保留")
    print("🗑️ 如需清除数据，可手动删除对应的数据目录")

def kill_chrome_processes_by_port(port):
    """根据端口号关闭Chrome进程"""
    killed_count = 0
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] and 'chrome' in proc.info['name'].lower():
                    cmdline = proc.info['cmdline']
                    if cmdline and any(f'--remote-debugging-port={port}' in arg for arg in cmdline):
                        print(f"🛑 关闭Chrome进程 PID:{proc.info['pid']} (端口:{port})")
                        proc.kill()
                        killed_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception as e:
        print(f"⚠️ 查找Chrome进程时出错: {e}")
    
    if killed_count > 0:
        time.sleep(2)  # 等待进程完全终止
        print(f"✅ 已关闭 {killed_count} 个Chrome进程")
        return True
    else:
        print(f"ℹ️ 未找到端口 {port} 的Chrome进程")
        return False

def kill_all_chrome_processes():
    """关闭所有Chrome进程"""
    killed_count = 0
    try:
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] and 'chrome' in proc.info['name'].lower():
                    print(f"🛑 关闭Chrome进程 PID:{proc.info['pid']}")
                    proc.kill()
                    killed_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception as e:
        print(f"⚠️ 查找Chrome进程时出错: {e}")
    
    if killed_count > 0:
        time.sleep(3)  # 等待进程完全终止
        print(f"✅ 已关闭 {killed_count} 个Chrome进程")
        return True
    else:
        print("ℹ️ 未找到Chrome进程")
        return False

# =============================================================================
# creator_data_integrator.py 需要的函数接口
# =============================================================================

def setup_and_launch_chrome(debug_port=9223, temp_dir=None, copy_profile=True):
    """
    设置并启动Chrome（creator_data_integrator.py需要的接口）
    
    Args:
        debug_port (int): Chrome调试端口
        temp_dir (str): 临时目录（可选）
        copy_profile (bool): 是否复制配置文件（可选）
    
    Returns:
        bool: 启动成功返回True，失败返回False
    """
    print(f"🚀 设置并启动Chrome (端口: {debug_port})")
    
    # 确定数据目录
    if temp_dir:
        data_dir = temp_dir
    else:
        data_dir = f'/tmp/chrome-{debug_port}'
    
    print(f"📁 使用数据目录: {data_dir}")
    
    # 启动Chrome
    return launch_chrome(debug_port, data_dir)

def kill_all_chrome_instances():
    """
    关闭所有Chrome实例（creator_data_integrator.py需要的接口）
    
    Returns:
        bool: 操作成功返回True
    """
    print("🛑 关闭所有Chrome实例...")
    return kill_all_chrome_processes()

def kill_chrome_instance_by_port(port):
    """
    根据端口关闭特定Chrome实例（creator_data_integrator.py需要的接口）
    
    Args:
        port (int): 要关闭的Chrome实例端口
    
    Returns:
        bool: 操作成功返回True
    """
    print(f"🛑 关闭端口 {port} 的Chrome实例...")
    return kill_chrome_processes_by_port(port)

def main():
    parser = argparse.ArgumentParser(description='Chrome启动器 - 简化版')
    parser.add_argument('--task', help='启动指定task')
    parser.add_argument('--port', type=int, default=9222, help='端口 (默认模式)')
    parser.add_argument('--dir', help='数据目录 (默认模式)')
    parser.add_argument('--status', action='store_true', help='显示状态')
    
    args = parser.parse_args()
    
    if args.status:
        show_status()
        return
    
    if args.task:
        success = launch_task(args.task)
        return 0 if success else 1
    
    # 默认模式
    data_dir = args.dir or f'/tmp/chrome-{args.port}'
    success = launch_chrome(args.port, data_dir)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 