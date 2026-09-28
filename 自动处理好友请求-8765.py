import asyncio
import json
import websockets

# --- 配置区 ---
WS_URL = "ws://localhost:8765"  # SnowLuma 的 WebSocket 地址，端口按实际改
CORRECT_ANSWER = "xp12"          # 正确的验证信息
TOKEN = ""                       # 如果 SnowLuma 设置了 Access Token 就填上，没有就留空

async def handle_friend_request(ws, event):
    """处理好友申请事件"""
    # OneBot 11 好友申请事件的字段
    flag = event.get("flag")              # 处理请求用的唯一标识
    user_id = event.get("user_id")        # 申请人 QQ 号
    comment = event.get("comment", "")    # 验证信息（留言）
    sub_type = event.get("sub_type")      # add / invite

    print(f"\n📩 收到好友申请")
    print(f"   QQ号: {user_id}")
    print(f"   验证信息: [{comment}]")
    print(f"   flag: {flag}")

    # 判断验证信息是否正确
    if comment.strip() == CORRECT_ANSWER:
        print(f"   ✅ 验证通过，准备同意")
        approve = True
    else:
        print(f"   ❌ 验证失败，准备拒绝")
        approve = False

    # 构造 OneBot 11 API 请求
    # 优先用 set_friend_add_request（标准接口）
    # 如果 SnowLuma 需要走 set_doubt_friends_add_request，改 action 即可
    api_request = {
        "action": "set_friend_add_request",
        "params": {
            "flag": flag,
            "approve": approve
        },
        "echo": f"handle_{user_id}"
    }

    await ws.send(json.dumps(api_request))
    print(f"   📤 已发送处理请求: approve={approve}")

async def main():
    # 如果没有 Token，直接用最简单的连接方式
    async with websockets.connect(WS_URL) as ws:
        print(f"✅ 已连接到 SnowLuma: {WS_URL}")
        print(f"👂 开始监听好友申请事件（正确验证信息: {CORRECT_ANSWER}）...\n")

        async for message in ws:
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                continue

            if data.get("post_type") == "request" and data.get("request_type") == "friend":
                asyncio.create_task(handle_friend_request(ws, data))
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 已退出")
