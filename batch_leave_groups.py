"""
批量退群工具 - 自动获取所有群并退出
用法: python batch_leave_groups.py
"""

import asyncio
import websockets
import json
import time
import sys

# ========== 配置 ==========
WS_URL = "ws://127.0.0.1:8765"  # NapCat WebSocket 地址
GROUPS_TO_KEEP = [
    "1031177320",
    "1070460605",
    "1009018182",
    "1058812511",
    "819395398",
    "1105681016",
    "743645787",
    "884695446"
]  # 保留的群号，不退出
CONFIRM_BEFORE_LEAVE = True  # 是否确认后再执行

async def batch_leave():
    print("=" * 50)
    print("🤖 批量退群工具")
    print("=" * 50)
    
    try:
        async with websockets.connect(WS_URL) as ws:
            print(f"✅ 已连接到 {WS_URL}")
            
            # 1. 获取群列表
            echo = f"get_groups_{int(time.time())}"
            await ws.send(json.dumps({
                "action": "get_group_list",
                "params": {},
                "echo": echo
            }))
            
            # 2. 等待响应
            groups = []
            timeout = 10
            start = time.time()
            while time.time() - start < timeout:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=1)
                    data = json.loads(raw)
                    if data.get("echo") == echo:
                        if data.get("status") == "ok":
                            groups = data.get("data", [])
                        break
                except asyncio.TimeoutError:
                    continue
            
            if not groups:
                print("❌ 获取群列表失败或没有群")
                return
            
            print(f"\n📋 当前群列表 (共 {len(groups)} 个):")
            for i, g in enumerate(groups, 1):
                group_id = g.get("group_id")
                group_name = g.get("group_name", "未命名")
                skip_mark = " [保留]" if str(group_id) in GROUPS_TO_KEEP else ""
                print(f"  {i}. {group_id} - {group_name}{skip_mark}")
            
            # 3. 过滤要退出的群（跳过保留群）
            to_leave = []
            for g in groups:
                gid = str(g.get("group_id"))
                if gid not in GROUPS_TO_KEEP:
                    to_leave.append(g)
            
            if not to_leave:
                print("\n📭 没有需要退出的群（所有群都在保留列表中）")
                return
            
            print(f"\n📋 将退出 {len(to_leave)} 个群:")
            for g in to_leave:
                print(f"  {g.get('group_id')} - {g.get('group_name', '未命名')}")
            
            if CONFIRM_BEFORE_LEAVE:
                confirm = input(f"\n⚠️ 确认退出以上 {len(to_leave)} 个群？(y/n): ").strip().lower()
                if confirm != 'y':
                    print("❌ 已取消")
                    return
            
            print("\n🔄 开始退群...")
            success = 0
            fail = 0
            
            for g in to_leave:
                group_id = g.get("group_id")
                group_name = g.get("group_name", "未命名")
                try:
                    await ws.send(json.dumps({
                        "action": "set_group_leave",
                        "params": {"group_id": int(group_id)}
                    }))
                    success += 1
                    print(f"  ✅ 已退出 {group_id} ({group_name})")
                    await asyncio.sleep(0.5)
                except Exception as e:
                    fail += 1
                    print(f"  ❌ 退出 {group_id} ({group_name}) 失败: {e}")
            
            print(f"\n✅ 完成！成功退出 {success} 个群，失败 {fail} 个")
            
            if fail > 0:
                print("\n💡 失败的群可能是机器人不在该群或权限不足")
            
    except ConnectionRefusedError:
        print(f"❌ 连接失败，请确保 NapCat 已运行: {WS_URL}")
    except Exception as e:
        print(f"❌ 异常: {e}")

if __name__ == "__main__":
    asyncio.run(batch_leave())
