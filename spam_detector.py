


import sys
import os
import json
import time
import builtins
from datetime import datetime
from typing import Dict, Optional, List
import asyncio
from typing import Optional


# ==================== 授权验证 ====================
def _verify_module():
    """验证模块授权"""
    module_name = "spam_detector"
    
    try:
        license_key = getattr(builtins, 'XP12_LICENSE_KEY', '')
        print(f"[调试] 从 builtins 读取密钥: {license_key}")
    except Exception as e:
        print(f"[调试] 读取 builtins 异常: {e}")
        license_key = ''
    
    expected_key = ''
    try:
        if os.path.exists("data/.module_license"):
            with open("data/.module_license", "r") as f:
                data = json.load(f)
                expected_key = data.get("license_key", '')
                print(f"[调试] 从文件读取密钥: {expected_key}")
    except Exception as e:
        print(f"[调试] 读取文件异常: {e}")
        pass
    
    print(f"[调试] 对比: license_key={license_key}, expected_key={expected_key}")
    
    if license_key != expected_key or not expected_key:
        print(f"❌ 模块 [{module_name}] 授权失败！")
        print(f"   请通过主程序调用本模块")
        sys.exit(1)
    
    print(f"✅ 模块 [{module_name}] 授权通过")

_verify_module()

# ==================== 正常代码 ====================
"""
模块名：spam_detector
功能：待补充
"""

# ==================== 正常代码 ====================




