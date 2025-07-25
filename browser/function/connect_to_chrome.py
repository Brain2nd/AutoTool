import pathlib
import sys


current_dir = pathlib.Path(__file__).parent
project_root = current_dir.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

# 创建浏览器工具实例
from ..browsertool import BrowserTool

def connect_to_chrome(preferred_port=None):
    """连接到已打开的Chrome浏览器
    
    Args:
        preferred_port (int, optional): 优先使用的端口号。如果指定，将优先尝试连接此端口
        
    Returns:
        BrowserTool实例或None
    """
    print("==== 连接Chrome浏览器示例 ====")
    print("\n提示: 请确保已使用调试模式启动Chrome:")
    print("  Windows: start chrome --remote-debugging-port=[端口]")
    print("  Mac:     open -a \"Google Chrome\" --args --remote-debugging-port=[端口]")
    print("  Linux:   google-chrome --remote-debugging-port=[端口]")
    print("\n常用端口: 9222(larkbusiness), 9223(influencertool), 9224(hr), 9225(sca)")
    
    if preferred_port:
        print(f"🎯 任务指定优先端口: {preferred_port}")
        endpoint_url = f"http://localhost:{preferred_port}"
    else:
        print("工具会自动尝试检测可用端口")
        endpoint_url = None
    
    print()

    browser_tool = BrowserTool()
    
    # 尝试连接到浏览器
    print("正在尝试连接到Chrome浏览器...")
    if preferred_port:
        # 如果指定了端口，直接尝试连接该端口
        result = browser_tool.connect_to_browser(endpoint_url=endpoint_url, preferred_port=preferred_port)
    else:
        # 如果没有指定端口，使用自动检测
        result = browser_tool.connect_to_browser()
    
    if not result['success']:
        print(f"连接失败: {result['message']}")
        
        # 如果指定了端口，尝试自动启动Chrome实例
        if preferred_port:
            print(f"🚀 尝试自动启动端口 {preferred_port} 的Chrome实例...")
            
            try:
                # 导入Chrome启动器
                from ..chrome_launcher import setup_and_launch_chrome
                
                # 启动Chrome实例
                launch_success = setup_and_launch_chrome(
                    debug_port=preferred_port,
                    temp_dir=None,  # 使用默认临时目录
                    copy_profile=True  # 复制默认配置文件
                )
                
                if launch_success:
                    print(f"✅ Chrome实例启动成功！尝试重新连接...")
                    
                    # 等待Chrome完全启动
                    import time
                    time.sleep(3)
                    
                    # 重新尝试连接
                    result = browser_tool.connect_to_browser(endpoint_url=endpoint_url, preferred_port=preferred_port)
                    
                    if result['success']:
                        print("🎉 重新连接成功！")
                    else:
                        print(f"❌ 重新连接失败: {result['message']}")
                        return None
                else:
                    print(f"❌ Chrome实例启动失败")
                    return None
                    
            except ImportError as e:
                print(f"❌ 无法导入Chrome启动器: {e}")
                print("💡 请手动启动Chrome或检查Chrome启动器模块")
                return None
            except Exception as e:
                print(f"❌ 启动Chrome时发生异常: {e}")
                return None
        else:
            print("💡 提示：请手动启动Chrome调试模式或指定端口参数")
            return None
    
    print("连接成功!")
    print(f"当前页面: {result['current_page_title']} ({result['current_page_url']})")
    
    # 显示所有页面
    print("\n已打开的页面:")
    for page in result['pages']:
        print(f"  [{page['index']}] {page['title']} ({page['url']})")
    
    # 获取连接信息
    print("\n连接信息:")
    connection_info = browser_tool.get_connection_info()
    for key, value in connection_info.items():
        print(f"  {key}: {value}")
    
    return browser_tool