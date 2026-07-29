"""
通过 LLOneBot WebSocket 获取群成员列表
用法: python get_group_members.py
"""

import asyncio
import json
import websockets
import os
import time
from datetime import datetime

class GroupMemberFetcher:
    def __init__(self, port=5678):
        self.ws_url = f"ws://127.0.0.1:{port}"
        self.websocket = None
    
    async def connect(self):
        """连接 WebSocket"""
        try:
            self.websocket = await websockets.connect(self.ws_url)
            print(f"✅ WebSocket 连接成功 ({self.ws_url})")
            return True
        except Exception as e:
            print(f"❌ WebSocket 连接失败: {e}")
            print("💡 请确保:")
            print("  1. LLOneBot 已启动并登录了你的主号")
            print("  2. WebSocket 端口号正确")
            return False
    
    async def get_group_list(self):
        """获取所有群列表"""
        echo = f"get_group_list_{int(time.time())}"
        await self.websocket.send(json.dumps({
            "action": "get_group_list",
            "params": {"no_cache": False},
            "echo": echo
        }))
        
        timeout = 10
        start = time.time()
        while time.time() - start < timeout:
            try:
                msg = await asyncio.wait_for(self.websocket.recv(), timeout=1)
                data = json.loads(msg)
                if data.get("echo") == echo:
                    if data.get("status") == "ok":
                        return data.get("data", [])
                    else:
                        print(f"❌ API错误: {data}")
                        return []
            except asyncio.TimeoutError:
                continue
            except json.JSONDecodeError:
                continue
        print("❌ 获取群列表超时")
        return []
    
    async def get_group_members(self, group_id: int):
        """获取指定群的成员列表"""
        echo = f"get_members_{group_id}_{int(time.time())}"
        await self.websocket.send(json.dumps({
            "action": "get_group_member_list",
            "params": {"group_id": group_id},
            "echo": echo
        }))
        
        timeout = 15
        start = time.time()
        while time.time() - start < timeout:
            try:
                msg = await asyncio.wait_for(self.websocket.recv(), timeout=1)
                data = json.loads(msg)
                if data.get("echo") == echo:
                    if data.get("status") == "ok":
                        return data.get("data", [])
                    else:
                        print(f"❌ API错误: {data}")
                        return []
            except asyncio.TimeoutError:
                continue
            except json.JSONDecodeError:
                continue
        print("❌ 获取群成员超时")
        return []
    
    def save_to_file(self, members, group_id):
        """保存成员列表到文件（只提取QQ号）"""
        qq_list = []
        for member in members:
            user_id = str(member.get("user_id"))
            if user_id:
                qq_list.append(user_id)
        
        filename = f"group_{group_id}_members.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            for qq in qq_list:
                f.write(qq + '\n')
        
        print(f"✅ 已保存 {len(qq_list)} 个QQ号到 {filename}")
        return filename
    
    async def run(self):
        """主流程"""
        print("=" * 50)
        print("🔍 获取群成员列表工具")
        print("=" * 50)
        
        # 询问端口
        port_input = input("请输入 LLOneBot WebSocket 端口（默认 5678）: ").strip()
        if port_input:
            try:
                self.ws_url = f"ws://127.0.0.1:{int(port_input)}"
            except ValueError:
                print("❌ 端口必须是数字，使用默认 5678")
                self.ws_url = "ws://127.0.0.1:5678"
        else:
            self.ws_url = "ws://127.0.0.1:5678"
        
        print(f"🔌 使用地址: {self.ws_url}")
        
        # 连接 WebSocket
        if not await self.connect():
            return
        
        # 获取群列表
        print("📡 获取群列表...")
        groups = await self.get_group_list()
        
        if not groups:
            print("❌ 没有获取到群列表，请检查：")
            print("  1. 你的主号是否登录了 LLOneBot")
            print("  2. 你的主号是否在群里")
            return
        
        print(f"\n📋 找到 {len(groups)} 个群:")
        for i, group in enumerate(groups, 1):
            group_name = group.get("group_name", "未命名")
            group_id = group.get("group_id")
            print(f"  {i}. {group_name} ({group_id})")
        
        # 选择群
        while True:
            try:
                choice = input("\n请输入要获取成员的群号（或序号）: ").strip()
                if not choice:
                    continue
                
                if choice.isdigit() and int(choice) <= len(groups):
                    group = groups[int(choice) - 1]
                    group_id = group.get("group_id")
                else:
                    group_id = int(choice)
                    found = False
                    for g in groups:
                        if g.get("group_id") == group_id:
                            found = True
                            break
                    if not found:
                        print(f"❌ 未找到群号: {group_id}")
                        continue
                break
            except Exception as e:
                print(f"输入错误: {e}")
        
        # 获取群成员
        print(f"📡 获取群 {group_id} 的成员列表...")
        members = await self.get_group_members(group_id)
        
        if not members:
            print("❌ 获取成员失败")
            return
        
        print(f"📋 获取到 {len(members)} 个成员")
        
        # 保存到文件
        filename = self.save_to_file(members, group_id)
        
        print("\n" + "=" * 50)
        print("✅ 完成！")
        print(f"📄 文件: {filename}")
        print(f"👥 共 {len(members)} 人")
        print("\n💡 下一步:")
        print(f"  运行黑名单工具，选择批量封禁，输入 {filename}")
        print("=" * 50)


async def main():
    fetcher = GroupMemberFetcher()
    await fetcher.run()

if __name__ == "__main__":
    asyncio.run(main())
