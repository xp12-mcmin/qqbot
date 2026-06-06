"""
独立点歌模块 - 可直接运行
功能：QQ 机器人点歌，支持语音消息
"""

import asyncio
import websockets
import json
import os
import re
import aiohttp
from datetime import datetime

# ==================== 配置 ====================
LLONEBOT_WS_URL = "ws://127.0.0.1:8765"  # LLOneBot WebSocket 地址
DOWNLOAD_DIR = "data/temp_music"  # 下载目录

# 点歌 API 配置
MUSIC_API = {
    "url": "https://a.aa.cab/qq.music",
    "params": {"num": 1, "n": 1, "type": 4}
}

# 签到消息（可选）
SIGN_MESSAGES = [
    "签到成功！获得+1积分~",
    "打卡成功！你是今天第一个！",
    "签到完成！今日运势：大吉！",
]

# ==================== 点歌服务 ====================
class MusicService:
    async def search(self, keyword: str) -> dict:
        """搜索歌曲"""
        try:
            params = MUSIC_API["params"].copy()
            params["msg"] = keyword
            
            async with aiohttp.ClientSession() as session:
                async with session.get(MUSIC_API["url"], params=params, timeout=15) as resp:
                    if resp.status == 200:
                        data = await resp.json(content_type=None)
                        if data.get("code") == 0:
                            song_data = data.get("data", {})
                            if song_data:
                                return {
                                    "success": True,
                                    "name": song_data.get("song", "未知"),
                                    "artist": song_data.get("singer", "未知"),
                                    "url": song_data.get("music", ""),
                                    "cover": song_data.get("cover", "")
                                }
                    return {"success": False, "msg": "搜索失败"}
        except Exception as e:
            return {"success": False, "msg": str(e)}
    
    async def download(self, url: str, filename: str) -> str:
        """下载音乐"""
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        filepath = os.path.join(DOWNLOAD_DIR, filename)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=60) as resp:
                    if resp.status == 200:
                        with open(filepath, 'wb') as f:
                            f.write(await resp.read())
                        return filepath
            return None
        except Exception as e:
            print(f"[下载] 失败: {e}")
            return None
    
    async def convert_to_amr(self, input_path: str, ffmpeg_path: str = None) -> str:
        """转换为 QQ 语音"""
        try:
            if not ffmpeg_path:
                ffmpeg_path = "ffmpeg.exe"
            
            if not os.path.exists(ffmpeg_path):
                return None
            
            output_path = input_path.replace('.m4a', '.amr').replace('.mp3', '.amr')
            
            cmd = [
                ffmpeg_path, '-i', input_path,
                '-acodec', 'amr_nb',
                '-ar', '8000',
                '-ac', '1',
                '-y',
                output_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.wait()
            
            if os.path.exists(output_path):
                return output_path
            return None
        except Exception as e:
            print(f"[转换] 失败: {e}")
            return None


# ==================== 机器人主程序 ====================
class MusicBot:
    def __init__(self):
        self.websocket = None
        self.bot_self_id = None
        self.music = MusicService()
    
    async def send_msg(self, group_id: int, message: str):
        """发送群消息"""
        await self.websocket.send(json.dumps({
            "action": "send_msg",
            "params": {
                "message_type": "group",
                "group_id": group_id,
                "message": message
            }
        }))
    
    async def handle_message(self, data: dict):
        """处理消息"""
        if data.get("post_type") != "message":
            return
        if data.get("message_type") != "group":
            return
        
        group_id = data.get("group_id")
        user_id = data.get("user_id")
        raw_msg = data.get("message", "")
        
        # 提取纯文本
        if isinstance(raw_msg, list):
            text = ""
            for seg in raw_msg:
                if seg.get("type") == "text":
                    text += seg.get("data", {}).get("text", "")
        else:
            text = str(raw_msg)
        
        text = text.strip()
        
        # ========== 点歌命令 ==========
        if text.startswith("点歌"):
            keyword = text[2:].strip()
            if not keyword:
                await self.send_msg(group_id, f"[CQ:at,qq={user_id}] 请指定歌曲名，如：点歌 稻香")
                return
            
            await self.send_msg(group_id, f"[CQ:at,qq={user_id}] 🔍 正在搜索《{keyword}》...")
            
            result = await self.music.search(keyword)
            if not result.get("success"):
                await self.send_msg(group_id, f"[CQ:at,qq={user_id}] ❌ 点歌失败：{result.get('msg')}")
                return
            
            song_name = result.get('name')
            artist = result.get('artist')
            music_url = result.get('url')
            cover_url = result.get('cover')
            
            await self.send_msg(group_id, f"[CQ:at,qq={user_id}] 📥 正在下载《{song_name}》...")
            
            safe_name = re.sub(r'[\\/*?:"<>|]', '', f"{song_name}-{artist}")
            filepath = await self.music.download(music_url, f"{safe_name}.m4a")
            
            msg_base = f"🎵 点歌成功！\n🎤 《{song_name}》- {artist}\n🔗 下载链接：{music_url}"
            
            if filepath:
                # 尝试转换语音
                amr_path = await self.music.convert_to_amr(filepath)
                if amr_path:
                    await self.websocket.send(json.dumps({
                        "action": "send_msg",
                        "params": {
                            "message_type": "group",
                            "group_id": group_id,
                            "message": f"[CQ:record,file=file:///{os.path.abspath(amr_path)}]"
                        }
                    }))
                    await self.send_msg(group_id, f"{msg_base}\n📢 已发送语音消息")
                else:
                    # 上传群文件
                    await self.websocket.send(json.dumps({
                        "action": "upload_group_file",
                        "params": {
                            "group_id": group_id,
                            "file": filepath,
                            "name": f"{song_name}-{artist}.m4a"
                        }
                    }))
                    await self.send_msg(group_id, f"{msg_base}\n📁 文件已上传群文件")
            else:
                await self.send_msg(group_id, msg_base)
        
        # ========== 签到命令 ==========
        elif "签到" in text or "打卡" in text:
            import random
            reply = random.choice(SIGN_MESSAGES)
            await self.send_msg(group_id, f"[CQ:at,qq={user_id}] {reply}")
    
    async def run(self):
        """运行机器人"""
        print("=" * 50)
        print("独立点歌模块 v1.0")
        print(f"连接地址: {LLONEBOT_WS_URL}")
        print("=" * 50)
        print("命令：点歌 <歌曲名>")
        print("     签到 / 打卡")
        print("=" * 50)
        
        while True:
            try:
                async with websockets.connect(LLONEBOT_WS_URL) as ws:
                    self.websocket = ws
                    print("✅ 连接成功，开始监听消息...")
                    
                    # 获取机器人ID
                    try:
                        init = await asyncio.wait_for(ws.recv(), timeout=3)
                        data = json.loads(init)
                        if data.get("post_type") == "meta_event":
                            self.bot_self_id = str(data.get("self_id", ""))
                            print(f"机器人ID: {self.bot_self_id}")
                    except:
                        pass
                    
                    # 消息循环
                    async for msg in ws:
                        try:
                            data = json.loads(msg)
                            await self.handle_message(data)
                        except Exception as e:
                            print(f"处理错误: {e}")
                            
            except ConnectionRefusedError:
                print("❌ 连接失败，请确保 LLOneBot 已启动")
                await asyncio.sleep(5)
            except Exception as e:
                print(f"连接异常: {e}")
                await asyncio.sleep(5)


# ==================== 启动 ====================
if __name__ == "__main__":
    asyncio.run(MusicBot().run())
