import sys
import os
import json
import time
import builtins
import random
import asyncio
import aiohttp

# ==================== 授权验证 ====================
def _verify_module():
    module_name = "ai_draw"
    try:
        license_key = getattr(builtins, 'XP12_LICENSE_KEY', '')
    except Exception:
        license_key = ''
    
    expected_key = ''
    try:
        if os.path.exists("data/.module_license"):
            with open("data/.module_license", "r") as f:
                data = json.load(f)
                expected_key = data.get("license_key", '')
    except Exception:
        pass
    
    if license_key != expected_key or not expected_key:
        print(f"❌ 模块 [{module_name}] 授权失败！请通过主程序调用本模块")
        sys.exit(1)
    
    print(f"✅ 模块 [{module_name}] 授权通过")

_verify_module()

# ==================== 正常代码 ====================
class AIDraw:
    def __init__(self):
        # 读取智谱专用的环境变量
        self.api_key = os.environ.get("zhipu_api", "").strip()
        self.base_url = os.environ.get("zhipu_url", "https://open.bigmodel.cn/api/paas/v4").strip()
            
        self.draw_dir = "data/ai_images"
        os.makedirs(self.draw_dir, exist_ok=True)
        
        # 智谱画图模型
        self.model = "cogview-3-flash"

    async def _do_draw(self, prompt: str) -> tuple:
        """执行单次绘画请求（调用智谱 API）"""
        if not self.api_key:
            return False, "未配置智谱 API 密钥（环境变量 zhipu_api）"

        try:
            url = f"{self.base_url}/images/generations"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.model,
                "prompt": prompt,  # 直接把传进来的（通常是英文）塞进去
                "size": "1024x1024"
            }
            
            timeout = aiohttp.ClientTimeout(total=180, connect=30)
            connector = aiohttp.TCPConnector(force_close=True)
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                print(f"[AI绘画] 正在请求智谱接口...")
                async with session.post(url, json=payload, headers=headers) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        print(f"[AI绘画] 接口报错: HTTP {resp.status} - {text[:100]}")
                        return False, f"接口报错: {resp.status}"
                    
                    data = await resp.json()
                    img_data = data.get("data", [])
                    if not img_data or not img_data[0].get("url"):
                        return False, "未获取到图片 URL"
                    
                    img_url = img_data[0]["url"]
                    
                    async with session.get(img_url, timeout=aiohttp.ClientTimeout(total=60)) as img_resp:
                        if img_resp.status != 200:
                            return False, f"图片下载失败: HTTP {img_resp.status}"
                        
                        filename = f"ai_draw_{int(time.time())}_{random.randint(1000,9999)}.png"
                        filepath = os.path.join(self.draw_dir, filename)
                        
                        with open(filepath, 'wb') as f:
                            f.write(await img_resp.read())
                        
                        print(f"[AI绘画] ✅ 图片已保存: {filepath}")
                        return True, filepath
                        
        except asyncio.TimeoutError:
            print("[AI绘画] ❌ 请求超时：服务器排队太久")
            return False, "服务器排队超时，请稍后再试"
        except Exception as e:
            print(f"[AI绘画] ❌ 异常: {e}")
            return False, str(e)
    
    async def draw(self, prompt: str) -> tuple:
        """对外暴露的画图接口"""
        # 主程序已经用过 AI 优化了 Prompt，这里直接交给 _do_draw 即可
        return await self._do_draw(prompt)

_ai_draw = None

def get_ai_draw():
    global _ai_draw
    if _ai_draw is None:
        _ai_draw = AIDraw()
    return _ai_draw
