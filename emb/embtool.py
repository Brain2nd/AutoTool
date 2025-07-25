#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
嵌入向量工具模块

提供文本嵌入向量的生成功能，支持不同的嵌入模型和API提供商
"""

import os
import json
import pathlib
import requests
from typing import Dict, Any, Optional, List, Union

# 获取配置文件的路径
current_dir = pathlib.Path(__file__).parent
config_dir = current_dir / "config"


class EmbTool:
    """文本嵌入向量工具类，提供统一的嵌入向量接口"""
    
    def __init__(self, config_name: str = "default"):
        """
        初始化嵌入向量工具
        
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
                "base_url": "https://api.jina.ai/v1/embeddings",
                "model": "jina-embeddings-v3",
                "task": "text-matching",
                "dimensions": 512  # 嵌入向量的默认维度
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
    
    def get_embedding(self, texts: Union[str, List[str]], model: Optional[str] = None, 
                      task: Optional[str] = None) -> Dict[str, Any]:
        """
        获取文本的嵌入向量
        
        Args:
            texts: 需要嵌入的文本或文本列表
            model: 模型名称，不指定则使用配置中的默认模型
            task: 任务类型，不指定则使用配置中的默认任务
            
        Returns:
            包含嵌入向量的结果字典
        """
        # 使用指定模型或默认模型
        model_name = model or self.config.get("model", "jina-embeddings-v3")
        task_type = task or self.config.get("task", "text-matching")
        
        # 确保texts是列表
        if isinstance(texts, str):
            texts = [texts]
        
        # 根据API类型调用不同的嵌入向量API
        api_type = self.config.get("api_type", "jina")
        
        if api_type == "jina":
            return self._get_jina_embedding(texts, model_name, task_type)
        elif api_type == "openai":
            return self._get_openai_embedding(texts, model_name)
        else:
            raise ValueError(f"不支持的API类型: {api_type}")
    
    def _get_jina_embedding(self, texts: List[str], model: str, task: str) -> Dict[str, Any]:
        """
        调用Jina API获取嵌入向量
        
        Args:
            texts: 文本列表
            model: 模型名称
            task: 任务类型
            
        Returns:
            包含嵌入向量的结果字典
        """
        url = self.config.get("base_url", "https://api.jina.ai/v1/embeddings")
        api_key = self.config.get("api_key", "")
        
        if not api_key:
            raise ValueError("缺少Jina API密钥，请在配置中设置api_key")
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        
        data = {
            'model': model,
            'task': task,
            'input': texts
        }
        
        try:
            response = requests.post(url, json=data, headers=headers)
            response.raise_for_status()  # 抛出HTTP错误
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": str(e),
                "message": "获取嵌入向量失败"
            }
    
    def _get_openai_embedding(self, texts: List[str], model: str) -> Dict[str, Any]:
        """
        调用OpenAI API获取嵌入向量
        
        Args:
            texts: 文本列表
            model: 模型名称
            
        Returns:
            包含嵌入向量的结果字典
        """
        url = self.config.get("base_url", "https://api.openai.com/v1/embeddings")
        api_key = self.config.get("api_key", "")
        
        if not api_key:
            raise ValueError("缺少OpenAI API密钥，请在配置中设置api_key")
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        
        # OpenAI要求每次只能发送一个文本，所以需要循环调用
        results = []
        for text in texts:
            data = {
                'model': model,
                'input': text
            }
            
            try:
                response = requests.post(url, json=data, headers=headers)
                response.raise_for_status()
                results.append(response.json())
            except requests.exceptions.RequestException as e:
                return {
                    "success": False,
                    "error": str(e),
                    "message": "获取嵌入向量失败"
                }
        
        # 合并结果
        return {
            "success": True,
            "model": model,
            "data": results
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
            "model": self.config.get("model", "jina-embeddings-v3"),
            "task": self.config.get("task", "text-matching"),
            "dimensions": self.config.get("dimensions", 512)
        }
    
    def set_config(self, config_data: Dict[str, Any]) -> bool:
        """
        设置嵌入工具配置
        
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
    
    def embedding_batch(self, texts: List[str], batch_size: int = 20) -> Dict[str, Any]:
        """
        批量处理文本嵌入，适用于大量文本
        
        Args:
            texts: 文本列表
            batch_size: 每批处理的文本数量
            
        Returns:
            合并后的嵌入结果
        """
        if not texts:
            return {"success": False, "message": "输入文本列表为空"}
        
        # 分批处理
        batches = [texts[i:i+batch_size] for i in range(0, len(texts), batch_size)]
        results = []
        
        for i, batch in enumerate(batches):
            print(f"处理批次 {i+1}/{len(batches)}...")
            batch_result = self.get_embedding(batch)
            
            if not batch_result.get("success", True):
                print(f"批次 {i+1} 处理失败: {batch_result.get('message', '未知错误')}")
                continue
                
            results.append(batch_result)
        
        # 合并结果
        return self._merge_batch_results(results)
    
    def _merge_batch_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        合并批处理结果
        
        Args:
            results: 批处理结果列表
            
        Returns:
            合并后的结果
        """
        if not results:
            return {"success": False, "message": "没有成功的批处理结果"}
        
        # 提取第一个结果的模型信息等
        merged = {
            "success": True,
            "model": results[0].get("model", "unknown"),
        }
        
        # 对于Jina API，合并data字段
        if self.config.get("api_type") == "jina":
            all_embeddings = []
            for result in results:
                if "data" in result:
                    all_embeddings.extend(result["data"])
            merged["data"] = all_embeddings
        
        # 对于OpenAI API，合并每个批次的data
        elif self.config.get("api_type") == "openai":
            all_data = []
            for result in results:
                if "data" in result:
                    all_data.extend(result["data"])
            merged["data"] = all_data
        
        return merged
    
    def get_similarity(self, text1: str, text2: str) -> float:
        """
        计算两段文本的相似度
        
        Args:
            text1: 第一段文本
            text2: 第二段文本
            
        Returns:
            相似度分数 (0-1)
        """
        import numpy as np
        
        # 获取嵌入向量
        embeddings = self.get_embedding([text1, text2])
        
        if not embeddings.get("success", True):
            raise ValueError(f"获取嵌入向量失败: {embeddings.get('message', '未知错误')}")
        
        # 提取向量
        vectors = []
        if self.config.get("api_type") == "jina":
            if "data" in embeddings:
                for item in embeddings["data"]:
                    if "embedding" in item:
                        vectors.append(item["embedding"])
        elif self.config.get("api_type") == "openai":
            if "data" in embeddings:
                for batch in embeddings["data"]:
                    if "data" in batch and len(batch["data"]) > 0:
                        if "embedding" in batch["data"][0]:
                            vectors.append(batch["data"][0]["embedding"])
        
        if len(vectors) != 2:
            raise ValueError("无法获取两段文本的有效嵌入向量")
        
        # 计算余弦相似度
        vec1 = np.array(vectors[0])
        vec2 = np.array(vectors[1])
        
        # 归一化向量
        vec1 = vec1 / np.linalg.norm(vec1)
        vec2 = vec2 / np.linalg.norm(vec2)
        
        # 计算余弦相似度
        similarity = np.dot(vec1, vec2)
        
        return float(similarity) 