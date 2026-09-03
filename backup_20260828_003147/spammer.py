import random
import time
import re
import json
from typing import Dict,Optional
import asyncio
class SimpleSpammer:
    """简单可用的刷屏器 - 修改版"""
    
    def __init__(self):
        self.tasks = {}  # 任务字典
        self.active = False
        self.websocket = None  # 添加websocket属性
        
        # 基础配置
        self.default_duration = 30  # 默认30秒
        self.min_interval = 0.1    # 最小间隔0.1秒
        self.max_interval = 0.5    # 最大间隔0.5秒
        
        # 脏话词库
        self.curses = [
            "傻逼", "废物", "垃圾", "弱智", "脑残",
            "憨批", "傻狗", "废物东西", "垃圾玩意",
            "看见你就烦", "赶紧滚", "别说话", "真恶心",
            "你妈死了", "操你妈", "滚远点", "闭嘴吧",
            "不会说话别说", "真让人无语", "脑子呢",
            "狗东西", "贱人", "弱智儿童", "智障玩意",
            "脑子被驴踢了", "你配吗", "真下头"
        ]
        
        print("[刷屏器] 简单刷屏器初始化完成")
    
    def set_websocket(self, websocket):
        """设置WebSocket连接"""
        self.websocket = websocket
        print("[刷屏器] WebSocket已设置")
    
    def parse_duration(self, text: str) -> int:
        """解析时长 - 最大1小时"""
        if not text:
            return self.default_duration
        
        MAX_DURATION = 3600  # 1小时 = 3600秒
        text = text.lower().strip()
        
        # 纯数字
        if text.isdigit():
            seconds = int(text)
            return max(5, min(seconds, MAX_DURATION))
        
        # 带单位
        patterns = [
            (r'(\d+)\s*s', 1),          # 30s
            (r'(\d+)\s*秒', 1),         # 30秒
            (r'(\d+)\s*m', 60),         # 1m
            (r'(\d+)\s*分钟', 60),      # 1分钟
            (r'(\d+)\s*min', 60),       # 1min
            (r'(\d+)\s*h', 3600),       # 1h
            (r'(\d+)\s*小时', 3600),    # 1小时
            (r'(\d+)\s*hr', 3600),      # 1hr
        ]
        
        for pattern, multiplier in patterns:
            match = re.match(pattern, text)
            if match:
                num = int(match.group(1))
                seconds = num * multiplier
                return max(5, min(seconds, MAX_DURATION))
        
        return self.default_duration
    
    async def start_spam(self, target_qq: int, group_id: int, 
                         duration_text: str) -> str:  # 移除websocket参数
        """开始刷屏"""


            
        return " 你好，该功能被禁用"
            

    
    async def _run_spam(self, task_id: str, target_qq: int, group_id: int, 
                       duration: int):  # 移除websocket参数
        """运行刷屏任务"""
        try:
            start_time = time.time()
            message_count = 0
            
            print(f"[刷屏器] 任务{task_id}开始运行")
            
            while time.time() - start_time < duration:
                try:
                    # 检查WebSocket
                    if not self.websocket:
                        print(f"[刷屏器] WebSocket丢失，停止任务")
                        break
                    
                    # 随机选择脏话
                    curse = random.choice(self.curses)
                    message = f"[CQ:at,qq={target_qq}] {curse}"
                    
                    # 发送消息（使用存储的websocket）
                    await self.websocket.send(json.dumps({
                        "action": "send_msg",
                        "params": {
                            "message_type": "group",
                            "group_id": int(group_id),
                            "message": message
                        }
                    }))
                    
                    message_count += 1
                    
                    # 每10条消息输出一次
                    if message_count % 10 == 0:
                        print(f"[刷屏器] 已发送{message_count}条消息")
                    
                    # 随机间隔
                    wait_time = random.uniform(self.min_interval, self.max_interval)
                    await asyncio.sleep(wait_time)
                    
                except Exception as e:
                    print(f"[刷屏器] 发送失败: {e}")
                    await asyncio.sleep(1)
            
            print(f"[刷屏器] 任务{task_id}完成，共发送{message_count}条消息")
            
        except Exception as e:
            print(f"[刷屏器] 任务{task_id}异常: {e}")
        finally:
            # 清理任务
            if task_id in self.tasks:
                del self.tasks[task_id]
            print(f"[刷屏器] 任务{task_id}已清理")
    
    def stop_group_spam(self, group_id: int) -> int:
        """停止群刷屏"""
        stopped = 0
        tasks_to_remove = []
        
        for task_id, task in self.tasks.items():
            if task_id.endswith(f"_{group_id}_"):
                if not task.done():
                    task.cancel()
                    stopped += 1
                tasks_to_remove.append(task_id)
        
        # 清理任务
        for task_id in tasks_to_remove:
            if task_id in self.tasks:
                del self.tasks[task_id]
        
        if stopped > 0:
            print(f"[刷屏器] 停止{stopped}个刷屏任务")
        
        return stopped
    
    def get_status(self) -> str:
        """获取状态"""
        if not self.tasks:
            return f" 你好，该功能被禁用"
        
        result = [f"当前有{len(self.tasks)}个刷屏任务:"]
        for task_id in self.tasks.keys():
            # 从task_id中解析信息
            parts = task_id.split('_')
            if len(parts) >= 4:
                target_qq = parts[1]
                group_id = parts[2]
                result.append(f"- 目标: {target_qq} @ 群{group_id}")
        
        return "\n".join(result)
    def stop_all(self) -> int:
        """停止所有刷屏任务"""
        stopped = 0
        
        for task_id, task in self.tasks.items():
            if not task.done():
                task.cancel()
                stopped += 1
                print(f"[刷屏器] 停止任务: {task_id}")
        
        # 清空任务字典
        self.tasks.clear()
        
        if stopped > 0:
            print(f"[刷屏器] 总共停止了 {stopped} 个刷屏任务")
        else:
            print(f"[刷屏器] 没有刷屏任务可停止")
        
        return stopped
    
    def stop_group_spam(self, group_id: int) -> int:
        """停止指定群的刷屏"""
        stopped = 0
        tasks_to_remove = []
        
        group_str = str(group_id)
        
        for task_id, task in self.tasks.items():
            # 检查task_id是否包含该群号
            if f"_{group_str}_" in task_id:
                if not task.done():
                    task.cancel()
                    stopped += 1
                    print(f"[刷屏器] 停止群{group_id}的任务: {task_id}")
                tasks_to_remove.append(task_id)
        
        # 清理任务
        for task_id in tasks_to_remove:
            if task_id in self.tasks:
                del self.tasks[task_id]
        
        return stopped
