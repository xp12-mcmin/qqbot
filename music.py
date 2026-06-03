"""
点歌功能模块 - 独立文件
"""

import aiohttp
import asyncio
import json
import os


class MusicService:
    """音乐服务类"""
    
    def __init__(self):
        self.apis = {
            "qq": {
                "name": "QQ音乐",
                "url": "https://a.aa.cab/qq.music",
                "params": {"msg": "", "num": 1, "n": 1, "type": 4}
            }
        }
        self.source_order = ["qq"]
        self.download_dir = "data/temp_music"
        os.makedirs(self.download_dir, exist_ok=True)
    
    async def search(self, keyword: str, source: str = None) -> dict:
        """搜索歌曲"""
        if source:
            return await self._search_one(keyword, source)
        
        for src in self.source_order:
            result = await self._search_one(keyword, src)
            if result.get("success"):
                return result
        return {"success": False, "msg": "所有音乐源都无法访问"}
    
    async def _search_one(self, keyword: str, source: str) -> dict:
        """在单个源搜索"""
        config = self.apis.get(source)
        if not config:
            return {"success": False, "msg": f"未知源: {source}"}
        
        params = config["params"].copy()
        params["msg"] = keyword
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(config["url"], params=params, timeout=15) as resp:
                    if resp.status == 200:
                        try:
                            data = await resp.json(content_type=None)
                        except:
                            text = await resp.text()
                            data = json.loads(text)
                        
                        if data.get("code") == 0:
                            song_data = data.get("data", {})
                            if song_data:
                                return {
                                    "success": True,
                                    "source": config["name"],
                                    "name": song_data.get("song", "未知"),
                                    "artist": song_data.get("singer", "未知"),
                                    "url": song_data.get("music", ""),
                                    "cover": song_data.get("cover", "")
                                }
                            else:
                                return {"success": False, "msg": "未找到相关歌曲"}
                        else:
                            return {"success": False, "msg": data.get("msg", "请求失败")}
                    else:
                        return {"success": False, "msg": f"HTTP {resp.status}"}
        except asyncio.TimeoutError:
            return {"success": False, "msg": "请求超时"}
        except Exception as e:
            print(f"[点歌错误] {e}")
            return {"success": False, "msg": str(e)}
    
    async def download_music(self, url: str, filename: str) -> str:
        """下载音乐文件"""
        filepath = os.path.join(self.download_dir, filename)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as resp:
                    if resp.status == 200:
                        with open(filepath, 'wb') as f:
                            f.write(await resp.read())
                        return filepath
                    else:
                        return None
        except Exception as e:
            print(f"[下载失败] {e}")
            return None


_music_service = None

def get_music_service():
    global _music_service
    if _music_service is None:
        _music_service = MusicService()
    return _music_service
