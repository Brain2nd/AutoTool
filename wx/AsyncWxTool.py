#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
微信发送文件测试 - 异步版本：使用asyncio和wxautox库实现将"Simone-OOIN建联商务群"加入监听并发送文件的功能
"""

import os
import sys
import asyncio
import time
import ctypes
import platform
import atexit
import weakref
import signal
import logging  # 添加日志模块
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
from collections import deque


# 导入wxautox库和ThreadPoolExecutor
from wxautox import WeChat
from concurrent.futures import ThreadPoolExecutor

# COM初始化常量
COINIT_APARTMENTTHREADED = 0x2
COINIT_MULTITHREADED = 0x0
COINIT_DISABLE_OLE1DDE = 0x4
COINIT_SPEED_OVER_MEMORY = 0x8

# 装饰器定义
def main_window_op(func):
    """标记为主窗口操作函数的装饰器"""
    func._window_type = "main"
    
    async def wrapper(self, *args, **kwargs):
        # 定义内部操作函数
        async def _operation():
            return await func(self, *args, **kwargs)
        # 通过队列执行操作
        return await self.add_to_main_window_queue(_operation())
    
    # 保持原函数的元数据
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper

def chat_window_op(func):
    """标记为子窗口操作函数的装饰器"""
    func._window_type = "chat"
    
    async def wrapper(self, chat, *args, **kwargs):
        # 获取子窗口锁
        chat_name = getattr(chat, 'who', 'unknown')
        if chat_name not in self.chat_window_locks:
            # 如果没有为这个窗口创建锁，创建一个
            self.chat_window_locks[chat_name] = asyncio.Lock()
            print(f"临时为子窗口 '{chat_name}' 创建了互斥锁")
        
        chat_lock = self.chat_window_locks[chat_name]
        
        # 在锁的保护下执行操作
        async with chat_lock:
            return await func(self, chat, *args, **kwargs)
    
    # 保持原函数的元数据
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper

def utility_op(func):
    """标记为工具函数的装饰器"""
    func._window_type = "utility"
    return func

def setup_op(func):
    """标记为环境设置函数的装饰器"""
    func._window_type = "setup"
    return func

# 全局跟踪所有工具实例，用于程序退出时清理
_all_wx_tools = weakref.WeakSet()

# 定义系统退出处理函数
def _cleanup_all_wx_tools():
    """程序退出时调用，确保所有微信工具实例都被清理"""
    if _all_wx_tools:
        print(f"程序退出，清理 {len(_all_wx_tools)} 个微信工具实例...")
        for tool in list(_all_wx_tools):
            try:
                if tool.wx and hasattr(tool.wx, 'listen') and not tool.has_shutdown:
                    print(f"强制清理 {id(tool)} 的微信资源...")
                    # 同步清理所有监听
                    listen_chats = list(tool.wx.listen.keys())
                    for chat_name in listen_chats:
                        try:
                            print(f"强制移除监听: {chat_name}")
                            # 尝试移除并验证结果
                            before_count = len(tool.wx.listen) if hasattr(tool.wx, 'listen') else 0
                            tool.wx.RemoveListenChat(chat_name)
                            # 检查是否还存在
                            after_count = len(tool.wx.listen) if hasattr(tool.wx, 'listen') else 0
                            still_exists = chat_name in tool.wx.listen if hasattr(tool.wx, 'listen') else False
                            
                            if not still_exists or before_count > after_count:
                                print(f"退出时成功移除监听: {chat_name}")
                            else:
                                print(f"退出时无法确认监听 {chat_name} 是否已移除")
                            
                            # 避免频繁操作导致的问题
                            time.sleep(0.5)
                        except Exception as e:
                            print(f"退出时移除监听 '{chat_name}' 出错: {e}")
                    
                    # 标记为已清理
                    tool.has_shutdown = True
            except Exception as e:
                print(f"退出清理时出错: {e}")

# 注册程序退出清理函数
atexit.register(_cleanup_all_wx_tools)

# 注册信号处理器（Linux和macOS）
if platform.system() != 'Windows':
    def signal_handler(sig, frame):
        print(f"接收到信号 {sig}，开始清理资源...")
        _cleanup_all_wx_tools()
        sys.exit(0)
    
    # 注册SIGINT和SIGTERM信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

class AsyncWxTool:
    """
    异步微信工具类
    提供基本的微信操作功能，每个函数单一职责
    包含主窗口和子窗口操作
    
    特性:
    - 支持异步并发操作
    - 主窗口操作队列保证串行执行
    - 子窗口操作支持并行处理，但同一窗口内串行
    - 支持三层自动资源释放保障：
      1. 使用with语句时自动释放
      2. 对象被销毁时尝试自动释放
      3. 程序退出时强制清理所有未释放的资源
    
    使用示例:
    ```python
    # 方式1: 使用with语句，确保资源自动释放
    async def example1():
        async with AsyncWxTool() as wx_tool:
            await wx_tool.setup()
            # 执行微信操作
            # ...
        # 退出with块时自动释放资源
    
    # 方式2: 手动管理资源
    async def example2():
        wx_tool = AsyncWxTool()
        try:
            await wx_tool.setup()
            # 执行微信操作
            # ...
        finally:
            # 手动释放资源
            await wx_tool.terminate_gracefully()
    ```
    """
    
    def __init__(self, exit_hook: bool = True):
        """初始化异步微信工具类
        
        Args:
            exit_hook: 是否启用程序退出时的自动清理钩子，默认为True
                      在特殊情况下可能需要禁用此功能，例如在多进程环境中
        """
        print("正在初始化微信工具环境...")
        
        # 初始化COM环境（主线程）
        self.init_com_for_thread()
        
        # 微信实例和线程池
        self.wx = None
        self.executor = None
        self.loop = None
        
        # 互斥锁：确保微信主窗口操作安全
        self.main_window_lock = None
        
        # 子窗口锁字典：针对每个子窗口的互斥锁
        self.chat_window_locks = {}
        
        # 主窗口操作队列
        self.main_window_queue = deque()
        self.main_window_queue_processing = False
        
        # 已释放标志
        self.has_shutdown = False
        
        # 添加到全局工具集合
        if exit_hook:
            _all_wx_tools.add(self)
        
    def __del__(self):
        """析构函数: 当对象被销毁时自动调用，确保释放所有监听"""
        if not self.has_shutdown and self.wx is not None:
            try:
                print(f"对象 {id(self)} 被销毁，尝试自动清理微信资源...")
                # 尝试同步清理方式，因为对象被销毁时事件循环可能已不可用
                self.sync_cleanup()
            except Exception as e:
                print(f"对象销毁时清理资源出错: {e}")
                print("提示: 资源未被完全清理，将在程序退出时强制清理")
        
    # 异步上下文管理器协议支持
    async def __aenter__(self):
        """异步上下文管理器入口方法"""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出方法，自动释放资源"""
        await self.cleanup()
        return False  # 不抑制异常传播
    
    @setup_op
    def init_com_for_thread(self):
        """初始化当前线程的COM环境"""
        if platform.system() == 'Windows':
            try:
                # 使用STA模式初始化COM
                ctypes.windll.ole32.CoInitializeEx(None, COINIT_APARTMENTTHREADED)
                print("[COM] 已初始化线程COM环境")
                return True
            except Exception as e:
                print(f"[错误] COM初始化失败: {e}")
                return False
        return True
    
    @setup_op
    def create_wx_instance(self):
        """在当前线程中创建WeChat实例并初始化COM"""
        # 确保COM环境初始化
        self.init_com_for_thread()
        # 创建WeChat实例
        return WeChat()
    
    @setup_op
    async def setup(self):
        """初始化微信环境"""
        # 创建线程池执行器和获取事件循环
        self.executor = ThreadPoolExecutor(max_workers=5)
        self.loop = asyncio.get_event_loop()
        
        # 创建互斥锁
        self.main_window_lock = asyncio.Lock()
        
        # 初始化WeChat实例（在线程池中执行）
        print("连接微信...")
        self.wx = await self.loop.run_in_executor(self.executor, self.create_wx_instance)
        if not self.wx:
            print("无法连接到微信，请确保微信已登录")
            return False
        
        print("微信连接成功")
        return True
    
    @setup_op
    async def shutdown(self):
        """关闭微信环境"""
        if self.has_shutdown:
            return
        
        # 等待队列中的所有操作完成
        if self.main_window_queue:
            print(f"等待 {len(self.main_window_queue)} 个主窗口操作完成...")
            while self.main_window_queue:
                await asyncio.sleep(0.5)
        
        if self.executor:
            self.executor.shutdown()
        
        self.has_shutdown = True
        print("微信工具已关闭")
    
    @setup_op
    async def cleanup(self):
        """异步清理资源：释放所有监听并关闭微信环境"""
        if self.has_shutdown:
            return
        
        try:
            print(f"开始自动清理对象 {id(self)} 的微信资源...")
            
            # 获取所有监听的聊天
            if self.wx and hasattr(self.wx, 'listen'):
                # 使用list创建副本，因为我们会在遍历过程中修改原字典
                listen_chats = list(self.wx.listen.keys())
                if listen_chats:
                    print(f"发现 {len(listen_chats)} 个未释放的监听...")
                    for chat_name in listen_chats:
                        try:
                            print(f"自动移除监听: {chat_name}")
                            # 检查前后状态来验证是否成功移除
                            before_in_list = chat_name in self.wx.listen if hasattr(self.wx, 'listen') else False
                            before_count = len(self.wx.listen) if hasattr(self.wx, 'listen') else 0
                            
                            await self.remove_listen_chat(chat_name)
                            
                            # 检查是否真的被移除了
                            after_in_list = chat_name in self.wx.listen if hasattr(self.wx, 'listen') else False
                            after_count = len(self.wx.listen) if hasattr(self.wx, 'listen') else 0
                            
                            if not after_in_list or before_count > after_count:
                                print(f"确认已成功移除监听: {chat_name}")
                            else:
                                print(f"警告: 可能未能移除监听 {chat_name}")
                            
                            # 确保间隔一段时间，避免微信接口限流
                            await asyncio.sleep(0.5)
                        except Exception as e:
                            print(f"移除监听 '{chat_name}' 时出错: {e}")
                else:
                    print("未发现未释放的监听")
            
            # 关闭微信环境
            await self.shutdown()
        except Exception as e:
            print(f"清理资源时出错: {e}")
        finally:
            self.has_shutdown = True
    
    def sync_cleanup(self):
        """同步清理资源（当事件循环未运行时使用）"""
        if self.has_shutdown:
            return
            
        try:
            print(f"开始同步清理对象 {id(self)} 的微信资源...")
            
            # 获取所有监听的聊天
            if self.wx and hasattr(self.wx, 'listen'):
                listen_chats = list(self.wx.listen.keys())
                if listen_chats:
                    print(f"发现 {len(listen_chats)} 个未释放的监听...")
                    for chat_name in listen_chats:
                        try:
                            print(f"自动移除监听: {chat_name}")
                            before_len = len(self.wx.listen) if hasattr(self.wx, 'listen') else 0
                            self.wx.RemoveListenChat(chat_name)
                            # 检查是否真的移除了
                            after_len = len(self.wx.listen) if hasattr(self.wx, 'listen') else 0
                            still_exists = chat_name in self.wx.listen if hasattr(self.wx, 'listen') else False
                            
                            if not still_exists or before_len > after_len:
                                print(f"成功移除监听: {chat_name}")
                            else:
                                print(f"无法确认监听 {chat_name} 是否移除")
                            # 等待一小段时间，避免微信接口限流
                            time.sleep(0.5)
                        except Exception as e:
                            print(f"移除监听 '{chat_name}' 时出错: {e}")
                else:
                    print("未发现未释放的监听")
            
            # 关闭线程池
            if self.executor:
                self.executor.shutdown(wait=True)
                print("线程池已关闭")
            
            self.has_shutdown = True
            print("微信工具已关闭")
        except Exception as e:
            print(f"同步清理资源时出错: {e}")
        finally:
            self.has_shutdown = True
    
    # ========================= 队列处理 =========================
    
    @utility_op
    async def add_to_main_window_queue(self, coro):
        """将主窗口操作添加到队列"""
        future = self.loop.create_future()
        self.main_window_queue.append((coro, future))
        
        # 启动队列处理（如果尚未启动）
        if not self.main_window_queue_processing:
            asyncio.create_task(self.process_main_window_queue())
        
        # 等待操作完成
        return await future
    
    @utility_op
    async def process_main_window_queue(self):
        """处理主窗口操作队列"""
        self.main_window_queue_processing = True
        
        try:
            while self.main_window_queue:
                # 获取下一个队列项
                coro, future = self.main_window_queue.popleft()
                
                # 执行操作
                try:
                    async with self.main_window_lock:
                        result = await coro
                    future.set_result(result)
                except Exception as e:
                    if not future.done():
                        future.set_exception(e)
        finally:
            self.main_window_queue_processing = False
    
    # ========================= 主窗口操作函数 =========================
    
    @main_window_op
    async def main_send_msg(self, msg: str, who: Optional[str] = None, clear: bool = True, 
                           at: Optional[Union[str, List[str]]] = None, exact: bool = False) -> bool:
        """主窗口发送文本消息
        
        Args:
            msg: 消息内容
            who: 要发送给谁，默认为当前聊天窗口
            clear: 是否清除原本聊天编辑框的内容，默认True
            at: 要@的人，可以是一个人或多个人，格式为str或list
            exact: who参数是否精确匹配，默认False
            
        Returns:
            是否成功发送
        """
        if who:
            print(f"主窗口发送消息: {msg} 至 {who}")
        else:
            print(f"主窗口发送消息: {msg} 至当前聊天窗口")
            
        result = await self.loop.run_in_executor(
            self.executor,
            lambda: self.wx.SendMsg(msg=msg, who=who, clear=clear, at=at, exact=exact)
        )
        
        if result:
            print("主窗口消息发送成功")
        else:
            print("主窗口消息发送失败")
        return result
    
    @main_window_op
    async def main_send_files(self, filepath: Union[str, List[str]], who: Optional[str] = None, 
                             exact: bool = False) -> bool:
        """主窗口发送文件
        
        Args:
            filepath: 文件路径或文件路径列表
            who: 要发送给谁，默认发送到当前聊天窗口
            exact: who参数是否精确匹配，默认False
            
        Returns:
            是否成功发送
        """
        # 转换为列表
        file_list = filepath if isinstance(filepath, list) else [filepath]
        
        # 检查文件是否存在
        for file_path in file_list:
            if not os.path.exists(file_path):
                print(f"错误: 文件不存在 {file_path}")
                return False
        
        if who:
            print(f"主窗口发送文件: {file_list} 至 {who}")
        else:
            print(f"主窗口发送文件: {file_list} 至当前聊天窗口")
        
        result = await self.loop.run_in_executor(
            self.executor,
            lambda: self.wx.SendFiles(filepath=file_list, who=who, exact=exact)
        )
        
        if result:
            print("主窗口文件发送成功")
        else:
            print("主窗口文件发送失败")
        return result
    
    @main_window_op
    async def main_at_all(self, msg: Optional[str], who: str, exact: bool = False):
        """主窗口发送@所有人消息
        
        Args:
            msg: 消息内容，可为空
            who: 要发送给谁，必须指定
            exact: who参数是否精确匹配，默认False
        """
        print(f"主窗口发送@所有人消息 至 {who}")
        await self.loop.run_in_executor(
            self.executor,
            lambda: self.wx.AtAll(msg=msg, who=who, exact=exact)
        )
        print("主窗口@所有人指令已执行")
    
    @main_window_op
    async def main_get_all_message(self, savepic: bool = False, savevideo: bool = False, 
                                  savefile: bool = False, savevoice: bool = False, 
                                  parseurl: bool = False) -> List:
        """获取主窗口当前聊天窗口所有消息
        
        Args:
            savepic: 是否保存图片，默认False
            savevideo: 是否保存视频，默认False
            savefile: 是否保存文件，默认False
            savevoice: 是否保存语音，默认False
            parseurl: 是否解析卡片链接，默认False
            
        Returns:
            消息列表
        """
        print("获取主窗口当前聊天所有消息")
        messages = await self.loop.run_in_executor(
            self.executor,
            lambda: self.wx.GetAllMessage(
                savepic=savepic,
                savevideo=savevideo,
                savefile=savefile,
                savevoice=savevoice,
                parseurl=parseurl
            )
        )
        if messages:
            print(f"主窗口获取到 {len(messages)} 条消息")
        else:
            print("主窗口未获取到任何消息")
        return messages
    
    @main_window_op
    async def main_get_next_new_message(self, savepic: bool = False, savevideo: bool = False, 
                                      savefile: bool = False, savevoice: bool = False, 
                                      parseurl: bool = False) -> Dict:
        """获取主窗口下一条未读消息
        
        Args:
            savepic: 是否保存图片，默认False
            savevideo: 是否保存视频，默认False
            savefile: 是否保存文件，默认False
            savevoice: 是否保存语音，默认False
            parseurl: 是否解析卡片链接，默认False
            
        Returns:
            消息字典，键为会话名，值为消息列表
        """
        print("获取主窗口下一条未读消息")
        result = await self.loop.run_in_executor(
            self.executor,
            lambda: self.wx.GetNextNewMessage(
                savepic=savepic,
                savevideo=savevideo,
                savefile=savefile,
                savevoice=savevoice,
                parseurl=parseurl
            )
        )
        if result:
            for session, messages in result.items():
                print(f"主窗口获取到来自 {session} 的 {len(messages)} 条未读消息")
        else:
            print("主窗口没有未读消息")
        return result
    
    @main_window_op
    async def main_get_all_new_message(self, savepic: bool = False, savevideo: bool = False, 
                                     savefile: bool = False, savevoice: bool = False, 
                                     parseurl: bool = False) -> Dict:
        """获取主窗口所有未读消息
        
        Args:
            savepic: 是否保存图片，默认False
            savevideo: 是否保存视频，默认False
            savefile: 是否保存文件，默认False
            savevoice: 是否保存语音，默认False
            parseurl: 是否解析卡片链接，默认False
            
        Returns:
            消息字典，键为会话名，值为消息列表
        """
        print("获取主窗口所有未读消息")
        result = await self.loop.run_in_executor(
            self.executor,
            lambda: self.wx.GetAllNewMessage(
                savepic=savepic,
                savevideo=savevideo,
                savefile=savefile,
                savevoice=savevoice,
                parseurl=parseurl
            )
        )
        if result:
            total_count = sum(len(msgs) for msgs in result.values())
            print(f"主窗口获取到共 {total_count} 条未读消息，来自 {len(result)} 个会话")
        else:
            print("主窗口没有未读消息")
        return result
    
    # ========================= 子窗口操作函数 =========================
    
    @main_window_op
    async def chat_with(self, who: str) -> bool:
        """切换到指定联系人聊天窗口（主窗口操作）
        
        Args:
            who: 联系人名称
            
        Returns:
            是否成功切换
        """
        print(f"切换到与 '{who}' 的聊天...")
        chat_result = await self.loop.run_in_executor(
            self.executor, 
            lambda: self.wx.ChatWith(who)
        )
        
        if not chat_result:
            print(f"无法找到或切换到与 '{who}' 的聊天")
            return False
        
        print(f"成功切换到与 '{who}' 的聊天")
        await asyncio.sleep(1)  # 等待切换完成
        return True
    
    @main_window_op
    async def add_listen_chat(self, who: str) -> bool:
        """添加监听（主窗口操作）
        
        Args:
            who: 要监听的联系人名称
            
        Returns:
            是否成功添加监听
        """
        print(f"将 '{who}' 添加到监听列表...")
        await self.loop.run_in_executor(
            self.executor, 
            lambda: self.wx.AddListenChat(
                who=who,
                savepic=True,
                savevideo=True,
                savefile=True,
                savevoice=True,
                parseurl=True
            )
        )
        
        print(f"成功将 '{who}' 添加到监听列表")
        return True
    
    @main_window_op
    async def get_chat_window(self, who: str):
        """获取聊天窗口对象（主窗口操作）
        
        Args:
            who: 联系人名称
            
        Returns:
            聊天窗口对象，如果失败则返回None
        """
        print(f"获取'{who}'的子窗口对象...")
        # 需要在线程池中获取wx.listen属性
        listen_dict = await self.loop.run_in_executor(
            self.executor, 
            lambda: self.wx.listen if hasattr(self.wx, 'listen') else {}
        )
        
        if who not in listen_dict:
            print(f"错误: 无法获取'{who}'的子窗口对象")
            return None
            
        chat = listen_dict[who]
        print(f"wx.listen 的数据类型: {type(listen_dict)}")
        print(f"成功获取子窗口对象")
        
        # 为这个子窗口创建锁（如果不存在）
        if who not in self.chat_window_locks:
            self.chat_window_locks[who] = asyncio.Lock()
            print(f"为子窗口 '{who}' 创建了互斥锁")
            
        return chat
    
    @chat_window_op
    async def send_msg(self, chat, message: str, clear: bool = True, at: Optional[Union[str, List[str]]] = None) -> bool:
        """子窗口发送文本消息
        
        Args:
            chat: 聊天窗口对象
            message: 消息内容
            clear: 是否清除原本聊天编辑框的内容，默认True
            at: 要@的人，可以是一个人或多个人，格式为str或list
            
        Returns:
            是否成功发送
        """
        print(f"子窗口发送消息: {message}")
        msg_result = await self.loop.run_in_executor(
            self.executor, 
            lambda: chat.SendMsg(message, clear=clear, at=at)
        )
        
        if msg_result:
            print("子窗口消息发送成功")
            return True
        else:
            print("子窗口消息发送失败")
            return False
    
    @chat_window_op
    async def send_files(self, chat, filepath: Union[str, List[str]], 
                         max_attempts: int = 3) -> bool:
        """子窗口发送文件
        
        Args:
            chat: 聊天窗口对象
            filepath: 文件路径或文件路径列表
            max_attempts: 最大尝试次数
            
        Returns:
            是否成功发送
        """
        # 转换为列表
        file_list = filepath if isinstance(filepath, list) else [filepath]
        
        # 检查文件是否存在
        for file_path in file_list:
            if not os.path.exists(file_path):
                print(f"错误: 文件不存在 {file_path}")
                return False
        
        print(f"子窗口发送文件: {file_list}")
        
        # 多次尝试发送文件
        file_sent = False
        
        for attempt in range(1, max_attempts + 1):
            print(f"尝试发送文件 (第{attempt}次)...")
            try:
                # 使用子窗口对象发送文件
                file_result = await self.loop.run_in_executor(
                    self.executor,
                    lambda: chat.SendFiles(filepath=file_list)
                )
                print(file_result)
                if file_result:
                    print("子窗口文件发送成功")
                    file_sent = True
                    break
                else:
                    print(f"第{attempt}次发送失败，等待2秒后重试...")
                    await asyncio.sleep(2)
            except Exception as e:
                print(f"第{attempt}次发送出错: {e}")
                if attempt < max_attempts:
                    print("等待3秒后重试...")
                    await asyncio.sleep(3)
        
        if not file_sent:
            print(f"经过{max_attempts}次尝试后，子窗口文件发送仍然失败")
            
        return file_sent
    
    @main_window_op
    async def get_listen_message(self) -> Dict:
        """获取监听消息（主窗口操作）
        
        Returns:
            监听消息字典
        """
        print("获取所有监听消息")
        result = await self.loop.run_in_executor(self.executor, self.wx.GetListenMessage)
        if result:
            total_count = sum(len(msgs) for msgs in result.values())
            print(f"获取到 {total_count} 条监听消息")
        else:
            print("没有获取到监听消息")
        return result
    
    @utility_op
    async def process_messages(self, listen_messages: Dict) -> int:
        """处理监听消息
        
        Args:
            listen_messages: 监听消息字典
            
        Returns:
            处理的消息数量
        """
        if not listen_messages:
            print("没有监听消息")
            return 0
            
        # 统计消息
        total_count = sum(len(msgs) for msgs in listen_messages.values())
        if total_count == 0:
            print("没有收到新消息")
            return 0
            
        print(f"收到 {total_count} 条新消息")
        
        # 处理消息
        for chat_wnd, messages in listen_messages.items():
            chat_name = chat_wnd.who if hasattr(chat_wnd, 'who') else "未知"
            print(f"来自 {chat_name} 的 {len(messages)} 条消息:")
            
            for msg in messages:
                sender = getattr(msg, 'sender', '未知')
                content = getattr(msg, 'content', '')
                msg_type = getattr(msg, 'type', 'unknown')
                
                print(f"  {sender}: {content} (类型: {msg_type})")
                
        return total_count
    
    @main_window_op
    async def remove_listen_chat(self, who: str) -> bool:
        """移除监听（主窗口操作）
        
        Args:
            who: 要移除监听的联系人名称
            
        Returns:
            是否成功移除
        """
        print(f"移除 '{who}' 的监听...")
        try:
            # 检查是否确实在监听列表中
            is_in_listen = False
            if hasattr(self.wx, 'listen'):
                is_in_listen = who in self.wx.listen
                
            # 调用移除监听函数
            await self.loop.run_in_executor(
                self.executor, 
                lambda: self.wx.RemoveListenChat(who)
            )
            
            # 再次检查是否还在监听列表中
            still_in_listen = False
            if hasattr(self.wx, 'listen'):
                still_in_listen = who in self.wx.listen
            
            # 判断移除是否成功：原本在列表中且现在不在列表中，或操作完全成功
            success = (is_in_listen and not still_in_listen) or not still_in_listen
            
            if success:
                print(f"监听 '{who}' 已成功移除")
                
                # 从锁字典中删除
                if who in self.chat_window_locks:
                    del self.chat_window_locks[who]
                    
                return True
            else:
                print(f"移除监听 '{who}' 失败或无此监听")
                return False
        except Exception as e:
            print(f"移除监听 '{who}' 时出错: {e}")
            return False
    
    @chat_window_op
    async def at_all(self, chat, message: Optional[str] = None):
        """子窗口发送@所有人消息
        
        Args:
            chat: 聊天窗口对象
            message: 消息内容，可为空
        """
        print("子窗口发送@所有人消息")
        await self.loop.run_in_executor(
            self.executor,
            lambda: chat.AtAll(msg=message)
        )
        print("子窗口@所有人指令已执行")
    
    @chat_window_op
    async def get_chat_info(self, chat) -> Dict:
        """获取聊天窗口信息
        
        Args:
            chat: 聊天窗口对象
            
        Returns:
            聊天窗口信息字典
        """
        print("获取聊天窗口信息")
        info = await self.loop.run_in_executor(
            self.executor,
            lambda: chat.ChatInfo()
        )
        print(f"获取到聊天信息: {info}")
        return info
    
    @chat_window_op
    async def load_more_message(self, chat, interval: float = 0.3) -> bool:
        """加载更多历史消息
        
        Args:
            chat: 聊天窗口对象
            interval: 滚动间隔时间，默认0.3秒
            
        Returns:
            是否成功加载
        """
        print("加载更多历史消息")
        result = await self.loop.run_in_executor(
            self.executor,
            lambda: chat.LoadMoreMessage(interval=interval)
        )
        if result:
            print("成功加载更多历史消息")
        else:
            print("加载更多历史消息失败")
        return result
    
    @chat_window_op
    async def get_all_message(self, chat, savepic: bool = False, savevideo: bool = False, 
                             savefile: bool = False, savevoice: bool = False, 
                             parseurl: bool = False) -> List:
        """获取当前聊天窗口所有消息
        
        Args:
            chat: 聊天窗口对象
            savepic: 是否保存图片，默认False
            savevideo: 是否保存视频，默认False
            savefile: 是否保存文件，默认False
            savevoice: 是否保存语音，默认False
            parseurl: 是否解析卡片链接，默认False
            
        Returns:
            消息列表
        """
        print("获取子窗口所有聊天消息")
        messages = await self.loop.run_in_executor(
            self.executor,
            lambda: chat.GetAllMessage(
                savepic=savepic,
                savevideo=savevideo,
                savefile=savefile,
                savevoice=savevoice,
                parseurl=parseurl
            )
        )
        if messages:
            print(f"子窗口成功获取到 {len(messages)} 条消息")
        else:
            print("子窗口未获取到任何消息")
        return messages

    @utility_op
    async def terminate_gracefully(self):
        """优雅地终止工具，释放所有监听并关闭微信环境
        
        Returns:
            是否成功终止
        """
        try:
            await self.cleanup()
            return True
        except Exception as e:
            print(f"终止工具时出错: {e}")
            return False
            
    # ========================= 联系人管理功能 =========================
    
    @main_window_op
    async def get_all_friends(self) -> List[Dict[str, Any]]:
        """获取所有好友列表
        
        Returns:
            好友信息列表，每项包含nickname（昵称）、remark（备注）、tags（标签）等信息
        """
        print("获取所有好友列表...")
        friends = await self.loop.run_in_executor(
            self.executor,
            self.wx.GetAllFriends
        )
        print(f"获取到 {len(friends) if friends else 0} 个好友")
        return friends

    @main_window_op
    async def get_all_recent_groups(self) -> List[tuple]:
        """获取所有最近群聊列表
        
        Returns:
            群聊信息列表，通常每项包含群名和成员数量
        """
        print("获取所有最近群聊...")
        groups = await self.loop.run_in_executor(
            self.executor,
            self.wx.GetAllRecentGroups
        )
        print(f"获取到 {len(groups) if groups else 0} 个群聊")
        return groups
    
    # ========================= 群聊管理功能 =========================
    
    @main_window_op
    async def add_group_members(self, group_name: str, members: List[str]) -> bool:
        """添加成员到群聊
        
        Args:
            group_name: 群聊名称
            members: 要添加的成员列表
            
        Returns:
            是否添加成功（由于微信API限制，实际返回值总是None，此处返回True表示操作已执行）
        """
        print(f"添加成员 {members} 到群聊 '{group_name}'...")
        try:
            await self.loop.run_in_executor(
                self.executor,
                lambda: self.wx.AddGroupMembers(group_name, members)
            )
            # 微信API的AddGroupMembers无法直接通过返回值判断是否成功
            # 假定操作已执行（实际上需要用户检查微信界面确认）
            print("已执行添加群成员操作，请在微信中确认结果")
            return True
        except Exception as e:
            print(f"添加群成员时出错: {e}")
            return False

    @main_window_op
    async def manage_group(self, name: str = None, remark: str = None, 
                         myname: str = None, notice: str = None,
                         quit: bool = False, who: Optional[str] = None) -> Dict[str, bool]:
        """管理群设置
        
        Args:
            name: 修改群名称，None表示不修改
            remark: 修改备注名，None表示不修改
            myname: 修改我在本群的昵称，None表示不修改
            notice: 修改群公告，None表示不修改
            quit: 是否退出群，为True时其他参数无效
            who: 群聊名称，默认为当前聊天窗口
            
        Returns:
            各项操作的结果，dict格式，key为设置项名称，value为该项是否设置成功
        """
        # 如果指定了群聊，先切换到该群聊
        if who:
            print(f"切换到群聊 '{who}' 并修改设置...")
            # 先切换到指定群聊
            chat_result = await self.loop.run_in_executor(
                self.executor, 
                lambda: self.wx.ChatWith(who)
            )
            
            if not chat_result:
                print(f"无法找到或切换到群聊 '{who}'")
                return {"switch": False}
                
            # 等待切换完成
            await asyncio.sleep(1)
            print("在当前窗口执行群设置修改...")
        else:
            print("修改当前聊天窗口群设置...")
        
        # 在当前窗口执行操作
        try:
            result = await self.loop.run_in_executor(
                self.executor,
                lambda: self.wx.ManageGroup(
                    name=name, 
                    remark=remark, 
                    myname=myname, 
                    notice=notice, 
                    quit=quit
                )
            )
            
            for key, success in result.items():
                if success:
                    print(f"成功修改群{key}")
                else:
                    print(f"修改群{key}失败")
            
            return result
        except Exception as e:
            print(f"修改群设置时出错: {e}")
            return {"error": str(e)}
        
    @main_window_op
    async def remove_group_members(self, group_name: Optional[str], members: List[str]) -> bool:
        """从群聊中移除成员
        
        Args:
            group_name: 群聊名称，None表示当前聊天窗口
            members: 要移除的成员列表
            
        Returns:
            是否移除成功（由于微信API限制，实际返回值总是None，此处返回True表示操作已执行）
        """
        if group_name:
            print(f"切换到群聊 '{group_name}' 并移除成员 {members}...")
            # 先切换到指定群聊
            chat_result = await self.loop.run_in_executor(
                self.executor, 
                lambda: self.wx.ChatWith(group_name)
            )
            
            if not chat_result:
                print(f"无法找到或切换到群聊 '{group_name}'")
                return False
                
            # 等待切换完成
            await asyncio.sleep(1)
            print(f"从当前群聊窗口移除成员 {members}...")
        else:
            print(f"从当前群聊窗口移除成员 {members}...")
            
        try:
            # 在当前窗口操作，不传递群名
            await self.loop.run_in_executor(
                self.executor,
                lambda: self.wx.RemoveGroupMembers("", members)
            )
            # 微信API的RemoveGroupMembers无法直接通过返回值判断是否成功
            # 假定操作已执行（实际上需要用户检查微信界面确认）
            print("已执行移除群成员操作，请在微信中确认结果")
            return True
        except Exception as e:
            print(f"移除群成员时出错: {e}")
            return False
        
    @main_window_op
    async def get_group_members(self, group_name: str) -> List[str]:
        """获取群成员列表
        
        Args:
            group_name: 群聊名称
            
        Returns:
            群成员列表
        """
        print(f"获取群聊 '{group_name}' 的成员列表...")
        members = await self.loop.run_in_executor(
            self.executor,
            lambda: self.wx.GetGroupMembers(group_name)
        )
        print(f"获取到 {len(members) if members else 0} 个群成员")
        return members
        
    # ========================= 好友请求管理功能 =========================
    
    @main_window_op
    async def get_new_friends(self) -> List[Any]:
        """获取新好友请求
        
        Returns:
            好友请求对象列表
        """
        print("获取新好友请求...")
        friend_requests = await self.loop.run_in_executor(
            self.executor,
            self.wx.GetNewFriends
        )
        print(f"获取到 {len(friend_requests) if friend_requests else 0} 个好友请求")
        return friend_requests

    @utility_op
    def get_friend_names_from_requests(self, friend_requests: List[Any]) -> List[str]:
        """从好友请求对象列表中提取请求者的名字列表
        
        Args:
            friend_requests: 好友请求对象列表
            
        Returns:
            所有好友请求者的名字列表
        """
        if not friend_requests:
            return []
        
        # 提取每个请求者的名字
        names = []
        for request in friend_requests:
            name = getattr(request, "name", "未知")
            names.append(name)
            msg = getattr(request, "msg", "无验证消息")
            print(f"好友请求: {name}, 验证消息: {msg}")
        
        print(f"共有 {len(names)} 个好友请求")
        return names

    @main_window_op
    async def accept_friend_request(self, request) -> bool:
        """接受好友请求
        
        Args:
            request: 好友请求对象
            
        Returns:
            是否成功接受
        """
        name = getattr(request, "name", "未知")
        print(f"接受 {name} 的好友请求...")
        
        try:
            await self.loop.run_in_executor(
                self.executor,
                request.Accept
            )
            print(f"已接受 {name} 的好友请求")
            return True
        except Exception as e:
            print(f"接受好友请求失败: {e}")
            return False
    
    @main_window_op
    async def accept_friend_requests(self, requests: List[Any], remark: str = None, tags: List[str] = None) -> Dict[str, Any]:
        """接受指定的多个好友请求
        
        Args:
            requests: 要接受的好友请求对象列表
            remark: 备注名，可以为None
            tags: 标签列表，可以为None
            
        Returns:
            处理结果信息
        """
        print(f"接受 {len(requests)} 个指定好友请求...")
        result = {
            'total': len(requests),
            'success': 0,
            'failed': 0,
            'details': []
        }
        
        if not requests:
            # 接受请求后，直接调用底层API切换到聊天界面
            print("请求处理完成，切换到聊天界面...")
            await self.loop.run_in_executor(
                self.executor,
                self.wx.SwitchToChat
            )
            print("没有提供要处理的好友请求")
            return result
        
        # 处理每个请求
        for request in requests:
            name = getattr(request, "name", "未知")
            try:
                if remark or tags:
                    # 如果提供了备注或标签，使用这些信息接受请求
                    await self.loop.run_in_executor(
                        self.executor,
                        lambda: request.Accept(remark=remark, tags=tags)
                    )
                else:
                    # 否则使用默认设置接受请求
                    await self.loop.run_in_executor(
                        self.executor,
                        request.Accept
                    )
                    
                result['success'] += 1
                result['details'].append({'name': name, 'status': 'success'})
                print(f"已接受 {name} 的好友请求")
            except Exception as e:
                result['failed'] += 1
                result['details'].append({'name': name, 'status': 'error', 'error': str(e)})
                print(f"处理 {name} 的好友请求时出错: {e}")
            
            # 避免操作过快
            await asyncio.sleep(3)
        
        # 接受请求后，直接调用底层API切换到聊天界面
        print("请求处理完成，切换到聊天界面...")
        await self.loop.run_in_executor(
            self.executor,
            self.wx.SwitchToChat
        )
        
        print(f"好友请求处理完成: 共 {result['total']} 个请求，成功 {result['success']} 个，失败 {result['failed']} 个")
        return result
            
    @main_window_op
    async def accept_all_friend_requests(self) -> Dict[str, Any]:
        """接受所有好友请求
        
        Returns:
            处理结果信息
        """
        print("接受所有好友请求...")
        result = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'details': []
        }
        
        # 获取所有好友请求
        friend_requests = await self.get_new_friends()
        if not friend_requests:
            print("没有待处理的好友请求")
            return result
            
        result['total'] = len(friend_requests)
        
        # 处理每个请求
        for request in friend_requests:
            name = getattr(request, "name", "未知")
            try:
                success = await self.accept_friend_request(request)
                if success:
                    result['success'] += 1
                    result['details'].append({'name': name, 'status': 'success'})
                else:
                    result['failed'] += 1
                    result['details'].append({'name': name, 'status': 'failed'})
            except Exception as e:
                result['failed'] += 1
                result['details'].append({'name': name, 'status': 'error', 'error': str(e)})
                print(f"处理 {name} 的好友请求时出错: {e}")
            
            # 避免操作过快
            await asyncio.sleep(1.5)
        
        # 直接调用底层API切换到聊天界面
        print("所有请求处理完成，切换到聊天界面...")
        await self.loop.run_in_executor(
            self.executor,
            self.wx.SwitchToChat
        )
            
        print(f"处理完成: 共 {result['total']} 个请求，成功 {result['success']} 个，失败 {result['failed']} 个")
        return result
    
    @main_window_op
    async def add_new_friend(self, keywords: str, addmsg: str = "你好，我是使用AutoOOIN的用户", 
                           remark: str = None, tags: List[str] = None) -> Tuple[int, str]:
        """添加新好友
        
        Args:
            keywords: 搜索关键词（微信号、手机号或QQ号）
            addmsg: 添加好友的验证消息
            remark: 备注名，可以为None
            tags: 标签列表，可以为None
            
        Returns:
            元组 (状态码, 消息)
            状态码说明:
            0: 未知原因添加失败
            1: 发送请求成功
            2: 已经是好友
            3: 已被对方拉黑
            4: 找不到相关账号或内容
        """
        print(f"添加好友，关键词: {keywords}")
        
        try:
            result = await self.loop.run_in_executor(
                self.executor,
                lambda: self.wx.AddNewFriend(keywords=keywords, addmsg=addmsg, remark=remark, tags=tags)
            )
            
            # 解析返回结果
            status_code = result[0] if isinstance(result, tuple) and len(result) > 0 else 0
            message = result[1] if isinstance(result, tuple) and len(result) > 1 else "未知结果"
            
            # 根据状态码输出不同消息
            status_messages = {
                0: "未知原因添加失败",
                1: "发送请求成功",
                2: "已经是好友",
                3: "已被对方拉黑",
                4: "找不到相关账号或内容"
            }
            
            status_text = status_messages.get(status_code, "未知状态")
            print(f"添加好友结果: {status_text}, 消息: {message}")
            
            # 添加好友操作完成后，直接调用底层API切换到聊天界面
            print("添加好友完成，切换到聊天界面...")
            await self.loop.run_in_executor(
                self.executor,
                self.wx.SwitchToChat
            )
            
            return result
        except Exception as e:
            print(f"添加好友失败: {e}")
            # 即使出现异常，也尝试切换到聊天界面
            try:
                print("尝试切换到聊天界面...")
                await self.loop.run_in_executor(
                    self.executor,
                    self.wx.SwitchToChat
                )
            except Exception as chat_ex:
                print(f"切换到聊天界面失败: {chat_ex}")
            return (0, f"错误: {str(e)}")
    
    # ========================= 界面控制功能 =========================
    
    @main_window_op
    async def switch_to_chat(self) -> bool:
        """切换到聊天界面
        
        Returns:
            是否成功切换
        """
        print("切换到聊天界面...")
        result = await self.loop.run_in_executor(
            self.executor,
            self.wx.SwitchToChat
        )
        return True
        
    @main_window_op
    async def switch_to_contacts(self) -> bool:
        """切换到通讯录
        
        Returns:
            是否成功切换
        """
        print("切换到通讯录...")
        result = await self.loop.run_in_executor(
            self.executor,
            self.wx.SwitchToContacts
        )
        if result:
            print("成功切换到通讯录")
        else:
            print("切换到通讯录失败")
        return result
        
    @main_window_op
    async def get_current_chat(self, details: bool = True) -> Union[Dict[str, Any], str]:
        """获取当前聊天信息
        
        Args:
            details: 是否获取详细信息，默认True
                     - True时返回Dict，包含chat_name、chat_type、group_member_count等信息
                     - False时返回str，仅包含当前聊天窗口对象的名称
            
        Returns:
            当details为True时，返回当前聊天信息字典
            当details为False时，返回当前聊天名称字符串
        """
        print("获取当前聊天信息...")
        result = await self.loop.run_in_executor(
            self.executor,
            lambda: self.wx.CurrentChat(details=details)
        )
        
        if details:
            # details=True时，返回值为字典
            if isinstance(result, dict):
                chat_name = result.get('chat_name', '未知')
                print(f"当前聊天: {chat_name}")
                return result
            else:
                print(f"当前聊天: {result if result else '未知'}")
                # 如果意外返回非字典，则构造一个基本字典
                return {'chat_name': str(result)}
        else:
            # details=False时，返回值为字符串
            chat_name = str(result) if result else '未知'
            print(f"当前聊天: {chat_name}")
            return chat_name
        
    # ========================= 群聊创建功能 =========================
    
    @main_window_op
    async def create_group_chat(self, members: List[str], retry_count: int = 3) -> bool:
        """创建群聊
        
        Args:
            members: 要添加的成员列表
            retry_count: 重试次数
            
        Returns:
            是否成功创建
        """
        print(f"创建群聊，添加 {len(members)} 位成员...")
        
        if len(members) < 2:
            print("创建群聊至少需要2个成员，创建失败")
            return False
            
        # 使用重试机制
        result = await self.retry_operation(
            lambda: self.wx.CreateGroupChat(members),
            retry_count=retry_count,
            operation_name="创建群聊"
        )
        
        if result:
            print("群聊创建成功")
        else:
            print("群聊创建失败")
            
        return result
        
    # ========================= 实用工具函数 =========================
    
    async def retry_operation(self, operation, retry_count=3, retry_interval=2, operation_name="操作"):
        """重试机制，对重要操作进行多次尝试
        
        Args:
            operation: 要执行的操作函数
            retry_count: 重试次数
            retry_interval: 重试间隔（秒）
            operation_name: 操作名称（用于日志）
            
        Returns:
            操作结果
        """
        attempt = 0
        while attempt < retry_count:
            attempt += 1
            try:
                print(f"执行{operation_name} (尝试 {attempt}/{retry_count})...")
                result = await self.loop.run_in_executor(self.executor, operation)
                
                # 根据返回值确定是否成功
                if result is not None and result is not False:
                    print(f"{operation_name}成功")
                    return result
                    
                print(f"{operation_name}失败，准备重试...")
                
            except Exception as e:
                print(f"{operation_name}出错: {e}，准备重试...")
                
            # 如果不是最后一次尝试，则等待后重试
            if attempt < retry_count:
                await asyncio.sleep(retry_interval)
                
        print(f"{operation_name}失败，已达到最大重试次数 {retry_count}")
        return None

    @chat_window_op
    async def chat_get_members(self, chat) -> List[str]:
        """获取当前聊天窗口的群成员列表（子窗口操作）
        
        Args:
            chat: 聊天窗口对象
            
        Returns:
            群成员列表
        """
        print("获取子窗口群成员列表...")
        members = await self.loop.run_in_executor(
            self.executor,
            chat.GetMembers
        )
        print(f"获取到 {len(members) if members else 0} 个群成员")
        return members
        
    @chat_window_op
    async def chat_manage_group(self, chat, name: str = None, remark: str = None, 
                              myname: str = None, notice: str = None,
                              quit: bool = False) -> Dict[str, bool]:
        """管理当前聊天窗口的群设置（子窗口操作）
        
        Args:
            chat: 聊天窗口对象
            name: 修改群名称，None表示不修改
            remark: 修改备注名，None表示不修改
            myname: 修改我在本群的昵称，None表示不修改
            notice: 修改群公告，None表示不修改
            quit: 是否退出群，为True时其他参数无效
            
        Returns:
            各项操作的结果，dict格式，key为设置项名称，value为该项是否设置成功
        """
        print("修改子窗口群设置...")
        result = await self.loop.run_in_executor(
            self.executor,
            lambda: chat.ManageGroup(
                name=name, 
                remark=remark, 
                myname=myname, 
                notice=notice, 
                quit=quit
            )
        )
        
        for key, success in result.items():
            if success:
                print(f"成功修改群{key}")
            else:
                print(f"修改群{key}失败")
        
        return result
        
    @chat_window_op
    async def chat_at_member(self, chat, member: str, msg: str = None) -> bool:
        """在群中@特定成员（子窗口操作）
        
        Args:
            chat: 聊天窗口对象
            member: 要@的成员名称
            msg: 消息内容，可为空
            
        Returns:
            是否成功@成员
        """
        print(f"在子窗口@成员 '{member}'...")
        result = await self.loop.run_in_executor(
            self.executor,
            lambda: chat.AtMember(member=member, msg=msg)
        )
        
        if result:
            print(f"成功@成员 '{member}'")
        else:
            print(f"@成员 '{member}' 失败")
            
        return result
        
    @chat_window_op
    async def chat_add_members(self, chat, members: List[str]) -> bool:
        """添加成员到当前群聊（子窗口操作）
        
        Args:
            chat: 聊天窗口对象
            members: 要添加的成员列表
            
        Returns:
            是否成功添加（由于微信API限制，实际返回值可能为None，此处返回True表示操作已执行）
        """
        print(f"子窗口添加 {len(members)} 个成员到群聊...")
        try:
            await self.loop.run_in_executor(
                self.executor,
                lambda: chat.AddChatMembers(members)
            )
            # 微信API的AddChatMembers无法直接通过返回值判断是否成功
            print("已执行添加群成员操作，请在微信中确认结果")
            return True
        except Exception as e:
            print(f"添加群成员时出错: {e}")
            return False
        
    @chat_window_op
    async def chat_remove_members(self, chat, members: List[str]) -> bool:
        """从当前群聊中移除成员（子窗口操作）
        
        Args:
            chat: 聊天窗口对象
            members: 要移除的成员列表
            
        Returns:
            是否成功移除（由于微信API限制，实际返回值可能为None，此处返回True表示操作已执行）
        """
        print(f"子窗口移除 {len(members)} 个成员...")
        try:
            # 直接使用chat对象操作，不需要获取群名
            await self.loop.run_in_executor(
                self.executor,
                lambda: chat.RemoveGroupMembers(members)
            )
            # 微信API的RemoveGroupMembers无法直接通过返回值判断是否成功
            print("已执行移除群成员操作，请在微信中确认结果")
            return True
        except Exception as e:
            print(f"移除群成员时出错: {e}")
            return False
        
    @chat_window_op
    async def chat_get_group_info(self, chat) -> Dict[str, Any]:
        """获取当前群聊的信息（子窗口操作）
        
        Args:
            chat: 聊天窗口对象
            
        Returns:
            群聊信息字典
        """
        print("获取子窗口群聊信息...")
        info = await self.loop.run_in_executor(
            self.executor,
            chat.GroupInfo
        )
        
        print(f"获取到群聊信息: {info}")
        return info
        
    @chat_window_op
    async def chat_get_current(self, chat, details: bool = True) -> Union[Dict[str, Any], str]:
        """获取子窗口当前聊天信息（子窗口操作）
        
        Args:
            chat: 聊天窗口对象
            details: 是否获取详细信息，默认True
                     - True时返回Dict，包含chat_name、chat_type、group_member_count等信息
                     - False时返回str，仅包含当前聊天窗口对象的名称
            
        Returns:
            当details为True时，返回当前聊天信息字典
            当details为False时，返回当前聊天名称字符串
        """
        print("获取子窗口当前聊天信息...")
        
        if hasattr(chat, 'CurrentChat'):
            result = await self.loop.run_in_executor(
                self.executor,
                lambda: chat.CurrentChat(details=details)
            )
            
            if details:
                # details=True时，返回值为字典
                if isinstance(result, dict):
                    chat_name = result.get('chat_name', '未知')
                    print(f"子窗口当前聊天: {chat_name}")
                    return result
                else:
                    print(f"子窗口当前聊天: {result if result else '未知'}")
                    # 如果意外返回非字典，则构造一个基本字典
                    return {'chat_name': str(result)}
            else:
                # details=False时，返回值为字符串
                chat_name = str(result) if result else '未知'
                print(f"子窗口当前聊天: {chat_name}")
                return chat_name
        else:
            # 如果子窗口没有CurrentChat方法，从基本属性构建信息
            chat_name = getattr(chat, 'who', 'unknown')
            
            if details:
                chat_info = {
                    'chat_name': chat_name,
                    'is_group': getattr(chat, 'is_group', False),
                    'member_count': len(getattr(chat, 'members', [])) if hasattr(chat, 'members') else 0
                }
                print(f"子窗口当前聊天: {chat_name} (从基本属性构建)")
                return chat_info
            else:
                print(f"子窗口当前聊天: {chat_name} (从基本属性获取)")
                return chat_name