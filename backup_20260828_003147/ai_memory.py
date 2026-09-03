# ai_memory.py
import json
import os
import time
from datetime import datetime
from typing import Dict, List, Optional
import hashlib

class AIMemoryModule:
    """AI记忆模块 - 自然的对话记忆，无需消息ID"""
    
    def __init__(self, data_dir="data/ai_memory"):
        self.data_dir = data_dir
        self.memory_file = os.path.join(data_dir, "conversation_memory.json")
        self.memory_expiry_hours = 1  # 记忆过期时间1小时
        self.max_context_messages = 10  # 最大上下文消息数
        
        # 确保目录存在
        os.makedirs(data_dir, exist_ok=True)
        
        # 用户对话记忆 {user_id: [{"timestamp": ..., "message": ..., "response": ...}]}
        self.user_memory = {}
        
        self.load_memory()
        print(f"[AI记忆] 模块初始化完成 - 已加载 {sum(len(v) for v in self.user_memory.values())} 条对话记忆")
    
    def load_memory(self):
        """加载记忆数据"""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.user_memory = data
                    
                    # 清理过期记忆
                    self.clean_expired_memory()
                    
                print(f"[AI记忆] 成功加载记忆文件")
            else:
                print(f"[AI记忆] 记忆文件不存在，创建新文件")
                self.save_memory()
        except Exception as e:
            print(f"[AI记忆] 加载记忆失败: {e}")
            self.user_memory = {}
    
    def save_memory(self):
        """保存记忆数据"""
        try:
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_memory, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"[AI记忆] 保存记忆失败: {e}")
            return False
    
    def clean_expired_memory(self):
        """清理过期记忆（1小时）"""
        current_time = time.time()
        expiry_seconds = self.memory_expiry_hours * 3600
        removed_count = 0
        
        for user_id in list(self.user_memory.keys()):
            # 过滤过期消息
            valid_messages = []
            for msg in self.user_memory[user_id]:
                if current_time - msg.get("timestamp", 0) <= expiry_seconds:
                    valid_messages.append(msg)
                else:
                    removed_count += 1
            
            # 更新或删除用户记录
            if valid_messages:
                self.user_memory[user_id] = valid_messages
            else:
                del self.user_memory[user_id]
        
        if removed_count > 0:
            print(f"[AI记忆] 清理了 {removed_count} 条过期记录")
            self.save_memory()
    
    def add_conversation(self, user_id: str, message: str, response: str):
        """添加对话记录"""
        user_id_str = str(user_id)
        timestamp = time.time()
        
        # 确保用户记录存在
        if user_id_str not in self.user_memory:
            self.user_memory[user_id_str] = []
        
        # 添加新记录
        record = {
            "timestamp": timestamp,
            "message": str(message)[:300],  # 限制长度
            "response": str(response)[:300],
            "time_str": datetime.fromtimestamp(timestamp).strftime("%H:%M")
        }
        
        self.user_memory[user_id_str].append(record)
        
        # 限制每个用户的记录数量
        if len(self.user_memory[user_id_str]) > self.max_context_messages:
            self.user_memory[user_id_str] = self.user_memory[user_id_str][-self.max_context_messages:]
        
        # 保存记忆
        self.save_memory()
        
        print(f"[AI记忆] 为用户 {user_id_str} 添加了对话记录")
    
    def get_conversation_context(self, user_id: str, current_message: str, limit: int = 5) -> str:
        """获取对话上下文"""
        user_id_str = str(user_id)
        
        if user_id_str not in self.user_memory or not self.user_memory[user_id_str]:
            return current_message
        
        # 获取最近的对话记录
        recent_conversations = self.user_memory[user_id_str][-limit:]
        
        context_parts = ["我们之前的对话："]
        
        for i, conv in enumerate(recent_conversations, 1):
            context_parts.append(f"[{conv['time_str']}] 你: {conv['message']}")
            context_parts.append(f"[{conv['time_str']}] 我: {conv['response']}")
        
        context_parts.append(f"现在你说: {current_message}")
        context_parts.append("请根据我们的对话历史来回复:")
        
        return "\n".join(context_parts)
    
    def get_previous_message(self, user_id: str) -> Optional[Dict]:
        """获取用户上一条消息"""
        user_id_str = str(user_id)
        
        if user_id_str not in self.user_memory or len(self.user_memory[user_id_str]) < 2:
            return None
        
        # 返回倒数第二条消息（最后一条是当前消息）
        return self.user_memory[user_id_str][-2]
    
    def get_recent_messages(self, user_id: str, limit: int = 5) -> List[Dict]:
        """获取用户最近的几条消息"""
        user_id_str = str(user_id)
        
        if user_id_str not in self.user_memory:
            return []
        
        return self.user_memory[user_id_str][-limit:]
    
    def clear_user_memory(self, user_id: str) -> int:
        """清除特定用户的记忆"""
        user_id_str = str(user_id)
        if user_id_str not in self.user_memory:
            return 0
        
        count = len(self.user_memory[user_id_str])
        del self.user_memory[user_id_str]
        self.save_memory()
        
        print(f"[AI记忆] 已清除用户 {user_id_str} 的 {count} 条记忆")
        return count
    
    def clear_all_memory(self) -> int:
        """清除所有记忆"""
        total_count = sum(len(v) for v in self.user_memory.values())
        self.user_memory = {}
        self.save_memory()
        
        print(f"[AI记忆] 已清除所有 {total_count} 条记忆")
        return total_count
    
    def get_memory_stats(self) -> Dict:
        """获取记忆统计"""
        return {
            "total_users": len(self.user_memory),
            "total_messages": sum(len(v) for v in self.user_memory.values()),
            "memory_expiry_hours": self.memory_expiry_hours
        }
