#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
飞书自动登录模块

使用 BrowserTool 自动完成飞书登录流程
"""

import time
import asyncio
from urllib.parse import urlparse, parse_qs
from typing import Optional
import sys
import os

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ..browser import BrowserTool


def auto_get_login_url(login_url: str, browser_tool: Optional[BrowserTool] = None, preferred_port: Optional[int] = None) -> Optional[str]:
    """
    自动完成飞书登录并获取跳转后的URL
    
    Args:
        login_url: 飞书登录URL
        browser_tool: BrowserTool实例，如果为None则创建新实例
        preferred_port: 优先使用的Chrome调试端口，如果为None则使用智能检测
        
    Returns:
        跳转后的完整URL，失败返回None
    """
    # 如果没有提供 browser_tool，创建一个新的
    if browser_tool is None:
        browser_tool = BrowserTool()
    
    page_index = None
    try:
        # 连接到浏览器
        if not browser_tool.is_connected():
            print("正在连接到浏览器...")
            # 传递preferred_port参数给connect_to_browser方法
            connect_result = browser_tool.connect_to_browser(preferred_port=preferred_port)
            if not connect_result['success']:
                print(f"连接浏览器失败: {connect_result['message']}")
                return None
        
        # 创建新标签页并导航到登录URL（在后台打开）
        print(f"正在后台打开登录页面: {login_url}")
        tab_result = browser_tool.create_new_tab_background(login_url)
        if not tab_result['success']:
            print(f"创建新标签页失败: {tab_result['message']}")
            return None
        
        page_index = tab_result['page_index']
        print(f"已创建新标签页，索引: {page_index}")
        
        # 等待页面加载
        time.sleep(3)
        
        # 定义点击登录按钮的异步操作
        async def click_login_button(page):
            """点击登录按钮的异步函数"""
            # 第一个按钮的选择器
            first_button_selector = '.ud__button.ud__button--outlined.ud__button--outlined-primary.ud__button--size-sm.access-btn'
            # 第二个按钮的选择器
            second_button_selector = '.ud__button.ud__button--filled.ud__button--filled-default.ud__button--size-md'
            
            try:
                # 尝试查找并点击第一个按钮
                print(f"正在查找第一个按钮: {first_button_selector}")
                try:
                    await page.wait_for_selector(first_button_selector, timeout=3000)
                    await page.click(first_button_selector)
                    print("已点击第一个按钮")
                    
                    # 等待一下，让页面响应
                    await asyncio.sleep(1)
                except Exception as e:
                    print(f"未找到第一个按钮或点击失败: {str(e)}")
                    print("将直接尝试点击第二个按钮")
                
                # 查找并点击第二个按钮
                print(f"正在查找第二个按钮: {second_button_selector}")
                await page.wait_for_selector(second_button_selector, timeout=5000)
                await page.click(second_button_selector)
                print("已点击第二个按钮")
                
            except Exception as e:
                print(f"点击按钮时出错: {str(e)}")
                raise
        
        # 使用导航监听功能
        print("开始监听导航事件...")
        nav_result = browser_tool.get_navigation_target_url(
            page_index=page_index,
            action_callback=click_login_button,
            timeout=10000
        )
        
        if nav_result['success']:
            target_url = nav_result.get('target_url')
            final_url = nav_result.get('final_url')
            
            print(f"\n导航监听结果:")
            print(f"  目标URL: {target_url}")
            print(f"  最终URL: {final_url}")
            
            # 优先返回目标URL（包含code的URL）
            if target_url and ("tangshi" in target_url or "lark" in target_url):
                print(f"\n成功获取到目标URL: {target_url}")
                return target_url
            elif final_url and ("tangshi" in final_url or "lark" in final_url) and "chrome-error://" not in final_url:
                print(f"\n使用最终URL: {final_url}")
                return final_url
            else:
                print("\n未找到有效的飞书URL")
                return None
        else:
            print(f"\n导航监听失败: {nav_result.get('message', 'Unknown error')}")
            return None
        
    except Exception as e:
        print(f"自动登录过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        # 清理：关闭打开的标签页
        if page_index is not None and browser_tool.is_connected():
            try:
                print("\n正在关闭登录标签页...")
                # 获取当前所有页面
                pages_info = browser_tool.get_connection_info()
                pages_count = pages_info.get('pages_count', 0)
                
                # 如果有多个标签页，关闭我们创建的那个
                if pages_count > 1:
                    # 使用 Playwright 的 API 关闭页面
                    if browser_tool.context and page_index < len(browser_tool.context.pages):
                        page_to_close = browser_tool.context.pages[page_index]
                        # 创建一个异步函数来关闭页面
                        async def close_page():
                            await page_to_close.close()
                        
                        # 执行关闭操作
                        if browser_tool._async_loop:
                            browser_tool._async_loop.run_until_complete(close_page())
                            print("已关闭登录标签页")
                else:
                    print("只有一个标签页，不关闭以免关闭整个浏览器")
            except Exception as e:
                print(f"关闭标签页时出错: {str(e)}")
        
        # 断开 BrowserTool 连接，释放资源
        if browser_tool and browser_tool.is_connected():
            try:
                print("正在断开浏览器连接...")
                browser_tool.disconnect()
                print("已断开浏览器连接")
            except Exception as e:
                print(f"断开浏览器连接时出错: {str(e)}")


def GET_LOGIN_CODE_AUTO(redirect_uri=None, app_id=None, config_file=None, preferred_port=None):
    """
    自动获取登录代码的替代函数
    
    与原始 GET_LOGIN_CODE 函数签名相同，但使用自动化方式获取代码
    
    Args:
        redirect_uri: 重定向URI
        app_id: 应用ID
        config_file: 配置文件路径
        preferred_port: 优先使用的Chrome调试端口
    """
    import configparser
    import os
    import inspect
    
    # 如果配置文件路径为空，则使用默认路径
    if not config_file:
        config_file = 'feishu-config.ini'

    config = configparser.ConfigParser()
    config.read(config_file, encoding='utf-8')

    # 获取重定向URL
    if not redirect_uri:
        redirect_uri = config.get('LOGIN_CODE', 'redirect_uri', fallback='http://127.0.0.1/')

    # 获取app_id
    if not app_id:
        app_id = config.get('ID', 'app_id', fallback='cli_a40141935331100e')

    login_url = f"https://open.feishu.cn/open-apis/authen/v1/index?redirect_uri={redirect_uri}&app_id={app_id}&state=some_random_string"
    print(f"自动登录URL: {login_url}")
    
    # 如果没有指定端口，根据调用栈自动检测
    if preferred_port is None:
        try:
            current_dir = os.getcwd()
            
            # 检查调用栈中的脚本路径
            calling_script = ""
            for frame_info in inspect.stack():
                filename = frame_info.filename
                if any(task in filename for task in ['influencertool', 'hr', 'larkbusiness', 'sca', 'macwx', 'asyncbusiness']):
                    calling_script = filename
                    break
            
            print(f"🔍 自动登录端口检测 - 调用脚本: {calling_script}")
            print(f"🔍 自动登录端口检测 - 当前目录: {current_dir}")
            
            # 根据调用脚本路径和当前目录确定端口
            if 'influencertool' in calling_script or 'influencertool' in current_dir:
                preferred_port = 9223  # influencertool端口
                print(f"🎯 检测到influencertool任务，使用端口: {preferred_port}")
            elif 'hr' in calling_script or 'hr' in current_dir:
                preferred_port = 9224  # hr端口
                print(f"🎯 检测到hr任务，使用端口: {preferred_port}")
            elif 'larkbusiness' in calling_script or 'larkbusiness' in current_dir:
                preferred_port = 9222  # larkbusiness端口
                print(f"🎯 检测到larkbusiness任务，使用端口: {preferred_port}")
            elif 'sca' in calling_script or 'sca' in current_dir:
                preferred_port = 9225  # sca端口
                print(f"🎯 检测到sca任务，使用端口: {preferred_port}")
            elif 'macwx' in calling_script or 'macwx' in current_dir:
                preferred_port = 9226  # macwx端口
                print(f"🎯 检测到macwx任务，使用端口: {preferred_port}")
            elif 'asyncbusiness' in calling_script or 'asyncbusiness' in current_dir:
                preferred_port = 9227  # asyncbusiness端口
                print(f"🎯 检测到asyncbusiness任务，使用端口: {preferred_port}")
            else:
                preferred_port = 9222  # 默认端口
                print(f"🎯 未检测到特定任务，使用默认端口: {preferred_port}")
                
        except Exception as e:
            print(f"⚠️ 端口自动检测失败: {e}，使用默认端口9222")
            preferred_port = 9222
    
    # 使用自动化方式获取跳转后的URL，传递端口参数
    new_url = auto_get_login_url(login_url, preferred_port=preferred_port)
    
    if new_url:
        print(f"获取到跳转后的URL: {new_url}")
        # 解析URL获取code
        parsed_url = urlparse(new_url)
        parsed_query = parse_qs(parsed_url.query)
        code = parsed_query.get("code")
        if code:
            return code[0]
        else:
            print("URL中未找到code参数")
            return None
    else:
        # 如果自动化失败，不再回退到手动方式，直接返回None
        print("自动登录失败，跳过本次登录操作")
        print(f"如需手动登录，请访问以下 URL：\n{login_url}")
        print("[提示] 程序将继续运行，跳过需要登录的操作")
        return None 