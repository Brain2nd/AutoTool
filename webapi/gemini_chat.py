"""
Gemini Web Chat Tool - 基于上下文管理器的设计
连接到现有浏览器，每个页面上下文对象管理独立的对话历史
"""

import os
import time
import json
from typing import Dict, Optional, List
from datetime import datetime
from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext

class GeminiChatAPI:
    """Gemini 网页聊天主API - 浏览器连接和页面上下文管理"""
    
    def __init__(self, cdp_port: int = 9222):
        self.playwright = None
        self.browser = None
        self.context = None
        self.cdp_port = cdp_port
        self.gemini_url = "https://gemini.google.com/app"
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
                is_gemini = "gemini.google.com" in url and "/app" in url
                
                page_info = {
                    "index": i,
                    "url": url,
                    "is_gemini": is_gemini
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
                    "is_gemini": False,
                    "title": "Error" if include_title else None
                })
        return pages_info
        
    def new_page(self) -> 'GeminiPageContext':
        """创建新的Gemini页面，返回页面上下文对象"""
        if not self.context:
            raise RuntimeError("未连接到浏览器")
            
        try:
            # 创建新标签页
            new_page = self.context.new_page()
            
            # 导航到Gemini
            new_page.goto(self.gemini_url, timeout=30000)
            
            # 持续监测页面加载完成（等待输入框出现）
            self._wait_for_page_ready(new_page)
            
            # 获取页面索引
            pages = self.context.pages
            page_index = pages.index(new_page)
            
            # 创建页面上下文对象
            page_context = GeminiPageContext(self, page_index, is_new_page=True)
            self._register_context(page_context)
            
            return page_context
            
        except Exception as e:
            raise RuntimeError(f"创建页面失败: {str(e)}")
            
    def page(self, page_index: int) -> 'GeminiPageContext':
        """获取现有页面的上下文对象"""
        if not self.context:
            raise RuntimeError("未连接到浏览器")
            
        pages = self.context.pages
        if page_index >= len(pages):
            raise IndexError("页面索引无效")
            
        # 创建页面上下文对象
        page_context = GeminiPageContext(self, page_index, is_new_page=False)
        self._register_context(page_context)
        
        return page_context
        
    def _register_context(self, context: 'GeminiPageContext'):
        """注册页面上下文"""
        self._page_contexts.append(context)
        
    def _unregister_context(self, context: 'GeminiPageContext'):
        """注销页面上下文"""
        if context in self._page_contexts:
            self._page_contexts.remove(context)
            
    # 保持所有已验证的核心业务逻辑方法不变
    def _wait_for_page_ready(self, page: Page, timeout: int = 30) -> bool:
        """等待页面加载完成 - 持续监测输入框出现"""
        input_selectors = [
            'div[contenteditable="true"]',
            'textarea[placeholder*="输入"]', 
            'textarea[placeholder*="Message"]',
            'div[role="textbox"]',
            'div.ql-editor'
        ]
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                for selector in input_selectors:
                    elements = page.query_selector_all(selector)
                    for element in elements:
                        if element.is_visible():
                            return True  # 找到可见输入框，页面加载完成
            except:
                pass
            time.sleep(0.5)
            
        return False  # 超时未找到输入框


