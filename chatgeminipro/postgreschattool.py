#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PostgreSQL聊天工具模块

提供基于PostgreSQL数据库的异步聊天功能，整合PostgresCacheTool和PostgresTool
实现高性能的聊天会话处理和历史记录管理
"""

import os
import json
import asyncio
import pathlib
from typing import Dict, Any, Optional, List, Tuple, Union
from datetime import datetime
import google.generativeai as genai
import httpx

# 导入自定义工具类
from ..cache.postgrescachetool import PostgresCacheTool
from ..db.postgrestool import PostgresTool

# 获取配置文件和模板文件的路径
current_dir = pathlib.Path(__file__).parent
config_dir = current_dir / "config"
template_dir = current_dir / "template"


class PostgresChatTool:
    """基于PostgreSQL的异步聊天工具类，整合数据库和缓存功能"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, use_cache: bool = True):
        """
        初始化聊天工具
        
        Args:
            config: 配置字典，如果不提供则加载默认配置
            use_cache: 是否使用缓存还原客户端，默认为True
        """
        self.config = config or self._load_config("default")
        self.client = None  # 异步API客户端
        self.template_cache = {}  # 模板缓存
        self.db_tool = None  # PostgreSQL数据库工具
        self.cache_tool = None  # PostgreSQL缓存工具
        self.message_history = []  # 当前会话的消息历史
        self.current_session_id = None  # 当前会话ID
        self.current_cache_id = None  # 当前缓存ID
        self.use_cache = use_cache  # 是否使用缓存还原客户端
        
    def _load_config(self, config_name: str) -> Dict[str, Any]:
        """
        加载配置文件
        
        Args:
            config_name: 配置文件名，不含扩展名
            
        Returns:
            配置信息字典
        """
        config_path = config_dir / f"{config_name}.json"
        
        # 检查配置文件是否存在
        if not config_path.exists():
            # 如果不存在，创建默认配置
            default_config = {
                "api_type": "gemini",
                "api_key": "",
                "model": "gemini-2.0-flash",
                "default_template": "default",
                "postgres": {
                    "user": "YOUR_DATABASE_USER_HERE",
                    "password": "YOUR_DATABASE_PASSWORD_HERE",
                    "database": "YOUR_DATABASE_NAME_HERE",
                    "host": "YOUR_DATABASE_HOST_HERE",
                    "port": "YOUR_DATABASE_PORT_HERE"
                }
            }
            
            # 确保目录存在
            config_dir.mkdir(exist_ok=True, parents=True)
            
            # 写入默认配置
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
                
            return default_config
        
        # 读取配置文件
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    async def _init_client(self) -> None:
        """初始化API客户端"""
        api_type = self.config.get("api_type", "gemini")
        
        if api_type == "gemini":
            # Google Gemini API
            self.client = genai.Client(
                api_key=self.config.get("api_key", "")
            )
        elif api_type == "openai" or api_type == "xai":
            # OpenAI或兼容OpenAI接口的模型（如X.AI的Grok）
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(
                api_key=self.config.get("api_key", ""),
                base_url=self.config.get("base_url", "https://api.openai.com/v1")
            )
        # 可以在此添加其他类型的API客户端
        else:
            raise ValueError(f"不支持的API类型: {api_type}")
    
    def _load_template(self, template_name: str) -> str:
        """
        加载提示词模板
        
        Args:
            template_name: 模板名称，不含扩展名
            
        Returns:
            模板内容
        """
        # 如果模板已经缓存，直接返回
        if template_name in self.template_cache:
            print(f"从缓存加载模板: {template_name}")
            return self.template_cache[template_name]
        
        print(f'加载模板: {template_name}')
        template_path = template_dir / f"{template_name}.txt"
        
        # 检查模板是否存在
        if not template_path.exists():
            print(f"模板文件不存在: {template_path}")
            # 创建默认模板
            default_template = "你是一个智能助手，请用简洁自然的语言回复用户的问题。"
            
            # 确保目录存在
            template_dir.mkdir(exist_ok=True, parents=True)
            
            # 写入默认模板
            with open(template_path, "w", encoding="utf-8") as f:
                f.write(default_template)
                
            self.template_cache[template_name] = default_template
            print(f"已创建默认模板: {template_name}")
            return default_template
        
        # 读取模板文件
        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read().strip()
            
        # 缓存模板
        self.template_cache[template_name] = template_content
        print(f"已读取模板文件: {template_name}, 内容长度: {len(template_content)}字符")
        return template_content
    
    async def initialize(self) -> bool:
        """
        初始化聊天工具（包括API客户端、数据库和缓存）
        
        Returns:
            是否初始化成功
        """
        try:
            # 初始化API客户端
            await self._init_client()
            
            # 获取PostgreSQL连接配置
            postgres_config = self.config.get("postgres", {})
            if not postgres_config:
                print("警告: PostgreSQL配置不存在，使用默认配置")
                postgres_config = {
                    "user": "YOUR_DATABASE_USER_HERE",
                    "password": "YOUR_DATABASE_PASSWORD_HERE",
                    "database": "YOUR_DATABASE_NAME_HERE",
                    "host": "YOUR_DATABASE_HOST_HERE",
                    "port": "YOUR_DATABASE_PORT_HERE"
                }
            
            # 初始化数据库工具
            self.db_tool = PostgresTool(**postgres_config)
            db_connected = await self.db_tool.connect()
            if not db_connected:
                print("错误: 连接PostgreSQL数据库失败")
                return False
            
            # 初始化缓存工具
            self.cache_tool = PostgresCacheTool(**postgres_config)
            cache_connected = await self.cache_tool.connect()
            if not cache_connected:
                print("错误: 连接PostgreSQL缓存服务失败")
                return False
            
            print("PostgreSQL聊天工具初始化成功")
            return True
        except Exception as e:
            print(f"初始化失败: {e}")
            return False
    
    async def close(self) -> None:
        """关闭所有连接"""
        if self.db_tool:
            await self.db_tool.close()
        
        if self.cache_tool:
            await self.cache_tool.close()
            
        print("所有数据库连接已关闭")
    
    async def _ensure_session_exists(self, session_name: str) -> int:
        """
        确保会话在数据库中存在，不存在则创建
        
        Args:
            session_name: 会话名称
            
        Returns:
            会话ID
        """
        return await self.db_tool.get_session_id(session_name)
    
    async def _ensure_cache_exists(self, session_id: int, template_name: Optional[str] = None) -> int:
        """
        确保缓存存在，不存在则创建
        
        Args:
            session_id: 会话ID
            template_name: 模板名称，不指定则使用默认模板
            
        Returns:
            缓存ID
        """
        # 查找与该会话关联的缓存
        caches = await self.cache_tool.find_caches_by_session(session_id, limit=1)
        
        if caches and self.use_cache:
            # 已有缓存且需要使用缓存
            return caches[0]['id']
        
        # 需要创建新缓存
        # 获取模板名称(而不是内容)
        template = template_name or self.config.get("default_template", "default")
        
        # 获取模板内容用于系统提示
        system_prompt = self._load_template(template)
        
        # 获取会话消息
        session_messages = await self.db_tool.get_messages(session_id, limit=100)
        
        # 转换为缓存消息格式
        cache_messages = []
        
        # 添加系统提示
        cache_messages.append({
            "role": "system",
            "content": system_prompt
        })
        
        # 添加历史消息
        for msg in session_messages:
            # 根据发送者确定角色
            if msg.get('sender') == 'AI':
                role = 'assistant'
            else:
                role = 'user'
                
            cache_messages.append({
                "role": role,
                "content": msg.get('content', ''),
                "id": msg.get('id')
            })
        
        # 创建缓存 - 传递模板名称而不是内容
        cache_id = await self.cache_tool.save_chat_cache(
            linked_session_id=session_id,
            model=self.config.get("model", "gemini-2.0-flash"),
            api_type=self.config.get("api_type", "gemini"),
            temperature=self.config.get("temperature", 0.7),
            system_prompt=template,  # 传递模板名称而不是内容
            messages=cache_messages
        )
        
        return cache_id
    
    async def set_session(self, session_name: str, template_name: Optional[str] = None, use_cache: Optional[bool] = None) -> Tuple[int, int]:
        """
        设置当前会话
        
        Args:
            session_name: 会话名称
            template_name: 模板名称，不指定则使用配置中的默认模板
            use_cache: 是否使用缓存，不指定则使用初始化时的设置
            
        Returns:
            (会话ID, 缓存ID)元组
        """
        # 如果指定了use_cache，临时修改设置
        original_use_cache = self.use_cache
        if use_cache is not None:
            self.use_cache = use_cache
            
        try:
            # 确保会话存在
            session_id = await self._ensure_session_exists(session_name)
            
            # 使用指定模板或默认模板
            template = template_name or self.config.get("default_template", "default")
            cache_id = await self._ensure_cache_exists(session_id, template)
            
            # 更新当前会话
            self.current_session_id = session_id
            self.current_cache_id = cache_id
            
            # 加载消息历史
            await self._load_message_history()
            
            return session_id, cache_id
        finally:
            # 恢复原始设置
            if use_cache is not None:
                self.use_cache = original_use_cache
    
    async def _load_message_history(self) -> None:
        """加载当前会话的消息历史"""
        if not self.current_cache_id:
            print("错误: 未设置当前会话")
            return
            
        # 从缓存获取消息
        self.message_history = await self.cache_tool.get_chat_messages(self.current_cache_id)
    
    async def chat(self, user_message: str, template_name: Optional[str] = None,
                model: Optional[str] = None, temperature: Optional[float] = None,
                session_name: Optional[str] = None, save_to_db: bool = True,
                use_cache: Optional[bool] = None) -> str:
        """
        与模型进行对话
        
        Args:
            user_message: 用户消息
            template_name: 模板名称，不指定则使用配置中的默认模板
            model: 模型名称，不指定则使用配置中的默认模型
            temperature: 温度参数，不指定则使用配置中的默认值
            session_name: 会话名称，不指定则使用当前会话
            save_to_db: 是否自动将消息保存到数据库，默认为True
            use_cache: 是否使用缓存，不指定则使用初始化时的设置
            
        Returns:
            模型回复
        """
        # 如果指定了会话名称，切换到该会话
        if session_name:
            await self.set_session(session_name, use_cache=use_cache)
        elif use_cache is not None and session_name is None and self.current_session_id:
            # 如果没有指定会话名称但指定了use_cache，且当前有会话，则重新加载当前会话
            current_session = await self.db_tool.get_session_by_id(self.current_session_id)
            if current_session:
                await self.set_session(current_session.get('name', ''), use_cache=use_cache)
        
        # 确保已设置当前会话
        if not self.current_session_id or not self.current_cache_id:
            raise ValueError("未设置当前会话，请先调用set_session方法")
        
        # 使用指定模板或默认模板
        template = template_name or self.config.get("default_template", "default")
        system_prompt = self._load_template(template)
        
        # 为Gemini构建输入文本（将模板拼接到前面）
        input_text = system_prompt + "\n\n"
        
        # 添加历史消息（不包含系统消息）
        for msg in self.message_history:
            if msg.get('role') != 'system':
                role = "用户" if msg.get('role') == 'user' else "助手"
                input_text += f"{role}: {msg.get('content', '')}\n"
        
        # 添加当前用户消息
        input_text += f"用户: {user_message}\n助手: "
        
        # 获取模型
        model_name = model or self.config.get("model", "gemini-2.0-flash")
        
        # 初始化消息ID变量
        user_msg_id = None
        ai_msg_id = None
        
        # 如果需要保存到数据库
        if save_to_db:
            # 1. 保存用户消息到数据库
            user_msg_id = await self.db_tool.add_message(
                session_id=self.current_session_id,
                sender="用户",
                content=user_message,
                msg_type="text"
            )
        
        # 2. 调用API
        api_type = self.config.get("api_type", "gemini")
        
        try:
            if api_type == "gemini":
                # 打印请求详情
                print(f"准备调用Gemini API:")
                print(f"  - API类型: {api_type}")
                print(f"  - 模型: {model_name}")
                print(f"  - 输入长度: {len(input_text)} 字符")
                
                print(f"开始调用Gemini API...")
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=input_text,
                    config=types.GenerateContentConfig(
                        thinking_config=types.ThinkingConfig(thinking_budget=1024)
                    ),
                )
                
                ai_response = response.text
                print(f"Gemini API调用成功，响应长度: {len(ai_response)}")
                
            elif api_type == "openai" or api_type == "xai":
                # 保持原有的OpenAI逻辑用于兼容性
                messages = [{"role": "system", "content": system_prompt}]
                
                # 添加历史消息（不包含系统消息）
                for msg in self.message_history:
                    if msg.get('role') != 'system':
                        messages.append({
                            "role": msg.get('role'),
                            "content": msg.get('content', '')
                        })
                
                # 添加用户消息
                messages.append({"role": "user", "content": user_message})
                
                # 获取OpenAI相关参数
                temp = temperature if temperature is not None else self.config.get("temperature", 0.7)
                max_tokens = self.config.get("max_tokens", 1000)
                
                # 打印请求详情
                print(f"准备调用OpenAI API:")
                print(f"  - API类型: {api_type}")
                print(f"  - 模型: {model_name}")
                print(f"  - 消息数量: {len(messages)}")
                print(f"  - 温度: {temp}")
                print(f"  - 最大令牌: {max_tokens}")
                
                # 设置超时
                timeout = httpx.Timeout(30.0, connect=10.0)
                self.client.timeout = timeout
                
                print(f"开始调用OpenAI API...")
                response = await self.client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=temp,
                    max_tokens=max_tokens
                )
                
                ai_response = response.choices[0].message.content
                print(f"OpenAI API调用成功，响应长度: {len(ai_response)}")
                
            else:
                raise ValueError(f"不支持的API类型: {api_type}")
                
            # 如果需要保存到数据库
            if save_to_db:
                # 3. 保存AI回复到数据库
                ai_msg_id = await self.db_tool.add_message(
                    session_id=self.current_session_id,
                    sender="AI",
                    content=ai_response,
                    msg_type="text"
                )
                
                # 4. 更新缓存
                # 更新消息历史
                updated_messages = await self.cache_tool.get_chat_messages(self.current_cache_id)
                
                # 添加新的用户消息和AI回复
                updated_messages.append({
                    "role": "user",
                    "content": user_message,
                    "id": user_msg_id
                })
                
                updated_messages.append({
                    "role": "assistant",
                    "content": ai_response,
                    "id": ai_msg_id
                })
                
                # 更新缓存 - 使用缓存当前的系统模板名称(不需要修改)
                # 注意: update_chat_cache只更新消息,不更新系统提示
                await self.cache_tool.update_chat_cache(
                    cache_id=self.current_cache_id,
                    new_messages=updated_messages
                )
                
                # 更新本地消息历史
                self.message_history = updated_messages
            
            return ai_response
        except httpx.TimeoutException as e:
            error_msg = f"API调用超时: {str(e)}"
            print(f"错误: {error_msg}")
            if save_to_db:
                await self.db_tool.add_message(
                    session_id=self.current_session_id,
                    sender="系统",
                    content=error_msg,
                    msg_type="error"
                )
            return error_msg
        except httpx.ConnectError as e:
            error_msg = f"无法连接到API服务器: {str(e)}"
            print(f"错误: {error_msg}")
            if save_to_db:
                await self.db_tool.add_message(
                    session_id=self.current_session_id,
                    sender="系统",
                    content=error_msg,
                    msg_type="error"
                )
            return error_msg
        except httpx.HTTPStatusError as e:
            error_msg = f"API返回错误状态码 {e.response.status_code}: {e.response.text[:500]}"
            print(f"错误: {error_msg}")
            if save_to_db:
                await self.db_tool.add_message(
                    session_id=self.current_session_id,
                    sender="系统",
                    content=error_msg,
                    msg_type="error"
                )
            return error_msg
        except Exception as e:
            error_msg = f"聊天请求失败: {type(e).__name__}: {str(e)}"
            print(f"错误: {error_msg}")
            import traceback
            traceback.print_exc()
            # 如果需要保存到数据库，才保存错误信息
            if save_to_db:
                # 保存错误信息到数据库
                await self.db_tool.add_message(
                    session_id=self.current_session_id,
                    sender="系统",
                    content=error_msg,
                    msg_type="error"
                )
            return error_msg
    
    async def get_chat_history(self, session_name: Optional[str] = None,
                            limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取聊天历史记录
        
        Args:
            session_name: 会话名称，不指定则使用当前会话
            limit: 返回条数限制
            
        Returns:
            聊天记录列表
        """
        # 如果指定了会话名称，切换到该会话
        if session_name:
            await self.set_session(session_name)
        
        # 确保已设置当前会话
        if not self.current_session_id:
            raise ValueError("未设置当前会话，请先调用set_session方法")
        
        # 获取会话消息
        return await self.db_tool.get_messages(self.current_session_id, limit=limit)
    
    async def get_session_by_id(self, session_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID获取会话信息
        
        Args:
            session_id: 会话ID
            
        Returns:
            会话信息字典或None（不存在）
        """
        if not self.db_tool:
            raise ValueError("数据库工具未初始化")
            
        return await self.db_tool.get_session_by_id(session_id)
    
    async def list_sessions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        列出所有会话
        
        Args:
            limit: 返回条数限制
            
        Returns:
            会话列表
        """
        return await self.db_tool.list_chat_caches(limit=limit)
    
    async def search_messages(self, keyword: str, session_name: Optional[str] = None,
                           limit: int = 20) -> List[Dict[str, Any]]:
        """
        搜索消息
        
        Args:
            keyword: 搜索关键词
            session_name: 会话名称，不指定则搜索所有会话
            limit: 返回条数限制
            
        Returns:
            匹配的消息列表
        """
        session_id = None
        if session_name:
            # 查找会话ID
            session = await self.db_tool.get_session_by_name(session_name)
            if session:
                session_id = session.get('id')
            else:
                print(f"警告: 会话 '{session_name}' 不存在")
                return []
                
        return await self.db_tool.search_messages(keyword, session_id=session_id)
    
    async def set_config(self, config_data: Dict[str, Any]) -> bool:
        """
        设置聊天工具配置
        
        Args:
            config_data: 配置数据字典
            
        Returns:
            操作是否成功
        """
        try:
            # 验证必要的配置项
            api_type = config_data.get("api_type", self.config.get("api_type", "gemini"))
            
            if api_type == "gemini":
                required_keys = ["api_type", "model"]
            else:
                required_keys = ["api_type", "model", "temperature"]
                
            for key in required_keys:
                if key not in config_data:
                    print(f"错误: 缺少必要的配置项 '{key}'")
                    return False
            
            # 更新配置
            self.config.update(config_data)
            
            # 重新初始化客户端
            await self._init_client()
            return True
        except Exception as e:
            print(f"设置配置失败: {e}")
            return False
    
    async def export_chat_history(self, session_name: str, output_path: Optional[str] = None) -> Optional[str]:
        """
        导出聊天历史记录到JSON文件
        
        Args:
            session_name: 会话名称
            output_path: 输出文件路径，不指定则自动生成
            
        Returns:
            导出文件路径或None（导出失败）
        """
        try:
            # 查找会话
            session = await self.db_tool.get_session_by_name(session_name)
            if not session:
                print(f"错误: 会话 '{session_name}' 不存在")
                return None
                
            # 查找会话的缓存
            caches = await self.cache_tool.find_caches_by_session(session['id'], limit=1)
            if not caches:
                print(f"错误: 会话 '{session_name}' 没有关联的缓存")
                return None
                
            # 导出缓存
            cache_id = caches[0]['id']
            return await self.cache_tool.export_to_json(cache_id, output_path)
        except Exception as e:
            print(f"导出聊天历史失败: {e}")
            return None
    
    async def import_chat_history(self, json_path: str) -> Optional[int]:
        """
        从JSON文件导入聊天历史记录
        
        Args:
            json_path: JSON文件路径
            
        Returns:
            缓存ID或None（导入失败）
        """
        try:
            return await self.cache_tool.import_from_json(json_path)
        except Exception as e:
            print(f"导入聊天历史失败: {e}")
            return None
    
    async def delete_session(self, session_name: str) -> bool:
        """
        删除会话及其关联的缓存
        
        Args:
            session_name: 会话名称
            
        Returns:
            操作是否成功
        """
        try:
            # 查找会话
            session = await self.db_tool.get_session_by_name(session_name)
            if not session:
                print(f"错误: 会话 '{session_name}' 不存在")
                return False
                
            # 查找会话的缓存
            caches = await self.cache_tool.find_caches_by_session(session['id'], limit=100)
            
            # 删除所有关联的缓存
            for cache in caches:
                await self.cache_tool.delete_chat_cache(cache['id'])
                
            # 删除会话
            success = await self.db_tool.delete_session(session['id'])
            
            # 如果当前会话被删除，清空当前会话信息
            if success and self.current_session_id == session['id']:
                self.current_session_id = None
                self.current_cache_id = None
                self.message_history = []
                
            return success
        except Exception as e:
            print(f"删除会话失败: {e}")
            return False

    def save_template(self, template_name: str, template_content: str) -> bool:
        """
        保存提示词模板
        
        Args:
            template_name: 模板名称，不含扩展名
            template_content: 模板内容
            
        Returns:
            是否保存成功
        """
        try:
            # 确保目录存在
            template_dir.mkdir(exist_ok=True, parents=True)
            
            # 保存模板
            template_path = template_dir / f"{template_name}.txt"
            with open(template_path, "w", encoding="utf-8") as f:
                f.write(template_content)
                
            # 更新缓存
            self.template_cache[template_name] = template_content
            
            print(f"已保存模板: {template_name}, 内容长度: {len(template_content)}字符")
            return True
        except Exception as e:
            print(f"保存模板失败: {e}")
            return False
    
    def list_templates(self) -> List[str]:
        """
        列出所有模板
        
        Returns:
            模板名称列表
        """
        # 确保目录存在
        template_dir.mkdir(exist_ok=True, parents=True)
        
        # 获取所有模板文件
        templates = [f.stem for f in template_dir.glob("*.txt")]
        print(f"模板列表: {templates}")
        return templates


# 示例使用方法
async def example_usage():
    """PostgresChatTool使用示例"""
    # 默认使用缓存
    chat_tool = PostgresChatTool()
    
    try:
        # 初始化工具
        initialized = await chat_tool.initialize()
        if not initialized:
            print("初始化失败")
            return
            
        # 设置会话
        await chat_tool.set_session("测试会话")
        
        # 发送消息并获取回复
        response = await chat_tool.chat("你好，请介绍一下PostgreSQL数据库")
        print(f"AI回复: {response}")
        
        # 不使用缓存，强制重新初始化会话
        response2 = await chat_tool.chat("继续介绍PostgreSQL的优势", use_cache=False)
        print(f"不使用缓存的AI回复: {response2}")
        
        # 获取会话历史
        history = await chat_tool.get_chat_history()
        print(f"会话历史: {history}")
        
    finally:
        # 关闭连接
        await chat_tool.close()
        
    # 也可以在初始化时就指定不使用缓存
    no_cache_tool = PostgresChatTool(use_cache=False)
    try:
        await no_cache_tool.initialize()
        await no_cache_tool.set_session("全新会话")
        response = await no_cache_tool.chat("你好，这是一个全新的会话")
        print(f"不使用缓存的工具回复: {response}")
    finally:
        await no_cache_tool.close()


# 入口函数
if __name__ == "__main__":
    asyncio.run(example_usage()) 