#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
重排序工具模块

提供文本重排序功能，支持不同的重排序模型和API提供商
"""

import os
import json
import pathlib
import requests
from typing import Dict, Any, Optional, List, Union

# 获取配置文件的路径
current_dir = pathlib.Path(__file__).parent
config_dir = current_dir / "config"


class RerankTool:
    """文本重排序工具类，提供统一的重排序接口"""
    
    def __init__(self, config_name: str = "default"):
        """
        初始化重排序工具
        
        Args:
            config_name: 配置文件名，不含扩展名
        """
        self.config = self._load_config(config_name)
        
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
                "api_type": "jina",
                "api_key": "",
                "base_url": "https://api.jina.ai/v1/rerank",
                "model": "jina-reranker-v2-base-multilingual",
                "top_n": 3,  # 默认返回前3个结果
                "return_documents": False  # 默认不返回文档内容
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
    
    def rerank(self, query: str, documents: List[str], 
              model: Optional[str] = None, top_n: Optional[int] = None,
              return_documents: Optional[bool] = None) -> Dict[str, Any]:
        """
        重排序文档列表
        
        Args:
            query: 查询文本
            documents: 文档列表
            model: 模型名称，不指定则使用配置中的默认模型
            top_n: 返回结果的数量，不指定则使用配置中的默认值
            return_documents: 是否在结果中返回文档内容，不指定则使用配置中的默认值
            
        Returns:
            重排序结果字典
        """
        # 使用指定参数或默认配置
        model_name = model or self.config.get("model", "jina-reranker-v2-base-multilingual")
        top_n_results = top_n or self.config.get("top_n", 3)
        should_return_docs = return_documents if return_documents is not None else self.config.get("return_documents", False)
        
        # 根据API类型调用不同的重排序API
        api_type = self.config.get("api_type", "jina")
        
        if api_type == "jina":
            return self._rerank_jina(query, documents, model_name, top_n_results, should_return_docs)
        else:
            raise ValueError(f"不支持的API类型: {api_type}")
    
    def _rerank_jina(self, query: str, documents: List[str], model: str, 
                    top_n: int, return_documents: bool) -> Dict[str, Any]:
        """
        调用Jina API进行重排序
        
        Args:
            query: 查询文本
            documents: 文档列表
            model: 模型名称
            top_n: 返回结果的数量
            return_documents: 是否在结果中返回文档内容
            
        Returns:
            重排序结果字典
        """
        url = self.config.get("base_url", "https://api.jina.ai/v1/rerank")
        api_key = self.config.get("api_key", "")
        
        if not api_key:
            raise ValueError("缺少Jina API密钥，请在配置中设置api_key")
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        
        data = {
            "model": model,
            "query": query,
            "top_n": top_n,
            "documents": documents,
            "return_documents": return_documents
        }
        
        try:
            response = requests.post(url, json=data, headers=headers)
            response.raise_for_status()  # 抛出HTTP错误
            result = response.json()
            
            # 添加成功标志
            result["success"] = True
            
            return result
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": str(e),
                "message": "重排序请求失败"
            }
    
    def save_config(self, config_name: str, config_data: Dict[str, Any]) -> None:
        """
        保存配置
        
        Args:
            config_name: 配置名称
            config_data: 配置数据
        """
        config_path = config_dir / f"{config_name}.json"
        
        # 确保目录存在
        config_dir.mkdir(exist_ok=True, parents=True)
        
        # 写入配置
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        
        # 更新当前配置
        if config_name == "default":
            self.config = config_data
    
    def list_configs(self) -> List[str]:
        """
        列出所有可用的配置
        
        Returns:
            配置名称列表
        """
        # 确保目录存在
        config_dir.mkdir(exist_ok=True, parents=True)
        
        # 获取配置列表
        configs = [f.stem for f in config_dir.glob("*.json")]
        return configs
        
    def get_client_config(self) -> Dict[str, Any]:
        """
        获取当前客户端配置
        
        Returns:
            配置信息字典
        """
        return {
            "api_type": self.config.get("api_type", "jina"),
            "model": self.config.get("model", "jina-reranker-v2-base-multilingual"),
            "top_n": self.config.get("top_n", 3),
            "return_documents": self.config.get("return_documents", False)
        }
    
    def set_config(self, config_data: Dict[str, Any]) -> bool:
        """
        设置重排序工具配置
        
        Args:
            config_data: 配置数据字典
            
        Returns:
            操作是否成功
        """
        try:
            # 验证必要的配置项
            required_keys = ["api_type", "api_key", "model"]
            for key in required_keys:
                if key not in config_data:
                    print(f"错误: 缺少必要的配置项 '{key}'")
                    return False
            
            # 更新配置
            self.config.update(config_data)
            return True
        except Exception as e:
            print(f"设置配置失败: {e}")
            return False
    
    def rerank_batch(self, queries: List[str], documents_list: List[List[str]], 
                    batch_size: int = 5) -> List[Dict[str, Any]]:
        """
        批量处理重排序请求
        
        Args:
            queries: 查询列表
            documents_list: 每个查询对应的文档列表
            batch_size: 批处理大小
            
        Returns:
            重排序结果列表
        """
        if len(queries) != len(documents_list):
            raise ValueError("查询列表和文档列表长度必须相同")
            
        results = []
        
        # 批量处理
        for i in range(0, len(queries), batch_size):
            batch_queries = queries[i:i + batch_size]
            batch_docs = documents_list[i:i + batch_size]
            
            print(f"处理批次 {i//batch_size + 1}/{(len(queries) + batch_size - 1)//batch_size}...")
            
            # 逐个处理查询
            for query, docs in zip(batch_queries, batch_docs):
                result = self.rerank(query, docs)
                results.append(result)
                
        return results
    
    def get_top_documents(self, query: str, documents: List[str], top_n: int = 3) -> List[Dict[str, Any]]:
        """
        获取与查询最相关的前N个文档
        
        Args:
            query: 查询文本
            documents: 文档列表
            top_n: 返回结果的数量
            
        Returns:
            包含索引、相关性分数和文档内容的结果列表
        """
        # 调用重排序API
        result = self.rerank(query, documents, top_n=top_n, return_documents=True)
        
        if not result.get("success", False):
            print(f"重排序请求失败: {result.get('message', '未知错误')}")
            return []
        
        # 提取结果
        reranked_results = result.get("results", [])
        
        # 整理结果格式
        top_docs = []
        for item in reranked_results:
            doc_index = item.get("index", -1)
            if 0 <= doc_index < len(documents):
                top_docs.append({
                    "index": doc_index,
                    "score": item.get("relevance_score", 0.0),
                    "document": documents[doc_index]
                })
        
        return top_docs 