class SpamDetector:
    """刷屏检测器"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.record_file = os.path.join(data_dir, "spam_detector_records.json")
        self.enabled_groups_file = os.path.join(data_dir, "spam_detector_groups.json")
        
        # 配置参数（不可变）
        self.time_window = 1           # 时间窗口（秒）
        self.max_messages = 5          # 窗口内最大消息数
        self.cooldown = 30             # 检测冷却（秒）
        self.base_mute_duration = 600  # 基础禁言时长（秒）= 10分钟
        self.max_mute_duration = 19200 # 最大禁言时长（秒）= 320分钟
        
        # 启用的群列表
        self.enabled_groups = []
        
        # 记录数据
        self.records = {}  # {group_id: {user_id: {"count": 0, "first_time": 0, "last_time": 0, "mute_level": 0, "mute_end_time": 0}}}
        self.cooldowns = {}  # {group_id: {user_id: last_check_time}}
        self.last_reset_date = None
        
        self.load_groups()
        self.load_records()
        self.check_reset()
        
        print("[刷屏检测] 初始化完成")
        print(f"[刷屏检测] 已启用群: {self.enabled_groups}")
    
    # ==================== 加载/保存 ====================
    
    def load_groups(self):
        """加载启用的群列表"""
        try:
            if os.path.exists(self.enabled_groups_file):
                with open(self.enabled_groups_file, 'r', encoding='utf-8') as f:
                    self.enabled_groups = json.load(f)
        except Exception as e:
            print(f"[刷屏检测] 群列表加载失败: {e}")
            self.enabled_groups = []
        self.save_groups()
    
    def save_groups(self):
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            with open(self.enabled_groups_file, 'w', encoding='utf-8') as f:
                json.dump(self.enabled_groups, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[刷屏检测] 群列表保存失败: {e}")
    
    def load_records(self):
        try:
            if os.path.exists(self.record_file):
                with open(self.record_file, 'r', encoding='utf-8') as f:
                    self.records = json.load(f)
        except Exception as e:
            print(f"[刷屏检测] 记录加载失败: {e}")
            self.records = {}
        self.save_records()
    def get_mute_level(self, group_id: str, user_id: str) -> int:
        """获取用户的禁言等级"""
        group_str = str(group_id)
        user_str = str(user_id)
        
        if group_str in self.records:
            if user_str in self.records[group_str]:
                return self.records[group_str][user_str].get("mute_level", 0)
        
        return 0
    def get_mute_end_time(self, group_id: str, user_id: str) -> int:
        """获取用户的禁言结束时间戳"""
        group_str = str(group_id)
        user_str = str(user_id)
        
        if group_str in self.records:
            if user_str in self.records[group_str]:
                return self.records[group_str][user_str].get("mute_end_time", 0)
        
        return 0
    def clear_user_record(self, group_id: str, user_id: str) -> bool:
        """清除用户的刷屏记录"""
        group_str = str(group_id)
        user_str = str(user_id)
        
        if group_str in self.records:
            if user_str in self.records[group_str]:
                del self.records[group_str][user_str]
                # 如果群记录为空，删除群记录
                if not self.records[group_str]:
                    del self.records[group_str]
                self.save_records()
                print(f"[刷屏检测] ✅ 已清除用户 {user_str} 在群 {group_str} 的记录")
                return True
        
        return False
    
    def clear_group_records(self, group_id: str) -> int:
        """清除群内所有用户的刷屏记录，返回清除数量"""
        group_str = str(group_id)
        count = 0
        
        if group_str in self.records:
            count = len(self.records[group_str])
            del self.records[group_str]
            self.save_records()
            print(f"[刷屏检测] ✅ 已清除群 {group_str} 的全部刷屏记录，共 {count} 条")
        
        return count
    def is_user_in_whitelist(self, user_id: str) -> bool:
        """检查用户是否在自动解禁白名单中"""
        return str(user_id) in self.user_whitelist
    def get_mute_level(self, group_id: str, user_id: str) -> int:
        """获取用户的禁言等级"""
        group_str = str(group_id)
        user_str = str(user_id)
        
        if group_str in self.records:
            if user_str in self.records[group_str]:
                return self.records[group_str][user_str].get("mute_level", 0)
        
        return 0
    def is_user_monitored(self, group_id: str, user_id: str) -> bool:
        """检查用户是否在刷屏监控中（有刷屏记录且未被清理）"""
        group_str = str(group_id)
        user_str = str(user_id)
        
        # 检查 records 里有没有该用户的记录
        if group_str in self.records:
            if user_str in self.records[group_str]:
                # 检查是否还有有效记录（最近24小时内有活动）
                last_time = self.records[group_str][user_str].get("last_time", 0)
                if time.time() - last_time < 86400:  # 24小时内
                    return True
        
        return False
    def save_records(self):
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            cleaned = self._clean_records()
            with open(self.record_file, 'w', encoding='utf-8') as f:
                json.dump(self.records, f, ensure_ascii=False, indent=2)
            if cleaned > 0:
                print(f"[刷屏检测] 清理了 {cleaned} 条过期记录")
        except Exception as e:
            print(f"[刷屏检测] 记录保存失败: {e}")
    
    def _clean_records(self) -> int:
        """清理超过24小时未活动的记录"""
        now = time.time()
        cleaned = 0
        for group_id in list(self.records.keys()):
            for user_id in list(self.records[group_id].keys()):
                last_time = self.records[group_id][user_id].get("last_time", 0)
                if now - last_time > 86400:
                    del self.records[group_id][user_id]
                    cleaned += 1
            if not self.records[group_id]:
                del self.records[group_id]
        return cleaned
    
    # ==================== 每日重置 ====================
    
    def check_reset(self):
        today = datetime.now().strftime("%Y-%m-%d")
        if self.last_reset_date != today:
            self._reset_daily()
            self.last_reset_date = today
            self.save_records()
            print(f"[刷屏检测] 每日重置完成 ({today})")
    
    def _reset_daily(self):
        for group_id in self.records:
            for user_id in self.records[group_id]:
                self.records[group_id][user_id]["mute_level"] = 0
                self.records[group_id][user_id]["mute_end_time"] = 0
                self.records[group_id][user_id]["count"] = 0
                self.records[group_id][user_id]["first_time"] = 0
                self.records[group_id][user_id]["last_time"] = 0
    
    # ==================== 群管理 ====================
    
    def enable_group(self, group_id: str) -> bool:
        if group_id not in self.enabled_groups:
            self.enabled_groups.append(group_id)
            self.save_groups()
            return True
        return False
    
    def disable_group(self, group_id: str) -> bool:
        if group_id in self.enabled_groups:
            self.enabled_groups.remove(group_id)
            self.save_groups()
            return True
        return False
    
    def is_group_enabled(self, group_id: str) -> bool:
        return group_id in self.enabled_groups
    
    def get_status(self, group_id: str = None) -> str:
        lines = ["📋 刷屏检测状态"]
        lines.append(f"时间窗口: {self.time_window}秒")
        lines.append(f"触发阈值: {self.max_messages}条")
        lines.append(f"基础禁言: {self._format_duration(self.base_mute_duration)}")
        lines.append(f"最大禁言: {self._format_duration(self.max_mute_duration)}")
        
        if group_id:
            enabled = self.is_group_enabled(group_id)
            lines.append(f"本群状态: {'✅ 已启用' if enabled else '❌ 未启用'}")
            if enabled and group_id in self.records:
                active = len([u for u in self.records[group_id] if self.records[group_id][u].get("mute_level", 0) > 0])
                lines.append(f"本群禁言用户: {active}人")
        else:
            lines.append(f"启用群: {len(self.enabled_groups)}个")
        
        return "\n".join(lines)
    
    # ==================== 核心检测 ====================
    
    async def check_message(self, group_id: str, user_id: str, websocket) -> Optional[Dict]:
        if not self.is_group_enabled(group_id):
            return None
        
        cooldown_key = f"{group_id}_{user_id}"
        now = time.time()
        if cooldown_key in self.cooldowns:
            if now - self.cooldowns[cooldown_key] < self.cooldown:
                return None
        
        if group_id not in self.records:
            self.records[group_id] = {}
        if user_id not in self.records[group_id]:
            self.records[group_id][user_id] = {
                "count": 0,
                "first_time": 0,
                "last_time": 0,
                "mute_level": 0,
                "mute_end_time": 0
            }
        
        record = self.records[group_id][user_id]
        
        # 检查是否在禁言中（如果有剩余禁言时间，重新禁言）
        if record["mute_end_time"] > now:
            remaining = record["mute_end_time"] - now
            record["mute_level"] += 1
            new_duration = min(
                self.base_mute_duration * (2 ** record["mute_level"]),
                self.max_mute_duration
            )
            if remaining < new_duration:
                new_duration = remaining
            record["mute_end_time"] = now + new_duration
            
            self.cooldowns[cooldown_key] = now
            self.save_records()
            
            return {
                "action": "set_group_ban",
                "params": {
                    "group_id": int(group_id),
                    "user_id": int(user_id),
                    "duration": int(new_duration)
                },
                "echo": f"spam_ban_{group_id}_{user_id}_{int(time.time())}"
            }
        
        # 更新消息计数
        if now - record["first_time"] > self.time_window:
            record["count"] = 1
            record["first_time"] = now
        else:
            record["count"] += 1
        
        record["last_time"] = now
        
        # 检查是否触发
        if record["count"] >= self.max_messages:
            record["mute_level"] += 1
            duration = min(
                self.base_mute_duration * (2 ** record["mute_level"]),
                self.max_mute_duration
            )
            record["mute_end_time"] = now + duration
            record["count"] = 0
            
            self.cooldowns[cooldown_key] = now
            self.save_records()
            
            print(f"[刷屏检测] 用户 {user_id} 在群 {group_id} 触发刷屏，等级 {record['mute_level']}，禁言 {self._format_duration(duration)}")
            
            return {
                "action": "set_group_ban",
                "params": {
                    "group_id": int(group_id),
                    "user_id": int(user_id),
                    "duration": int(duration)
                },
                "echo": f"spam_ban_{group_id}_{user_id}_{int(time.time())}"
            }
        
        self.save_records()
        return None
    
    # ==================== 工具方法 ====================
    
    def _format_duration(self, seconds: int) -> str:
        if seconds <= 0:
            return "永久"
        
        units = [
            (86400, "天"),
            (3600, "小时"),
            (60, "分钟"),
            (1, "秒")
        ]
        
        parts = []
        remaining = seconds
        for unit_sec, unit_name in units:
            if remaining >= unit_sec:
                count = remaining // unit_sec
                remaining %= unit_sec
                parts.append(f"{int(count)}{unit_name}")
        
        return "".join(parts) if parts else "0秒"


# ==================== 全局实例 ====================
_spam_detector = None

def get_spam_detector():
    global _spam_detector
    if _spam_detector is None:
        _spam_detector = SpamDetector()
    return _spam_detector
