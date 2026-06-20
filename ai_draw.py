"""
AI 绘画模块 - 百度文心 API
"""

import aiohttp
import asyncio
import os
import time
import random
import json


class AIDraw:
    def __init__(self):
        self.api_url = "http://qwq.nki.pw/API/AI/BaiDuDraw.php"
        self.draw_dir = "data/ai_images"
        os.makedirs(self.draw_dir, exist_ok=True)
    
    def optimize_keyword(self, keyword: str) -> str:
        """优化关键词"""
        if "二次元" in keyword or "动漫" in keyword:
            keyword = keyword.replace("二次元", "动漫风格").replace("动漫", "动漫风格")
        if "写实" in keyword:
            keyword = keyword.replace("写实", "写实风格")
        
        content_map = {
            "猫娘": "猫娘少女",
            "白丝": "白丝少女",
            "赛博朋克": "赛博朋克城市",
            "风景": "风景画",
            "星空": "星空夜景",
            "古风": "古风美女",
            "仙侠": "仙侠人物",
        }
        for key, value in content_map.items():
            if key in keyword:
                keyword = keyword.replace(key, value)
                break
        
        if not any(x in keyword for x in ["高清", "精美", "唯美"]):
            keyword = keyword + "高清"
        
        return keyword
    
    def generate_retry_keywords(self, keyword: str) -> list:
        """生成备用关键词"""
        retry_list = [
            keyword,
            keyword + "精美",
            keyword + "唯美",
            "好看的" + keyword,
            "美丽的" + keyword,
        ]
        return list(dict.fromkeys(retry_list))
    
    async def _do_draw(self, keyword: str) -> tuple:
        """执行单次绘画请求"""
        try:
            params = {"keyword": keyword}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.api_url, params=params, timeout=60) as resp:
                    if resp.status != 200:
                        return False, f"HTTP {resp.status}"
                    
                    text = await resp.text()
                    data = json.loads(text)
                    
                    if data.get("code") != 200:
                        return False, data.get("msg", "绘画失败")
                    
                    img_urls = data.get("data", [])
                    if not img_urls:
                        return False, "未获取到图片"
                    
                    img_url = random.choice(img_urls)
                    
                    async with session.get(img_url, timeout=30) as img_resp:
                        if img_resp.status != 200:
                            return False, f"下载失败: HTTP {img_resp.status}"
                        
                        os.makedirs(self.draw_dir, exist_ok=True)
                        filename = f"ai_draw_{int(time.time())}_{random.randint(1000,9999)}.jpg"
                        filepath = os.path.join(self.draw_dir, filename)
                        
                        with open(filepath, 'wb') as f:
                            f.write(await img_resp.read())
                        
                        return True, filepath
                        
        except Exception as e:
            return False, str(e)
    
    async def draw(self, keyword: str) -> tuple:
        """生成图片，自动优化关键词 + 重试"""
        optimized = self.optimize_keyword(keyword)
        retry_keywords = self.generate_retry_keywords(optimized)
        
        for kw in retry_keywords[:3]:
            success, result = await self._do_draw(kw)
            if success:
                return True, result
            if "超时" not in result:
                await asyncio.sleep(2)
        
        if keyword != optimized:
            success, result = await self._do_draw(keyword)
            if success:
                return True, result
        
        return False, "绘画失败，请换个关键词试试"


_ai_draw = None

def get_ai_draw():
    global _ai_draw
    if _ai_draw is None:
        _ai_draw = AIDraw()
    return _ai_draw
