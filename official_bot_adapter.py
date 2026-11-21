import asyncio
import aiohttp
import requests
import websockets
import json
import time
import os
import sys
import hashlib
import re
from aiohttp import web
from typing import Optional

# ========== 配置（从 config.json 读取）==========
# ========== HTTP 服务配置 ==========
HTTP_PORT = 3001
msg_queue = []  # 官方消息队列，主程序来取

# ========== 配置读取（config.json，唯一配置来源）==========
def load_config():
    """读取同目录下的 config.json，作为全局唯一配置来源"""
    cfg = {}
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json"), "r", encoding="utf-8") as f:
            cfg = json.load(f)
        print("[官方适配] ✅ 已读取 config.json")
    except FileNotFoundError:
        print("[官方适配] ⚠️ 未找到 config.json，将使用默认值")
    except Exception as e:
        print(f"[官方适配] ⚠️ config.json 读取失败: {e}")
    return cfg

CONFIG = load_config()

APP_ID = CONFIG.get("QQ_OFFICIAL_APP_ID") or ""
APP_SECRET = CONFIG.get("QQ_OFFICIAL_APP_SECRET") or ""
BOT_QQ = CONFIG.get("QQ_OFFICIAL_BOT_QQ") or ""
ACCESS_TOKEN = None
TOKEN_EXPIRE_TIME = 0
WS_URL = None
handler = None
BOT_OPENID = None  # 机器人自身 OpenID（首次请求后缓存）

if APP_ID:
    print(f"[官方适配] ✅ 已读取 APP_ID: {APP_ID[:6]}...")
if BOT_QQ:
    print(f"[官方适配] ✅ 机器人QQ号: {BOT_QQ}")

# ========== Token 管理 ==========
def get_access_token_sync():
    global ACCESS_TOKEN, TOKEN_EXPIRE_TIME
    print(f"[官方适配] 当前使用的 APP_ID: {APP_ID}")
    if not APP_ID or not APP_SECRET:
        print(f"[官方适配] ❌ 缺少 APP_ID 或 APP_SECRET (APP_ID='{APP_ID}', APP_SECRET长度={len(APP_SECRET)})，无法获取 Token")
        return None
    url = "https://api.bot.qq.com/app/getAppAccessToken"
    payload = {"appId": APP_ID, "clientSecret": APP_SECRET}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        print(f"[官方适配] HTTP 状态码: {resp.status_code}")
        raw_text = resp.text
        print(f"[官方适配] 响应原文: {raw_text}")
        try:
            data = resp.json()
        except Exception:
            data = {"raw_text": raw_text}
        if "access_token" in data:
            ACCESS_TOKEN = data.get("access_token")
            TOKEN_EXPIRE_TIME = time.time() + int(data.get("expires_in", 7200)) - 60
            print(f"[官方适配] ✅ Token 自动获取成功，有效期至 {time.ctime(TOKEN_EXPIRE_TIME)}")
            return ACCESS_TOKEN
        else:
            print(f"[官方适配] ❌ Token 失败: {data}")
            return None
    except Exception as e:
        print(f"[官方适配] ❌ Token 请求异常: {type(e).__name__}: {e}")
        return None

def ensure_token():
    global ACCESS_TOKEN
    if not ACCESS_TOKEN or time.time() >= TOKEN_EXPIRE_TIME:
        print("[官方适配] 🔄 Token 即将过期，自动刷新...")
        ACCESS_TOKEN = get_access_token_sync()
    return ACCESS_TOKEN

