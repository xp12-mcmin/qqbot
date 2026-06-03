"""
联网搜索模块 - 支持图片输出
"""

import aiohttp
import asyncio
from typing import Optional
from PIL import Image, ImageDraw, ImageFont
import os


class WebSearch:
    """Ollama 联网搜索"""
    
    def __init__(self, model: str = "deepseek-v3.1:671b-cloud"):
        self.base_url = "http://127.0.0.1:11434"
        self.model = model
        self.font_dir = "fonts"
        self._load_font()
    
    def _load_font(self):
        """加载字体"""
        try:
            font_path = os.path.join(self.font_dir, "simhei.ttf")
            if os.path.exists(font_path):
                self.font_title = ImageFont.truetype(font_path, 22)
                self.font_text = ImageFont.truetype(font_path, 16)
            else:
                self.font_title = ImageFont.load_default()
                self.font_text = ImageFont.load_default()
        except:
            self.font_title = ImageFont.load_default()
            self.font_text = ImageFont.load_default()
    
    def text_to_image(self, text: str, title: str = "搜索结果") -> Optional[str]:
        """将文本转换为图片"""
        try:
            import textwrap
            
            # 图片宽度
            img_width = 650
            # 每行最大字符数
            max_chars = 50
            # 行高
            line_height = 28
            
            # 拆分文本为多行
            lines = []
            for line in text.split('\n'):
                if len(line) <= max_chars:
                    lines.append(line)
                else:
                    wrapped = textwrap.wrap(line, width=max_chars)
                    lines.extend(wrapped)
            
            # 计算图片高度
            img_height = 100 + len(lines) * line_height + 50
            
            # 创建图片
            img = Image.new('RGB', (img_width, img_height), color='#1a1a2e')
            draw = ImageDraw.Draw(img)
            
            # 画背景边框
            draw.rectangle([5, 5, img_width-5, img_height-5], outline='#333333', width=2)
            
            # 标题
            draw.text((20, 20), f"🌐 {title}", fill='#00ff88', font=self.font_title)
            
            # 分割线
            draw.line((20, 55, img_width-20, 55), fill='#333333', width=1)
            
            # 内容
            y = 75
            for line in lines:
                draw.text((20, y), line, fill='#ffffff', font=self.font_text)
                y += line_height
            
            # 底部提示
            draw.text((20, y+10), "💡 数据来源于联网搜索", fill='#888888', font=self.font_text)
            
            # 保存临时文件
            temp_dir = "data/temp_images"
            os.makedirs(temp_dir, exist_ok=True)
            import time
            filename = f"search_{int(time.time()*1000)}.png"
            filepath = os.path.join(temp_dir, filename)
            img.save(filepath, "PNG")
            
            return filepath
        except Exception as e:
            print(f"[联网搜索] 图片生成失败: {e}")
            return None
    
    async def search(self, query: str) -> Optional[str]:
        """执行联网搜索，返回图片路径"""
        try:
            payload = {
                "model": self.model,
                "messages": [{
                    "role": "user",
                    "content": f"请使用联网搜索功能，搜索以下内容并提供详细结果：{query}"
                }],
                "stream": False
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=30
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        reply = data.get('message', {}).get('content', '')
                        if reply:
                            # 生成图片
                            img_path = self.text_to_image(reply, f"搜索: {query[:30]}")
                            return img_path
                        else:
                            return None
                    else:
                        return None
        except Exception as e:
            print(f"[联网搜索] 失败: {e}")
            return None
    
    async def chat_with_search(self, question: str) -> Optional[str]:
        """带搜索的AI问答，返回图片路径"""
        try:
            payload = {
                "model": self.model,
                "messages": [{
                    "role": "user",
                    "content": f"请使用联网搜索功能回答以下问题：{question}"
                }],
                "stream": False
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=30
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        reply = data.get('message', {}).get('content', '')
                        if reply:
                            img_path = self.text_to_image(reply, f"问答: {question[:30]}")
                            return img_path
                        else:
                            return None
                    else:
                        return None
        except Exception as e:
            print(f"[联网搜索] 失败: {e}")
            return None


# 全局实例
_web_search = None

def get_web_search():
    global _web_search
    if _web_search is None:
        _web_search = WebSearch()
    return _web_search
