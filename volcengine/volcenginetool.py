import os
import json
import pathlib
# 通过 pip install "volcengine-python-sdk[ark]" 安装方舟SDK
from volcenginesdkarkruntime import Ark

class VolcengineTool:
    def __init__(self, config_name="default"):
        # 获取当前文件所在目录
        current_dir = pathlib.Path(__file__).parent
        
        # 读取配置文件
        config_path = current_dir / "config" / f"{config_name}.json"
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        # 从环境变量中获取API KEY，配置方法见：https://www.volcengine.com/docs/82379/1399008
        self.api_key = config.get("api_kep", "")
        self.model = config.get("model", "doubao-1.5-pro-32k")
        
        # 模板目录
        self.template_dir = current_dir / "template"
        
        # 初始化Ark客户端
        self.client = Ark(api_key=self.api_key)
    
    def load_template(self, template_name):
        """加载模板文件内容"""
        template_path = self.template_dir / f"{template_name}.txt"
        if template_path.exists():
            with open(template_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""
    
    def chat(self, content, template_name=None):
        """创建一个对话请求"""
        message_content = content
        
        # 如果指定了模板，则加载模板内容并拼接
        if template_name:
            template_content = self.load_template(template_name)
            if template_content:
                message_content = template_content + "\n" + content
        
        # 创建对话请求
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "user", "content": message_content},
            ],
        )
        
        return completion.choices[0].message.content

# 使用示例
if __name__ == "__main__":
    tool = VolcengineTool()
    response = tool.chat(input('请输入：'),"星职盟评论回复")
    print(response)