# ========== 机器人自身 OpenID 获取 ==========
async def get_bot_openid() -> str:
    """获取机器人自身 OpenID（GET /users/@me），成功则缓存到 BOT_OPENID。
    失败时输出明确警告并把 BOT_OPENID 留空。"""
    global BOT_OPENID
    if BOT_OPENID:
        return BOT_OPENID
    try:
        token = ensure_token()
        if not token:
            print("[官方适配] ❌ 获取机器人 OpenID 失败：无有效 Token")
            BOT_OPENID = ""
            return ""
        import aiohttp
        url = "https://api.sgroup.qq.com/users/@me"
        headers = {"Authorization": f"QQBot {token}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    bot_id = data.get("id", "") or ""
                    if bot_id:
                        BOT_OPENID = bot_id
                        print(f"[官方适配] ✅ 机器人自身 OpenID: {BOT_OPENID}")
                    else:
                        BOT_OPENID = ""
                        print(f"[官方适配] ⚠️ /users/@me 返回中未找到 id 字段: {data}")
                else:
                    err_text = await resp.text()
                    BOT_OPENID = ""
                    print(f"[官方适配] ❌ 获取机器人 OpenID 失败: HTTP {resp.status} - {err_text[:200]}")
    except Exception as e:
        BOT_OPENID = ""
        print(f"[官方适配] ❌ 获取机器人 OpenID 异常: {e}")
    return BOT_OPENID

def get_bot_openid_sync() -> str:
    """同步版：获取机器人自身 OpenID（供非 async 场景如 is_at_bot 调用）。
    与异步版共用 BOT_OPENID 缓存。"""
    global BOT_OPENID
    if BOT_OPENID:
        return BOT_OPENID
    try:
        token = ensure_token()
        if not token:
            print("[官方适配] ❌ 获取机器人 OpenID 失败：无有效 Token")
            BOT_OPENID = ""
            return ""
        url = "https://api.sgroup.qq.com/users/@me"
        headers = {"Authorization": f"QQBot {token}"}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            bot_id = data.get("id", "") or ""
            if bot_id:
                BOT_OPENID = bot_id
                print(f"[官方适配] ✅ 机器人自身 OpenID: {BOT_OPENID}")
            else:
                BOT_OPENID = ""
                print(f"[官方适配] ⚠️ /users/@me 返回中未找到 id 字段: {data}")
        else:
            BOT_OPENID = ""
            print(f"[官方适配] ❌ 获取机器人 OpenID 失败: HTTP {resp.status_code} - {resp.text[:200]}")
    except Exception as e:
        BOT_OPENID = ""
        print(f"[官方适配] ❌ 获取机器人 OpenID 异常: {e}")
    return BOT_OPENID

# ========== Gateway 获取 ==========
async def get_gateway_url(retries: int = 3, delay: float = 5.0):
    token = ensure_token()
    if not token:
        return None
    url = "https://api.bot.qq.com/gateway"
    headers = {"Authorization": f"QQBot {token}"}
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as resp:
                    data = await resp.json()
                    gw = data.get("url")
                    if gw:
                        if attempt > 1:
                            print(f"[官方适配] ✅ Gateway 第{attempt}次重试成功: {gw}")
                        return gw
                    print(f"[官方适配] ⚠️ Gateway 返回为空 (第{attempt}/{retries}次)")
        except Exception as e:
            last_err = e
            print(f"[官方适配] ⚠️ Gateway 异常 (第{attempt}/{retries}次): {e}")
        if attempt < retries:
            print(f"[官方适配] ⏳ {delay}s 后重试 Gateway...")
            await asyncio.sleep(delay)
    print(f"[官方适配] ❌ Gateway 重试{retries}次均失败: {last_err}")
    return None

# ========== WebSocket 连接（兼容）==========
async def ws_connect_with_header(uri, headers):
    for header_name in ["extra_headers", "additional_headers", "http_headers"]:
        try:
            return await websockets.connect(uri, **{header_name: headers}, ping_interval=20, ping_timeout=20)
        except TypeError:
            continue
    return await websockets.connect(uri, ping_interval=20, ping_timeout=20)

# ========== OpenID 转数字 ID ==========
def openid_to_int(openid):
    if not openid:
        return "0"
    h = hashlib.md5(openid.encode()).hexdigest()
    num = abs(int(h[:10], 16))
    return str(num)

# ========== 文件哈希计算 ==========
def calc_md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()

def calc_sha1(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()

def calc_md5_10m(data: bytes) -> str:
    chunk = data[:10002432]
    return hashlib.md5(chunk).hexdigest()

# ========== 图片上传 ==========
async def upload_image_official(user_openid: str, image_data: bytes, filename: str = "image.jpg"):
    token = ensure_token()
    if not token:
        return None
    
    headers = {"Authorization": f"QQBot {token}", "Content-Type": "application/json"}
    
    file_md5 = calc_md5(image_data)
    file_sha1 = calc_sha1(image_data)
    file_md5_10m = calc_md5_10m(image_data)
    file_size = str(len(image_data))
    
    preupload_url = f"https://api.bot.qq.com/v2/users/{user_openid}/upload_prepare"
    payload = {
        "file_type": 1,
        "file_size": file_size,
        "file_name": filename,
        "md5": file_md5,
        "sha1": file_sha1,
        "md5_10m": file_md5_10m
    }
    
    print(f"[官方适配] 📤 预上传: {json.dumps(payload, ensure_ascii=False)}")
    
    async with aiohttp.ClientSession() as session:
        async with session.post(preupload_url, json=payload, headers=headers, timeout=10) as resp:
            if resp.status != 200:
                text = await resp.text()
                print(f"[官方适配] ❌ 预上传失败: {resp.status} - {text[:200]}")
                return None
            data = await resp.json()
            upload_id = data.get("upload_id")
            parts = data.get("parts", [])
            block_size = data.get("block_size")
            if not upload_id or not parts:
                print(f"[官方适配] ❌ 预上传返回异常: {data}")
                return None
            presigned_url = parts[0].get("presigned_url")
            part_index = parts[0].get("index", 1)
            print(f"[官方适配] ✅ 预上传成功，upload_id: {upload_id}, part_index: {part_index}")
        
        try:
            async with session.put(presigned_url, data=image_data, headers={"Content-Type": "application/octet-stream"}) as put_resp:
                if put_resp.status not in [200, 204]:
                    text = await put_resp.text()
                    print(f"[官方适配] ❌ 上传文件内容失败: {put_resp.status} - {text[:200]}")
                    return None
                etag = put_resp.headers.get('ETag', '').strip('"')
                print(f"[官方适配] ✅ 文件内容上传成功, ETag: {etag}")
        except Exception as e:
            print(f"[官方适配] ❌ 上传文件内容异常: {e}")
            return None
        
        part_finish_url = f"https://api.bot.qq.com/v2/users/{user_openid}/upload_part_finish"
        part_finish_payload = {
            "upload_id": upload_id,
            "part_index": part_index,
            "block_size": block_size,
            "md5": file_md5
        }
        print(f"[官方适配] 📤 分片完成确认: {json.dumps(part_finish_payload, ensure_ascii=False)}")
        
        try:
            async with session.post(part_finish_url, json=part_finish_payload, headers=headers, timeout=10) as pf_resp:
                if pf_resp.status != 200:
                    text = await pf_resp.text()
                    print(f"[官方适配] ❌ 分片完成确认失败: {pf_resp.status} - {text[:200]}")
                    return None
                try:
                    resp_text = await pf_resp.text()
                    if resp_text and resp_text.strip():
                        print(f"[官方适配] ✅ 分片完成确认响应: {resp_text[:200]}")
                    else:
                        print("[官方适配] ✅ 分片完成确认成功（空响应）")
                except:
                    print("[官方适配] ✅ 分片完成确认成功")
        except Exception as e:
            print(f"[官方适配] ❌ 分片完成确认异常: {e}")
            print("[官方适配] ⚠️ 分片确认异常，但继续尝试合并...")
        
        print("[官方适配] ⏳ 等待服务端处理...")
        await asyncio.sleep(2)
        
        finalize_url = f"https://api.bot.qq.com/v2/users/{user_openid}/files"
        finalize_payload = {
            "file_type": 1,
            "upload_id": upload_id,
            "srv_send_msg": False,
            "file_name": filename
        }
        print(f"[官方适配] 📤 合并上传: {json.dumps(finalize_payload, ensure_ascii=False)}")
        
        try:
            async with session.post(finalize_url, json=finalize_payload, headers=headers, timeout=10) as finalize_resp:
                if finalize_resp.status != 200:
                    text = await finalize_resp.text()
                    print(f"[官方适配] ❌ 合并上传失败: {finalize_resp.status} - {text[:200]}")
                    return None
                data = await finalize_resp.json()
                file_info = data.get("file_info")
                if file_info:
                    print(f"[官方适配] ✅ 合并上传成功，file_info 长度: {len(file_info)}")
                    return file_info
                else:
                    print(f"[官方适配] ❌ 未获取到 file_info: {data}")
                    return None
        except Exception as e:
            print(f"[官方适配] ❌ 合并上传异常: {e}")
            return None

async def upload_image_official_group(group_openid: str, image_data: bytes, filename: str = "image.jpg"):
    token = ensure_token()
    if not token:
        return None
    
    headers = {"Authorization": f"QQBot {token}", "Content-Type": "application/json"}
    
    file_md5 = calc_md5(image_data)
    file_sha1 = calc_sha1(image_data)
    file_md5_10m = calc_md5_10m(image_data)
    file_size = str(len(image_data))
    
    preupload_url = f"https://api.bot.qq.com/v2/groups/{group_openid}/upload_prepare"
    payload = {
        "file_type": 1,
        "file_size": file_size,
        "file_name": filename,
        "md5": file_md5,
        "sha1": file_sha1,
        "md5_10m": file_md5_10m
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(preupload_url, json=payload, headers=headers, timeout=10) as resp:
            if resp.status != 200:
                text = await resp.text()
                print(f"[官方适配] ❌ 群聊预上传失败: {resp.status} - {text[:200]}")
                return None
            data = await resp.json()
            upload_id = data.get("upload_id")
            parts = data.get("parts", [])
            block_size = data.get("block_size")
            if not upload_id or not parts:
                return None
            presigned_url = parts[0].get("presigned_url")
            part_index = parts[0].get("index", 1)
            print(f"[官方适配] ✅ 群聊预上传成功，upload_id: {upload_id}")
        
        try:
            async with session.put(presigned_url, data=image_data, headers={"Content-Type": "application/octet-stream"}) as put_resp:
                if put_resp.status not in [200, 204]:
                    text = await put_resp.text()
                    print(f"[官方适配] ❌ 群聊上传文件内容失败: {put_resp.status} - {text[:200]}")
                    return None
                etag = put_resp.headers.get('ETag', '').strip('"')
                print(f"[官方适配] ✅ 群聊文件内容上传成功, ETag: {etag}")
        except Exception as e:
            print(f"[官方适配] ❌ 群聊上传文件内容异常: {e}")
            return None
        
        part_finish_url = f"https://api.bot.qq.com/v2/groups/{group_openid}/upload_part_finish"
        part_finish_payload = {
            "upload_id": upload_id,
            "part_index": part_index,
            "block_size": block_size,
            "md5": file_md5
        }
        print(f"[官方适配] 📤 群聊分片完成确认: {json.dumps(part_finish_payload, ensure_ascii=False)}")
        
        try:
            async with session.post(part_finish_url, json=part_finish_payload, headers=headers, timeout=10) as pf_resp:
                if pf_resp.status != 200:
                    text = await pf_resp.text()
                    print(f"[官方适配] ❌ 群聊分片完成确认失败: {pf_resp.status} - {text[:200]}")
                    return None
                try:
                    resp_text = await pf_resp.text()
                    if resp_text and resp_text.strip():
                        print(f"[官方适配] ✅ 群聊分片完成确认响应: {resp_text[:200]}")
                    else:
                        print("[官方适配] ✅ 群聊分片完成确认成功（空响应）")
                except:
                    print("[官方适配] ✅ 群聊分片完成确认成功")
        except Exception as e:
            print(f"[官方适配] ❌ 群聊分片完成确认异常: {e}")
            print("[官方适配] ⚠️ 分片确认异常，但继续尝试合并...")
        
        print("[官方适配] ⏳ 等待服务端处理...")
        await asyncio.sleep(2)
        
        finalize_url = f"https://api.bot.qq.com/v2/groups/{group_openid}/files"
        finalize_payload = {
            "file_type": 1,
            "upload_id": upload_id,
            "srv_send_msg": False,
            "file_name": filename
        }
        
        try:
            async with session.post(finalize_url, json=finalize_payload, headers=headers, timeout=10) as finalize_resp:
                if finalize_resp.status != 200:
                    text = await finalize_resp.text()
                    print(f"[官方适配] ❌ 群聊合并上传失败: {finalize_resp.status} - {text[:200]}")
                    return None
                data = await finalize_resp.json()
                file_info = data.get("file_info")
                if file_info:
                    print(f"[官方适配] ✅ 群聊合并上传成功")
                    return file_info
                else:
                    print(f"[官方适配] ❌ 群聊未获取到 file_info: {data}")
                    return None
        except Exception as e:
            print(f"[官方适配] ❌ 群聊合并上传异常: {e}")
            return None

# ========== 语音上传（file_type=3）==========
async def upload_voice_official(user_openid: str, voice_data: bytes, filename: str = "voice.m4a"):
    token = ensure_token()
    if not token:
        return None
    
    headers = {"Authorization": f"QQBot {token}", "Content-Type": "application/json"}
    
    file_md5 = calc_md5(voice_data)
    file_sha1 = calc_sha1(voice_data)
    file_md5_10m = calc_md5_10m(voice_data)
    file_size = str(len(voice_data))
    
    preupload_url = f"https://api.bot.qq.com/v2/users/{user_openid}/upload_prepare"
    payload = {
        "file_type": 3,
        "file_size": file_size,
        "file_name": filename,
        "md5": file_md5,
        "sha1": file_sha1,
        "md5_10m": file_md5_10m
    }
    
    print(f"[官方适配] 📤 语音预上传: {json.dumps(payload, ensure_ascii=False)}")
    
    async with aiohttp.ClientSession() as session:
        async with session.post(preupload_url, json=payload, headers=headers, timeout=10) as resp:
            if resp.status != 200:
                text = await resp.text()
                print(f"[官方适配] ❌ 语音预上传失败: {resp.status} - {text[:200]}")
                return None
            data = await resp.json()
            upload_id = data.get("upload_id")
            parts = data.get("parts", [])
            block_size = data.get("block_size")
            if not upload_id or not parts:
                print(f"[官方适配] ❌ 语音预上传返回异常: {data}")
                return None
            presigned_url = parts[0].get("presigned_url")
            part_index = parts[0].get("index", 1)
            print(f"[官方适配] ✅ 语音预上传成功，upload_id: {upload_id}")
        
        try:
            async with session.put(presigned_url, data=voice_data, headers={"Content-Type": "application/octet-stream"}) as put_resp:
                if put_resp.status not in [200, 204]:
                    text = await put_resp.text()
                    print(f"[官方适配] ❌ 语音上传失败: {put_resp.status} - {text[:200]}")
                    return None
                etag = put_resp.headers.get('ETag', '').strip('"')
                print(f"[官方适配] ✅ 语音内容上传成功, ETag: {etag}")
        except Exception as e:
            print(f"[官方适配] ❌ 语音上传异常: {e}")
            return None
        
        part_finish_url = f"https://api.bot.qq.com/v2/users/{user_openid}/upload_part_finish"
        part_finish_payload = {
            "upload_id": upload_id,
            "part_index": part_index,
            "block_size": block_size,
            "md5": file_md5
        }
        
        try:
            async with session.post(part_finish_url, json=part_finish_payload, headers=headers, timeout=10) as pf_resp:
                if pf_resp.status != 200:
                    text = await pf_resp.text()
                    print(f"[官方适配] ❌ 语音分片完成确认失败: {pf_resp.status} - {text[:200]}")
                    return None
                print("[官方适配] ✅ 语音分片完成确认成功")
        except Exception as e:
            print(f"[官方适配] ❌ 语音分片完成确认异常: {e}")
        
        await asyncio.sleep(2)
        
        finalize_url = f"https://api.bot.qq.com/v2/users/{user_openid}/files"
        finalize_payload = {
            "file_type": 3,
            "upload_id": upload_id,
            "srv_send_msg": False,
            "file_name": filename
        }
        
        try:
            async with session.post(finalize_url, json=finalize_payload, headers=headers, timeout=10) as finalize_resp:
                if finalize_resp.status != 200:
                    text = await finalize_resp.text()
                    print(f"[官方适配] ❌ 语音合并失败: {finalize_resp.status} - {text[:200]}")
                    return None
                data = await finalize_resp.json()
                file_info = data.get("file_info")
                if file_info:
                    print(f"[官方适配] ✅ 语音合并成功，file_info 长度: {len(file_info)}")
                    return file_info
                else:
                    print(f"[官方适配] ❌ 未获取到 file_info: {data}")
                    return None
        except Exception as e:
            print(f"[官方适配] ❌ 语音合并异常: {e}")
            return None

async def upload_voice_official_group(group_openid: str, voice_data: bytes, filename: str = "voice.m4a"):
    """群聊上传语音 - 必须用 file_type=4（语音），否则 QQ 会渲染成文件而不是语音！

    【重试与降级】：
      1. 预上传最多重试 3 次，每次失败 sleep(2) 后再试；
      2. 强制超时：total=60 / connect=15 / sock_read=30（宽容 WinError 121）；
      3. 3 次全失败 → 返回 None（由调用方降级为纯文本提示），绝不抛出卡死事件循环；
      4. 分片上传严格按 parts 逐片 PUT + part_finish + /files 合并。
    """
    token = ensure_token()
    if not token:
        print("[官方适配] ❌ 无有效 Token，无法上传语音")
        return None

    headers = {"Authorization": f"QQBot {token}", "Content-Type": "application/json"}

    file_md5 = calc_md5(voice_data)
    file_sha1 = calc_sha1(voice_data)
    file_md5_10m = calc_md5_10m(voice_data)
    file_size = str(len(voice_data))

    preupload_url = f"https://api.bot.qq.com/v2/groups/{group_openid}/upload_prepare"
    payload = {
        "file_type": 3,   # ← 语音必须用 3！官方文档：1=图片 2=视频 3=语音 4=文件
        "file_size": file_size,
        "file_name": filename,
        "md5": file_md5,
        "sha1": file_sha1,
        "md5_10m": file_md5_10m
    }

    try:
        async with aiohttp.ClientSession() as session:
            # ===== 1. 预上传（带 3 次重试） =====
            upload_id = None
            parts = []
            preupload_ok = False
            for attempt in range(1, 4):
                try:
                    async with session.post(
                        preupload_url, json=payload, headers=headers,
                        timeout=aiohttp.ClientTimeout(total=60, connect=15, sock_read=30)
                    ) as resp:
                        if resp.status != 200:
                            text = await resp.text()
                            print(f"[官方适配] ❌ 群聊语音预上传失败（第{attempt}次）: HTTP {resp.status} - {text[:200]}")
                        else:
                            data = await resp.json()
                            upload_id = data.get("upload_id")
                            parts = data.get("parts", [])
                            if upload_id and parts:
                                preupload_ok = True
                                print(f"[官方适配] ✅ 群聊语音预上传成功，upload_id: {upload_id}, 分片数: {len(parts)}")
                                break
                            print(f"[官方适配] ⚠️ 群聊语音预上传响应缺 upload_id/parts（第{attempt}次）")
                except asyncio.TimeoutError:
                    print(f"[官方适配] ⏱️ 群聊语音预上传超时（第{attempt}次，WinError 121 类），稍后重试")
                except aiohttp.ClientError as ce:
                    print(f"[官方适配] ❌ 群聊语音预上传网络错误（第{attempt}次）: {type(ce).__name__}: {ce}")
                except Exception as e:
                    print(f"[官方适配] ❌ 群聊语音预上传异常（第{attempt}次）: {type(e).__name__}: {e}")

                if attempt < 3:
                    try:
                        await asyncio.sleep(2)
                    except Exception:
                        pass

            if not preupload_ok:
                print(f"[官方适配] 🚫 群聊语音预上传 3 次均失败，返回 None 由调用方降级")
                return None

            # ===== 2. 逐片上传 + 确认 =====
            for part in parts:
                part_index = part.get("index", 1)
                presigned_url = part.get("presigned_url")
                block_size = int(part.get("block_size", 0))

                start = (part_index - 1) * block_size
                end = min(start + block_size, len(voice_data))
                chunk = voice_data[start:end]
                actual_size = len(chunk)
                chunk_md5 = hashlib.md5(chunk).hexdigest()

                # PUT 上传
                try:
                    async with session.put(
                        presigned_url, data=chunk,
                        headers={"Content-Type": "application/octet-stream"},
                        timeout=aiohttp.ClientTimeout(total=60, connect=15, sock_read=30)
                    ) as put_resp:
                        if put_resp.status not in [200, 204]:
                            text = await put_resp.text()
                            print(f"[官方适配] ❌ 分片 {part_index} 上传失败: {put_resp.status}")
                            return None
                except (asyncio.TimeoutError, aiohttp.ClientError) as ce:
                    print(f"[官方适配] ❌ 分片 {part_index} 上传异常: {type(ce).__name__}: {ce}")
                    return None

                # 确认分片
                part_finish_url = f"https://api.bot.qq.com/v2/groups/{group_openid}/upload_part_finish"
                part_finish_payload = {
                    "upload_id": upload_id,
                    "part_index": part_index,
                    "block_size": str(actual_size),
                    "md5": chunk_md5
                }
                try:
                    async with session.post(
                        part_finish_url, json=part_finish_payload, headers=headers,
                        timeout=aiohttp.ClientTimeout(total=60, connect=15, sock_read=30)
                    ) as pf_resp:
                        if pf_resp.status != 200:
                            text = await pf_resp.text()
                            print(f"[官方适配] ❌ 分片 {part_index} 确认失败: {pf_resp.status} - {text[:200]}")
                            return None
                except (asyncio.TimeoutError, aiohttp.ClientError) as ce:
                    print(f"[官方适配] ❌ 分片 {part_index} 确认异常: {type(ce).__name__}: {ce}")
                    return None

            # 等待处理
            await asyncio.sleep(2)

            # ===== 3. 合并上传（语音也用 file_type = 3） =====
            finalize_url = f"https://api.bot.qq.com/v2/groups/{group_openid}/files"
            finalize_payload = {
                "file_type": 3,
                "upload_id": upload_id,
                "srv_send_msg": False,
                "file_name": filename
            }
            try:
                async with session.post(
                    finalize_url, json=finalize_payload, headers=headers,
                    timeout=aiohttp.ClientTimeout(total=60, connect=15, sock_read=30)
                ) as finalize_resp:
                    if finalize_resp.status != 200:
                        text = await finalize_resp.text()
                        print(f"[官方适配] ❌ 群聊语音合并失败: {finalize_resp.status} - {text[:200]}")
                        return None
                    data = await finalize_resp.json()
                    file_info = data.get("file_info")
                    if file_info:
                        print(f"[官方适配] ✅ 群聊语音合并成功")
                        return file_info
                    else:
                        print(f"[官方适配] ❌ 群聊语音未获取到 file_info: {data}")
                        return None
            except (asyncio.TimeoutError, aiohttp.ClientError) as ce:
                print(f"[官方适配] ❌ 群聊语音合并异常: {type(ce).__name__}: {ce}")
                return None
    except Exception as e:
        print(f"[官方适配] 🚫 群聊语音上传整体异常（已降级）: {type(e).__name__}: {e}")
        return None

# ========== 视频上传 ==========
# 官方富媒体上传策略：
#   · < 5MB → 直接上传二进制（POST /v2/groups/{group_openid}/files, file_type=2, file_data base64）
#   · >= 5MB → 分片上传（upload_prepare → PUT 分片 → part_finish → /files 合并）
_VIDEO_SMALL_LIMIT = 5 * 1024 * 1024  # 5MB

async def upload_video_official_group(group_openid: str, video_data: bytes, filename: str = "video.mp4"):
    """群聊上传视频，返回 file_info。小文件直接传，大文件分片传。"""
    token = ensure_token()
    if not token:
        print("[官方适配] ❌ 视频上传失败：无有效 Token")
        return None
    file_size = len(video_data)
    file_md5 = calc_md5(video_data)
    print(f"[官方适配] 📤 视频上传: {filename} ({file_size} bytes) 模式={'直接' if file_size < _VIDEO_SMALL_LIMIT else '分片'}")

    if file_size < _VIDEO_SMALL_LIMIT:
        # ===== < 5MB：直接上传二进制 =====
        return await _upload_video_direct(group_openid, video_data, filename)
    else:
        # ===== >= 5MB：分片上传 =====
        return await _upload_video_chunked(group_openid, video_data, filename)

async def _upload_video_direct(group_openid: str, video_data: bytes, filename: str):
    """直接上传（<5MB）：POST /files，file_type=2 + file_data(base64 二进制)"""
    import base64
    import traceback
    try:
        token = ensure_token()
        headers = {"Authorization": f"QQBot {token}", "Content-Type": "application/json"}
        file_md5 = calc_md5(video_data)
        file_sha1 = calc_sha1(video_data)
        file_size = str(len(video_data))
        files_url = f"https://api.bot.qq.com/v2/groups/{group_openid}/files"
        payload = {
            "file_type": 2,
            "file_data": base64.b64encode(video_data).decode("ascii"),
            "file_size": file_size,
            "file_name": filename,
            "md5": file_md5,
            "sha1": file_sha1,
            "srv_send_msg": False,
        }
        print(f"[官方适配] 📤 视频直接上传: url={files_url} size={file_size}")
        async with aiohttp.ClientSession() as session:
            async with session.post(files_url, json=payload, headers=headers, timeout=60) as resp:
                resp_body = await resp.text()
                if resp.status == 200:
                    data = await resp.json()
                    file_info = data.get("file_info")
                    if file_info:
                        print(f"[官方适配] ✅ 视频直接上传成功, file_info={str(file_info)[:120]}...")
                        return file_info
                    print(f"[官方适配] ❌ 视频直接上传未获取到 file_info: {data}")
                    return None
                else:
                    print(f"[官方适配] ❌ 视频直接上传失败(完整): HTTP {resp.status} - {resp_body}")
                    return None
    except Exception as e:
        print(f"[官方适配] ❌ 视频直接上传异常: {type(e).__name__}: {e}\n{traceback.format_exc()}")
        return None

async def _upload_video_chunked(group_openid: str, video_data: bytes, filename: str):
    """分片上传（>=5MB）：upload_prepare → PUT 各片（严格校验） → part_finish → /files 合并

    修复要点：
      · 用 math.ceil 精确计算分片数，杜绝最后一刀越界多跑一次 / 读到空分片。
      · 每次取分片前显式定位 offset（等价于 f.seek），取完后加空分片保护。
      · PUT 的 timeout 使用 aiohttp.ClientTimeout 对象，禁止直接传整数。
      · aiohttp.ClientSession 在分片循环外只创建一次。
      · 每个分片 PUT 捕获 aiohttp.ClientOSError / asyncio.TimeoutError，最多重试 3 次，
        重试前 await asyncio.sleep(2 ** attempt) 指数退避。
      · 所有 raise 都携带具体错误上下文，禁止空消息。
    """
    import traceback
    import math
    try:
        token = ensure_token()
        headers = {"Authorization": f"QQBot {token}", "Content-Type": "application/json"}
        file_md5 = calc_md5(video_data)
        file_sha1 = calc_sha1(video_data)
        file_md5_10m = calc_md5_10m(video_data)
        file_size = len(video_data)
        if file_size <= 0:
            raise ValueError(f"视频数据为空，无法分片上传（{filename}）")
        preupload_url = f"https://api.bot.qq.com/v2/groups/{group_openid}/upload_prepare"
        payload = {
            "file_type": 4,
            "file_size": str(file_size),
            "file_name": filename,
            "md5": file_md5,
            "sha1": file_sha1,
            "md5_10m": file_md5_10m
        }
        # ===== Session 在循环外只创建一次；timeout 用 ClientTimeout 对象 =====
        timeout = aiohttp.ClientTimeout(total=120)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # 1) 预上传
            async with session.post(preupload_url, json=payload, headers=headers,
                                    timeout=aiohttp.ClientTimeout(total=120)) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    print(f"[官方适配] ❌ 群聊视频预上传失败: {resp.status} - {text[:200]}")
                    return None
                data = await resp.json()
                upload_id = data.get("upload_id")
                parts = data.get("parts", [])
                block_size = data.get("block_size")
                if block_size is not None:
                    block_size = int(block_size)
                if not upload_id or not parts:
                    print(f"[官方适配] ❌ 群聊视频预上传返回异常: {data}")
                    return None
                if block_size <= 0:
                    raise ValueError(f"预上传返回的 block_size 无效: {block_size}（{filename}）")
                print(f"[官方适配] ✅ 群聊视频预上传成功，upload_id={upload_id}, 分片数={len(parts)}, block_size={block_size}")
            # 2) 逐片 PUT（最后一块允许不足 block_size，其余必须精确）
            _total_parts = len(parts)
            # 精确计算应切分片数，防止末尾越界 / 空分片
            expected_total = math.ceil(file_size / block_size)
            if expected_total != _total_parts:
                print(f"[官方适配] ⚠️ 分片数不一致: 服务端={_total_parts} 本地计算={expected_total}，以实际上传分片为准")
            # 记录实际成功上传的分片（后续确认 / 合并只认这些分片，跳过空分片）
            uploaded_parts = []
            for part in parts:
                part_index = part.get("index", 1)
                presigned_url = part.get("presigned_url")
                actual_block_size = int(part.get("block_size", block_size or 0))
                _bs = int(block_size) if block_size else 0
                # 服务端 index 为 1 起；显式定位 offset（等价于 f.seek(offset)），再取分片
                offset = (part_index - 1) * _bs
                expected_bytes = video_data[offset:offset + _bs] if _bs else b""
                # 空分片保护：末尾空分片不再上传，直接跳过（不参与确认 / 合并）
                if not expected_bytes:
                    print(f"[官方适配] ⚠️ 分片 {part_index} 读取到空数据（文件末尾），跳过该空分片")
                    continue
                if _total_parts > 1 and part_index == _total_parts:
                    if len(expected_bytes) > actual_block_size:
                        raise ValueError(
                            f"分片 {part_index} 字节数超上限: 上限={actual_block_size} 实际={len(expected_bytes)}（{filename}）"
                        )
                else:
                    if len(expected_bytes) != actual_block_size:
                        raise ValueError(
                            f"分片 {part_index} 字节数不符: 期望={actual_block_size} 实际={len(expected_bytes)}（{filename}）"
                        )
                part_md5 = calc_md5(expected_bytes)
                # 分片 PUT 带重试（捕获 ClientOSError / TimeoutError，指数退避）
                await _put_video_part_with_retry(
                    session, presigned_url, expected_bytes, part_index, part_md5, filename
                )
                uploaded_parts.append(part_index)
            # 3) 只对实际成功上传的分片逐片确认（跳过空分片，避免对未上传分片做 part_finish 报 400）
            part_finish_url = f"https://api.bot.qq.com/v2/groups/{group_openid}/upload_part_finish"
            for part_index in uploaded_parts:
                _bs = int(block_size) if block_size else 0
                offset = (part_index - 1) * _bs
                _part_slice = video_data[offset:offset + _bs] if _bs else b""
                part_md5 = calc_md5(_part_slice)
                part_finish_payload = {
                    "upload_id": upload_id,
                    "part_index": part_index,
                    "block_size": len(_part_slice),
                    "md5": part_md5
                }
                async with session.post(part_finish_url, json=part_finish_payload, headers=headers,
                                        timeout=aiohttp.ClientTimeout(total=120)) as pf_resp:
                    if pf_resp.status != 200:
                        text = await pf_resp.text()
                        print(f"[官方适配] ❌ 分片 {part_index} 完成确认失败: HTTP {pf_resp.status} - {text[:200]}")
                        return None
                print(f"[官方适配] ✅ 分片 {part_index} 完成确认成功")
            # 4) 合并
            await asyncio.sleep(2)
            finalize_url = f"https://api.bot.qq.com/v2/groups/{group_openid}/files"
            finalize_payload = {"file_type": 4, "upload_id": upload_id, "srv_send_msg": False, "file_name": filename}
            async with session.post(finalize_url, json=finalize_payload, headers=headers,
                                    timeout=aiohttp.ClientTimeout(total=120)) as finalize_resp:
                resp_body = await finalize_resp.text()
                if finalize_resp.status != 200:
                    print(f"[官方适配] ❌ 群聊视频合并失败(完整): HTTP {finalize_resp.status} - {resp_body}")
                    return None
                data = await finalize_resp.json()
                file_info = data.get("file_info")
                if file_info:
                    print("[官方适配] ✅ 群聊视频合并成功")
                    return file_info
                else:
                    print(f"[官方适配] ❌ 群聊视频未获取到 file_info: {data}")
                    return None
    except Exception as e:
        print(f"[官方适配] ❌ 群聊视频分片上传异常: {type(e).__name__}: {e}\n{traceback.format_exc()}")
        return None


async def _put_video_part_with_retry(
    session: aiohttp.ClientSession,
    presigned_url: str,
    part_bytes: bytes,
    part_index: int,
    part_md5: str,
    filename: str,
) -> None:
    """单个视频分片的 PUT 上传，带最多 3 次重试与指数退避。

    捕获 aiohttp.ClientOSError（WinError 121 信号灯超时）与 asyncio.TimeoutError。
    """
    max_retries = 3
    attempt = 0
    while True:
        try:
            async with session.put(
                presigned_url, data=part_bytes,
                headers={"Content-Type": "application/octet-stream"},
                timeout=aiohttp.ClientTimeout(total=120),
            ) as put_resp:
                if put_resp.status not in (200, 204):
                    text = await put_resp.text()
                    raise aiohttp.ClientResponseError(
                        request_info=put_resp.request_info,
                        history=put_resp.history,
                        status=put_resp.status,
                        message=(
                            f"分片 {part_index} PUT 失败: HTTP {put_resp.status} "
                            f"- {text[:200]}（{filename}）"
                        ),
                    )
                etag = put_resp.headers.get('ETag', '').strip('"')
                print(f"[官方适配] ✅ 分片 {part_index} PUT 成功 ({len(part_bytes)} bytes, md5={part_md5[:8]}..., ETag={etag})")
                return  # 成功，直接返回

        except (aiohttp.ClientOSError, asyncio.TimeoutError) as exc:
            if attempt >= max_retries:
                raise RuntimeError(
                    f"分片 {part_index} 在 {max_retries} 次重试后仍失败: "
                    f"{type(exc).__name__}: {exc}（{filename}）"
                ) from exc
            print(f"[官方适配] ⏱️ 分片 {part_index} 上传 {type(exc).__name__}（第{attempt + 1}次），指数退避 {2 ** attempt}s 后重试")
            await asyncio.sleep(2 ** attempt)  # 指数退避：1s / 2s / 4s
            attempt += 1

        except aiohttp.ClientError as exc:
            if attempt >= max_retries:
                raise RuntimeError(
                    f"分片 {part_index} 在 {max_retries} 次重试后仍失败: "
                    f"{type(exc).__name__}: {exc}（{filename}）"
                ) from exc
            print(f"[官方适配] 🔄 分片 {part_index} 上传 {type(exc).__name__}（第{attempt + 1}次），指数退避 {2 ** attempt}s 后重试")
            await asyncio.sleep(2 ** attempt)
            attempt += 1

async def send_video_official_group(group_openid: str, video_data: bytes, filename: str = "video.mp4",
                                    msg_id: str = None) -> tuple:
    """官方 API 群聊发送视频（上传 + 发 msg_type=7 富媒体消息）。返回 (success, error)"""
    token = ensure_token()
    if not token:
        return False, "无有效 Token"
    file_info = await upload_video_official_group(group_openid, video_data, filename)
    if not file_info:
        return False, "视频上传失败（upload_video_official_group 返回空）"
    url = f"https://api.bot.qq.com/v2/groups/{group_openid}/messages"
    payload = {"msg_type": 7, "media": {"file_info": file_info}}
    if msg_id:
        payload["msg_id"] = msg_id
        seq = _msg_seq_counter.get(msg_id, 0) + 1
        _msg_seq_counter[msg_id] = seq
        payload["msg_seq"] = seq
    headers = {"Authorization": f"QQBot {token}", "Content-Type": "application/json"}
    print(f"[官方适配] 📤 群聊发送视频 msg_type=7 file_info={str(file_info)[:120]}... msg_id={msg_id}")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=120) as resp:
                resp_body = await resp.text()
                if resp.status == 200:
                    print("[官方适配] ✅ 群聊视频发送成功")
                    return True, None
                else:
                    print(f"[官方适配] ❌ 群聊视频发送失败(完整): HTTP {resp.status} - {resp_body}")
                    return False, f"HTTP {resp.status} {resp_body[:300]}"
    except Exception as e:
        import traceback
        print(f"[官方适配] ❌ 群聊视频发送异常(完整): {e!r}\n{traceback.format_exc()}")
        return False, f"异常[{type(e).__name__}] {e}"

async def download_image(url: str) -> Optional[bytes]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=15) as resp:
                if resp.status == 200:
                    return await resp.read()
                else:
                    print(f"[官方适配] ❌ 下载图片失败: {resp.status}")
                    return None
    except Exception as e:
        print(f"[官方适配] ❌ 下载图片异常: {e}")
        return None

def resolve_image_path(path: str) -> Optional[str]:
    if not path:
        return None
    if path.startswith('/'):
        path = path[1:]
    path = path.replace('/', '\\')
    if os.path.exists(path):
        return path
    alt1 = os.path.join(os.getcwd(), path)
    if os.path.exists(alt1):
        return alt1
    base_dir = os.path.dirname(os.path.abspath(__file__))
    alt2 = os.path.join(base_dir, path)
    if os.path.exists(alt2):
        return alt2
    if path.startswith('C:'):
        alt3 = path[3:]
        if os.path.exists(alt3):
            return alt3
    return None

# ========== 消息发送（支持纯文本 + 图片 + 语音）==========
async def send_message_official(message: str, user_openid=None, group_openid=None, official_msg_id=None):
    token = ensure_token()
    if not token:
        return False
    
    headers = {"Authorization": f"QQBot {token}", "Content-Type": "application/json"}
    
    # ===== 检测语音 CQ 码 =====
    voice_match = re.search(r'\[CQ:record,file=([^\]]+)\]', message)
    print(f"[官方适配] 🔍 语音CQ检测: matched={bool(voice_match)}, message[:100]={message[:100]}")
    if voice_match:
        file_ref = voice_match.group(1).strip()
        print(f"[官方适配] 🔍 语音file_ref={file_ref}")
        
        raw_path = file_ref
        if raw_path.startswith('file:///'):
            raw_path = raw_path[8:]
            print(f"[官方适配] 🔍 去掉file:///前缀后: {raw_path}")
        file_path = resolve_image_path(raw_path)
        print(f"[官方适配] 🔍 resolve_image_path 结果: {file_path}")
        if not file_path:
            print(f"[官方适配] ❌ 语音文件不存在: {raw_path}")
            return False
        
        try:
            with open(file_path, 'rb') as f:
                voice_data = f.read()
        except Exception as e:
            print(f"[官方适配] ❌ 读取语音失败: {e}")
            return False
        
        filename = os.path.basename(file_path)
        
        if user_openid:
            file_info = await upload_voice_official(user_openid, voice_data, filename)
        elif group_openid:
            file_info = await upload_voice_official_group(group_openid, voice_data, filename)
        else:
            return False
        
        if not file_info:
            print("[官方适配] ⚠️ 语音上传失败")
            return False
        
        if group_openid:
            url = f"https://api.bot.qq.com/v2/groups/{group_openid}/messages"
        elif user_openid:
            url = f"https://api.bot.qq.com/v2/users/{user_openid}/messages"
        else:
            return False
        
        payload = {
            "msg_type": 7,
            "media": {"file_info": file_info}
        }
        if official_msg_id:
            payload["msg_id"] = official_msg_id
            # msg_seq 递增避免去重
            seq = _msg_seq_counter.get(official_msg_id, 0) + 1
            _msg_seq_counter[official_msg_id] = seq
            payload["msg_seq"] = seq
        
        print(f"[官方适配] 📤 发送语音 (msg_type=7), file_info={str(file_info)[:200]}")

        # 带 3 次重试 + 强制超时，容忍 WinError 121；失败绝不抛出
        for attempt in range(1, 4):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url, json=payload, headers=headers,
                        timeout=aiohttp.ClientTimeout(total=60, connect=15, sock_read=30)
                    ) as resp:
                        if resp.status == 200:
                            print("[官方适配] ✅ 语音消息发送成功")
                            return True
                        else:
                            text = await resp.text()
                            print(f"[官方适配] ❌ 发送语音失败（第{attempt}次）: HTTP {resp.status} - {text[:200]}")
            except asyncio.TimeoutError:
                print(f"[官方适配] ⏱️ 发送语音超时（第{attempt}次，WinError 121 类），稍后重试")
            except aiohttp.ClientOSError as ce:
                print(f"[官方适配] ⏱️ 发送语音连接超时（第{attempt}次）: {ce}")
            except aiohttp.ClientError as ce:
                print(f"[官方适配] ❌ 发送语音网络错误（第{attempt}次）: {type(ce).__name__}: {ce}")
            except Exception as e:
                print(f"[官方适配] ❌ 发送语音异常（第{attempt}次）: {type(e).__name__}: {e}")

            if attempt < 3:
                try:
                    await asyncio.sleep(2)
                except Exception:
                    pass

        # 3 次都失败 → 降级为纯文本提示，绝不抛出
        try:
            await send_message_official("❌ 点歌成功，但语音发送超时，请稍后重试", group_openid=group_openid, official_msg_id=None)
        except Exception as e:
            print(f"[官方适配] ❌ 降级提示发送失败: {e}")
        return False
    
    # ===== 检测图片 CQ 码 =====
    img_match = re.search(r'\[CQ:image,file=([^\]]+)\]', message)
    if img_match:
        file_ref = img_match.group(1).strip()
        
        if file_ref.startswith('data:image'):
            import base64
            b64_data = file_ref.split(',', 1)[-1]
            image_data = base64.b64decode(b64_data)
            filename = "help.png"
        else:
            raw_path = file_ref
            if raw_path.startswith('file:///'):
                raw_path = raw_path[8:]
            file_path = resolve_image_path(raw_path)
            if not file_path:
                print(f"[官方适配] ❌ 图片不存在: {raw_path}")
                return False
            with open(file_path, 'rb') as f:
                image_data = f.read()
            filename = os.path.basename(file_path)
        
        if user_openid:
            file_info = await upload_image_official(user_openid, image_data, filename)
        elif group_openid:
            file_info = await upload_image_official_group(group_openid, image_data, filename)
        else:
            return False
        
        if not file_info:
            print("[官方适配] ⚠️ 上传失败，降级为文字消息")
            return await send_message_official(
                f"📷 图片: {file_path if 'file_path' in dir() else 'unknown'}",
                user_openid=user_openid,
                group_openid=group_openid,
                official_msg_id=official_msg_id
            )
        
        if group_openid:
            url = f"https://api.bot.qq.com/v2/groups/{group_openid}/messages"
        elif user_openid:
            url = f"https://api.bot.qq.com/v2/users/{user_openid}/messages"
        else:
            return False
        
        payload = {
            "msg_type": 7,
            "media": {"file_info": file_info}
        }
        if official_msg_id:
            payload["msg_id"] = official_msg_id
            seq = _msg_seq_counter.get(official_msg_id, 0) + 1
            _msg_seq_counter[official_msg_id] = seq
            payload["msg_seq"] = seq
        
        print(f"[官方适配] 📤 发送图片: {json.dumps(payload, ensure_ascii=False)}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, timeout=10) as resp:
                    if resp.status == 200:
                        print("[官方适配] ✅ 图片消息发送成功")
                        return True
                    else:
                        text = await resp.text()
                        print(f"[官方适配] ❌ 发送图片失败: {resp.status} - {text[:200]}")
                        return False
        except Exception as e:
            print(f"[官方适配] ❌ 发送图片异常: {e}")
            return False
    
    # ===== 纯文本消息 =====
    if group_openid:
        url = f"https://api.bot.qq.com/v2/groups/{group_openid}/messages"
    elif user_openid:
        url = f"https://api.bot.qq.com/v2/users/{user_openid}/messages"
    else:
        print(f"[官方适配] ❌ 无法发送文本：group_openid={group_openid}, user_openid={user_openid}")
        return False
    
    # ===== 官方模式：@ 用官方 mentions 结构，剥离 [CQ:at] 老格式 和 裸 <@openid> 文本 =====
    import re as _re
    _at_openids = []
    for _m in _re.finditer(r'\[CQ:at,qq=([^\]]+)\]', message):
        _v = _m.group(1).strip()
        if _v:
            _at_openids.append(user_id_map.get(str(_v), _v))
    for _m in _re.finditer(r'<@([^>]+)>', message):
        _v = _m.group(1).strip()
        if _v:
            _at_openids.append(user_id_map.get(str(_v), _v))
    # 剥离 [CQ:at] 老格式 与 裸 <@openid>，保留其它 CQ 码清理
    clean_content = _re.sub(r'\[CQ:at,qq=[^\]]+\]', '', message)
    clean_content = _re.sub(r'<@[^>]+>', '', clean_content)
    clean_content = _re.sub(r'\[CQ:[^\]]*\]', '', clean_content).strip()
    if not clean_content and not _at_openids:
        print(f"[官方适配] ⚠️ 去掉CQ码后消息为空，跳过发送")
        return True
    # 构造官方 mentions：{"openid": ..., "is_your_bot": ...}
    _bot_openid = get_bot_openid_sync()
    _mentions = []
    for _oid in dict.fromkeys(_at_openids):
        if _oid:
            _mentions.append({"openid": _oid, "is_your_bot": bool(_bot_openid and _oid == _bot_openid)})

    payload = {
        "msg_type": 0,
        "content": clean_content
    }
    if _mentions:
        payload["mentions"] = _mentions
    if official_msg_id:
        payload["msg_id"] = official_msg_id
        seq = _msg_seq_counter.get(official_msg_id, 0) + 1
        _msg_seq_counter[official_msg_id] = seq
        payload["msg_seq"] = seq
    
    print(f"[官方适配] 📤 发送文本: {json.dumps(payload, ensure_ascii=False)} (url={url})")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=10) as resp:
                resp_body = await resp.text()
                print(f"[官方适配] 发送文本 HTTP {resp.status}: {resp_body}")
                if resp.status == 200:
                    return True
                else:
                    print(f"[官方适配] ❌ 发送失败(完整): {resp.status} - {resp_body}")
                    return False
    except Exception as e:
        import traceback
        print(f"[官方适配] ❌ 发送异常(完整): {e!r}\n{traceback.format_exc()}")
        return False

