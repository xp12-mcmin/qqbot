"""
自动签到脚本 - 使用网络时间同步
"""

import asyncio
import websockets
import json
import time
from datetime import datetime, timedelta
import random
import aiohttp


class AutoSign:
    def __init__(self):
        self.websocket = None
        self.sign_groups = []
        self.running = True
        
        # 网络时间服务器列表
        self.time_servers = [
            "http://worldtimeapi.org/api/timezone/Asia/Shanghai",
            "http://api.time.taobao.com/api/get_ippack?type=gettimenow",
            "http://quan.suning.com/getSysTime.do",
            "http://ntp.aliyun.com",
        ]
        
        # 缓存的网络时间偏移
        self.time_offset = 0  # 网络时间 - 本地时间
        self.last_sync = 0
    
    def _now(self):
        """获取当前时间（考虑网络时间偏移）"""
        if self.time_offset != 0:
            return (datetime.now() + timedelta(seconds=self.time_offset)).strftime("%H:%M:%S.%f")[:-3]
        return datetime.now().strftime("%H:%M:%S.%f")[:-3]
    
    def _get_datetime(self):
        """获取当前 datetime 对象（考虑偏移）"""
        if self.time_offset != 0:
            return datetime.now() + timedelta(seconds=self.time_offset)
        return datetime.now()
    
    async def sync_time(self):
        """从网络同步时间（修复时区问题）"""
        print(f"[{self._now()}] 🌐 正在同步网络时间...")
        
        # 使用苏宁时间API
        api_url = "http://quan.suning.com/getSysTime.do"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.text()
                        import json
                        result = json.loads(data)
                        # 返回格式 {"sysTime2":"2026-05-04 08:30:00","sysTime1":"20260504083000"}
                        if 'sysTime2' in result:
                            # 解析网络时间（不带时区信息）
                            net_time_str = result['sysTime2']
                            net_time = datetime.strptime(net_time_str, "%Y-%m-%d %H:%M:%S")
                            
                            # 获取本地时间（不带时区信息）
                            local_time = datetime.now()
                            
                            # 移除本地时间的微秒，保持精度一致
                            local_time = local_time.replace(microsecond=0)
                            
                            # 计算偏移（两个都是 naive datetime，可以相减）
                            self.time_offset = (net_time - local_time).total_seconds()
                            self.last_sync = time.time()
                            
                            print(f"[{self._now()}] ✅ 时间同步成功")
                            print(f"   网络时间: {net_time.strftime('%Y-%m-%d %H:%M:%S')}")
                            print(f"   本地时间: {local_time.strftime('%Y-%m-%d %H:%M:%S')}")
                            print(f"   时间差: {self.time_offset:.2f} 秒")
                            return True
        except Exception as e:
            print(f"   同步失败: {e}")
        
        print(f"[{self._now()}] ❌ 同步失败，使用本地时间")
        self.time_offset = 0
        return False
                            
   
    async def connect(self):
        try:
            self.websocket = await websockets.connect("ws://127.0.0.1:8765")
            print(f"[{self._now()}] ✅ 连接成功")
            return True
        except Exception as e:
            print(f"[{self._now()}] ❌ 连接失败: {e}")
            return False
    
    async def keep_alive(self):
        """持续接收消息，保持连接活跃"""
        while self.running and self.websocket:
            try:
                msg = await asyncio.wait_for(self.websocket.recv(), timeout=10)
                # 忽略接收到的消息，只用于保持连接
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"[{self._now()}] ❌ 连接异常: {e}")
                self.websocket = None
                break
    
    async def get_group_list(self):
        if not self.websocket:
            return False
        try:
            await self.websocket.send(json.dumps({
                "action": "get_group_list",
                "params": {"no_cache": False},
                "echo": f"get_list_{int(time.time()*1000)}"
            }))
            
            timeout = 10
            start = time.time()
            while time.time() - start < timeout:
                try:
                    msg = await asyncio.wait_for(self.websocket.recv(), timeout=1)
                    data = json.loads(msg)
                    if data.get("echo", "").startswith("get_list_"):
                        if data.get("status") == "ok":
                            groups = data.get("data", [])
                            self.sign_groups = [str(g["group_id"]) for g in groups]
                            print(f"[{self._now()}] 📋 获取到 {len(self.sign_groups)} 个群")
                            return True
                except asyncio.TimeoutError:
                    continue
            return False
        except Exception as e:
            print(f"[{self._now()}] ❌ 获取群列表失败: {e}")
            return False
    
    async def sign_group(self, group_id: str):
        """打卡单个群"""
        try:
            # 发送打卡消息
            sign_messages = [
                "午夜打卡！新的一天开始啦~",
                "零点签到！又是崭新的一天！",
                "深夜打卡成功！大家早点休息~",
                "准时打卡！开启新的一天！",
                "午夜时分，打卡完成！"
            ]
            msg = random.choice(sign_messages)
            
            msg_data = {
                "action": "send_msg",
                "params": {
                    "message_type": "group",
                    "group_id": int(group_id),
                    "message": msg
                },
                "echo": f"msg_{group_id}_{int(time.time()*1000)}"
            }
            await self.websocket.send(json.dumps(msg_data))
            
            # 调用打卡API
            sign_data = {
                "action": "send_group_sign",
                "params": {
                    "group_id": int(group_id)
                },
                "echo": f"sign_{group_id}_{int(time.time()*1000)}"
            }
            await self.websocket.send(json.dumps(sign_data))
            
            return True
        except Exception as e:
            print(f"[{self._now()}] ❌ {group_id}: {e}")
            return False
    
    async def sign_all(self):
        """打卡所有群"""
        if not self.sign_groups:
            print(f"[{self._now()}] ❌ 群列表为空")
            return
        
        success = 0
        total = len(self.sign_groups)
        print(f"[{self._now()}] 🚀 开始打卡 {total} 个群...")
        
        for i, group_id in enumerate(self.sign_groups):
            if await self.sign_group(group_id):
                success += 1
                print(f"[{self._now()}] ✅ {i+1}/{total}: {group_id}")
            else:
                print(f"[{self._now()}] ❌ {i+1}/{total}: {group_id}")
            await asyncio.sleep(0.05)
        
        print(f"[{self._now()}] 🎉 完成: 成功 {success}/{total}")
    
    async def wait_for_midnight(self):
        """等待午夜签到（基于网络时间）"""
        last_print = -1
        last_minute = -1
        
        while True:
            now_net = self._get_datetime()
            tomorrow = now_net.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            seconds_left = (tomorrow - now_net).total_seconds()
            
            # 每5分钟重新同步一次时间，防止漂移
            if time.time() - self.last_sync > 300:  # 5分钟
                await self.sync_time()
            
            # 打印倒计时
            if seconds_left <= 60:
                # 最后60秒，每秒打印
                if int(seconds_left) != last_print:
                    print(f"[{self._now()}] ⏰ 距离签到还有 {int(seconds_left)} 秒")
                    last_print = int(seconds_left)
                    last_minute = -1
            elif seconds_left <= 300:
                # 最后5分钟，每10秒打印
                current = int(seconds_left // 10)
                if current != last_print:
                    print(f"[{self._now()}] ⏰ 距离签到还有 {int(seconds_left)} 秒")
                    last_print = current
            else:
                # 大于5分钟，每分钟打印
                minutes_left = int(seconds_left // 60)
                if minutes_left != last_minute:
                    print(f"[{self._now()}] ⏰ 距离签到还有 {minutes_left} 分钟")
                    last_minute = minutes_left
                    last_print = -1
            
            # 最后10秒，精确等待
            if seconds_left <= 10:
                if seconds_left <= 0.05:
                    print(f"[{self._now()}] 🔥 开始抢签!")
                    await self.sign_all()
                    return
                else:
                    await asyncio.sleep(0.01)
                    continue
            
            # 正常等待
            if seconds_left <= 60:
                await asyncio.sleep(0.1)
            else:
                await asyncio.sleep(5)
    
    async def run(self):
        print("=" * 50)
        print("       自动签到脚本 v5.0")
        print("       使用网络时间同步")
        print("=" * 50)
        
        # 启动时同步时间
        await self.sync_time()
        
        while True:
            # 连接
            if not await self.connect():
                await asyncio.sleep(5)
                continue
            
            # 获取群列表
            if not await self.get_group_list():
                await asyncio.sleep(10)
                continue
            
            # 启动保活任务
            keep_task = asyncio.create_task(self.keep_alive())
            
            # 等待签到
            await self.wait_for_midnight()
            
            # 停止保活
            self.running = False
            keep_task.cancel()
            
            print(f"[{self._now()}] ✅ 今日签到完成")
            await asyncio.sleep(10)
            self.running = True


if __name__ == "__main__":
    asyncio.run(AutoSign().run())
