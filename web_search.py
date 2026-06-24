"""
联网搜索模块 - 使用 Ollama API
"""

import aiohttp
import asyncio
import json
import os
import urllib.parse


class WebSearch:
    def __init__(self):
        # 从环境变量读取 API Key
        self.api_key = os.environ.get("OLLAMA_API_KEY", "")
        self.ollama_url = "http://127.0.0.1:11434/api/generate"
    
    async def search(self, query: str) -> str:
        """使用 Ollama 进行联网搜索，返回图片路径"""
        if not self.api_key:
            print("[搜索] 未设置 OLLAMA_API_KEY 环境变量")
            return None
        
        try:
            # 构建搜索提示词
            prompt = f"""请搜索以下问题并给出答案，需要联网获取实时信息：
问题：{query}

要求：
1. 如果能够获取到实时信息，请给出准确的答案
2. 如果无法获取实时信息，请说明无法获取
3. 答案要简洁明了
4. 如果有相关链接，可以附上"""
            
            payload = {
                "model": "qwen2.5:3b",  # 使用本地模型
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 500
                }
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.ollama_url, json=payload, headers=headers, timeout=30) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        result = data.get("response", "")
                        
                        # 生成图片（如果需要）
                        img_path = await self._generate_result_image(query, result)
                        return img_path
                    else:
                        print(f"[搜索] HTTP {resp.status}")
                        return None
        except Exception as e:
            print(f"[搜索] 错误: {e}")
            return None
    
    async def _generate_result_image(self, query: str, result: str) -> str:
        """生成搜索结果图片"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            import time
            
            # 创建图片
            width, height = 600, 400
            img = Image.new('RGB', (width, height), color='#1a1a2e')
            draw = ImageDraw.Draw(img)
            
            # 加载字体
            try:
                font_title = ImageFont.truetype("simhei.ttf", 20)
                font_text = ImageFont.truetype("simhei.ttf", 16)
            except:
                font_title = ImageFont.load_default()
                font_text = ImageFont.load_default()
            
            # 绘制标题
            draw.text((20, 20), f"🔍 搜索结果：{query[:30]}", fill='#00ff88', font=font_title)
            
            # 分割线
            draw.line((20, 55, width-20, 55), fill='#333333', width=1)
            
            # 绘制结果（限制长度）
            lines = []
            max_len = 35
            for i in range(0, len(result), max_len):
                lines.append(result[i:i+max_len])
            
            y = 80
            for line in lines[:10]:  # 最多10行
                draw.text((20, y), line, fill='#ffffff', font=font_text)
                y += 25
            
            # 底部提示
            draw.line((20, y+10, width-20, y+10), fill='#333333', width=1)
            draw.text((20, y+30), "💡 数据来自AI搜索", fill='#aaaaaa', font=font_text)
            
            # 保存图片
            os.makedirs("data/temp_images", exist_ok=True)
            img_path = f"data/temp_images/search_{int(time.time())}.png"
            img.save(img_path)
            
            return img_path
        except Exception as e:
            print(f"[生成图片] 错误: {e}")
            return None


_web_search = None

def get_web_search():
    global _web_search
    if _web_search is None:
        _web_search = WebSearch()
    return _web_search