# ========== 消息转换 ==========

# ===== 防重复推送缓存（按 msg_id 去重） =====
_seen_msg_ids = []
_SEEN_MAX = 500

def _is_duplicate_msg(msg_id: str) -> bool:
    """判断该 msg_id 是否已处理过；若没有则记录并返回 False。"""
    global _seen_msg_ids
    if not msg_id:
        return False
    if msg_id in _seen_msg_ids:
        return True
    _seen_msg_ids.append(msg_id)
    if len(_seen_msg_ids) > _SEEN_MAX:
        _seen_msg_ids = _seen_msg_ids[-_SEEN_MAX:]
    return False


# ========== 官方群聊图片附件下载（AI 图像识别支持）==========
# 官方事件 d.attachments[] 中图片项的 url 带时效签名，必须在收到事件时立即下载。
# 文件名用消息 id（多附件时用 附件id_序号），存到 .qq-images/ 目录。

QQ_IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".qq-images")

def _content_type_to_ext(content_type: str) -> str:
    """按响应 Content-Type 嗅探扩展名"""
    ct = (content_type or "").split(";")[0].strip().lower()
    if ct == "image/png":
        return ".png"
    if ct == "image/jpeg":
        return ".jpg"
    if ct == "image/gif":
        return ".gif"
    if ct == "image/webp":
        return ".webp"
    if ct == "image/bmp":
        return ".bmp"
    if ct == "image/":
        return ".bin"
    return ".img"

