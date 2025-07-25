"""
Poe Web Chat Tool - 基于上下文管理器的设计
连接到现有浏览器，每个页面上下文对象管理独立的对话历史
"""

import os
import time
import json
from typing import Dict, Optional, List
from datetime import datetime
from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext

class PoeChatAPI:
    """Poe 网页聊天主API - 浏览器连接和页面上下文管理"""
    
    def __init__(self, cdp_port: int = 9222):
        self.playwright = None
        self.browser = None
        self.context = None
        self.cdp_port = cdp_port
        self.poe_url = "https://poe.com/"
        self._page_contexts = []  # 维护所有创建的页面上下文
        
    def __del__(self):
        """销毁时关闭所有页面上下文"""
        try:
            print(f"🧹 正在清理API对象，共有 {len(self._page_contexts)} 个页面上下文")
            # 销毁所有页面上下文
            for context in self._page_contexts[:]:  # 复制列表避免修改冲突
                context.destroy()
            self.disconnect()
            print("🧹 API对象清理完成")
        except Exception as e:
            print(f"⚠️  API对象清理时出错: {str(e)}")
        
    def connect(self) -> bool:
        """连接到现有浏览器"""
        try:
            self.playwright = sync_playwright().start()
            cdp_url = f"http://localhost:{self.cdp_port}"
            self.browser = self.playwright.chromium.connect_over_cdp(cdp_url)
            
            contexts = self.browser.contexts
            if contexts:
                self.context = contexts[0]
                return True
            else:
                return False
        except Exception:
            return False
            
    def disconnect(self):
        """断开连接"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
            
    def list_pages(self, include_title: bool = False) -> List[Dict]:
        """获取所有页面信息"""
        if not self.context:
            return []
            
        pages_info = []
        for i, page in enumerate(self.context.pages):
            try:
                url = page.url
                is_poe = "poe.com" in url
                
                page_info = {
                    "index": i,
                    "url": url,
                    "is_poe": is_poe
                }
                
                # 只在需要时获取标题（会很慢）
                if include_title:
                    try:
                        page_info["title"] = page.title()
                    except:
                        page_info["title"] = "Unknown"
                        
                pages_info.append(page_info)
                
            except Exception:
                pages_info.append({
                    "index": i,
                    "url": "Error loading",
                    "is_poe": False,
                    "title": "Error" if include_title else None
                })
        return pages_info
        
    def new_page(self, model_name: str = "Claude-3.5-Sonnet") -> 'PoePageContext':
        """创建新的Poe页面，返回页面上下文对象"""
        if not self.context:
            raise RuntimeError("未连接到浏览器")
            
        try:
            # 创建新标签页
            new_page = self.context.new_page()
            
            # 导航到Poe
            new_page.goto(self.poe_url, timeout=30000)
            
            # 等待页面加载并选择模型
            self._wait_for_page_ready_and_select_model(new_page, model_name)
            
            # 获取页面索引
            pages = self.context.pages
            page_index = pages.index(new_page)
            
            # 创建页面上下文对象
            page_context = PoePageContext(self, page_index, is_new_page=True)
            self._register_context(page_context)
            
            return page_context
            
        except Exception as e:
            raise RuntimeError(f"创建页面失败: {str(e)}")
            
    def page(self, page_index: int) -> 'PoePageContext':
        """获取现有页面的上下文对象"""
        if not self.context:
            raise RuntimeError("未连接到浏览器")
            
        pages = self.context.pages
        if page_index >= len(pages):
            raise IndexError("页面索引无效")
            
        # 创建页面上下文对象
        page_context = PoePageContext(self, page_index, is_new_page=False)
        self._register_context(page_context)
        
        return page_context
        
    def _register_context(self, context: 'GeminiPageContext'):
        """注册页面上下文"""
        self._page_contexts.append(context)
        
    def _unregister_context(self, context: 'GeminiPageContext'):
        """注销页面上下文"""
        if context in self._page_contexts:
            self._page_contexts.remove(context)
            
    # Poe网站的页面准备和模型选择逻辑
    def _wait_for_page_ready_and_select_model(self, page: Page, model_name: str, timeout: int = 60) -> bool:
        """等待页面加载完成并选择指定模型"""
        print(f"⏳ 等待页面加载并选择模型: {model_name}")
        
        start_time = time.time()
        
        # 第1步：等待并点击模型选择按钮
        while time.time() - start_time < timeout:
            try:
                # 查找模型选择按钮
                model_button = page.query_selector('.button_root__TL8nv.button_ghost__YsMI5.button_sm__hWzjK.button_center__RsQ_o.button_showIconOnly-always__05Gb5')
                if model_button and model_button.is_visible():
                    print("✅ 找到模型选择按钮，点击中...")
                    model_button.click()
                    break
            except:
                pass
            time.sleep(1)
        else:
            print("❌ 未找到模型选择按钮")
            return False
            
        # 第2步：等待搜索框出现并输入模型名称
        time.sleep(2)  # 等待页面切换
        while time.time() - start_time < timeout:
            try:
                search_input = page.query_selector('.SearchBar_input__somiR')
                if search_input and search_input.is_visible():
                    print(f"✅ 找到搜索框，输入模型名称: {model_name}")
                    search_input.fill(model_name)
                    time.sleep(1)  # 等待搜索结果
                    break
            except:
                pass
            time.sleep(1)
        else:
            print("❌ 未找到搜索框")
            return False
            
        # 第3步：选择匹配的模型
        while time.time() - start_time < timeout:
            try:
                # 查找所有模型选项
                bot_items = page.query_selector_all('[class*="BotListItem_botName"]')
                for item in bot_items:
                    if item.is_visible():
                        item_text = item.inner_text().strip()
                        if item_text == model_name:
                            print(f"✅ 找到匹配的模型: {item_text}，选择中...")
                            item.click()
                            time.sleep(3)  # 等待模型加载
                            return True
            except:
                pass
            time.sleep(1)
        
        print(f"❌ 未找到匹配的模型: {model_name}")
        return False


class PoePageContext:
    """Poe页面上下文管理器 - 独立的对话历史和生命周期"""
    
    def __init__(self, api: PoeChatAPI, page_index: int, is_new_page: bool = False):
        self.api = api
        self.page_index = page_index
        self.is_new_page = is_new_page
        self._chat_history = []  # 纯内存存储，销毁即删除
        self._destroyed = False
        
        # 保存页面对象引用，避免索引变化问题
        if self.api.context and page_index < len(self.api.context.pages):
            self._page_obj = self.api.context.pages[page_index]
        else:
            self._page_obj = None
        
        # Poe的停止按钮选择器（判断回复结束）
        self.stop_button_selector = '.Button_buttonBase__Bv9Vx.Button_tertiary__KEQm1.ChatStopMessageButton_stopButton__QOW41.ChatFooterHoveringButtonSection_center__KuhMd'
        
    def __del__(self):
        """销毁时关闭页面并删除JSON文件"""
        self.destroy()
        
    def __enter__(self):
        """上下文管理器入口"""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口 - 销毁上下文对象（关闭页面）"""
        self.destroy()
        
    def destroy(self):
        """手动销毁 - 关闭页面并清除内存历史"""
        if self._destroyed:
            return
            
        try:
            # 关闭页面（仅对新创建的页面）
            if self.is_new_page and self._page_obj:
                try:
                    self._page_obj.close()
                    print(f"🗑️  页面 {self.page_index} 已关闭")
                except Exception as e:
                    print(f"⚠️  关闭页面 {self.page_index} 时出错: {str(e)}")
                    
            # 清除内存中的对话历史
            self._chat_history.clear()
                
            # 从API中注销
            self.api._unregister_context(self)
            
        except Exception as e:
            print(f"⚠️  销毁页面上下文时出错: {str(e)}")
        finally:
            self._destroyed = True
            self._page_obj = None  # 清除页面对象引用
            
    def chat(self, message: str, max_retries: int = 3) -> str:
        """发送消息并获取回复，失败时重试整个流程"""
        if self._destroyed:
            raise RuntimeError("页面上下文已销毁")
            
        if not self.api.context:
            raise RuntimeError("浏览器连接已断开")
        
        if not self._page_obj:
            raise RuntimeError("页面对象无效")
            
        page = self._page_obj
        last_error = None
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    print(f"🔄 重试整个对话流程 {attempt}/{max_retries-1}...")
                    time.sleep(3)  # 等待页面稳定
                
                # 记录用户消息到历史（只在第一次尝试时记录）
                if attempt == 0:
                    user_record = {
                        "timestamp": datetime.now().isoformat(),
                        "type": "user",
                        "message": message
                    }
                    self._chat_history.append(user_record)
                
                # 发送消息
                if not self._send_message_to_page(page, message):
                    raise RuntimeError("发送消息失败")
                    
                # 等待响应
                if not self._wait_for_response(page):
                    raise RuntimeError("等待响应失败")
                    
                # 获取回复，最多重试5次
                response = None
                for retry in range(5):
                    response = self._get_response_from_page(page)
                    if response and len(response.strip()) > 10:  # 确保回复有实际内容
                        break
                    print(f"⏳ 正在获取回复内容，重试 {retry + 1}/5...")
                    time.sleep(2)
                    
                if not response:
                    raise RuntimeError("获取回复失败，可能AI还在生成中")
                
                # 检查回复质量 - 避免只有时间戳或过短的回复
                if len(response.strip()) < 10:
                    raise RuntimeError(f"回复内容过短或无效: '{response.strip()}'")
                    
                # 记录AI回复到历史
                ai_record = {
                    "timestamp": datetime.now().isoformat(),
                    "type": "assistant",
                    "message": response
                }
                self._chat_history.append(ai_record)
                
                return response
                
            except Exception as e:
                last_error = e
                print(f"⚠️ 第{attempt+1}次对话尝试失败: {str(e)}")
                
                if attempt < max_retries - 1:
                    # 等待一段时间再重试
                    wait_time = (attempt + 1) * 3
                    print(f"⏳ 等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
        
        # 所有重试都失败，记录错误到历史
        error_record = {
            "timestamp": datetime.now().isoformat(),
            "type": "error",
            "message": f"发送消息'{message}'时出错，已重试{max_retries}次: {str(last_error)}"
        }
        self._chat_history.append(error_record)
        
        raise RuntimeError(f"对话失败，已重试{max_retries}次: {str(last_error)}")
            
    def get_chat_history(self) -> List[Dict]:
        """获取完整对话历史"""
        return self._chat_history.copy()
        
    def get_history_json(self) -> Dict:
        """获取对话历史的JSON格式"""
        return {
            "page_index": self.page_index,
            "chat_history": self._chat_history
        }
            
    def get_title(self) -> str:
        """获取页面标题"""
        if self._destroyed or not self._page_obj:
            return "Unknown"
            
        try:
            return self._page_obj.title()
        except:
            return "Unknown"
        
    def get_url(self) -> str:
        """获取页面URL"""
        if self._destroyed or not self._page_obj:
            return "Unknown"
            
        try:
            return self._page_obj.url
        except:
            return "Unknown"
        
    def is_active(self) -> bool:
        """检查页面是否仍然有效"""
        if self._destroyed or not self._page_obj:
            return False
            
        try:
            # 检查页面是否还在浏览器中
            return self._page_obj in self.api.context.pages if self.api.context else False
        except:
            return False
            
    def screenshot(self, path: str):
        """页面截图"""
        if self._destroyed or not self._page_obj:
            raise RuntimeError("页面上下文无效")
            
        try:
            self._page_obj.screenshot(path=path)
        except Exception as e:
            raise RuntimeError(f"截图失败: {str(e)}")
            


        
    # 保持所有已验证的核心业务逻辑方法不变
    def _send_message_to_page(self, page: Page, message: str) -> bool:
        """向页面发送消息"""
        try:
            # Poe的输入框选择器 - 尝试多种可能的选择器
            input_selectors = [
                'textarea[class*="GrowingTextArea"]',  # 包含GrowingTextArea的textarea
                'textarea[placeholder*=""]',  # 任何有placeholder的textarea
                'textarea',  # 通用textarea
                '.GrowingTextArea_textArea',  # 原始选择器作为备选
            ]
            
            input_element = None
            for selector in input_selectors:
                try:
                    element = page.query_selector(selector)
                    if element and element.is_visible():
                        input_element = element
                        print(f"✅ 找到输入框，使用选择器: {selector}")
                        break
                except:
                    continue
            
            if not input_element:
                print("❌ 未找到Poe输入框")
                # 调试信息：列出页面上所有textarea
                try:
                    all_textareas = page.query_selector_all('textarea')
                    print(f"🔍 页面上共有 {len(all_textareas)} 个textarea元素")
                    for i, ta in enumerate(all_textareas):
                        try:
                            class_attr = ta.get_attribute('class') or 'no-class'
                            placeholder = ta.get_attribute('placeholder') or 'no-placeholder'
                            is_visible = ta.is_visible()
                            print(f"  textarea[{i}]: class='{class_attr[:50]}', placeholder='{placeholder[:30]}', visible={is_visible}")
                        except:
                            print(f"  textarea[{i}]: 无法获取属性")
                except:
                    pass
                return False
                
            # 清空输入框并输入消息
            input_element.click()
            time.sleep(0.5)
            input_element.fill("")
            
            # 输入消息
            input_element.fill(message)
            
            # 按Enter发送（Poe使用Enter发送）
            input_element.press('Enter')
            return True
                
        except Exception as e:
            print(f"⚠️ 发送消息时出错: {str(e)}")
            return False
            
    def _wait_for_response(self, page: Page) -> bool:
        """等待响应完成 - 检测停止按钮的消失"""
        time.sleep(2)  # 等待AI开始生成
        print("⏳ 等待AI回复完成...")
        
        # 先等待停止按钮出现（说明AI开始回复）
        stop_button_appeared = False
        for _ in range(10):  # 最多等待10秒
            try:
                stop_button = page.query_selector(self.stop_button_selector)
                if stop_button and stop_button.is_visible():
                    print("✅ AI开始生成回复")
                    stop_button_appeared = True
                    break
            except:
                pass
            time.sleep(1)
        
        if not stop_button_appeared:
            print("⚠️ 未检测到AI开始生成，继续等待...")
        
        # 然后等待停止按钮消失（说明AI回复完成）
        while True:
            try:
                stop_button = page.query_selector(self.stop_button_selector)
                if not stop_button or not stop_button.is_visible():
                    print("✅ AI回复完成")
                    return True
            except:
                pass
            time.sleep(1)  # 每秒检查一次
        
    def _get_response_from_page(self, page: Page) -> Optional[str]:
        """从页面获取回复 - 区分think过程、最终回复和Related searches"""
        try:
            time.sleep(3)  # 等待DOM更新和渲染
            
            # 获取所有左侧消息气泡（AI回复）
            response_elements = page.query_selector_all('[class*="Message_leftSideMessageBubble"]')
            
            if response_elements:
                latest_response = response_elements[-1]
                
                # 方法1: 尝试通过DOM结构精确提取
                final_response = self._extract_final_response_from_dom(latest_response)
                if final_response:
                    # DOM提取后也需要清理时间戳
                    cleaned_response = self._clean_trailing_timestamp(final_response)
                    return cleaned_response
                
                # 方法2: 后备方案 - 通过文本内容过滤
                response_text = latest_response.inner_text().strip()
                if response_text:
                    return self._filter_response_text(response_text)
                    
            return None
            
        except Exception as e:
            print(f"⚠️ 获取回复时出错: {str(e)}")
            return None

    def _extract_final_response_from_dom(self, response_element) -> Optional[str]:
        """通过DOM结构精确提取最终回复内容"""
        try:
            # 先尝试移除think过程（blockquote）和Related searches
            
            # 1. 查找并标记blockquote元素（think过程）
            blockquotes = response_element.query_selector_all('blockquote')
            print(f"🔍 找到 {len(blockquotes)} 个blockquote元素（think过程）")
            
            # 2. 查找Related searches标记
            related_searches_elements = response_element.query_selector_all('p')
            related_searches_start = None
            
            for p_element in related_searches_elements:
                p_text = p_element.inner_text().strip()
                if 'related searches' in p_text.lower():
                    related_searches_start = p_element
                    print(f"🔍 找到Related searches开始标记: {p_text}")
                    break
            
            # 3. 获取完整的HTML内容
            full_html = response_element.inner_html()
            
            # 4. 移除blockquote内容和其他think相关元素
            for blockquote in blockquotes:
                try:
                    blockquote_html = blockquote.evaluate('el => el.outerHTML')
                    full_html = full_html.replace(blockquote_html, '')
                except:
                    pass
            
            # 5. 移除可能的thinking文本行和时间戳
            all_elements = response_element.query_selector_all('*')
            for element in all_elements:
                try:
                    element_text = element.inner_text().strip()
                    element_text_lower = element_text.lower()
                    
                    # 移除独立的thinking行或明显的thinking开头
                    if (element_text_lower in ['thinking...', 'thinking', 'think'] or 
                        element_text_lower.startswith(('thinking...', 'thinking about', 'let me think'))):
                        element_html = element.evaluate('el => el.outerHTML')
                        full_html = full_html.replace(element_html, '')
                        print(f"🧹 移除thinking元素: {element_text}")
                        continue
                    
                    # 移除时间戳元素
                    import re
                    if re.match(r'^\d{1,2}:\d{2}$', element_text):
                        element_html = element.evaluate('el => el.outerHTML')
                        full_html = full_html.replace(element_html, '')
                        print(f"🧹 移除时间戳元素: {element_text}")
                        continue
                        
                    # 移除包含时间戳的生成信息
                    if (len(element_text) < 30 and 
                        re.search(r'\d{1,2}:\d{2}', element_text) and
                        any(keyword in element_text_lower for keyword in ['generated', 'created', 'time', '生成', '创建'])):
                        element_html = element.evaluate('el => el.outerHTML')
                        full_html = full_html.replace(element_html, '')
                        print(f"🧹 移除时间相关元素: {element_text}")
                        
                except:
                    pass
            
            # 6. 如果找到Related searches，移除其后的所有内容
            if related_searches_start:
                try:
                    # 获取Related searches元素的outerHTML
                    related_html = related_searches_start.evaluate('el => el.outerHTML')
                    # 找到Related searches在HTML中的位置，移除其后所有内容
                    related_pos = full_html.find(related_html)
                    if related_pos != -1:
                        full_html = full_html[:related_pos]
                except:
                    pass
            
            # 7. 创建临时元素来提取纯文本
            if full_html.strip():
                # 使用更安全的方式来提取纯文本内容
                clean_text = response_element.evaluate('''
                    (element, html_content) => {
                        const tempDiv = document.createElement('div');
                        tempDiv.innerHTML = html_content;
                        return tempDiv.innerText.trim();
                    }
                ''', full_html)
                
                if clean_text and clean_text.strip():
                    print(f"✅ DOM提取成功，内容长度: {len(clean_text)}")
                    return clean_text.strip()
                    
        except Exception as e:
            print(f"⚠️ DOM提取失败: {str(e)}")
            
        return None

    def _filter_response_text(self, response_text: str) -> str:
        """通过文本内容过滤最终回复（后备方案）"""
        try:
            print(f"📝 使用文本过滤方案，原始长度: {len(response_text)}")
            
            # 1. 按段落分割文本（用双换行符）
            paragraphs = response_text.split('\n\n')
            filtered_paragraphs = []
            
            # 2. 过滤掉think过程和Related searches
            for paragraph in paragraphs:
                paragraph = paragraph.strip()
                if not paragraph:
                    continue
                
                # 跳过可能的think过程标志 - 更精确的匹配
                paragraph_lower = paragraph.lower().strip()
                
                # 检查是否是独立的thinking标志行
                if paragraph_lower in ['thinking...', 'thinking', 'think']:
                    print(f"⏭️ 跳过think过程段落: {paragraph[:50]}...")
                    continue
                
                # 检查是否以thinking开头（通常是think过程的开始）
                if paragraph_lower.startswith(('thinking...', 'thinking', 'think:', '思考:', 'let me think')):
                    print(f"⏭️ 跳过think过程段落: {paragraph[:50]}...")
                    continue
                
                # 检查其他think模式
                if any(pattern in paragraph_lower for pattern in [
                    'i need to think', '让我想想', '我需要思考'
                ]):
                    print(f"⏭️ 跳过think过程段落: {paragraph[:50]}...")
                    continue
                
                # 检测Related searches开始 - 停止处理
                if 'related searches' in paragraph.lower():
                    print(f"🔍 检测到Related searches，停止: {paragraph[:50]}...")
                    break
                
                # 跳过可能的引用或元数据
                if paragraph.startswith(('Source:', '来源:', 'Citations:', '引用:')):
                    print(f"⏭️ 跳过引用段落: {paragraph[:50]}...")
                    continue
                
                # 跳过末尾的时间戳（格式如 14:21）
                import re
                if re.match(r'^\d{1,2}:\d{2}$', paragraph.strip()):
                    print(f"⏭️ 跳过时间戳段落: {paragraph[:50]}...")
                    continue
                
                # 收集有效内容
                filtered_paragraphs.append(paragraph)
            
            # 3. 重新组合文本
            if filtered_paragraphs:
                result = '\n\n'.join(filtered_paragraphs).strip()
                
                # 最后清理末尾的时间戳
                result = self._clean_trailing_timestamp(result)
                
                print(f"✅ 文本过滤完成，过滤后长度: {len(result)}")
                return result
            
            # 4. 如果过滤后为空，尝试简单的行过滤
            lines = response_text.split('\n')
            filtered_lines = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # 检测Related searches - 停止
                if 'related searches' in line.lower():
                    break
                
                # 跳过明显的think标志 - 更精确匹配
                line_lower = line.lower().strip()
                
                # 检查独立的thinking行
                if line_lower in ['thinking...', 'thinking', 'think']:
                    print(f"⏭️ 跳过think行: {line[:30]}...")
                    continue
                
                # 检查以特定thinking模式开头的行
                if line_lower.startswith(('thinking...', 'thinking about', 'think:', '思考:')):
                    print(f"⏭️ 跳过think行: {line[:30]}...")
                    continue
                
                # 跳过时间戳行（格式如 14:21）
                import re
                if re.match(r'^\d{1,2}:\d{2}$', line.strip()):
                    print(f"⏭️ 跳过时间戳行: {line[:30]}...")
                    continue
                
                filtered_lines.append(line)
            
            if filtered_lines:
                result = '\n'.join(filtered_lines).strip()
                
                # 最后清理末尾的时间戳
                result = self._clean_trailing_timestamp(result)
                
                print(f"✅ 行级过滤完成，长度: {len(result)}")
                return result
            
            # 5. 如果所有过滤都失败，清理原文本的时间戳后返回
            print("⚠️ 所有过滤方案都失败，返回清理时间戳后的原文本")
            return self._clean_trailing_timestamp(response_text)
            
        except Exception as e:
            print(f"⚠️ 文本过滤失败: {str(e)}")
            return self._clean_trailing_timestamp(response_text)

    def _clean_trailing_timestamp(self, text: str) -> str:
        """清理文本末尾的时间戳"""
        try:
            import re
            
            # 按行分割文本
            lines = text.strip().split('\n')
            
            # 检查最后几行是否包含时间戳模式
            cleaned_lines = []
            
            for line in lines:
                line_stripped = line.strip()
                
                # 检查是否是时间戳格式（如 14:21, 9:30, 23:59）
                if re.match(r'^\d{1,2}:\d{2}$', line_stripped):
                    print(f"🧹 清理末尾时间戳: {line_stripped}")
                    continue  # 跳过时间戳行
                
                # 检查是否是包含时间戳的行（如 "Generated at 14:21"）
                if re.search(r'\b\d{1,2}:\d{2}\b', line_stripped):
                    # 如果整行都是时间相关，跳过
                    if len(line_stripped) < 20 and any(keyword in line_stripped.lower() for keyword in 
                                                      ['generated', 'created', 'time', '生成', '创建']):
                        print(f"🧹 清理时间相关行: {line_stripped}")
                        continue
                
                cleaned_lines.append(line)
            
            result = '\n'.join(cleaned_lines).strip()
            
            # 最后再检查末尾是否有独立的时间戳
            result = re.sub(r'\s*\d{1,2}:\d{2}\s*$', '', result).strip()
            
            return result
            
        except Exception as e:
            print(f"⚠️ 时间戳清理失败: {str(e)}")
            return text


# 简化的使用示例
def main():
    """新API使用示例"""
    print("🚀 Poe Chat API 快速示例")
    print("💡 完整测试请运行: python test/test_poe_chat.py")
    
    api = PoeChatAPI()
    
    try:
        # 连接浏览器
        if not api.connect():
            print("❌ 连接浏览器失败")
            print("请确保Chrome/Edge浏览器已启动，并添加 --remote-debugging-port=9222 参数")
            return
            
        print("✓ 浏览器连接成功")
        
        # 获取所有页面
        pages = api.list_pages()
        print(f"📄 当前页面数量: {len(pages)}")
        
        # 方式1：使用with语句创建新页面（推荐）
        with api.new_page("Claude-3.5-Sonnet") as page:
            print(f"✓ 新页面创建成功")
            
            response1 = page.chat("你好，我是测试用户")
            print(f"🤖 AI回复1: {response1}")
            
            response2 = page.chat("请介绍一下你自己")
            print(f"🤖 AI回复2: {response2}")
            
            print(f"📝 对话历史条数: {len(page.get_chat_history())}")
            
        # 页面会在对象销毁时自动关闭和清理
        print("✓ 页面上下文已退出")
        
    except Exception as e:
        print(f"❌ 操作失败: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # API对象销毁时会自动清理所有资源
        pass


if __name__ == "__main__":
    main() 