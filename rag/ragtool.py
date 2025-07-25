#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RAG工具模块

提供基于嵌入向量的文本检索和生成功能，支持不同的嵌入模型和API提供商
"""

import os
import json
import pathlib
import requests
import numpy as np
from typing import Dict, Any, Optional, List, Union, Tuple

# 获取配置文件的路径
current_dir = pathlib.Path(__file__).parent
config_dir = current_dir / "config"


class RAGTool:
    """RAG工具类，提供统一的嵌入向量生成和相似度计算接口"""
    
    def __init__(self, config_name: str = "default"):
        """
        初始化RAG工具
        
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
                "api_key": "",  # 需要用户设置
                "base_url": "https://api.jina.ai/v1/embeddings",
                "model": "jina-embeddings-v3",
                "task": "text-matching",
                "dimensions": 512,  # 嵌入向量的默认维度
                "cache_dir": str(current_dir / "cache")  # 缓存目录
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
    
    def get_embeddings(self, texts: Union[str, List[str]], model: Optional[str] = None, 
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
            return self._get_jina_embeddings(texts, model_name, task_type)
        elif api_type == "openai":
            return self._get_openai_embeddings(texts, model_name)
        else:
            return {
                "success": False,
                "message": f"不支持的API类型: {api_type}"
            }
    
    def _get_jina_embeddings(self, texts: List[str], model: str, task: str) -> Dict[str, Any]:
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
            return {
                "success": False,
                "message": "缺少Jina API密钥，请在配置中设置api_key"
            }
        
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
            
            result = response.json()
            # 添加成功标志和相关信息
            result["success"] = True
            result["message"] = f"成功获取 {len(texts)} 个文本的嵌入向量"
            
            return result
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": str(e),
                "message": "获取嵌入向量失败"
            }
    
    def _get_openai_embeddings(self, texts: List[str], model: str) -> Dict[str, Any]:
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
            return {
                "success": False,
                "message": "缺少OpenAI API密钥，请在配置中设置api_key"
            }
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        
        # OpenAI API支持批量处理
        data = {
            'model': model,
            'input': texts
        }
        
        try:
            response = requests.post(url, json=data, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            # 添加成功标志和相关信息
            return {
                "success": True,
                "message": f"成功获取 {len(texts)} 个文本的嵌入向量",
                "model": model,
                "data": result.get("data", []),
                "usage": result.get("usage", {})
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": str(e),
                "message": "获取嵌入向量失败"
            }
    
    def calculate_similarity(self, text1: str, text2: str) -> Dict[str, Any]:
        """
        计算两段文本的相似度
        
        Args:
            text1: 第一段文本
            text2: 第二段文本
            
        Returns:
            相似度计算结果
        """
        # 获取文本的嵌入向量
        embeddings_result = self.get_embeddings([text1, text2])
        
        if not embeddings_result.get("success", False):
            return {
                "success": False,
                "message": embeddings_result.get("message", "获取嵌入向量失败")
            }
        
        # 提取嵌入向量
        embeddings = []
        
        if self.config.get("api_type") == "jina":
            # Jina API
            for item in embeddings_result.get("data", []):
                if "embedding" in item:
                    embeddings.append(item["embedding"])
        elif self.config.get("api_type") == "openai":
            # OpenAI API
            for item in embeddings_result.get("data", []):
                if "embedding" in item:
                    embeddings.append(item["embedding"])
        
        if len(embeddings) != 2:
            return {
                "success": False,
                "message": "无法获取两段文本的有效嵌入向量"
            }
        
        # 计算余弦相似度
        try:
            vec1 = np.array(embeddings[0])
            vec2 = np.array(embeddings[1])
            
            # 归一化向量
            vec1 = vec1 / np.linalg.norm(vec1)
            vec2 = vec2 / np.linalg.norm(vec2)
            
            # 计算余弦相似度
            similarity = np.dot(vec1, vec2)
            
            return {
                "success": True,
                "message": "成功计算文本相似度",
                "similarity": float(similarity),
                "text1": text1,
                "text2": text2
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"计算相似度时出错: {str(e)}"
            }
    
    def calculate_similarities(self, query: str, texts: List[str]) -> Dict[str, Any]:
        """
        计算查询文本与多个文本的相似度
        
        Args:
            query: 查询文本
            texts: 待比较的文本列表
            
        Returns:
            包含多个相似度计算结果的字典
        """
        # 构建输入文本列表
        all_texts = [query] + texts
        
        # 获取所有文本的嵌入向量
        embeddings_result = self.get_embeddings(all_texts)
        
        if not embeddings_result.get("success", False):
            return {
                "success": False,
                "message": embeddings_result.get("message", "获取嵌入向量失败")
            }
        
        # 提取嵌入向量
        embeddings = []
        
        if self.config.get("api_type") == "jina":
            # Jina API
            for item in embeddings_result.get("data", []):
                if "embedding" in item:
                    embeddings.append(item["embedding"])
        elif self.config.get("api_type") == "openai":
            # OpenAI API
            for item in embeddings_result.get("data", []):
                if "embedding" in item:
                    embeddings.append(item["embedding"])
        
        if len(embeddings) != len(all_texts):
            return {
                "success": False,
                "message": "嵌入向量数量与文本数量不匹配"
            }
        
        # 计算查询向量与其他向量的余弦相似度
        try:
            query_vec = np.array(embeddings[0])
            query_vec = query_vec / np.linalg.norm(query_vec)
            
            similarities = []
            
            for i, embedding in enumerate(embeddings[1:], 1):
                vec = np.array(embedding)
                vec = vec / np.linalg.norm(vec)
                
                # 计算余弦相似度
                similarity = np.dot(query_vec, vec)
                
                similarities.append({
                    "index": i - 1,  # 索引从0开始
                    "text": texts[i - 1],
                    "similarity": float(similarity)
                })
            
            # 按相似度排序
            similarities.sort(key=lambda x: x["similarity"], reverse=True)
            
            return {
                "success": True,
                "message": f"成功计算 {len(texts)} 个文本与查询的相似度",
                "query": query,
                "results": similarities
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"计算相似度时出错: {str(e)}"
            }
    
    def find_similar_elements(self, description: str, elements: List[Dict[str, Any]], 
                             threshold: float = 0.3, max_results: int = 10) -> Dict[str, Any]:
        """
        在DOM元素列表中查找与描述相似的元素
        
        Args:
            description: 功能描述
            elements: 元素列表，每个元素应包含text字段
            threshold: 相似度阈值，默认0.3
            max_results: 最大返回结果数，默认10
            
        Returns:
            相似元素列表，按相似度排序
        """
        if not elements:
            return {
                "success": False,
                "message": "元素列表为空"
            }
        
        # 提取所有元素的文本内容
        element_texts = []
        for element in elements:
            # 获取元素的文本内容
            element_text = element.get('text', '')
            
            # 提取可能包含功能描述的属性
            attributes = element.get('attributes', {})
            alt_text = attributes.get('alt', '')
            aria_label = attributes.get('aria-label', '')
            title = attributes.get('title', '')
            placeholder = attributes.get('placeholder', '')
            
            # 合并所有文本属性
            combined_text = ' '.join(filter(None, [element_text, alt_text, aria_label, title, placeholder]))
            
            # 如果是链接，也包含href
            if 'href' in element and element['href']:
                combined_text += ' ' + element['href']
            
            element_texts.append(combined_text if combined_text else "[无文本内容]")
        
        # 计算相似度
        similarity_result = self.calculate_similarities(description, element_texts)
        
        if not similarity_result.get("success", False):
            return {
                "success": False,
                "message": similarity_result.get("message", "计算相似度失败")
            }
        
        # 筛选超过阈值的结果
        filtered_results = []
        for res in similarity_result["results"]:
            if res["similarity"] >= threshold:
                # 添加元素信息
                element_with_similarity = elements[res["index"]].copy()
                element_with_similarity["similarity"] = res["similarity"]
                filtered_results.append(element_with_similarity)
        
        # 截取前max_results个结果
        top_results = filtered_results[:max_results]
        
        return {
            "success": True,
            "message": f"找到 {len(top_results)} 个与 '{description}' 相似的元素",
            "description": description,
            "matches": top_results,
            "count": len(top_results)
        }
    
    def save_config(self, config_name: str, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        保存配置
        
        Args:
            config_name: 配置名称
            config_data: 配置数据
            
        Returns:
            保存结果
        """
        config_path = config_dir / f"{config_name}.json"
        
        # 确保目录存在
        config_dir.mkdir(exist_ok=True, parents=True)
        
        try:
            # 写入配置
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            # 更新当前配置
            if config_name == "default":
                self.config = config_data
                
            return {
                "success": True,
                "message": f"成功保存配置 '{config_name}'"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"保存配置失败: {str(e)}"
            }
    
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
            "dimensions": self.config.get("dimensions", 512),
            "api_base_url": self.config.get("base_url", "https://api.jina.ai/v1/embeddings")
        }
    
    def set_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        设置RAG工具配置
        
        Args:
            config_data: 配置数据字典
            
        Returns:
            配置结果
        """
        try:
            # 验证必要的配置项
            required_keys = ["api_type", "api_key", "model"]
            missing_keys = [key for key in required_keys if key not in config_data]
            
            if missing_keys:
                return {
                    "success": False,
                    "message": f"缺少必要的配置项: {', '.join(missing_keys)}"
                }
            
            # 更新配置
            self.config.update(config_data)
            
            return {
                "success": True,
                "message": "成功更新配置"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"设置配置失败: {str(e)}"
            } 