def _official_image_attachments(d: dict) -> list:
    """从官方事件对象中提取需要下载的图片附件 URL（去重）。"""
    urls = []
    atts = d.get("attachments") or []
    for att in atts:
        if not isinstance(att, dict):
            continue
        # 图片项：type == "image" 或带 image 子结构
        a_type = str(att.get("type") or "").lower()
        img = att.get("image") or att.get("image_info") or {}
        is_image = a_type == "image" or (isinstance(img, dict) and (img.get("url") or att.get("url")))
        if not is_image:
            continue
        url = None
        if isinstance(img, dict):
            url = img.get("url")
        if not url:
            url = att.get("url")
        if url and url not in urls:
            urls.append(url)
    return urls

def download_official_images(d: dict) -> list:
    """收到官方事件时同步下载 d.attachments 里的图片（url 带时效签名，不能延后）。

    按 Content-Type 嗅探扩展名，文件名用消息 id / 附件 id，存到 .qq-images/。
    成功/失败均打日志；任何异常都被捕获，返回已成功下载的本地绝对路径列表（不会抛出）。
    """
    local_paths = []
    urls = _official_image_attachments(d)
    if not urls:
        return local_paths

    msg_id = str(d.get("id") or "")
    try:
        os.makedirs(QQ_IMAGES_DIR, exist_ok=True)
    except Exception as e:
        print(f"[图片下载] ❌ 创建 .qq-images 目录失败: {e}")
        return local_paths

    for i, url in enumerate(urls):
        # 文件名：消息id_序号（附件有 id 时优先用附件id）
        att_id = ""
        try:
            atts = d.get("attachments") or []
            att_id = str(atts[i].get("id") or "") if i < len(atts) and isinstance(atts[i], dict) else ""
        except Exception:
            att_id = ""
        base_name = f"{msg_id}_{i + 1}" if len(urls) > 1 else (msg_id or "unknown")
        if att_id:
            base_name = f"{att_id}_{i + 1}" if len(urls) > 1 else att_id

        try:
            resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 200 and resp.content:
                ext = _content_type_to_ext(resp.headers.get("Content-Type", ""))
                file_path = os.path.join(QQ_IMAGES_DIR, f"{base_name}{ext}")
                with open(file_path, "wb") as f:
                    f.write(resp.content)
                local_paths.append(os.path.abspath(file_path))
                print(f"[图片下载] ✅ 成功: {os.path.abspath(file_path)} ({len(resp.content)} bytes, {resp.headers.get('Content-Type')})")
            else:
                code = None
                message = None
                try:
                    body = resp.json()
                    code = body.get("code")
                    message = body.get("message")
                except Exception:
                    pass
                print(f"[图片下载] ❌ 失败: HTTP {resp.status_code} code={code} message={message} url={url[:80]}")
        except Exception as e:
            print(f"[图片下载] ❌ 异常: {type(e).__name__}: {e} url={url[:80]}")

    return local_paths


