import pathlib
import sys
import os
import asyncio


current_dir = pathlib.Path(__file__).parent
project_root = current_dir.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

# 导入聊天工具类
from ...chat.postgreschattool import PostgresChatTool

# 获取模板目录
template_dir = os.path.join(project_root, 'tool', 'chat', 'template')

import re
import json
    

def analysis_resume(image_path, position_name=None):
    """
    分析简历图片并返回结构化结果
    
    Args:
        image_path: 简历图片路径
        position_name: 职位名称，用于选择对应的模板
        
    Returns:
        dict: 包含分析结果的字典
    """
    
    # 创建异步运行函数
    async def _async_analysis():
        # 初始化聊天工具
        chat_tool = PostgresChatTool(use_cache=False)  # 不使用缓存，每次都是新的分析
        
        try:
            # 初始化工具
            initialized = await chat_tool.initialize()
            if not initialized:
                return {"level": "D", "name": "未知", "reason": "聊天工具初始化失败"}
            
            # 设置会话
            session_name = f"简历分析_{os.path.basename(image_path)}_{int(asyncio.get_event_loop().time())}"
            await chat_tool.set_session(session_name)
            
            # 从配置文件读取职位名称到模板的映射
            map_file_path = os.path.join(project_root, 'tool', 'chat', 'map', 'map.json')
            position_template_map = {}
            
            try:
                if os.path.exists(map_file_path):
                    with open(map_file_path, 'r', encoding='utf-8') as f:
                        position_template_map = json.load(f)
                    print(f"成功加载职位映射配置，共 {len(position_template_map)} 个映射")
                else:
                    print(f"警告：映射配置文件不存在: {map_file_path}")
            except Exception as e:
                print(f"加载映射配置文件失败: {str(e)}")
            
            # 根据职位名称选择模板
            if position_name and position_name in position_template_map:
                template_to_use = position_template_map[position_name]
                print(f"职位 '{position_name}' 映射到模板: {template_to_use}")
            else:
                # 默认使用 hr 模板
                template_to_use = "hr"
                if position_name:
                    print(f"职位 '{position_name}' 没有映射，使用默认模板: {template_to_use}")
                else:
                    print(f"未指定职位，使用默认模板: {template_to_use}")
            
            # 检查模板是否存在
            template_path = os.path.join(template_dir, f"{template_to_use}.txt")
            if not os.path.exists(template_path):
                print(f"模板 '{template_to_use}' 不存在，将使用默认的'hr'模板")
                template_to_use = "hr"
            
            print(f"最终使用模板: {template_to_use}")
            
            # 使用多模态功能分析图片
            prompt = "请分析这份简历，并按照模板要求返回JSON格式的评估结果。"
            
            # 调用聊天工具的图片分析功能
            response = await chat_tool.chat_with_image(
                user_message=prompt,
                image_path=image_path,
                template_name=template_to_use,
                save_to_db=False,  # 不保存到数据库
                use_cache=False    # 不使用缓存
            )
            
            # 打印回答内容，用于调试
            print('===============')
            print(f"模型回答内容: {response}")
            print('===============')
            
            # 尝试从回答中提取JSON对象
            try:
                # 方法1: 尝试查找被```json和```包裹的JSON块
                json_blocks = re.findall(r'```(?:json)?\s*(.*?)\s*```', response, re.DOTALL)
                for block in json_blocks:
                    try:
                        # 尝试解析每个找到的块
                        result_json = json.loads(block)
                        if all(key in result_json for key in ["level", "name", "reason"]):
                            return {
                                "level": result_json.get("level", "D"),
                                "name": result_json.get("name", "未知"),
                                "reason": result_json.get("reason", "未提供原因")
                            }
                    except json.JSONDecodeError:
                        continue
                
                # 方法2: 尝试直接查找JSON对象格式的字符串
                json_patterns = [
                    # 标准格式，双引号
                    r'\{\s*"level"\s*:\s*"([A-D])"\s*,\s*"name"\s*:\s*"([^"]*)"\s*,\s*"reason"\s*:\s*"([^"]*)"\s*\}',
                    # 使用单引号的格式
                    r'\{\s*\'level\'\s*:\s*\'([A-D])\'\s*,\s*\'name\'\s*:\s*\'([^\']*)\'\s*,\s*\'reason\'\s*:\s*\'([^\']*)\'\s*\}',
                    # 混合引号格式
                    r'\{\s*[\'"]level[\'"]\s*:\s*[\'"]([A-D])[\'"]\s*,\s*[\'"]name[\'"]\s*:\s*[\'"]([^\'"]*)[\'"]'
                    r'\s*,\s*[\'"]reason[\'"]\s*:\s*[\'"]([^\'"]*)[\'"].*?\}'
                ]
                
                for pattern in json_patterns:
                    match = re.search(pattern, response, re.DOTALL)
                    if match:
                        if len(match.groups()) == 3:
                            # 如果正则表达式捕获了三个组，直接使用它们
                            return {
                                "level": match.group(1),
                                "name": match.group(2),
                                "reason": match.group(3)
                            }
                        else:
                            # 否则尝试解析整个匹配的字符串
                            json_str = match.group().replace("'", '"')
                            try:
                                result_json = json.loads(json_str)
                                return {
                                    "level": result_json.get("level", "D"),
                                    "name": result_json.get("name", "未知"),
                                    "reason": result_json.get("reason", "未提供原因")
                                }
                            except json.JSONDecodeError:
                                continue
                
                # 方法3: 尝试单独提取每个字段
                level_match = re.search(r'[\'"]level[\'"]\s*:\s*[\'"]([A-D])[\'"]', response)
                name_match = re.search(r'[\'"]name[\'"]\s*:\s*[\'"]([^\'"]*)[\'"]', response)
                reason_match = re.search(r'[\'"]reason[\'"]\s*:\s*[\'"]([^\'"]*)[\'"]', response)
                
                if level_match and name_match and reason_match:
                    return {
                        "level": level_match.group(1),
                        "name": name_match.group(1),
                        "reason": reason_match.group(1)
                    }
                
                # 方法4: 最后尝试使用更宽松的匹配方式
                # 先找到包含level、name和reason的大括号块
                brace_pattern = r'\{[^{}]*level[^{}]*name[^{}]*reason[^{}]*\}'
                brace_match = re.search(brace_pattern, response, re.DOTALL)
                
                if brace_match:
                    # 提取键值对
                    json_str = brace_match.group()
                    # 规范化JSON字符串
                    json_str = re.sub(r'(["\'])(level|name|reason)(["\'])\s*:\s*', r'"\2":', json_str)
                    json_str = re.sub(r':\s*(["\'])(.*?)(["\'])', r':"\2"', json_str)
                    # 确保使用双引号
                    json_str = json_str.replace("'", '"')
                    
                    try:
                        result_json = json.loads(json_str)
                        return {
                            "level": result_json.get("level", "D"),
                            "name": result_json.get("name", "未知"),
                            "reason": result_json.get("reason", "未提供原因")
                        }
                    except json.JSONDecodeError:
                        pass
                
                return {"level": "D", "name": "未知", "reason": "未找到符合格式的JSON响应"}
            except Exception as e:
                return {"level": "D", "name": "未知", "reason": f"解析响应时出错: {str(e)}"}
                
        except Exception as e:
            return {"level": "D", "name": "未知", "reason": f"分析过程出错: {str(e)}"}
        finally:
            # 关闭连接
            await chat_tool.close()
    
    # 运行异步函数
    try:
        # 获取或创建事件循环
        try:
            loop = asyncio.get_running_loop()
            # 如果已经在事件循环中，创建任务并等待
            task = loop.create_task(_async_analysis())
            return loop.run_until_complete(task)
        except RuntimeError:
            # 如果没有运行的事件循环，创建新的
            return asyncio.run(_async_analysis())
    except Exception as e:
        return {"level": "D", "name": "未知", "reason": f"运行异步分析时出错: {str(e)}"}