"""
自动解禁模块
- 群白名单：机器人被禁言时自动解禁自己
- 用户白名单：白名单用户被禁言时自动解禁他们
默认关闭，需管理员开启
"""

import json
import os
import time
from typing import Dict, List, Optional

class AutoUnmuteManager:
    def __init__(self, data_dir: str = "data"):
        self.config_file = os.path.join(data_dir, "auto_unmute_config.json")
        self.log_file = os.path.join(data_dir, "auto_unmute_logs.json")
        
        # 全局开关
        self.enabled: bool = False
        # 群白名单
        self.group_whitelist: List[str] = []
        # 用户白名单
        self.user_whitelist: List[str] = []
        # 冷却记录
        self.cooldowns: Dict[str, float] = {}  # key: group_id 或 user_id
        self.cooldown_seconds: int = 30
        
        os.makedirs(data_dir, exist_ok=True)
        self._load_config()
        self._log("模块初始化完成", f"全局开关: {'开启' if self.enabled else '关闭'}")
    
    def _load_config(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.enabled = data.get('enabled', False)
                    self.group_whitelist = data.get('group_whitelist', [])
                    self.user_whitelist = data.get('user_whitelist', [])
            else:
                self._save_config()
        except Exception as e:
            print(f"[自动解禁] 加载配置失败: {e}")
    
    def _save_config(self):
        try:
            data = {
                'enabled': self.enabled,
                'group_whitelist': self.group_whitelist,
                'user_whitelist': self.user_whitelist
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[自动解禁] 保存配置失败: {e}")
    
    def _log(self, event: str, detail: str = "", success: bool = True):
        """记录日志"""
        try:
            logs = []
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            logs.append({
                "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "event": event,
                "detail": detail,
                "success": success
            })
            if len(logs) > 500:
                logs = logs[-500:]
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    def is_in_cooldown(self, key: str) -> bool:
        """检查是否在冷却期"""
        if key in self.cooldowns:
            if time.time() - self.cooldowns[key] < self.cooldown_seconds:
                return True
        return False
    
    def set_cooldown(self, key: str):
        self.cooldowns[key] = time.time()
    
    # ---------- 群白名单管理 ----------
    def add_group(self, group_id: str) -> bool:
        if group_id in self.group_whitelist:
            return False
        self.group_whitelist.append(group_id)
        self._save_config()
        self._log("添加群白名单", group_id)
        return True
    
    def remove_group(self, group_id: str) -> bool:
        if group_id not in self.group_whitelist:
            return False
        self.group_whitelist.remove(group_id)
        self._save_config()
        self._log("移除群白名单", group_id)
        return True
    
    def is_group_whitelisted(self, group_id: str) -> bool:
        return group_id in self.group_whitelist
    
    # ---------- 用户白名单管理 ----------
    def add_user(self, user_id: str) -> bool:
        if user_id in self.user_whitelist:
            return False
        self.user_whitelist.append(user_id)
        self._save_config()
        self._log("添加用户白名单", user_id)
        return True
    
    def remove_user(self, user_id: str) -> bool:
        if user_id not in self.user_whitelist:
            return False
        self.user_whitelist.remove(user_id)
        self._save_config()
        self._log("移除用户白名单", user_id)
        return True
    
    def is_user_whitelisted(self, user_id: str) -> bool:
        return user_id in self.user_whitelist
    
    # ---------- 开关 ----------
    def set_enabled(self, enabled: bool):
        self.enabled = enabled
        self._save_config()
        self._log("全局开关", "开启" if enabled else "关闭")
    
    # ---------- 事件处理 ----------
    def should_auto_unmute_self(self, group_id: str, duration: int) -> bool:
        """判断是否应该自动解禁自己"""
        if not self.enabled:
            return False
        if duration <= 0:  # 解除禁言事件不处理
            return False
        if not self.is_group_whitelisted(group_id):
            return False
        if self.is_in_cooldown(f"group_{group_id}"):
            return False
        return True
    
    def should_auto_unmute_user(self, user_id: str, group_id: str, duration: int) -> bool:
        """判断是否应该自动解禁其他用户"""
        if not self.enabled:
            return False
        if duration <= 0:
            return False
        if not self.is_user_whitelisted(user_id):
            return False
        # 可选：也可以限制只在白名单群中解禁他人，这里不限制
        if self.is_in_cooldown(f"user_{user_id}"):
            return False
        return True
    
    def get_status(self) -> str:
        lines = [
            "【🤖 自动解禁系统】",
            f"全局开关: {'✅ 开启' if self.enabled else '❌ 关闭'}",
            f"群白名单: {len(self.group_whitelist)} 个群",
            f"用户白名单: {len(self.user_whitelist)} 个用户",
            "",
            "📋 命令:",
            "  !自动解禁 开关 开/关",
            "  !自动解禁 添加群 <群号>",
            "  !自动解禁 移除群 <群号>",
            "  !自动解禁 添加用户 <QQ>",
            "  !自动解禁 移除用户 <QQ>",
            "  !自动解禁 列表",
            "  !自动解禁 状态",
        ]
        return "\n".join(lines)
    
    def get_list(self) -> str:
        lines = ["【自动解禁配置】"]
        if self.group_whitelist:
            lines.append("群白名单:")
            for g in self.group_whitelist:
                lines.append(f"  • {g}")
        else:
            lines.append("群白名单: 无")
        if self.user_whitelist:
            lines.append("用户白名单:")
            for u in self.user_whitelist:
                lines.append(f"  • {u}")
        else:
            lines.append("用户白名单: 无")
        return "\n".join(lines)