def parse_official_content(content, top_mentions=None):
    """解析官方 content 字段（JSON 字符串 / 纯文本），返回 (纯文本, mentions 列表)。
    <@openid> 标记统一转成 [CQ:at,qq=openid]。"""
    import re
    text = ""
    mentions = []
    if not content:
        return "", mentions
    if isinstance(content, str):
        c = content.strip()
        if c.startswith("{") or c.startswith("["):
            parsed = None
            try:
                parsed = json.loads(c)
            except Exception:
                parsed = None
            if parsed is not None:
                if isinstance(parsed, dict):
                    text = parsed.get("content") or parsed.get("text") or ""
                    mentions = parsed.get("mentions") or []
                elif isinstance(parsed, list):
                    for seg in parsed:
                        if isinstance(seg, dict):
                            text += str(seg.get("text") or seg.get("content") or "")
                            if seg.get("type") == "at":
                                mentions.append({"member_openid": seg.get("member_openid") or seg.get("id", "")})
                if not text:
                    text = c
            else:
                text = c
        else:
            text = c
    else:
        text = str(content or "")
    text = re.sub(r'<@([^>]+)>', r'[CQ:at,qq=\1]', text).strip()
    if top_mentions and isinstance(top_mentions, list):
        for m in top_mentions:
            if isinstance(m, dict):
                mentions.append(m)
    return text, mentions


