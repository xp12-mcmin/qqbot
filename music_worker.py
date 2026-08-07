# music_worker.py
import asyncio
import os
import sys
import json
import base64
import aiohttp
import subprocess
import websockets
from music import get_music_service

# ==================== 转换函数 ====================

async def convert_to_amr(input_path: str) -> str:
    """转 AMR"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ffmpeg_path = os.path.join(script_dir, "ffmpeg.exe")
    
    if not os.path.exists(ffmpeg_path):
        print(f"[音乐进程] ffmpeg.exe 不存在: {ffmpeg_path}")
        return None
    
    output_path = input_path.replace('.m4a', '.amr').replace('.mp3', '.amr')
    
    try:
        cmd = [
            ffmpeg_path, "-y", "-i", input_path,
            "-vn", "-ar", "8000", "-ac", "1", "-ab", "12.2k",
            output_path
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        if os.path.exists(output_path):
            print(f"[音乐进程] AMR 转换成功: {output_path}")
            return output_path
        return None
    except Exception as e:
        print(f"[音乐进程] AMR 转换失败: {e}")
        return None


async def convert_to_silk(input_path: str) -> str:
    """转 SILK"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ffmpeg_path = os.path.join(script_dir, "ffmpeg.exe")
    silk_encoder_path = os.path.join(script_dir, "silk_v3_encoder.exe")
    
    if not os.path.exists(ffmpeg_path) or not os.path.exists(silk_encoder_path):
        print(f"[音乐进程] ffmpeg 或 silk_encoder 不存在")
        return None
    
    base_name = os.path.splitext(input_path)[0]
    pcm_path = f"{base_name}.pcm"
    silk_path = f"{base_name}.silk"
    
    try:
        # M4A → PCM
        cmd_ffmpeg = [
            ffmpeg_path, "-y", "-i", input_path,
            "-vn", "-ar", "24000", "-ac", "1", "-f", "s16le", pcm_path
        ]
        proc = await asyncio.create_subprocess_exec(*cmd_ffmpeg)
        await proc.wait()
        
        if not os.path.exists(pcm_path):
            print(f"[音乐进程] PCM 生成失败")
            return None
        
        # PCM → SILK
        cmd_silk = [
            silk_encoder_path, pcm_path, silk_path,
            "-Fs_API", "24000", "-rate", "24000"
        ]
        proc = await asyncio.create_subprocess_exec(*cmd_silk)
        await proc.wait()
        
        # 清理 PCM
        if os.path.exists(pcm_path):
            os.remove(pcm_path)
        
        if os.path.exists(silk_path):
            print(f"[音乐进程] SILK 转换成功: {silk_path}")
            return silk_path
        return None
    except Exception as e:
        print(f"[音乐进程] SILK 转换失败: {e}")
        return None


# ==================== 发送函数 ====================

async def send_via_http_m4a(group_id: int, filepath: str) -> bool:
    """方案一：HTTP 发送 M4A（NapCat 自己转码）"""
    try:
        with open(filepath, "rb") as f:
            audio_base64 = base64.b64encode(f.read()).decode()
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://127.0.0.1:3000/send_group_msg",
                json={
                    "group_id": group_id,
                    "message": f"[CQ:record,file=base64://{audio_base64}]"
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result.get("status") == "ok"
                return False
    except Exception as e:
        print(f"[音乐进程] HTTP 发送 M4A 异常: {e}")
        return False


async def send_via_http_amr(group_id: int, filepath: str) -> bool:
    """方案二：HTTP 发送 AMR（备用）"""
    try:
        with open(filepath, "rb") as f:
            audio_base64 = base64.b64encode(f.read()).decode()
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://127.0.0.1:3000/send_group_msg",
                json={
                    "group_id": group_id,
                    "message": f"[CQ:record,file=base64://{audio_base64}]"
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result.get("status") == "ok"
                return False
    except Exception as e:
        print(f"[音乐进程] HTTP 发送 AMR 异常: {e}")
        return False


async def send_via_websocket(group_id: int, amr_path: str, silk_path: str, ws_url: str):
    """方案三：WebSocket 本地发送 AMR + SILK（最终备用）"""
    try:
        async with websockets.connect(ws_url) as ws:
            if amr_path and os.path.exists(amr_path):
                amr_abs = os.path.abspath(amr_path)
                await ws.send(json.dumps({
                    "action": "send_msg",
                    "params": {
                        "message_type": "group",
                        "group_id": group_id,
                        "message": f"[CQ:record,file=file:///{amr_abs.replace('\\', '/')}]"
                    }
                }))
                print(f"[音乐进程] WebSocket 发送 AMR 成功")
            
            if silk_path and os.path.exists(silk_path):
                silk_abs = os.path.abspath(silk_path)
                await ws.send(json.dumps({
                    "action": "send_msg",
                    "params": {
                        "message_type": "group",
                        "group_id": group_id,
                        "message": f"[CQ:record,file=file:///{silk_abs.replace('\\', '/')}]"
                    }
                }))
                print(f"[音乐进程] WebSocket 发送 SILK 成功")
            
            return True
    except Exception as e:
        print(f"[音乐进程] WebSocket 发送失败: {e}")
        return False


# ==================== 主任务 ====================

async def send_audio_task(group_id: int, filepath: str, ws_url: str):
    """完整点歌发送任务（三保险）"""
    print(f"[音乐进程] 开始处理: group_id={group_id}, file={filepath}")
    
    # 先转好备用格式
    amr_path = await convert_to_amr(filepath)
    silk_path = await convert_to_silk(filepath)
    
    # ===== 方案一：HTTP 发送 M4A（NapCat 自己转码，手机兼容最好） =====
    print(f"[音乐进程] 方案一: HTTP 发送 M4A...")
    success = await send_via_http_m4a(group_id, filepath)
    if success:
        print(f"[音乐进程] ✅ 方案一成功")
        return
    
    # ===== 方案二：HTTP 发送 AMR（NapCat 转 AMR） =====
    if amr_path and os.path.exists(amr_path):
        print(f"[音乐进程] 方案二: HTTP 发送 AMR...")
        success = await send_via_http_amr(group_id, amr_path)
        if success:
            print(f"[音乐进程] ✅ 方案二成功")
            return
    
    # ===== 方案三：WebSocket 本地发送 AMR + SILK（最终备用） =====
    print(f"[音乐进程] 方案三: WebSocket 本地发送 AMR + SILK...")
    success = await send_via_websocket(group_id, amr_path, silk_path, ws_url)
    if success:
        print(f"[音乐进程] ✅ 方案三成功")
    else:
        print(f"[音乐进程] ❌ 所有方案均失败")


# ==================== 入口 ====================

if __name__ == "__main__":
    try:
        group_id = int(sys.argv[1])
        filepath = sys.argv[2]
        ws_url = sys.argv[3] if len(sys.argv) > 3 else "ws://127.0.0.1:8765"
        
        print(f"[音乐进程] 启动参数: group_id={group_id}, file={filepath}, ws_url={ws_url}")
        asyncio.run(send_audio_task(group_id, filepath, ws_url))
        print(f"[音乐进程] 任务完成，退出")
    except Exception as e:
        print(f"[音乐进程] 启动失败: {e}")
        import traceback
        traceback.print_exc()
