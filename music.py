


import sys
import os
import json
import time
import builtins
from datetime import datetime
from typing import Dict, Optional, List
import asyncio
import aiohttp
import shutil   # convert_to_amr 里用了

# ==================== 授权验证 ====================
def _verify_module():
    """验证模块授权"""
    module_name = "music"
    
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
"""
模块名：music
功能：待补充
"""

# ==================== 正常代码 ====================

__plugin_author__ = "xp12"
"""
点歌功能模块 - 支持下载和QQ语音转换

FFmpeg 下载地址（用于音频转语音）：
- 官方下载：https://ffmpeg.org/download.html
- Windows 完整版：https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip
- 解压后将 bin/ffmpeg.exe 放到项目目录
"""




class MusicService:
    """音乐服务类（QQ 音乐底层接口直连，无需第三方 API）"""

    def __init__(self):
        self.download_dir = "data/temp_music"
        os.makedirs(self.download_dir, exist_ok=True)

    # ---------------- curl 工具 ----------------
    async def _curl_get_json(self, url: str, timeout: int = 15) -> dict:
        """用 Windows 自带 curl.exe 异步 GET 并解析 JSON"""
        cmd = [
            "curl.exe", "-s",
            "-A", "Mozilla/5.0",
            url,
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            text = stdout.decode("utf-8", errors="replace").strip()
            if not text:
                raise ValueError("curl 返回为空")
            return json.loads(text)
        except asyncio.TimeoutError:
            raise
        except json.JSONDecodeError:
            raise ValueError("响应不是合法 JSON")

    # ---------------- 搜索 ----------------
    async def search(self, keyword: str, source: str = None) -> dict:
        """QQ 音乐底层接口搜索（无需第三方 API）"""
        try:
            # 1. 搜索：取第一首，提取 songname、singer[0].name、songmid
            search_url = (
                "https://c.y.qq.com/soso/fcgi-bin/client_search_cp"
                f"?p=1&n=3&w={keyword}&format=json"
            )
            data = await self._curl_get_json(search_url, timeout=15)
            song_list = ((data.get("data") or {}).get("song") or {}).get("list") or []
            if not song_list:
                return {"success": False, "msg": "未找到相关歌曲"}

            song = song_list[0]
            song_name = song.get("songname", "未知")
            singers = song.get("singer") or []
            artist = singers[0].get("name", "未知") if singers else "未知"
            songmid = song.get("songmid", "")
            if not songmid:
                return {"success": False, "msg": "未获取到歌曲ID"}

            # 提取专辑 mid，拼高清封面链接
            albummid = song.get("albummid", "")
            cover = f"https://y.gtimg.cn/music/photo_new/T002R300x300M000{albummid}.jpg" if albummid else ""

            # 2. 获取直链（构造 vkey 请求，用 aiohttp params 字典传参，避免 JSON 空格/引号编码问题）
            vkey_payload = {
                "req_0": {
                    "module": "vkey.GetVkeyServer",
                    "method": "CgiGetVkey",
                    "param": {
                        "guid": "3581234567",
                        "songmid": [songmid],
                        "songtype": [0],
                        "uin": "0",
                        "loginflag": 1,
                        "platform": "20",
                    },
                },
                "comm": {"uin": 0, "format": "json", "ct": 24, "cv": 0},
            }
            vkey_params = {
                "format": "json",
                "data": json.dumps(vkey_payload, separators=(",", ":")),
            }
            vkey_url = "https://u.y.qq.com/cgi-bin/musicu.fcg"
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    vkey_url,
                    params=vkey_params,
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        return {"success": False, "msg": f"vkey 接口 HTTP {resp.status}"}
                    vkey = await resp.json(content_type=None)

            midurlinfo = ((vkey.get("req_0") or {}).get("data") or {}).get("midurlinfo") or []
            if not midurlinfo:
                return {"success": False, "msg": "未获取到播放链接"}

            purl = midurlinfo[0].get("purl", "")
            if not purl:
                return {"success": False, "msg": "该歌曲没有版权或需要 VIP"}

            direct_url = f"http://aqqmusic.tc.qq.com/{purl}"

            # 3. 返回
            return {
                "success": True,
                "name": song_name,
                "artist": artist,
                "url": direct_url,
                "cover": cover,
                "download_url": direct_url,
            }
        except asyncio.TimeoutError:
            return {"success": False, "msg": "QQ音乐连接超时"}
        except Exception as e:
            print(f"[点歌错误] {e}")
            return {"success": False, "msg": str(e)}

    async def download_music(self, url: str, filename: str) -> str:
        """下载音乐文件（curl.exe 直连 QQ 音乐 CDN）"""
        filepath = os.path.join(self.download_dir, filename)

        try:
            cmd = [
                "curl.exe", "-s", "-L",
                "-A", "Mozilla/5.0",
                "-o", filepath,
                "--max-time", "60",
                url,
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            if proc.returncode != 0:
                err = (stderr or b"").decode("utf-8", errors="replace").strip()
                print(f"[下载] curl 失败 (code={proc.returncode}): {err}")
                return None

            size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
            if size < 5 * 1024:
                print(f"[下载] 文件太小（{size} bytes），疑似非音频内容")
                os.remove(filepath)
                return None

            print(f"[下载] 成功: {filepath} ({size} bytes)")
            return filepath
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