def convert_official_to_onebot(data):
    global BOT_QQ
    
    op_code = data.get("op")
    
    if op_code == 11:
        return None
    
    if op_code == 0:
        d = data.get("d", {})
        event_type = data.get("t", "")
        msg_id = d.get("id", "")
        # ===== 防重复推送去重 =====
        if msg_id and _is_duplicate_msg(msg_id):
            return None
        
        if event_type == "C2C_MESSAGE_CREATE":
            user_openid = d.get("author", {}).get("user_openid", "")
            text = d.get("content", "")
            if not text:
                return None
            fake_user_id = openid_to_int(user_openid)
            register_user_mapping(fake_user_id, user_openid)
            register_user_msg_id(fake_user_id, msg_id)
            return {
                "post_type": "message",
                "message_type": "private",
                "user_id": fake_user_id,
                "group_id": None,
                "message": text,
                "raw_message": text,
                "self_id": BOT_QQ,
                "sender": {
                    "user_id": fake_user_id,
                    "nickname": d.get("author", {}).get("username", "")
                },
                "_official_user_openid": user_openid,
                "_official_msg_id": msg_id,
                "_official_msg_type": "private"
            }
        
        elif event_type == "GROUP_AT_MESSAGE_CREATE":
            user_openid = d.get("author", {}).get("user_openid", "")
            group_openid = d.get("group_openid", "")
            raw_text = d.get("content", "")
            # ===== 图片附件：url 带时效签名，必须在收到事件时同步下载，不能延后 =====
            local_image_paths = download_official_images(d)
            if local_image_paths:
                print(f"[官方适配] 🖼️ 群@消息图片已本地化: {local_image_paths}")
            if not raw_text:
                return None
            
            # 解析官方 content（JSON 字符串 / 纯文本）
            text, _at_mentions = parse_official_content(raw_text, d.get("mentions"))
            print(f"[官方适配] 📝 @消息解析后文本: {text[:60]}")
            
            fake_user_id = openid_to_int(user_openid)
            fake_group_id = openid_to_int(group_openid)
            register_group_mapping(fake_group_id, group_openid)
            register_user_mapping(fake_user_id, user_openid)
            register_group_msg_id(fake_group_id, msg_id)
            return {
                "post_type": "message",
                "message_type": "group",
                "user_id": fake_user_id,
                "group_id": fake_group_id,
                "message": text,
                "raw_message": text,
                "self_id": BOT_QQ,
                "sender": {
                    "user_id": fake_user_id,
                    "nickname": d.get("author", {}).get("username", "")
                },
                "_official_user_openid": user_openid,
                "_official_group_openid": group_openid,
                "_official_msg_id": msg_id,
                "_official_msg_type": "group",
                "_local_image_paths": local_image_paths
            }
        
        elif event_type == "GROUP_MESSAGE_CREATE":
            # ===== 群聊普通消息（开启全量消息后推送，不触发任何回复） =====
            # ===== 图片附件：url 带时效签名，必须在收到事件时同步下载，不能延后 =====
            _local_image_paths = download_official_images(d)
            if _local_image_paths:
                print(f"[官方适配] 🖼️ 群消息图片已本地化: {_local_image_paths}")
            author = d.get("author", {})
            member_openid = (author.get("user_openid", "") or author.get("id", "") or author.get("member_openid", ""))
            group_openid = d.get("group_openid", "") or d.get("group_id", "")
            raw_text = d.get("content", "")
            # ===== 提取图片附件（可能 content 为空，只有 attachments 图片） =====
            _attachment_urls = []
            try:
                for _att in (d.get("attachments") or []):
                    if not isinstance(_att, dict):
                        continue
                    _img = _att.get("image") or _att.get("image_info") or {}
                    _a_url = None
                    if isinstance(_img, dict):
                        _a_url = _img.get("url")
                    if not _a_url:
                        _a_url = _att.get("url")
                    if _a_url and _a_url not in _attachment_urls:
                        _attachment_urls.append(_a_url)
            except Exception:
                _attachment_urls = []
            # 图片-only 消息：content 为空但有附件图片，仍要进入后续处理（图片审核/撤回）
            if not raw_text and not _attachment_urls:
                return None
            # ===== 解析 content：可能是 JSON 字符串（内含 mentions），也可能是纯文本 =====
            import re
            _content_json = None
            _text = ""
            _mentions = []
            if isinstance(raw_text, str):
                _c = raw_text.strip()
                if _c.startswith("{") or _c.startswith("["):
                    try:
                        _content_json = json.loads(_c)
                    except Exception:
                        _content_json = None
                if _content_json is not None:
                    if isinstance(_content_json, dict):
                        _text = _content_json.get("content") or _content_json.get("text") or ""
                        _mentions = _content_json.get("mentions") or []
                    elif isinstance(_content_json, list):
                        for seg in _content_json:
                            if isinstance(seg, dict):
                                _text += str(seg.get("text") or seg.get("content") or "")
                                if seg.get("type") == "at":
                                    _m = {"member_openid": seg.get("member_openid") or seg.get("id", "")}
                                    _mentions.append(_m)
                    if not _text:
                        _text = _c
                else:
                    _text = _c
                    _mentions = []
            else:
                _text = str(raw_text or "")
            text = re.sub(r'<@([^>]+)>', r'[CQ:at,qq=\1]', _text).strip()
            if not text:
                text = _text.strip() or "（空消息）"
            fake_user_id = openid_to_int(member_openid) if member_openid else ""
            fake_group_id = openid_to_int(group_openid)
            register_group_mapping(fake_group_id, group_openid)
            if member_openid:
                register_user_mapping(fake_user_id, member_openid)
            register_group_msg_id(fake_group_id, msg_id)
            # ===== 判断是否 @ 了机器人：is_you:true 或 bot:true 且 openid==本机器人 =====
            _top_mentions = d.get("mentions") or []
            _all_mentions = []
            if isinstance(_top_mentions, list):
                _all_mentions.extend(_top_mentions)
            if isinstance(_mentions, list):
                _all_mentions.extend(_mentions)
            _is_at_bot = False
            try:
                _bot_openid = get_bot_openid_sync()
            except Exception:
                _bot_openid = ""
            for _m in _all_mentions:
                if not isinstance(_m, dict):
                    continue
                if _m.get("is_you") is True or _m.get("is_you") == "true":
                    _is_at_bot = True
                    break
                if _m.get("bot") is True or _m.get("bot") == "true":
                    if _bot_openid:
                        _mid = _m.get("member_openid") or _m.get("openid") or _m.get("id") or ""
                        if _mid and _mid == _bot_openid:
                            _is_at_bot = True
                            break
                    else:
                        _is_at_bot = True
                        break
                if _bot_openid:
                    _mid = _m.get("member_openid") or _m.get("openid") or _m.get("id") or ""
                    if _mid and _mid == _bot_openid:
                        _is_at_bot = True
                        break
            _msg_type = "group" if _is_at_bot else "group_silent"
            _ret = {
                "post_type": "message",
                "message_type": "group",
                "user_id": fake_user_id,
                "group_id": fake_group_id,
                "message": text,
                "raw_message": text,
                "message_id": msg_id,
                "self_id": BOT_QQ,
                "sender": {
                    "user_id": fake_user_id,
                    "nickname": author.get("username", "")
                },
                "_official_user_openid": member_openid,
                "_official_group_openid": group_openid,
                "_official_msg_id": msg_id,
                "_official_msg_type": _msg_type,
                "_attachment_image_urls": _attachment_urls
            }
            if _local_image_paths:
                _ret["_local_image_paths"] = _local_image_paths
            return _ret

        else:
            print(f"[官方适配] ⚠️ 未知事件类型: {event_type}")
            return None
    
    return None

