"""
自动退群重进模块
功能：监控指定群聊，当机器人被禁言时间超过阈值时，自动退群并重新加入
默认关闭，需要管理员手动开启配置
"""

import json
import os
import time
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
import threading


@dataclass
class GroupConfig:
    """群聊配置"""
    group_id: str
    enabled: bool = False  # 是否启用该群的自动重进
    mute_threshold: int = 600  # 禁言阈值（秒），默认10分钟=600秒，小于10秒不触发
    auto_rejoin: bool = True  # 是否自动重进
    max_retries: int = 3  # 最大重试次数
    retry_delay: int = 5  # 重试延迟（秒）
    cooldown: int = 3600  # 冷却时间（秒），避免频繁退群重进


class AutoRejoinManager:
    """自动退群重进管理器"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.config_file = os.path.join(data_dir, "auto_rejoin_config.json")
        self.log_file = os.path.join(data_dir, "auto_rejoin_logs.json")
        
        # 配置
        self.global_enabled: bool = False  # 全局开关，默认关闭
        self.groups: Dict[str, GroupConfig] = {}  # 群配置
        self.cooldowns: Dict[str, float] = {}  # 冷却记录 {群号: 最后退群时间}
        
        # 确保目录存在
        os.makedirs(data_dir, exist_ok=True)
        
        # 加载配置
        self._load_config()
        
        print(f"[自动重进] 模块初始化完成，全局开关: {'开启' if self.global_enabled else '关闭'}")
        print(f"[自动重进] 已配置群: {len(self.groups)}个")
    
    def _load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.global_enabled = data.get('global_enabled', False)
                    
                    # 加载群配置
                    groups_data = data.get('groups', {})
                    for group_id, config in groups_data.items():
                        self.groups[group_id] = GroupConfig(
                            group_id=group_id,
                            enabled=config.get('enabled', False),
                            mute_threshold=config.get('mute_threshold', 600),
                            auto_rejoin=config.get('auto_rejoin', True),
                            max_retries=config.get('max_retries', 3),
                            retry_delay=config.get('retry_delay', 5),
                            cooldown=config.get('cooldown', 3600)
                        )
                print(f"[自动重进] 配置加载成功")
            else:
                self._save_config()
                print(f"[自动重进] 创建默认配置文件")
        except Exception as e:
            print(f"[自动重进] 配置加载失败: {e}")
            self._save_config()
    
    def _save_config(self):
        """保存配置文件"""
        try:
            groups_data = {}
            for group_id, config in self.groups.items():
                groups_data[group_id] = {
                    'enabled': config.enabled,
                    'mute_threshold': config.mute_threshold,
                    'auto_rejoin': config.auto_rejoin,
                    'max_retries': config.max_retries,
                    'retry_delay': config.retry_delay,
                    'cooldown': config.cooldown
                }
            
            data = {
                'global_enabled': self.global_enabled,
                'groups': groups_data
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"[自动重进] 配置保存成功")
        except Exception as e:
            print(f"[自动重进] 配置保存失败: {e}")
    
    def _log_event(self, group_id: str, event_type: str, message: str, success: bool = True):
        """记录事件日志"""
        try:
            logs = []
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            
            log_entry = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'group_id': group_id,
                'event_type': event_type,
                'message': message,
                'success': success
            }
            
            logs.append(log_entry)
            # 只保留最近1000条日志
            if len(logs) > 1000:
                logs = logs[-1000:]
            
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[自动重进] 日志记录失败: {e}")
    
    def is_in_cooldown(self, group_id: str) -> bool:
        """检查是否在冷却期内"""
        if group_id in self.cooldowns:
            elapsed = time.time() - self.cooldowns[group_id]
            config = self.groups.get(group_id)
            cooldown = config.cooldown if config else 3600
            if elapsed < cooldown:
                remaining = int(cooldown - elapsed)
                print(f"[自动重进] 群{group_id}在冷却期内，剩余{remaining}秒")
                return True
        return False
    
    def should_handle_mute(self, group_id: str, duration: int) -> bool:
        """
        判断是否需要处理禁言事件
        规则：
        1. 全局开关必须开启
        2. 群必须在配置中且启用
        3. 不在冷却期内
        4. 禁言时长 >= 阈值（默认600秒），且 > 10秒（10秒以内不触发）
        """
        # 全局开关检查
        if not self.global_enabled:
            return False
        
        # 10秒以内的禁言不触发（防止短时间禁言误触发）
        if duration <= 10:
            print(f"[自动重进] 群{group_id}被禁言{duration}秒，小于10秒，不触发")
            return False
        
        # 群配置检查
        group_config = self.groups.get(str(group_id))
        if not group_config or not group_config.enabled:
            return False
        
        # 冷却检查
        if self.is_in_cooldown(str(group_id)):
            return False
        
        # 禁言时长检查
        if duration >= group_config.mute_threshold:
            print(f"[自动重进] 群{group_id}被禁言{duration}秒，达到阈值{group_config.mute_threshold}秒")
            return True
        
        print(f"[自动重进] 群{group_id}被禁言{duration}秒，未达到阈值{group_config.mute_threshold}秒")
        return False
    
    async def execute_rejoin(self, group_id: str, websocket) -> tuple:
        """执行退群重进操作"""
        group_id_str = str(group_id)
        group_config = self.groups.get(group_id_str)
        
        if not group_config:
            return False, "群配置不存在"
        
        if not group_config.auto_rejoin:
            return False, "该群未启用自动重进"
        
        # 更新冷却时间
        self.cooldowns[group_id_str] = time.time()
        
        # 尝试退群重进
        success = False
        error_msg = ""
        
        for attempt in range(group_config.max_retries):
            try:
                print(f"[自动重进] 群{group_id} 第{attempt+1}次尝试退群...")
                
                # 发送退群请求
                await websocket.send(json.dumps({
                    "action": "set_group_leave",
                    "params": {
                        "group_id": int(group_id),
                        "is_dismiss": False
                    },
                    "echo": f"auto_rejoin_leave_{group_id}_{int(time.time())}"
                }))
                
                self._log_event(group_id_str, "leave_attempt", f"第{attempt+1}次尝试退群", True)
                
                # 等待退群完成
                await asyncio.sleep(2)
                
                print(f"[自动重进] 群{group_id} 退群成功，等待{group_config.retry_delay}秒后尝试加群...")
                await asyncio.sleep(group_config.retry_delay)
                
                # 发送加群请求（需要群号或邀请链接，这里使用群号）
                await websocket.send(json.dumps({
                    "action": "set_group_add",
                    "params": {
                        "group_id": int(group_id)
                    },
                    "echo": f"auto_rejoin_add_{group_id}_{int(time.time())}"
                }))
                
                self._log_event(group_id_str, "join_attempt", f"第{attempt+1}次尝试加群", True)
                
                success = True
                error_msg = ""
                break
                
            except Exception as e:
                error_msg = str(e)
                print(f"[自动重进] 群{group_id} 第{attempt+1}次尝试失败: {e}")
                self._log_event(group_id_str, "attempt_failed", str(e), False)
                
                if attempt < group_config.max_retries - 1:
                    await asyncio.sleep(group_config.retry_delay)
        
        if success:
            self._log_event(group_id_str, "rejoin_success", "退群重进成功", True)
            return True, "退群重进成功"
        else:
            self._log_event(group_id_str, "rejoin_failed", error_msg, False)
            return False, f"退群重进失败: {error_msg}"
    
    # ==================== 管理命令 ====================
    
    def set_global_enabled(self, enabled: bool):
        """设置全局开关"""
        self.global_enabled = enabled
        self._save_config()
        print(f"[自动重进] 全局开关: {'开启' if enabled else '关闭'}")
    
    def add_group(self, group_id: str, mute_threshold: int = 600, auto_rejoin: bool = True) -> bool:
        """添加群配置"""
        group_id_str = str(group_id)
        if group_id_str in self.groups:
            return False
        
        # 阈值不能小于10秒
        if mute_threshold < 10:
            mute_threshold = 10
        
        self.groups[group_id_str] = GroupConfig(
            group_id=group_id_str,
            enabled=True,
            mute_threshold=mute_threshold,
            auto_rejoin=auto_rejoin,
            max_retries=3,
            retry_delay=5,
            cooldown=3600
        )
        self._save_config()
        print(f"[自动重进] 添加群{group_id_str}，阈值{mute_threshold}秒")
        return True
    
    def remove_group(self, group_id: str) -> bool:
        """移除群配置"""
        group_id_str = str(group_id)
        if group_id_str not in self.groups:
            return False
        
        del self.groups[group_id_str]
        self._save_config()
        print(f"[自动重进] 移除群{group_id_str}")
        return True
    
    def set_group_enabled(self, group_id: str, enabled: bool) -> bool:
        """设置单个群开关"""
        group_id_str = str(group_id)
        if group_id_str not in self.groups:
            return False
        
        self.groups[group_id_str].enabled = enabled
        self._save_config()
        print(f"[自动重进] 群{group_id_str}开关: {'开启' if enabled else '关闭'}")
        return True
    
    def set_group_threshold(self, group_id: str, threshold: int) -> bool:
        """设置群禁言阈值"""
        group_id_str = str(group_id)
        if group_id_str not in self.groups:
            return False
        
        # 阈值不能小于10秒
        if threshold < 10:
            threshold = 10
        
        self.groups[group_id_str].mute_threshold = threshold
        self._save_config()
        print(f"[自动重进] 群{group_id_str}阈值设置为{threshold}秒")
        return True
    
    def get_group_config(self, group_id: str) -> Optional[Dict]:
        """获取群配置"""
        group_id_str = str(group_id)
        if group_id_str not in self.groups:
            return None
        
        config = self.groups[group_id_str]
        return {
            'group_id': config.group_id,
            'enabled': config.enabled,
            'mute_threshold': config.mute_threshold,
            'auto_rejoin': config.auto_rejoin,
            'max_retries': config.max_retries,
            'retry_delay': config.retry_delay,
            'cooldown': config.cooldown,
            'in_cooldown': self.is_in_cooldown(group_id_str)
        }
    
    def list_groups(self) -> List[Dict]:
        """列出所有配置的群"""
        result = []
        for group_id, config in self.groups.items():
            result.append({
                'group_id': group_id,
                'enabled': config.enabled,
                'mute_threshold': config.mute_threshold,
                'in_cooldown': self.is_in_cooldown(group_id)
            })
        return result
    
    def get_status(self) -> str:
        """获取状态信息"""
        lines = [
            "【自动退群重进系统】",
            f"全局开关: {'✅ 开启' if self.global_enabled else '❌ 关闭'}",
            f"配置群数: {len(self.groups)}个",
            "",
            "配置详情:"
        ]
        
        for group_id, config in self.groups.items():
            cooldown_status = "⏳ 冷却中" if self.is_in_cooldown(group_id) else "✅ 可用"
            lines.append(f"  群{group_id}: {'开启' if config.enabled else '关闭'} | 阈值{config.mute_threshold}秒 | {cooldown_status}")
        
        if not self.groups:
            lines.append("  暂无配置群")
        
        return "\n".join(lines)
