"""
点歌功能模块 - 支持下载和QQ语音转换

FFmpeg 下载地址（用于音频转语音）：
- 官方下载：https://ffmpeg.org/download.html
- Windows 完整版：https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip
- 解压后将 bin/ffmpeg.exe 放到项目目录
"""

import aiohttp
import asyncio
import json
import os
import re
import subprocess

import aiohttp
import asyncio
import json
import os
import re
import subprocess


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
                        # 尝试解析 JSON
                        try:
                            data = await resp.json(content_type=None)
                        except:
                            text = await resp.text()
                            data = json.loads(text)
                        
                        # 打印调试信息，方便排查
                        print(f"[点歌调试] API返回: code={data.get('code')}")
                        
                        # 关键：检查返回的 code 是否为 0
                        if data.get("code") == 0:
                            # 获取 data 字段中的歌曲信息
                            song_data = data.get("data", {})
                            if song_data:
                                music_url = song_data.get("music", "")
                                # 确保获取到音乐链接
                                if music_url:
                                    return {
                                        "success": True,
                                        "source": config["name"],
                                        "name": song_data.get("song", "未知"),
                                        "artist": song_data.get("singer", "未知"),
                                        "url": music_url,
                                        "cover": song_data.get("cover", "")
                                    }
                                else:
                                    return {"success": False, "msg": "未获取到播放链接"}
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
                async with session.get(url, timeout=60) as resp:
                    if resp.status == 200:
                        with open(filepath, 'wb') as f:
                            f.write(await resp.read())
                        print(f"[下载] 成功: {filepath}")
                        return filepath
                    else:
                        print(f"[下载] HTTP {resp.status}")
                        return None
        except Exception as e:
            print(f"[下载] 失败: {e}")
            return None
    
    async def convert_to_amr(self, input_path: str) -> str:
        """将音频文件转换为 QQ 语音格式 (AMR)"""
        try:
            output_path = input_path.replace('.m4a', '.amr').replace('.mp3', '.amr')
            
            # 使用项目目录下的 ffmpeg
            script_dir = os.path.dirname(os.path.abspath(__file__))
            ffmpeg_path = os.path.join(script_dir, "ffmpeg.exe")
            
            # 如果项目目录没有，尝试系统 PATH
            if not os.path.exists(ffmpeg_path):
                import shutil
                ffmpeg_path = shutil.which('ffmpeg')
                if not ffmpeg_path:
                    print(f"[转换] ffmpeg 未找到，跳过语音转换")
                    return None
            
            print(f"[转换] 使用 ffmpeg: {ffmpeg_path}")
            
            # 先转成 wav 中间格式（避免编码器问题）
            temp_wav = input_path.replace('.m4a', '.wav').replace('.mp3', '.wav')
            
            # 步骤1：转成 wav
            cmd1 = [ffmpeg_path, '-i', input_path, '-y', temp_wav]
            process1 = await asyncio.create_subprocess_exec(
                *cmd1,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process1.wait()
            
            if not os.path.exists(temp_wav):
                print(f"[转换] 转 wav 失败")
                return None
            
            # 步骤2：wav 转 amr
            cmd2 = [
                ffmpeg_path, '-i', temp_wav,
                '-acodec', 'amr_nb',
                '-ar', '8000',
                '-ac', '1',
                '-y',
                output_path
            ]
            process2 = await asyncio.create_subprocess_exec(
                *cmd2,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process2.wait()
            
            # 清理临时文件
            if os.path.exists(temp_wav):
                os.remove(temp_wav)
            
            if os.path.exists(output_path):
                size = os.path.getsize(output_path)
                if size < 1024 * 1024:  # 小于1MB
                    print(f"[转换] 成功: {output_path} ({size} bytes)")
                    return output_path
                else:
                    print(f"[转换] 文件太大: {size} bytes")
                    os.remove(output_path)
            return None
        except Exception as e:
            print(f"[转换] 失败: {e}")
            return None

_music_service = None

def get_music_service():
    global _music_service
    if _music_service is None:
        _music_service = MusicService()
    return _music_service
