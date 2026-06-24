"""
独立拍一拍模块
功能：批量拍一拍群成员
指令：!拍一拍全体 <次数>
权限：仅管理员可用，最多50次
"""

import asyncio
import websockets
import json
import time
import sys
from datetime import datetime


class PatAllBot:
    def __init__(self):
        self.websocket = None
        self.bot_self_id = None
        self.ws_url = "ws://127.0.0.1:8765"
        
        # 管理员列表（可在此添加）
        self.admins = [
            "3280406098",  # 你的QQ号
            # "123456789",  # 其他管理员
        ]
    
    def log(self, msg, level="INFO"):
        time_str = datetime.now().strftime("%H:%M:%S")
        print(f"[{time_str}] [{level}] {msg}")
    
    async def connect(self):
        """连接 LLOneBot"""
        try:
            self.websocket = await websockets.connect(self.ws_url)
            self.log("连接成功")
            
            # 接收初始消息
            try:
                init = await asyncio.wait_for(self.websocket.recv(), timeout=3)
                data = json.loads(init)
                if data.get("post_type") == "meta_event":
                    self.bot_self_id = str(data.get("self_id", ""))
                    self.log(f"机器人ID: {self.bot_self_id}")
            except:
                pass
            
            return True
        except Exception as e:
            self.log(f"连接失败: {e}", "ERROR")
            return False
    
    def is_admin(self, user_id: str) -> bool:
        """检查是否为管理员"""
        return user_id in self.admins
    
    async def get_group_members(self, group_id: int) -> list:
        """获取群成员列表"""
        try:
            request_id = f"get_members_{int(time.time()*1000)}"
            
            await self.websocket.send(json.dumps({
                "action": "get_group_member_list",
                "params": {"group_id": group_id},
                "echo": request_id
            }))
            
            # 等待响应
            timeout = 10
            start = time.time()
            while time.time() - start < timeout:
                try:
                    response = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                    data = json.loads(response)
                    if data.get("echo") == request_id:
                        if data.get("status") == "ok":
                            members = data.get("data", [])
                            # 过滤掉机器人自己
                            members = [m for m in members if str(m.get("user_id")) != self.bot_self_id]
                            return members
                        else:
                            self.log(f"获取成员失败: {data.get('message')}", "ERROR")
                            return []
                except asyncio.TimeoutError:
                    continue
            
            return []
        except Exception as e:
            self.log(f"获取成员异常: {e}", "ERROR")
            return []
    
    async def pat_member(self, group_id: int, user_id: int):
        """拍一拍单个成员"""
        try:
            await self.websocket.send(json.dumps({
                "action": "send_msg",
                "params": {
                    "message_type": "group",
                    "group_id": group_id,
                    "message": f"[CQ:poke,qq={user_id}]"
                }
            }))
            return True
        except Exception as e:
            self.log(f"拍一拍失败: {e}", "ERROR")
            return False
    
    async def pat_all(self, group_id: int, times: int):
        """拍一拍全体成员"""
        self.log(f"开始获取群 {group_id} 成员列表...")
        
        members = await self.get_group_members(group_id)
        if not members:
            self.log("获取成员列表失败或群为空", "ERROR")
            return 0, 0
        
        self.log(f"获取到 {len(members)} 个成员（已过滤机器人）")
        self.log(f"开始拍一拍，每个成员拍 {times} 次...")
        
        success = 0
        failed = 0
        
        for member in members:
            user_id = member.get("user_id")
            nickname = member.get("card") or member.get("nickname") or str(user_id)
            
            for i in range(times):
                if await self.pat_member(group_id, user_id):
                    success += 1
                    print(f"  ✅ 拍 {nickname} ({user_id}) 第{i+1}次")
                else:
                    failed += 1
                    print(f"  ❌ 拍 {nickname} ({user_id}) 失败")
                
                # 每次拍一拍间隔0.3秒
                await asyncio.sleep(0.3)
            
            # 每个成员之间间隔0.5秒
            await asyncio.sleep(0.5)
        
        return success, failed
    
    async def send_msg(self, group_id: int, message: str):
        """发送群消息"""
        try:
            await self.websocket.send(json.dumps({
                "action": "send_msg",
                "params": {
                    "message_type": "group",
                    "group_id": group_id,
                    "message": message
                }
            }))
        except Exception as e:
            self.log(f"发送消息失败: {e}", "ERROR")
    
    async def handle_message(self, data: dict):
        """处理消息"""
        if data.get("post_type") != "message":
            return
        if data.get("message_type") != "group":
            return
        
        group_id = data.get("group_id")
        user_id = str(data.get("user_id"))
        raw_msg = data.get("message", "")
        
        # 提取文本
        if isinstance(raw_msg, list):
            text = ""
            for seg in raw_msg:
                if seg.get("type") == "text":
                    text += seg.get("data", {}).get("text", "")
        else:
            text = str(raw_msg)
        
        text = text.strip()
        
        # 拍一拍全体命令
        if text.startswith("!拍一拍全体") or text.startswith("！拍一拍全体"):
            # 权限检查
            if not self.is_admin(user_id):
                await self.send_msg(group_id, f"[CQ:at,qq={user_id}] ❌ 权限不足，只有管理员可以使用此命令")
                return
            
            parts = text.split()
            times = 1  # 默认1次
            
            if len(parts) >= 2:
                try:
                    times = int(parts[1])
                    if times < 1:
                        times = 1
                    if times > 50:
                        times = 50
                        await self.send_msg(group_id, f"[CQ:at,qq={user_id}] ⚠️ 次数上限为50次，已自动调整为50")
                except:
                    times = 1
            
            await self.send_msg(group_id, f"[CQ:at,qq={user_id}] 📢 开始拍一拍全体成员，每人{times}次，请稍候...")
            
            # 执行拍一拍
            success, failed = await self.pat_all(group_id, times)
            
            await self.send_msg(group_id, f"[CQ:at,qq={user_id}] ✅ 拍一拍完成！\n成功: {success} 次，失败: {failed} 次")
    
    async def run(self):
        """运行机器人"""
        print("=" * 50)
        print("拍一拍全体模块 v1.0")
        print("指令: !拍一拍全体 [次数]")
        print("示例: !拍一拍全体 3")
        print(f"管理员: {', '.join(self.admins)}")
        print("权限: 仅管理员可用")
        print("次数: 1-50 次")
        print("=" * 50)
        
        while True:
            try:
                if not await self.connect():
                    await asyncio.sleep(5)
                    continue
                
                async for msg in self.websocket:
                    try:
                        data = json.loads(msg)
                        await self.handle_message(data)
                    except Exception as e:
                        self.log(f"处理消息异常: {e}", "ERROR")
                        
            except websockets.exceptions.ConnectionClosed:
                self.log("连接断开，5秒后重连...")
                await asyncio.sleep(5)
            except Exception as e:
                self.log(f"连接异常: {e}", "ERROR")
                await asyncio.sleep(5)


if __name__ == "__main__":
    try:
        asyncio.run(PatAllBot().run())
    except KeyboardInterrupt:
        print("\n程序已退出")
