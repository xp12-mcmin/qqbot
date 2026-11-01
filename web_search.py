import sys
import os
import json
import time
import builtins
import aiohttp
from typing import Optional

# ==================== 授权验证 ====================
def _verify_module():
    """验证模块授权"""
    module_name = "web_search"
    
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


class WebSearch:
    def __init__(self):
        # 读取环境变量
        self.zhipu_key = os.environ.get("zhipu_api", "").strip()
        self.agnes_key = os.environ.get("api", "").strip()
        self.agnes_url = os.environ.get("api_url", "https://api.agnes-ai.cn/v1").strip()
    
    async def search(self, query: str) -> str:
        """执行搜索并调用 AI 总结"""
        if not self.zhipu_key:
            return "❌ 未配置智谱 API 密钥（环境变量 zhipu_api），无法搜索"

        # 1. 调用智谱联网搜索
        url = "https://open.bigmodel.cn/api/paas/v4/tools"
        headers = {
            "Authorization": f"Bearer {self.zhipu_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "tool": "web-search-pro",
            "messages": [{"role": "user", "content": query}]
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, timeout=30) as resp:
                    if resp.status != 200:
                        return f"❌ 搜索接口报错: HTTP {resp.status}"
                    
                    data = await resp.json()
                    choices = data.get("choices", [])
                    if not choices:
                        return "🔍 没有找到相关结果"
                    
                    tool_calls = choices[0].get("message", {}).get("tool_calls", [])
                    
                    search_results = []
                    for call in tool_calls:
                        if call.get("type") == "search_result":
                            search_results = call.get("search_result", [])
                            break
                            
                    if not search_results:
                        return "🔍 没有找到相关结果"
                    
                    # 提取前 3 条的摘要文本
                    raw_text = ""
                    for i, item in enumerate(search_results[:3], 1):
                        title = item.get("title", "无标题")
                        content = item.get("content", "无内容")
                        raw_text += f"【{title}】\n{content}\n\n"

        except Exception as e:
            return f"❌ 搜索网络异常: {e}"

        # 2. 如果配置了 Agnes，调用它来总结
        if self.agnes_key:
            summary = await self._summarize_with_ai(query, raw_text)
            if summary:
                return summary
                
        # 如果 Agnes 没配置或者挂了，就直接返回原始摘要（截断一下）
        return f"🌐 关于「{query}」的搜索结果：\n\n{raw_text[:800]}..."

    async def _summarize_with_ai(self, query: str, raw_text: str) -> Optional[str]:
        """调用 Agnes 将搜索结果总结成人话"""
        prompt = f"请根据以下网页摘要，简练、准确地回答用户的问题：“{query}”。\n\n网页摘要内容：\n{raw_text}\n\n请直接输出最终回答，字数控制在150字以内，不要包含“根据搜索结果”等废话。"
        
        headers = {
            "Authorization": f"Bearer {self.agnes_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "agnes-2.5-flash",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "temperature": 0.3
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.agnes_url}/chat/completions", json=payload, headers=headers, timeout=30) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        summary = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                        if summary:
                            return f"🔍 搜索并总结：\n\n{summary}"
        except Exception as e:
            print(f"[搜索] AI总结失败: {e}")
        
        return None


_web_search = None

def get_web_search():
    global _web_search
    if _web_search is None:
        _web_search = WebSearch()
    return _web_search
