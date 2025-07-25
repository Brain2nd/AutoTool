#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
豆包配置测试脚本

测试豆包（火山方舟）API配置是否正确工作
"""

import asyncio
import os
import sys
import pathlib

# 添加项目根目录到Python路径
current_dir = pathlib.Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

from ..chatdoubao.postgreschattool import PostgresChatTool


async def test_doubao_config():
    """测试豆包配置"""
    print("=" * 50)
    print("豆包配置测试")
    print("=" * 50)
    
    try:
        # 1. 加载豆包配置
        print("1. 加载豆包配置...")
        chat_tool = PostgresChatTool()
        config = chat_tool._load_config("doubao")
        
        print(f"配置加载成功:")
        print(f"  - 配置名称: {config.get('name')}")
        print(f"  - API类型: {config.get('api_type')}")
        print(f"  - 基础URL: {config.get('base_url')}")
        print(f"  - 模型: {config.get('model', '未设置')}")
        print(f"  - API Key: {'已设置' if config.get('api_key') else '未设置'}")
        
        # 2. 检查环境变量
        print("\\n2. 检查环境变量...")
        ark_api_key = os.environ.get("ARK_API_KEY")
        if ark_api_key:
            print(f"  - ARK_API_KEY: 已设置 (长度: {len(ark_api_key)})")
        else:
            print("  - ARK_API_KEY: 未设置")
            print("  - 提示: 请设置环境变量 ARK_API_KEY")
        
        # 3. 初始化聊天工具
        print("\\n3. 初始化聊天工具...")
        chat_tool_doubao = PostgresChatTool(config=config)
        
        # 模拟初始化API客户端（不连接数据库）
        await chat_tool_doubao._init_client()
        
        print("  - API客户端初始化成功")
        print(f"  - 客户端类型: {type(chat_tool_doubao.client)}")
        
        # 4. 检查配置兼容性
        print("\\n4. 检查配置兼容性...")
        
        # 检查必要的配置项
        required_configs = ["api_type", "base_url"]
        missing_configs = []
        
        for key in required_configs:
            if not config.get(key):
                missing_configs.append(key)
        
        if missing_configs:
            print(f"  - 缺少配置项: {missing_configs}")
        else:
            print("  - 所有必要配置项都已设置")
        
        # 5. 配置验证结果
        print("\\n5. 配置验证结果:")
        
        api_key_available = bool(config.get("api_key") or ark_api_key)
        model_set = bool(config.get("model"))
        
        print(f"  - API Key可用: {'✓' if api_key_available else '✗'}")
        print(f"  - 模型已设置: {'✓' if model_set else '✗'}")
        print(f"  - 基础URL正确: {'✓' if 'ark.cn-beijing.volces.com' in config.get('base_url', '') else '✗'}")
        
        # 6. 使用建议
        print("\\n6. 使用建议:")
        
        if not api_key_available:
            print("  - 请设置环境变量 ARK_API_KEY 或在配置文件中设置 api_key")
            print("  - 示例: export ARK_API_KEY='your-api-key-here'")
        
        if not model_set:
            print("  - 请在配置文件中设置具体的模型名称")
            print("  - 示例: \\\"model\\\": \\\"ep-20241001234567-abcde\\\"")
        
        print("\\n" + "=" * 50)
        
        if api_key_available and model_set:
            print("✓ 配置验证通过！可以开始使用豆包API")
        else:
            print("✗ 配置不完整，请根据建议进行设置")
            
        print("=" * 50)
        
    except Exception as e:
        print(f"配置测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_doubao_config())