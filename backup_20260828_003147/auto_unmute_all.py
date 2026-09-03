"""
自动解禁全体禁言模块
- 检测到全体禁言（duration > 0）时自动解禁
- 只对白名单群生效
- 权限由调用方控制（命令已硬编码默认管理员）
"""

import time
import json
import os
from typing import Dict, Optional


class AutoUnmuteAll:
    """自动解禁全体禁言"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.config_file = os.path.join(data_dir, "auto_unmute_all_config.json")
        
        # 默认配置
        self.config = {
            "enabled_groups": [],       # 启用的群列表
            "cooldown": 60,             # 冷却时间（秒）
            "log_enabled": True         # 是否记录日志
        }
        
        self.cooldowns: Dict[str, float] = {}
        self.load_config()
        
        print("[自动解禁全体] 初始化完成")
        print(f"[自动解禁全体] 启用群: {self.config['enabled_groups']}")
    
    def load_config(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                    for key in self.config:
                        if key in saved:
                            self.config[key] = saved[key]
        except Exception as e:
            print(f"[自动解禁全体] 配置加载失败: {e}")
        self.save_config()
    
    def save_config(self):
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[自动解禁全体] 配置保存失败: {e}")
    
    def is_group_enabled(self, group_id: str) -> bool:
        return group_id in self.config["enabled_groups"]
    
    def enable_group(self, group_id: str) -> bool:
        if group_id not in self.config["enabled_groups"]:
            self.config["enabled_groups"].append(group_id)
            self.save_config()
            return True
        return False
    
    def disable_group(self, group_id: str) -> bool:
        if group_id in self.config["enabled_groups"]:
            self.config["enabled_groups"].remove(group_id)
            self.save_config()
            return True
        return False
    
    def should_handle(self, group_id: str) -> bool:
        """检查是否需要处理"""
        if not self.is_group_enabled(group_id):
            return False
        
        now = time.time()
        if group_id in self.cooldowns:
            if now - self.cooldowns[group_id] < self.config["cooldown"]:
                return False
        
        self.cooldowns[group_id] = now
        return True
    
    def handle_mute_all(self, group_id: str, operator_id: str, duration: int) -> Optional[Dict]:
        """
        处理全体禁言事件
        返回解禁操作 dict 或 None
        """
        if not self.should_handle(group_id):
            return None
        
        if duration <= 0:
            return None
        
        print(f"[自动解禁全体] 检测到全体禁言！群:{group_id}, 操作者:{operator_id}, 时长:{duration}秒")
        
        if self.config["log_enabled"]:
            self._log_event(group_id, operator_id, duration)
        
        return {
            "action": "set_group_ban",
            "params": {
                "group_id": int(group_id),
                "user_id": 0,
                "duration": 0
            },
            "echo": f"auto_unmute_all_{group_id}_{int(time.time())}"
        }
    
    def _log_event(self, group_id: str, operator_id: str, duration: int):
        """记录事件日志"""
        log_file = os.path.join(self.data_dir, "auto_unmute_all_logs.json")
        try:
            logs = []
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            
            logs.append({
                "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "group_id": group_id,
                "operator_id": operator_id,
                "duration": duration,
                "action": "auto_unmute_all"
            })
            
            if len(logs) > 100:
                logs = logs[-100:]
            
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[自动解禁全体] 日志写入失败: {e}")
    
    def get_status(self, group_id: str = None) -> str:
        lines = ["📋 自动解禁全体状态"]
        lines.append(f"冷却时间: {self.config['cooldown']}秒")
        
        if group_id:
            enabled = self.is_group_enabled(group_id)
            lines.append(f"本群状态: {'✅ 已启用' if enabled else '❌ 未启用'}")
        else:
            lines.append(f"启用群: {len(self.config['enabled_groups'])}个")
            if self.config['enabled_groups']:
                lines.append(f"群列表: {', '.join(self.config['enabled_groups'][:10])}")
                if len(self.config['enabled_groups']) > 10:
                    lines.append(f"... 共 {len(self.config['enabled_groups'])} 个")
        
        return "\n".join(lines)


# ==================== 全局实例 ====================
_auto_unmute_all = None

def get_auto_unmute_all():
    global _auto_unmute_all
    if _auto_unmute_all is None:
        _auto_unmute_all = AutoUnmuteAll()
    return _auto_unmute_all
