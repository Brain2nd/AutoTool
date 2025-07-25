import pathlib
import json
import base64
import os
from typing import Dict, Any, Optional, List
from openai import OpenAI

# 获取配置文件和模板文件的路径
current_dir = pathlib.Path(__file__).parent
config_dir = current_dir / "config"
template_dir = current_dir / "template"
map_dir = current_dir / "map"


class QwenTool:
    """千问多模态工具类，提供与千问模型的对话接口"""
    
    def __init__(self, config_name: str = "default"):
        """
        初始化千问工具
        
        Args:
            config_name: 配置文件名，不含扩展名，默认为default
        """
        # 确保配置目录和模板目录存在
        config_dir.mkdir(exist_ok=True, parents=True)
        template_dir.mkdir(exist_ok=True, parents=True)
        map_dir.mkdir(exist_ok=True, parents=True)
        
        # 加载配置
        self.config = self._load_config(config_name)
        self.client = self._init_client()
        self.template_cache = {}  # 模板缓存
        self.template_map = self._load_template_map()  # 加载模板映射
    
    def _load_template_map(self) -> Dict[str, str]:
        """
        加载模板映射关系
        
        Returns:
            模板映射字典
        """
        map_path = map_dir / "map.json"
        
        # 检查映射文件是否存在
        if not map_path.exists():
            # 如果不存在，创建空映射
            empty_map = {}
            
            # 写入空映射
            with open(map_path, "w", encoding="utf-8") as f:
                json.dump(empty_map, f, ensure_ascii=False, indent=2)
                
            return empty_map
        
        # 读取映射文件
        with open(map_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
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
                "api_key": "",
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "model": "qvq-max",
                "temperature": 0.7,
                "max_tokens": 1000,
                "default_template": "default"
            }
            
            # 写入默认配置
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
                
            return default_config
        
        # 读取配置文件
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def _init_client(self) -> OpenAI:
        """
        初始化OpenAI客户端
        
        Returns:
            OpenAI客户端实例
        """
        return OpenAI(
            api_key=self.config.get("api_key"),
            base_url=self.config.get("base_url")
        )
    
    #  base 64 编码格式
    def encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
    
    def _get_mapped_template(self, template_name: str) -> str:
        """
        根据模板名称获取映射后的模板名称
        
        Args:
            template_name: 原始模板名称
            
        Returns:
            映射后的模板名称
        """
        # 检查是否存在映射关系
        if template_name in self.template_map:
            return self.template_map[template_name]
        return template_name
    
    def _load_template(self, template_name: str) -> str:
        """
        加载提示词模板
        
        Args:
            template_name: 模板名称，不含扩展名
            
        Returns:
            模板内容字符串
        """
        # 如果模板已缓存，直接返回
        if template_name in self.template_cache:
            return self.template_cache[template_name]
        
        template_path = template_dir / f"{template_name}.txt"
        
        # 检查模板文件是否存在
        if not template_path.exists():
            # 如果不存在，创建默认模板
            default_template = "你是一个智能助手，请根据用户的问题提供专业、准确的回答。"
            
            # 写入默认模板
            with open(template_path, "w", encoding="utf-8") as f:
                f.write(default_template)
                
            self.template_cache[template_name] = default_template
            return default_template
        
        # 读取模板文件
        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()
            
        # 缓存模板
        self.template_cache[template_name] = template_content
        return template_content
        
    def chat(self, prompt: str, template_name: Optional[str] = None, 
             image_path: Optional[str] = None, stream: bool = False) -> Dict[str, Any]:
        """
        与千问模型进行对话
        
        Args:
            prompt: 用户输入的提示词
            template_name: 使用的模板名称，不提供则使用配置中的默认模板
            image_path: 图片路径，如果提供则进行多模态对话
            stream: 是否使用流式输出
            
        Returns:
            对话结果字典
        """
        # 确定使用的模板
        if template_name is None:
            template_name = self.config.get("default_template", "default")
        else:
            # 检查是否有模板映射
            template_name = self._get_mapped_template(template_name)
        
        # 加载模板
        template = self._load_template(template_name)
        
        # 构建消息内容
        content = []
        
        # 如果有图片，添加图片内容
        if image_path and os.path.exists(image_path):
            base64_image = self.encode_image(image_path)
            # 根据图片扩展名确定MIME类型
            ext = os.path.splitext(image_path)[1].lower()
            mime_type = "jpeg" if ext == ".jpg" else ext[1:]  # 去掉点号
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/{mime_type};base64,{base64_image}"}
            })
        
        # 添加文本内容
        content.append({
            "type": "text",
            "text": f"{template}\n{prompt}"
        })
        
        # 构建请求参数
        params = {
            "model": self.config.get("model", "qvq-max"),
            "messages": [{"role": "user", "content": content}],
            "stream": stream
        }
        
        # 添加可选参数
        if "temperature" in self.config:
            params["temperature"] = self.config["temperature"]
        if "max_tokens" in self.config:
            params["max_tokens"] = self.config["max_tokens"]
        
        try:
            # 发送请求
            response = self.client.chat.completions.create(**params)
            
            # 处理流式响应
            if stream:
                return {"success": True, "response": response}
            
            # 处理非流式响应
            return {
                "success": True,
                "content": response.choices[0].message.content,
                "usage": response.usage.to_dict() if hasattr(response, "usage") else None
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def process_stream(self, stream_response):
        """
        处理流式响应
        
        Args:
            stream_response: 流式响应对象
            
        Returns:
            生成器，产生每个响应块
        """
        reasoning_content = ""
        answer_content = ""
        is_answering = False
        
        for chunk in stream_response:
            # 如果chunk.choices为空，可能是usage信息
            if not chunk.choices:
                if hasattr(chunk, "usage"):
                    yield {"type": "usage", "data": chunk.usage.to_dict()}
                continue
            
            delta = chunk.choices[0].delta
            
            # 处理思考过程
            if hasattr(delta, "reasoning_content") and delta.reasoning_content is not None:
                reasoning_content += delta.reasoning_content
                yield {"type": "reasoning", "data": delta.reasoning_content}
            # 处理回答内容
            elif hasattr(delta, "content") and delta.content is not None:
                # 标记开始回答
                if not is_answering and delta.content:
                    is_answering = True
                    yield {"type": "answer_start"}
                
                answer_content += delta.content
                yield {"type": "answer", "data": delta.content}
        
        # 返回完整内容
        yield {"type": "complete", "reasoning": reasoning_content, "answer": answer_content}


# 测试代码
if __name__ == "__main__":
    # 初始化千问工具
    qwen = QwenTool()
    reasoning_content = ""  # 定义完整思考过程
    answer_content = ""     # 定义完整回复
    is_answering = False   # 判断是否结束思考过程并开始回复
    input_text = input("请输入你的问题：")
    
    # 获取模板类型
    template_input = input("请输入模板类型（直接回车使用默认）：")
    template_name = template_input.strip() if template_input.strip() else None
    
    completion = qwen.chat(input_text, template_name=template_name, image_path=r"C:\Users\NUC\Desktop\AutoOOIN\screenshot_page0_1744968311.png", stream=True)
    
    if completion["success"]:
        stream_response = completion["response"]
        for chunk in qwen.process_stream(stream_response):
            if chunk["type"] == "reasoning":
                print(chunk["data"], end="", flush=True)
                reasoning_content += chunk["data"]
            elif chunk["type"] == "answer":
                print(chunk["data"], end="", flush=True)
                answer_content += chunk["data"]
            elif chunk["type"] == "answer_start":
                is_answering = True
            elif chunk["type"] == "complete":
                print("\n" + "=" * 20 + "思考过程" + "=" * 20 + "\n")       
