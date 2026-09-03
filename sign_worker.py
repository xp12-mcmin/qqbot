"""
独立打卡工作线程 - 使用队列
"""

import time
import random
import threading


class SignWorker(threading.Thread):
    """打卡工作线程"""
    
    def __init__(self, send_func, sign_groups, send_message_enabled):
        super().__init__()
        self.send_func = send_func  # 发送消息的函数
        self.sign_groups = sign_groups
        self.send_message_enabled = send_message_enabled
        self.daemon = True
        
        self.on_progress = None
        self.on_finish = None
        self.is_running = False
        
    def run(self):
        """线程入口"""
        self.is_running = True
        self._do_sign()
    
    def _do_sign(self):
        """执行打卡（同步版本，不使用asyncio）"""
        success_count = 0
        fail_count = 0
        total = len(self.sign_groups)
        
        sign_messages = [
            "午夜打卡！新的一天开始啦~",
            "零点签到！又是崭新的一天！",
            "深夜打卡成功！大家早点休息~",
            "准时打卡！开启新的一天！",
            "午夜时分，打卡完成！"
        ]
        
        for i, group_id in enumerate(self.sign_groups):
            if not self.is_running:
                break
            
            if self.on_progress:
                self.on_progress(i + 1, total, group_id)
            
            try:
                if self.send_message_enabled:
                    sign_msg = random.choice(sign_messages)
                    message_data = {
                        "action": "send_msg",
                        "params": {
                            "message_type": "group",
                            "group_id": int(group_id),
                            "message": sign_msg
                        },
                        "echo": f"sign_{group_id}_{int(time.time())}"
                    }
                else:
                    message_data = {
                        "action": "send_group_sign",
                        "params": {"group_id": int(group_id)},
                        "echo": f"sign_{group_id}_{int(time.time())}"
                    }
                
                # 调用发送函数（同步）
                self.send_func(message_data)
                success_count += 1
                print(f"[打卡] 群 {group_id} 打卡成功 ({i+1}/{total})")
                
            except Exception as e:
                fail_count += 1
                print(f"[打卡] 群 {group_id} 打卡失败: {e}")
            
            # 延迟，避免风控
            if i < total - 1:
                time.sleep(random.uniform(1.5, 2.5))
        
        if self.on_finish:
            self.on_finish(success_count, fail_count, total)
        
        self.is_running = False
    
    def stop(self):
        self.is_running = False