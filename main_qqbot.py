import asyncio
import json
import requests
import websockets
from qai主程序 import MessageHandler, OllamaAI

# ===== 你的凭证 =====
APP_ID = "1905161246"
APP_SECRET = "mUDwgQAvgSE1ocQE3siYPG80tmfZTOJF"

# ===== 获取 Access Token =====
def get_access_token():
    url = "https://bots.qq.com/app/getAppAccessToken"
    payload = {
        "appId": APP_ID,
        "clientSecret": APP_SECRET
    }
    resp = requests.post(url, json=payload)
    data = resp.json()
    print(f"[Token] 获取成功，有效期 {data.get('expires_in')} 秒")
    return data.get("access_token")

# ===== 创建处理器 =====
handler = MessageHandler()
handler.ai = OllamaAI()

# ===== 发送回复 =====
async def send_reply(ws, channel_id, content, reply_text):
    """发送回复消息"""
    try:
        payload = {
            "op": 0,
            "d": {
                "channel_id": channel_id,
                "content": reply_text
            }
        }
        await ws.send(json.dumps(payload))
        print(f"[回复] {reply_text[:50]}...")
    except Exception as e:
        print(f"[回复失败] {e}")

# ===== 主程序 =====
async def main():
    # 1. 获取 Access Token
    access_token = get_access_token()
    
    # 2. 获取 Gateway 地址
    url = "https://api.sgroup.qq.com/gateway"
    headers = {"Authorization": f"QQBot {access_token}"}
    resp = requests.get(url, headers=headers)
    wss_url = resp.json().get("url")
    print(f"[连接] Gateway: {wss_url}")

    # 3. 连接 WebSocket
    async with websockets.connect(wss_url) as ws:
        # 接收 Hello
        hello = await ws.recv()
        print(f"[Hello] 心跳间隔: {json.loads(hello).get('d', {}).get('heartbeat_interval')}ms")

        # 发送鉴权
        auth = {
            "op": 2,
            "d": {
                "token": f"QQBot {access_token}",
                "intents": 1 << 0,  # 消息事件
                "shard": [0, 1]
            }
        }
        await ws.send(json.dumps(auth))
        print("[鉴权] 已发送")

        # 4. 接收消息
        async for msg in ws:
            data = json.loads(msg)
            op = data.get("op")
            t = data.get("t")
            d = data.get("d")

            # 心跳处理
            if op == 11:
                print("[心跳] 已回复")
                continue

            if op == 10:
                # Hello 消息（重连时处理）
                continue

            # 消息事件
            if op == 0 and t == "MESSAGE_CREATE":
                content = d.get("content", "")
                author = d.get("author", {})
                user_id = author.get("id")
                channel_id = d.get("channel_id")
                guild_id = d.get("guild_id")
                message_id = d.get("id")

                print(f"[消息] 用户 {user_id}: {content}")

                # 构造 fake_data 给 handler
                fake_data = {
                    "post_type": "message",
                    "message_type": "group" if guild_id else "private",
                    "user_id": str(user_id),
                    "group_id": str(guild_id) if guild_id else None,
                    "message": content,
                    "self_id": APP_ID,
                    "channel_id": channel_id,
                    "message_id": message_id
                }

                # 调用你的消息处理器
                reply = handler.handle_message(fake_data)

                # 发送回复
                if reply and isinstance(reply, dict):
                    reply_text = reply.get("params", {}).get("message", "")
                    if reply_text:
                        await send_reply(ws, channel_id, content, reply_text)

            # 其他事件
            elif op == 0:
                print(f"[事件] {t}: {d}")

            # 错误处理
            elif op == 9:
                print("[错误] 需要重新鉴权")

            else:
                print(f"[未处理] op={op}, t={t}")

if __name__ == "__main__":
    print("=" * 50)
    print("[启动] QQ 官方 WebSocket 机器人")
    print(f"[启动] AppID: {APP_ID}")
    print("=" * 50)
    asyncio.run(main())
