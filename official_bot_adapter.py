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

# ========== Gateway 获取 ==========
async def get_gateway_url():
    token = ensure_token()
    if not token:
        return None
    url = "https://api.bot.qq.com/gateway"
    headers = {"Authorization": f"QQBot {token}"}
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers) as resp:
                data = await resp.json()
                return data.get("url")
    except Exception as e:
        print(f"[官方适配] ❌ Gateway 异常: {e}")
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
    token = ensure_token()
    if not token:
        return None
    
    headers = {"Authorization": f"QQBot {token}", "Content-Type": "application/json"}
    
    file_md5 = calc_md5(voice_data)
    file_sha1 = calc_sha1(voice_data)
    file_md5_10m = calc_md5_10m(voice_data)
    file_size = str(len(voice_data))
    
    preupload_url = f"https://api.bot.qq.com/v2/groups/{group_openid}/upload_prepare"
    payload = {
        "file_type": 3,
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
                print(f"[官方适配] ❌ 群聊语音预上传失败: {resp.status} - {text[:200]}")
                return None
            data = await resp.json()
            upload_id = data.get("upload_id")
            parts = data.get("parts", [])
            block_size = data.get("block_size")
            if not upload_id or not parts:
                return None
            presigned_url = parts[0].get("presigned_url")
            part_index = parts[0].get("index", 1)
            print(f"[官方适配] ✅ 群聊语音预上传成功，upload_id: {upload_id}")
        
        try:
            async with session.put(presigned_url, data=voice_data, headers={"Content-Type": "application/octet-stream"}) as put_resp:
                if put_resp.status not in [200, 204]:
                    text = await put_resp.text()
                    print(f"[官方适配] ❌ 群聊语音上传失败: {put_resp.status} - {text[:200]}")
                    return None
                etag = put_resp.headers.get('ETag', '').strip('"')
                print(f"[官方适配] ✅ 群聊语音内容上传成功, ETag: {etag}")
        except Exception as e:
            print(f"[官方适配] ❌ 群聊语音上传异常: {e}")
            return None
        
        part_finish_url = f"https://api.bot.qq.com/v2/groups/{group_openid}/upload_part_finish"
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
                    print(f"[官方适配] ❌ 群聊语音分片完成确认失败: {pf_resp.status} - {text[:200]}")
                    return None
                print("[官方适配] ✅ 群聊语音分片完成确认成功")
        except Exception as e:
            print(f"[官方适配] ❌ 群聊语音分片完成确认异常: {e}")
        
        await asyncio.sleep(2)
        
        finalize_url = f"https://api.bot.qq.com/v2/groups/{group_openid}/files"
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
        except Exception as e:
            print(f"[官方适配] ❌ 群聊语音合并异常: {e}")
            return None

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
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, timeout=10) as resp:
                    if resp.status == 200:
                        print("[官方适配] ✅ 语音消息发送成功")
                        return True
                    else:
                        text = await resp.text()
                        print(f"[官方适配] ❌ 发送语音失败: {resp.status} - {text[:200]}")
                        return False
        except Exception as e:
            print(f"[官方适配] ❌ 发送语音异常: {e}")
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
    
    # 去掉 CQ 码，避免把 CQ 码当纯文本发出去
    import re as _re
    clean_content = _re.sub(r'\[CQ:[^\]]*\]', '', message).strip()
    if not clean_content:
        print(f"[官方适配] ⚠️ 去掉CQ码后消息为空，跳过发送")
        return True
    
    payload = {
        "msg_type": 0,
        "content": clean_content
    }
    if official_msg_id:
        payload["msg_id"] = official_msg_id
        seq = _msg_seq_counter.get(official_msg_id, 0) + 1
        _msg_seq_counter[official_msg_id] = seq
        payload["msg_seq"] = seq
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=10) as resp:
                if resp.status == 200:
                    return True
                else:
                    text = await resp.text()
                    print(f"[官方适配] ❌ 发送失败: {resp.status} - {text[:200]}")
                    return False
    except Exception as e:
        print(f"[官方适配] ❌ 发送异常: {e}")
        return False

# ========== 消息转换 ==========
def convert_official_to_onebot(data):
    global BOT_QQ
    
    op_code = data.get("op")
    
    if op_code == 11:
        return None
    
    if op_code == 0:
        d = data.get("d", {})
        event_type = data.get("t", "")
        msg_id = d.get("id", "")
        
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
            if not raw_text:
                return None
            
            text = re.sub(r'<@(\d+)>', r'[CQ:at,qq=\1]', raw_text).strip()
            
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
                "_official_msg_type": "group"
            }
        
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
    
    gateway_url = await get_gateway_url()
    if not gateway_url:
        print("[适配器] ❌ 无法获取 Gateway")
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
async def send_group_text(group_id: int, text: str, msg_id: str = None) -> tuple:
    """通过官方 API 发送群聊文本消息
    自动将 [CQ:at,qq=xxx] 转换为 <@openid> 格式
    msg_id: 可选，原始消息 ID（官方机器人回复群消息时必须带）
    返回 (success: bool, error: str|None)
    """
    group_openid = group_id_map.get(str(group_id))
    if not group_openid:
        return False, f"未找到群 {group_id} 的 OpenID 映射"
    
    token = ensure_token()
    if not token:
        return False, "无有效 Token"
    
    # 将 [CQ:at,qq=fake_id] 转换为 <@user_openid>
    def convert_at(match):
        fake_qq = match.group(1)
        real_openid = user_id_map.get(str(fake_qq), "")
        if real_openid:
            return f"<@{real_openid}>"
        return match.group(0)
    
    import re
    clean_text = re.sub(r'\[CQ:at,qq=(\d+)\]', convert_at, text)
    
    headers = {"Authorization": f"QQBot {token}", "Content-Type": "application/json"}
    url = f"https://api.bot.qq.com/v2/groups/{group_openid}/messages"
    payload = {"msg_type": 0, "content": clean_text}
    if msg_id:
        payload["msg_id"] = msg_id
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=10) as resp:
                if resp.status == 200:
                    return True, None
                else:
                    error_text = await resp.text()
                    print(f"[官方适配] ❌ 群文本发送失败: {resp.status} - {error_text[:200]}")
                    return False, error_text[:200]
    except Exception as e:
        print(f"[官方适配] ❌ 群文本发送异常: {e}")
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