# ========== HTTP 服务（主程序通过 HTTP 通信）==========

async def http_send(request):
    """主程序发消息到这里"""
    try:
        data = await request.json()
        print(f"[适配器] 📨 收到主程序消息: {json.dumps(data, ensure_ascii=False)[:100]}...")
        
        # 解析主程序的回复
        params = data.get("params", {})
        message = params.get("message", "")
        msg_type = params.get("message_type", "")
        
        if not message:
            return web.json_response({"status": "error", "msg": "no message"})
        
        # 获取 openid（从上下文或缓存中获取）
        group_openid = data.get("_official_group_openid")
        user_openid = data.get("_official_user_openid")
        official_msg_id = data.get("_official_msg_id")
        
        # 发送到官方 QQ
        result = await send_message_official(
            message,
            user_openid=user_openid,
            group_openid=group_openid,
            official_msg_id=official_msg_id
        )
        
        if result:
            return web.json_response({"status": "ok"})
        else:
            return web.json_response({"status": "error", "msg": "send failed"})
            
    except Exception as e:
        print(f"[适配器] ❌ 处理主程序消息异常: {e}")
        return web.json_response({"status": "error", "msg": str(e)}, status=500)

async def http_poll(request):
    """主程序轮询获取官方消息"""
    global msg_queue
    if msg_queue:
        msg = msg_queue.pop(0)
        return web.json_response(msg)
    return web.json_response({"status": "empty"})

async def http_start():
    """启动 HTTP 服务"""
    app = web.Application()
    app.router.add_post('/send', http_send)
    app.router.add_get('/poll', http_poll)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', HTTP_PORT)
    await site.start()
    print(f"[适配器] ✅ HTTP 服务已启动: http://127.0.0.1:{HTTP_PORT}")
    print("[适配器] ⏳ 等待主程序轮询...")
    return runner

# ========== 主循环 ==========
async def official_bot_main():
    global handler, WS_URL, BOT_QQ, msg_queue
    
    # 1. 先启动 HTTP 服务
    http_runner = await http_start()
    if not http_runner:
        print("[适配器] ❌ HTTP 服务启动失败，退出")
        return
    
    # 2. 连接官方 QQ
    token = ensure_token()
    if not token:
        print("[适配器] ❌ 无法获取 Token")
        return
    
    gateway_url = None
    for _gw_try in range(3):
        gateway_url = await get_gateway_url(retries=3, delay=5.0)
        if gateway_url:
            break
        print(f"[适配器] ⏳ Gateway 获取失败，第{_gw_try+1}/3次重试...")
        if _gw_try < 2:
            await asyncio.sleep(10)
    if not gateway_url:
        print("[适配器] ❌ 无法获取 Gateway（已重试3轮×3次，全部失败）")
        return
    WS_URL = gateway_url
    print(f"[适配器] ✅ Gateway: {WS_URL}")
    
    headers = {"Authorization": f"QQBot {token}"}
    
    # 3. 主循环：连接官方 QQ 并转发消息
    while True:
        try:
            token = ensure_token()
            if not token:
                await asyncio.sleep(5)
                continue
            headers["Authorization"] = f"QQBot {token}"
            
            print("[适配器] 🔗 连接 WebSocket...")
            ws = await ws_connect_with_header(WS_URL, headers)
            async with ws:
                print("[适配器] ✅ WebSocket 已连接")
                
                hello_received = False
                heartbeat_interval = 41250
                
                while not hello_received:
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=10)
                        data = json.loads(raw)
                        if data.get("op") == 10:
                            hello_received = True
                            heartbeat_interval = data.get("d", {}).get("heartbeat_interval", 41250)
                            print(f"[适配器] 💓 心跳间隔: {heartbeat_interval}ms")
                            break
                        elif data.get("op") == 9:
                            print("[适配器] ⚠️ 无效 Session，重连...")
                            break
                    except asyncio.TimeoutError:
                        print("[适配器] ⚠️ 等待 Hello 超时，重连...")
                        break
                
                if not hello_received:
                    continue
                
                identify_payload = {
                    "op": 2,
                    "d": {
                        "token": f"QQBot {token}",
                        "intents": 1 << 25,
                        "shard": [0, 1],
                        "properties": {
                            "os": "Windows",
                            "browser": "QQBot",
                            "device": "QQBot"
                        }
                    }
                }
                await ws.send(json.dumps(identify_payload))
                print("[适配器] 📤 已发送 identify 握手包")
                
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=5)
                    data = json.loads(raw)
                    if data.get("t") == "READY":
                        print("[适配器] ✅ Identify 成功，准备接收消息")
                except asyncio.TimeoutError:
                    print("[适配器] ⚠️ Identify 响应超时")
                
                async def heartbeat_task(ws, interval):
                    while True:
                        await asyncio.sleep(interval / 1000)
                        try:
                            await ws.send(json.dumps({"op": 1, "d": None}))
                            print("[适配器] 💓 心跳")
                        except:
                            break
                asyncio.create_task(heartbeat_task(ws, heartbeat_interval))
                
                while True:
                    if time.time() >= TOKEN_EXPIRE_TIME:
                        print("[适配器] 🔄 Token 过期，重连...")
                        break
                    
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=30)
                        print(f"[适配器] 📨 原始: {raw[:200]}...")
                        data = json.loads(raw)
                        op = data.get("op")
                        
                        if op == 11:
                            continue
                        elif op == 0:
                            onebot = convert_official_to_onebot(data)
                            if onebot:
                                print(f"[适配器] 📩 收到消息，加入队列")
                                # 加入队列，等主程序轮询
                                msg_queue.append(onebot)
                                print(f"[适配器] 📊 队列长度: {len(msg_queue)}")
                        elif op == 9:
                            print("[适配器] ⚠️ 无效 Session，重连...")
                            break
                        elif op == 10:
                            heartbeat_interval = data.get("d", {}).get("heartbeat_interval", 41250)
                    except asyncio.TimeoutError:
                        continue
                    except websockets.exceptions.ConnectionClosed:
                        print("[适配器] 🔄 WebSocket 断开，重连...")
                        break
                        
        except Exception as e:
            print(f"[适配器] ❌ 连接异常: {e}")
            await asyncio.sleep(5)

# ========== 群ID 映射缓存（fake_id -> group_openid）==========
group_id_map = {}   # fake_group_id (str) -> group_openid (str)
user_id_map = {}    # fake_user_id (str) -> user_openid (str)
_last_group_msg_id = {}  # fake_group_id (str) -> last official msg_id (str)
_last_user_msg_id = {}   # fake_user_id (str) -> last official msg_id (str)
_msg_seq_counter = {}    # msg_id (str) -> int，同一 msg_id 的回复计数

def register_group_mapping(fake_group_id: str, group_openid: str):
    """注册群映射，供 send_group_text 使用"""
    if fake_group_id and group_openid:
        group_id_map[str(fake_group_id)] = group_openid
        print(f"[官方适配] 📝 注册群映射: {fake_group_id} -> {group_openid[:10]}...")

def register_user_mapping(fake_user_id: str, user_openid: str):
    """注册用户映射"""
    if fake_user_id and user_openid:
        user_id_map[str(fake_user_id)] = user_openid
        print(f"[官方适配] 📝 注册用户映射: {fake_user_id} -> {user_openid[:10]}...")

def register_group_msg_id(fake_group_id: str, msg_id: str):
    """记录群最新消息 ID，供后台任务回复"""
    if fake_group_id and msg_id:
        _last_group_msg_id[str(fake_group_id)] = msg_id

def register_user_msg_id(fake_user_id: str, msg_id: str):
    """记录用户最新消息 ID，供后台任务回复"""
    if fake_user_id and msg_id:
        _last_user_msg_id[str(fake_user_id)] = msg_id

def get_group_msg_id(fake_group_id: str) -> str:
    return _last_group_msg_id.get(str(fake_group_id))

def get_user_msg_id(fake_user_id: str) -> str:
    return _last_user_msg_id.get(str(fake_user_id))

def consume_group_msg_id(fake_group_id: str):
    """使用并清除群 msg_id（官方 API 每条 msg_id 只能用一次）"""
    _last_group_msg_id.pop(str(fake_group_id), None)

def consume_user_msg_id(fake_user_id: str):
    """使用并清除用户 msg_id"""
    _last_user_msg_id.pop(str(fake_user_id), None)

