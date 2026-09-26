import asyncio
import json
import time
import websockets

# ============ 配置区 ============
WS_URL = "ws://localhost:8765"           # SnowLuma WebSocket 地址，端口按实际改
SEND_INTERVAL = 1                         # 每条消息间隔（秒）
WAIT_SECONDS = 3 * 3600                   # 等待回复时间：3小时（测试时改成 60）
CHECK_INTERVAL = 300                      # 检查间隔：5分钟（测试时改成 20）
MESSAGE_TEXT = "你好呀，在吗？看到请回复一下哦～(自动清除好友程序(刚刚的有bug))"
# ================================

# 内存状态
pending = {}      # {user_id(str): {"send_time": ts, "nickname": str}}
replied = set()   # 已回复的 user_id


async def send_api(ws, action, params, echo="default"):
    """发送 OneBot API 请求"""
    await ws.send(json.dumps({"action": action, "params": params, "echo": echo}))


async def handle_friend_list(ws, data):
    """收到好友列表后，逐个发消息"""
    friends = data.get("data", [])
    print(f"\n👥 共 {len(friends)} 个好友，开始发送消息...\n")

    for i, friend in enumerate(friends, 1):
        user_id = str(friend.get("user_id"))
        nickname = friend.get("nickname", "未知")

        # 跳过已在待清理列表或已回复的
        if user_id in pending or user_id in replied:
            print(f"   ⏭️ 跳过 {nickname} ({user_id})")
            continue

        await send_api(ws, "send_private_msg", {
            "user_id": int(user_id),
            "message": MESSAGE_TEXT
        }, echo=f"send_{user_id}")

        pending[user_id] = {
            "send_time": time.time(),
            "nickname": nickname
        }
        print(f"   📤 [{i}/{len(friends)}] 已发送给 {nickname} ({user_id})")

        await asyncio.sleep(SEND_INTERVAL)
        await asyncio.sleep(0)  # 让出控制权，让接收循环能跑

    print(f"\n✅ 群发完成，共 {len(pending)} 人等待回复，"
          f"{WAIT_SECONDS // 3600} 小时后检查...\n")


async def check_and_delete(ws):
    """检查超时未回复的好友并删除"""
    now = time.time()
    to_delete = [uid for uid, info in pending.items()
                 if now - info["send_time"] >= WAIT_SECONDS]

    if not to_delete:
        print(f"🔍 检查完毕，暂无超时好友（待回复: {len(pending)}）")
        return

    print(f"\n⏰ 发现 {len(to_delete)} 个超时未回复，开始删除...")
    for uid in to_delete:
        nickname = pending[uid]["nickname"]
        await send_api(ws, "delete_friend", {"user_id": int(uid)}, echo=f"del_{uid}")
        print(f"   🗑️ 已删除 {nickname} ({uid})")
        del pending[uid]
        await asyncio.sleep(2)
    print("✅ 删除完成\n")


async def periodic_check(ws):
    """定时检查任务"""
    while True:
        await asyncio.sleep(CHECK_INTERVAL)
        try:
            await check_and_delete(ws)
        except Exception as e:
            print(f"⚠️ 检查任务出错: {e}")


async def handle_private_message(ws, event):
    """收到私聊消息，标记为已回复"""
    user_id = str(event.get("user_id"))
    if user_id in pending:
        nickname = pending[user_id]["nickname"]
        msg = event.get("raw_message", "")
        print(f"💬 收到 {nickname} ({user_id}) 回复: {msg}  →  已标记，不会被删")
        replied.add(user_id)
        del pending[user_id]


async def main():
    # 显式设置心跳参数，避免默认值太短导致误判断开
    async with websockets.connect(
        WS_URL,
        ping_interval=30,
        ping_timeout=60,
        close_timeout=10,
    ) as ws:
        print(f"✅ 已连接到 SnowLuma: {WS_URL}\n")

        # 启动定时检查任务（后台）
        asyncio.create_task(periodic_check(ws))

        # 请求好友列表
        print("📋 正在获取好友列表...")
        await send_api(ws, "get_friend_list", {}, echo="get_friends")

        # 主接收循环
        async for message in ws:
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                continue

            echo = data.get("echo", "")

            # 1. 好友列表响应 → 扔到后台去群发，不阻塞接收
            if echo == "get_friends":
                asyncio.create_task(handle_friend_list(ws, data))
                continue

            # 2. 私聊消息 → 标记已回复
            if data.get("post_type") == "message" and data.get("message_type") == "private":
                asyncio.create_task(handle_private_message(ws, data))
                continue

            # 3. 调试：打印发送/删除的异常返回
            if echo.startswith("del_") or echo.startswith("send_"):
                status = data.get("status", "?")
                if status != "ok":
                    print(f"   ⚠️ {echo} 返回: {data}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 已退出")
        print(f"最终待回复: {list(pending.keys())}")
        print(f"已回复: {list(replied)}")
