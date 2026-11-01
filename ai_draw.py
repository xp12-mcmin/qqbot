import sys
import os
import json
import time
import builtins
import random
import asyncio
import aiohttp
from datetime import datetime


# ==================== 授权验证 ====================
def _verify_module():
    """验证模块授权"""
    module_name = "ai_draw"
    
    try:
        license_key = getattr(builtins, 'XP12_LICENSE_KEY', '')
        print(f"[调试] 从 builtins 读取密钥: {license_key}")
    except Exception as e:
        print(f"[调试] 读取 builtins 异常: {e}")
        license_key = ''
    
    expected_key = ''
    try:
        if os.path.exists("data/.module_license"):
            with open("data/.module_license", "r") as f:
                data = json.load(f)
                expected_key = data.get("license_key", '')
                print(f"[调试] 从文件读取密钥: {expected_key}")
    except Exception as e:
        print(f"[调试] 读取文件异常: {e}")
        pass
    
    print(f"[调试] 对比: license_key={license_key}, expected_key={expected_key}")
    
    if license_key != expected_key or not expected_key:
        print(f"❌ 模块 [{module_name}] 授权失败！")
        print(f"   请通过主程序调用本模块")
        sys.exit(1)
    
    print(f"✅ 模块 [{module_name}] 授权通过")

_verify_module()


# ==================== 正常代码 ====================
import os

class AIDraw:
    def __init__(self):
        # 🚀 从环境变量读取，并加上 .strip() 清理所有的空格和换行符！
        raw_key = os.environ.get("zhipu_api", "")
        self.api_key = raw_key.strip() if raw_key else ""
        
        raw_url = os.environ.get("zhipu_url", "")
        self.base_url = raw_url.strip() if raw_url else "https://open.bigmodel.cn/api/paas/v4"
        
        # 如果没有写 url，默认给智谱的
        if not self.base_url:
            self.base_url = "https://open.bigmodel.cn/api/paas/v4"

        # 🆕 调试代码：启动时打印一下（屏蔽中间部分），确认读到了！
        if self.api_key:
            masked = f"{self.api_key[:8]}...{self.api_key[-6:]}" if len(self.api_key) > 15 else "长度异常"
            print(f"[AI绘画] ✅ 成功读取环境变量密钥: {masked}")
            print(f"[AI绘画] ✅ 成功读取环境变量地址: {self.base_url}")
        else:
            print("[AI绘画] ❌ 严重警告：没有在环境变量中找到 'zhipu_api'！")
            
        self.draw_dir = "data/ai_images"
        os.makedirs(self.draw_dir, exist_ok=True)
        self.model = "cogview-3-flash"
    def optimize_keyword(self, keyword: str) -> str:
        """优化关键词"""
        # 如果包含猫娘，强行注入二次元人类特征
        if "猫娘" in keyword:
            keyword = keyword.replace("猫娘", "二次元少女，长着可爱的猫耳朵，人类脸庞，日系动漫风格")
            
        if "二次元" in keyword or "动漫" in keyword:
            keyword = keyword.replace("二次元", "动漫风格").replace("动漫", "动漫风格")
        if "写实" in keyword:
            keyword = keyword.replace("写实", "写实风格")
        
        content_map = {
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
        
        # 强制加上画质词，防止它乱画
        if not any(x in keyword for x in ["高清", "精美", "唯美"]):
            keyword = keyword + "，精美，高清，杰作"
        
        return keyword
    
    async def _do_draw(self, keyword: str) -> tuple:
        """执行单次绘画请求（调用智谱 API）"""
        if not self.api_key:
            return False, "未配置 API 密钥（环境变量 api）"

        try:
            url = f"{self.base_url}/images/generations"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.model,
                "prompt": keyword,
                "size": "1024x1024"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, timeout=60) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        return False, f"HTTP {resp.status}: {text[:50]}"
                    
                    data = await resp.json()
                    
                    # 解析智谱的返回格式
                    # 成功格式: {"created": 123, "data": [{"url": "https://..."}]}
                    img_data = data.get("data", [])
                    if not img_data or not img_data[0].get("url"):
                        return False, "未获取到图片 URL"
                    
                    img_url = img_data[0]["url"]
                    
                    # 下载图片并保存到本地
                    async with session.get(img_url, timeout=30) as img_resp:
                        if img_resp.status != 200:
                            return False, f"图片下载失败: HTTP {img_resp.status}"
                        
                        filename = f"ai_draw_{int(time.time())}_{random.randint(1000,9999)}.png"
                        filepath = os.path.join(self.draw_dir, filename)
                        
                        with open(filepath, 'wb') as f:
                            f.write(await img_resp.read())
                        
                        return True, filepath
                        
        except asyncio.TimeoutError:
            return False, "请求超时"
        except Exception as e:
            return False, str(e)
    
    async def draw(self, keyword: str) -> tuple:
        """生成图片"""
        optimized = self.optimize_keyword(keyword)
        
        # 尝试两次（第一次优化后的词，第二次原词）
        success, result = await self._do_draw(optimized)
        if success:
            return True, result
            
        if keyword != optimized:
            success, result = await self._do_draw(keyword)
            if success:
                return True, result
                
        return False, result


_ai_draw = None

def get_ai_draw():
    global _ai_draw
    if _ai_draw is None:
        _ai_draw = AIDraw()
    return _ai_draw
