"""
名片管理模块 - 强制改名、循环清空
"""

import asyncio
import json
import time


class RenameManager:
    def __init__(self, websocket=None):
        self.websocket = websocket
        self.loop_tasks = {}  # {task_key: asyncio.Task}
    
    def set_websocket(self, websocket):
        self.websocket = websocket
    
    async def force_rename(self, group_id: str, user_ids: list, operator_id: str) -> dict:
        """强制改名片为空白"""
        results = []
        for uid in user_ids:
            try:
                await self.websocket.send(json.dumps({
                    "action": "set_group_card",
                    "params": {
                        "group_id": int(group_id),
                        "user_id": int(uid),
                        "card": ""
                    },
                    "echo": f"force_rename_{uid}_{int(time.time()*1000)}"
                }))
                results.append(f"✅ {uid} 名片已清空")
                await asyncio.sleep(0.5)
            except Exception as e:
                results.append(f"❌ {uid} 失败: {e}")
        
        if not results:
            return {
                "action": "send_msg",
                "params": {
                    "message_type": "group",
                    "group_id": int(group_id),
                    "message": "❌ 没有执行任何改名操作"
                }
            }
        
        return {
            "action": "send_msg",
            "params": {
                "message_type": "group",
                "group_id": int(group_id),
                "message": "\n".join(results)
            }
        }
    
    async def start_loop_rename(self, group_id: str, user_ids: list, operator_id: str) -> dict:
        """启动循环清空名片（每5秒一次）"""
        task_key = f"loop_rename_{group_id}"
        
        if task_key in self.loop_tasks and not self.loop_tasks[task_key].done():
            return {
                "action": "send_msg",
                "params": {
                    "message_type": "group",
                    "group_id": int(group_id),
                    "message": "⏳ 该群已有循环任务在运行，请先停止再启动"
                }
            }
        
        task = asyncio.create_task(
            self._loop_worker(group_id, user_ids)
        )
        self.loop_tasks[task_key] = task
        
        return {
            "action": "send_msg",
            "params": {
                "message_type": "group",
                "group_id": int(group_id),
                "message": f"✅ 已启动循环清空名片\n群: {group_id}\n目标: {', '.join(user_ids)}\n间隔: 5秒\n\n发送「!停止清空 {group_id}」停止"
            }
        }
    
    async def _loop_worker(self, group_id: str, user_ids: list):
        """循环清空名片工作线程"""
        task_key = f"loop_rename_{group_id}"
        count = 0
        
        try:
            while True:
                count += 1
                print(f"[循环清空] 第 {count} 次执行 - 群{group_id}")
                
                for uid in user_ids:
                    try:
                        await self.websocket.send(json.dumps({
                            "action": "set_group_card",
                            "params": {
                                "group_id": int(group_id),
                                "user_id": int(uid),
                                "card": ""
                            },
                            "echo": f"loop_rename_{uid}_{int(time.time()*1000)}"
                        }))
                        await asyncio.sleep(0.3)
                    except Exception as e:
                        print(f"[循环清空] 用户{uid}失败: {e}")
                
                await asyncio.sleep(5)
                
        except asyncio.CancelledError:
            print(f"[循环清空] 群{group_id} 任务已停止")
            if task_key in self.loop_tasks:
                del self.loop_tasks[task_key]
        except Exception as e:
            print(f"[循环清空] 异常: {e}")
            if task_key in self.loop_tasks:
                del self.loop_tasks[task_key]
    
    async def stop_loop_rename(self, group_id: str, operator_id: str) -> dict:
        """停止循环清空"""
        task_key = f"loop_rename_{group_id}"
        
        if task_key in self.loop_tasks and not self.loop_tasks[task_key].done():
            self.loop_tasks[task_key].cancel()
            await asyncio.sleep(0.5)
            if task_key in self.loop_tasks:
                del self.loop_tasks[task_key]
            return {
                "action": "send_msg",
                "params": {
                    "message_type": "group",
                    "group_id": int(group_id),
                    "message": f"✅ 已停止群{group_id}的循环清空"
                }
            }
        else:
            return {
                "action": "send_msg",
                "params": {
                    "message_type": "group",
                    "group_id": int(group_id),
                    "message": f"❌ 群{group_id}没有正在运行的循环任务"
                }
            }