# ========== 群聊文本发送 ==========
async def send_group_text(group_id: int, text: str, msg_id: str = None,
                          group_openid: str = None) -> tuple:
    """通过官方 API 发送群聊文本消息
    自动将 [CQ:at,qq=xxx]（xxx 是 openid 或 OneBot 假QQ）转换为 <@openid> 格式
    msg_id: 可选，原始消息 ID（官方机器人回复群消息时必须带）
    group_openid: 可选，缺失时调用方传当前事件的 group_openid 现场补建，避免直接抛错
    返回 (success: bool, error: str|None)
    """
    # ===== 群号 → group_openid：先查映射，缺失时用调用方传入的现场补建 =====
    group_openid = group_openid or group_id_map.get(str(group_id))
    if not group_openid:
        print(f"[官方适配] ❌ 群 {group_id} 无 OpenID 映射且未传入 group_openid")
        return False, f"未找到群 {group_id} 的 OpenID 映射"
    # 现场补建映射（供后续发送复用）
    if not group_id_map.get(str(group_id)):
        register_group_mapping(str(group_id), group_openid)
        print(f"[官方适配] 📝 现场补建群映射: {group_id} -> {group_openid[:12]}...")

    token = ensure_token()
    if not token:
        return False, "无有效 Token"

    # ===== 官方模式：@ 用官方 mentions 结构，不把 openid 当纯文本拼进 content =====
    # 1) 提取所有 @ 目标（兼容 [CQ:at,qq=X] 与 <@X>，X 是 openid 或 OneBot 假QQ）
    import re
    _openids = []
    for _m in re.finditer(r'\[CQ:at,qq=([^\]]+)\]', text):
        _v = _m.group(1).strip()
        if _v:
            _openids.append(user_id_map.get(str(_v), _v))
    for _m in re.finditer(r'<@([^>]+)>', text):
        _v = _m.group(1).strip()
        if _v:
            _openids.append(user_id_map.get(str(_v), _v))
    # 2) 去掉 content 里残留的 [CQ:at] 老格式 和 裸 <@openid> 文本
    clean_text = re.sub(r'\[CQ:at,qq=[^\]]+\]', '', text)
    clean_text = re.sub(r'<@[^>]+>', '', clean_text)
    clean_text = clean_text.strip()
    # 3) 构造官方 mentions 结构：{"openid": ..., "is_your_bot": ...}
    _bot_openid = get_bot_openid_sync()
    mentions = []
    for _oid in dict.fromkeys(_openids):  # 去重保序
        if not _oid:
            continue
        mentions.append({"openid": _oid, "is_your_bot": bool(_bot_openid and _oid == _bot_openid)})

    headers = {"Authorization": f"QQBot {token}", "Content-Type": "application/json"}
    url = f"https://api.bot.qq.com/v2/groups/{group_openid}/messages"
    payload = {"msg_type": 0, "content": clean_text}
    if mentions:
        payload["mentions"] = mentions
    if msg_id:
        payload["msg_id"] = msg_id
    print(f"[官方适配] 📤 发送群文本: url={url} content={clean_text[:80]!r}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=10) as resp:
                resp_body = await resp.text()
                if resp.status == 200:
                    print(f"[官方适配] ✅ 群文本发送成功")
                    return True, None
                else:
                    print(f"[官方适配] ❌ 群文本发送失败(完整): HTTP {resp.status} - {resp_body}")
                    return False, f"HTTP {resp.status} {resp_body[:300]}"
    except Exception as e:
        import traceback
        print(f"[官方适配] ❌ 群文本发送异常(完整): {e!r}\n{traceback.format_exc()}")
        return False, f"异常[{type(e).__name__}] {e}"

# ========== 群成员禁言（restrict_chat_setting） ==========
async def delete_official_group_message(group_openid: str, message_id: str) -> tuple:
    """
    官方 API 撤回群消息（DELETE /v2/groups/{group_openid}/messages/{message_id}）
    官方限制：消息发出后 2 分钟内可撤回，且机器人需有群管理权限。
    返回 (success: bool, error: str|None)
    """
    try:
        if not group_openid:
            return False, "缺少 group_openid"
        if not message_id:
            return False, "缺少 message_id"

        token = ensure_token()
        if not token:
            return False, "无有效 Token"

        url = f"https://api.bot.qq.com/v2/groups/{group_openid}/messages/{message_id}"
        headers = {"Authorization": f"QQBot {token}"}
        print(f"[官方适配] 📤 撤回群消息: DELETE {url}")
        async with aiohttp.ClientSession() as session:
            async with session.delete(url, headers=headers, timeout=10) as resp:
                resp_body = await resp.text()
                if resp.status in (200, 204):
                    print(f"[官方适配] ✅ 群消息撤回成功: {message_id}")
                    return True, None
                else:
                    print(f"[官方适配] ❌ 群消息撤回失败: HTTP {resp.status} - {resp_body}")
                    return False, f"HTTP {resp.status} {resp_body[:300]}"
    except Exception as e:
        import traceback
        _tb = traceback.format_exc()
        print(f"[官方适配] ❌ 群消息撤回异常: {type(e).__name__}: {e}\n{_tb}")
        return False, f"异常[{type(e).__name__}] {e}"


# ========== 群成员禁言（restrict_chat_setting） ==========
async def restrict_group_member(group_openid: str, member_openid: str, duration: int = 600) -> tuple:
    """
    官方 API 群成员禁言（restrict_chat_setting）
    直接使用官方事件里 @ 到的 member_openid，走 /v2/groups/{group_openid}/restrict_chat_setting
    按官方最新文档：
      · 禁言用 mute_expire_at（RFC3339 字符串，如 2026-08-05T11:23:05+08:00），不再用 mute_end_timestamp
      · duration: 秒数；0 表示解除禁言（op=del，mute_expire_at 传空串）
    返回 (success: bool, error: str|None)
    """
    from datetime import datetime, timedelta
    try:
        if not group_openid:
            return False, "缺少 group_openid"
        if not member_openid:
            return False, "缺少 member_openid"

        token = ensure_token()
        if not token:
            return False, "无有效 Token"

        url = f"https://api.sgroup.qq.com/v2/groups/{group_openid}/restrict_chat_setting"
        # ===== 生成 RFC3339 到期时间（本地时区偏移，如 +08:00）=====
        if duration and duration > 0:
            # 官方最大禁言 30 天
            max_dur = 30 * 24 * 3600
            if duration > max_dur:
                duration = max_dur
            expire_dt = datetime.now().astimezone() + timedelta(seconds=int(duration))
            mute_expire_at = expire_dt.isoformat(timespec="seconds")  # 2026-08-05T11:23:05+08:00
            op = "add"
        else:
            mute_expire_at = ""  # 立即解除禁言
            op = "del"
        payload = {
            "members": [
                {
                    "op": op,
                    "member_openid": member_openid,
                    "mute_expire_at": mute_expire_at,
                }
            ]
        }
        headers = {"Authorization": f"QQBot {token}", "Content-Type": "application/json"}
        print(f"[官方适配] 📤 群成员禁言: {json.dumps(payload, ensure_ascii=False)} (url={url})")
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=10) as resp:
                resp_body = await resp.text()
                print(f"[官方适配] ❌ 群成员禁言 HTTP {resp.status}: {resp_body}")
                if resp.status in (200, 204):
                    print(f"[官方适配] ✅ 群成员禁言成功")
                    return True, None
                else:
                    print(f"[官方适配] ❌ 群成员禁言失败(完整): HTTP {resp.status} - {resp_body}")
                    return False, f"HTTP {resp.status} {resp_body[:500]}"
    except Exception as e:
        import traceback
        _tb = traceback.format_exc()
        print(f"[官方适配] ❌ 群成员禁言异常(完整): type={type(e).__name__} msg={e!r}\n{_tb}")
        return False, f"异常[{type(e).__name__}] {e}"

# ========== 入群申请审批（approval_join_request） ==========
async def approve_join_request(group_openid: str, member_openid: str, join_request_id: str,
                               op: str = "approve", reject_reason: str = "",
                               add_to_member_blacklist: bool = False) -> tuple:
    """
    官方 API 入群申请审批
    POST /v2/groups/{group_openid}/approval_join_request/{member_openid}
      op: approve 通过 / decline 拒绝
      join_request_id: 申请ID
      reject_reason: 拒绝理由（op=decline 时可填）
      add_to_member_blacklist: 是否同时加入群黑名单（op=decline 时可填）
    返回 (success: bool, error: str|None)
    """
    try:
        if not group_openid:
            return False, "缺少 group_openid"
        if not member_openid:
            return False, "缺少 member_openid"
        if op not in ("approve", "decline"):
            return False, f"非法审批动作: {op}"

        token = ensure_token()
        if not token:
            return False, "无有效 Token"

        url = f"https://api.sgroup.qq.com/v2/groups/{group_openid}/approval_join_request/{member_openid}"
        payload = {"op": op}
        if join_request_id:
            payload["join_request_id"] = join_request_id
        if op == "decline":
            if reject_reason:
                payload["reject_reason"] = reject_reason
            payload["add_to_member_blacklist"] = bool(add_to_member_blacklist)
        headers = {"Authorization": f"QQBot {token}", "Content-Type": "application/json"}
        print(f"[官方适配] 📤 入群审批: {op} openid={member_openid[:10]}...")
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=10) as resp:
                if resp.status in (200, 204):
                    print(f"[官方适配] ✅ 入群审批成功: {op}")
                    return True, None
                else:
                    err_text = await resp.text()
                    print(f"[官方适配] ❌ 入群审批失败: {resp.status} - {err_text[:200]}")
                    return False, f"{resp.status} {err_text[:200]}"
    except Exception as e:
        print(f"[官方适配] ❌ 入群审批异常: {e}")
        return False, str(e)

# ========== 测试模式 ==========
async def test_mode():
    token = ensure_token()
    if not token:
        print("❌ 获取 Token 失败")
        return
    
    user_openid = "09AAF23C5552D991CA3600E8AD185CD3"
    test_path = r"C:\Users\xp123\Desktop\qai\data\temp_images\lottery_daily_2249528587_1785947147.png"
    
    if os.path.exists(test_path):
        print(f"✅ 图片存在: {test_path}")
        await send_message_official(
            f"[CQ:image,file=file:///{test_path}]",
            user_openid=user_openid
        )
    else:
        print(f"❌ 图片不存在: {test_path}")

# ========== 启动入口 ==========
def start_adapter():
    print("[适配器] 🚀 启动官方适配器 (HTTP 轮询模式)")
    print(f"[适配器] 📡 监听端口: {HTTP_PORT}")
    print("[适配器] 💡 主程序请选择官方适配器模式连接")
    asyncio.run(official_bot_main())

if __name__ == "__main__":
    print("=" * 50)
    print("🤖 官方适配器独立启动 (HTTP 轮询模式)")
    print("=" * 50)
    print("1. 启动 HTTP 服务 (等待主程序轮询)")
    print("2. 测试模式 (发送测试图片)")
    print("=" * 50)
    
    choice = input("请选择模式 (1/2): ").strip()
    
    if choice == "2":
        asyncio.run(test_mode())
    else:
        start_adapter()