class GeminiPageContext:
    """Gemini页面上下文管理器 - 独立的对话历史和生命周期"""
    
    def __init__(self, api: GeminiChatAPI, page_index: int, is_new_page: bool = False):
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
        
        # 完成指示器选择器（用户多次强调过的精确选择器）
        self.completion_selector = '.mat-icon.notranslate.ng-tns-c1014041185-5.icon-filled.gds-icon-l.google-symbols.mat-ligature-font.mat-icon-no-color'
        
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
            
    def chat(self, message: str) -> str:
        """发送消息并获取回复，自动记录到历史"""
        if self._destroyed:
            raise RuntimeError("页面上下文已销毁")
            
        if not self.api.context:
            raise RuntimeError("浏览器连接已断开")
            
        try:
            if not self._page_obj:
                raise RuntimeError("页面对象无效")
                
            page = self._page_obj
            
            # 记录用户消息到历史
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
                if response:
                    break
                print(f"⏳ 正在获取回复内容，重试 {retry + 1}/5...")
                time.sleep(2)
                
            if not response:
                raise RuntimeError("获取回复失败，可能AI还在生成中")
                
            # 记录AI回复到历史
            ai_record = {
                "timestamp": datetime.now().isoformat(),
                "type": "assistant",
                "message": response
            }
            self._chat_history.append(ai_record)
            
            return response
            
        except Exception as e:
            # 记录错误到历史
            error_record = {
                "timestamp": datetime.now().isoformat(),
                "type": "error",
                "message": f"发送消息'{message}'时出错: {str(e)}"
            }
            self._chat_history.append(error_record)
            raise
            
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
            # 查找输入框
            input_selectors = [
                'div[contenteditable="true"]',
                'textarea[placeholder*="输入"]', 
                'textarea[placeholder*="Message"]',
                'div[role="textbox"]',
                'div.ql-editor'
            ]
            
            input_element = None
            for selector in input_selectors:
                try:
                    elements = page.query_selector_all(selector)
                    for element in elements:
                        if element.is_visible():
                            input_element = element
                            break
                    if input_element:
                        break
                except:
                    continue
                    
            if not input_element:
                return False
                
            # 清空输入框并输入消息
            input_element.click()
            time.sleep(0.5)
            input_element.fill("")
            
            # 多行文本处理
            if '\n' in message:
                input_element.fill(message)
            else:
                input_element.type(message)
            
            # 查找发送按钮
            send_selectors = [
                'button[aria-label*="Send"]',
                'button[aria-label*="发送"]',
                'button:has-text("Send")',
                'button:has-text("发送")',
                '[data-testid="send-button"]',
                'button[type="submit"]'
            ]
            
            send_button = None
            for selector in send_selectors:
                try:
                    button = page.query_selector(selector)
                    if button and button.is_visible() and button.is_enabled():
                        send_button = button
                        break
                except:
                    continue
                    
            if send_button:
                send_button.click()
                return True
            else:
                return False
                
        except Exception:
            return False
            
    def _wait_for_response(self, page: Page) -> bool:
        """等待响应完成 - 无时间限制，直到AI真正回复完成"""
        time.sleep(2)  # 等待AI开始生成
        print("⏳ 等待AI回复完成...")
        
        while True:
            try:
                completion_element = page.query_selector(self.completion_selector)
                if completion_element and completion_element.is_visible():
                    print("✅ AI回复完成")
                    return True
            except:
                pass
            time.sleep(1)  # 每秒检查一次
        
    def _get_response_from_page(self, page: Page) -> Optional[str]:
        """从页面获取回复"""
        try:
            time.sleep(3)  # 等待DOM更新和渲染
            
            response_elements = page.query_selector_all('[class*="response-content ng-tns-c"]')
            
            if response_elements:
                latest_response = response_elements[-1]
                response_text = latest_response.inner_text().strip()
                
                if response_text:
                    # 过滤"显示思路"前缀
                    if response_text.startswith("显示思路"):
                        first_newline = response_text.find('\n')
                        if first_newline != -1:
                            response_text = response_text[first_newline + 1:].strip()
                        else:
                            # 如果只有"显示思路"没有换行，说明还在加载中，返回None重试
                            return None
                    
                    # 如果回复内容为空或只有"显示思路"，返回None重试
                    if not response_text or response_text == "显示思路":
                        return None
                    
                    # 过滤末尾的"来源"UI元素
                    if response_text.endswith("来源"):
                        response_text = response_text[:-2].strip()
                    
                    # 过滤包含换行符的"来源"情况
                    lines = response_text.split('\n')
                    if lines and lines[-1].strip() == "来源":
                        response_text = '\n'.join(lines[:-1]).strip()
                    
                    return response_text
                    
            return None
            
        except Exception:
            return None


# 简化的使用示例
def main():
    """新API使用示例"""
    api = GeminiChatAPI()
    
    try:
        # 连接浏览器
        if not api.connect():
            print("❌ 连接浏览器失败")
            return
            
        print("✓ 浏览器连接成功")
        
        # 获取所有页面
        pages = api.list_pages()
        print(f"📄 当前页面数量: {len(pages)}")
        
        # 方式1：使用with语句创建新页面（推荐）
        with api.new_page() as page:
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
    finally:
        # API对象销毁时会自动清理所有资源
        pass


if __name__ == "__main__":
    main() 