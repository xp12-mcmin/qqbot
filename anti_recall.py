"""
防撤回系统 - 完整版（支持图片）
"""

import os
import json
import time
import random
import asyncio
import re
from datetime import datetime
from typing import Dict, List, Optional, Any

from image_cache import get_image_cache


class AntiRecallLogger:
    def __init__(self):
        # 配置文件路径
        self.data_dir = "data"
        self.config_file = os.path.join(self.data_dir, "anti_recall_config.json")
        self.protected_accounts_file = os.path.join(self.data_dir, "protected_accounts.json")
        
        self._ensure_data_dir()
        self._load_config()
        self._load_protected_accounts()
        
        # 系统状态
        self.bot_self_id = None
        self.initialized = False
        self.revenge_enabled = True
        
        # 消息缓存
        self.message_cache: Dict[str, Dict] = {}
        self.id_mapping: Dict[str, str] = {}
        
        # 冷却机制
        self.revenge_cooldown = 1
        self.group_cooldowns: Dict[str, float] = {}
        
        # 图片缓存
        self.image_cache = get_image_cache()
        
        print(f"[防撤回] 系统初始化完成")
        print(f"[防撤回] 目标群: {self.all_target_groups}")
        print(f"[防撤回] 受保护账号: {self.protected_accounts}")
    
    def _ensure_data_dir(self):
        try:
            os.makedirs(self.data_dir, exist_ok=True)
        except Exception as e:
            print(f"[防撤回] 创建目录失败: {e}")
    
    def _load_config(self):
        default_config = {
            "target_group": "1009018182",
            "additional_groups": ["1085287072", "158853515", "1080663142", "655450225", "743645787", "1087384403"],
            "disabled_group": "597105096",
            "special_qq_monitor": {"2249528587": {"enabled": True, "cache_limit": 40}}
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.target_group = config.get("target_group", default_config["target_group"])
                    self.additional_groups = config.get("additional_groups", default_config["additional_groups"])
                    self.disabled_group = config.get("disabled_group", default_config["disabled_group"])
            else:
                self.target_group = default_config["target_group"]
                self.additional_groups = default_config["additional_groups"]
                self.disabled_group = default_config["disabled_group"]
                self._save_config()
        except Exception as e:
            self.target_group = default_config["target_group"]
            self.additional_groups = default_config["additional_groups"]
            self.disabled_group = default_config["disabled_group"]
        
        self.all_target_groups = [self.target_group] + self.additional_groups
    
    def _save_config(self):
        try:
            config = {
                "target_group": self.target_group,
                "additional_groups": self.additional_groups,
                "disabled_group": self.disabled_group
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[防撤回] 保存配置失败: {e}")
    
    def _load_protected_accounts(self):
        default_accounts = ["2249528587"]
        try:
            if os.path.exists(self.protected_accounts_file):
                with open(self.protected_accounts_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.protected_accounts = data.get("accounts", default_accounts)
            else:
                self.protected_accounts = default_accounts
                self._save_protected_accounts()
        except Exception as e:
            self.protected_accounts = default_accounts
    
    def _save_protected_accounts(self):
        try:
            with open(self.protected_accounts_file, 'w', encoding='utf-8') as f:
                json.dump({"accounts": self.protected_accounts}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[防撤回] 保存账号失败: {e}")
    
    # ==================== 管理方法 ====================
    
    def set_bot_id(self, bot_id: str):
        if bot_id and str(bot_id).strip():
            self.bot_self_id = str(bot_id).strip()
            self.initialized = True
            print(f"[防撤回] ✅ 机器人ID: {self.bot_self_id}")
    
    def add_target_group(self, group_id: str) -> bool:
        group_id = str(group_id)
        if group_id not in self.all_target_groups:
            self.all_target_groups.append(group_id)
            if group_id != self.target_group:
                self.additional_groups.append(group_id)
            self._save_config()
            return True
        return False
    
    def remove_target_group(self, group_id: str) -> bool:
        group_id = str(group_id)
        if group_id in self.all_target_groups and group_id != self.target_group:
            self.all_target_groups.remove(group_id)
            if group_id in self.additional_groups:
                self.additional_groups.remove(group_id)
            self._save_config()
            return True
        return False
    
    def add_protected_account(self, account: str) -> bool:
        account = str(account)
        if account not in self.protected_accounts:
            self.protected_accounts.append(account)
            self._save_protected_accounts()
            return True
        return False
    
    def remove_protected_account(self, account: str) -> bool:
        account = str(account)
        if account in self.protected_accounts and account != "2249528587":
            self.protected_accounts.remove(account)
            self._save_protected_accounts()
            return True
        return False
    
    def get_protected_accounts(self) -> List[str]:
        return self.protected_accounts.copy()
    
    def get_target_groups_info(self) -> str:
        result = ["[防撤回目标群]"]
        result.append(f"主要: {self.target_group}")
        if self.additional_groups:
            result.append(f"额外 ({len(self.additional_groups)}个):")
            for i, g in enumerate(self.additional_groups, 1):
                result.append(f"  {i}. {g}")
        return "\n".join(result)
    
    def clear_group_messages(self, group_id: str) -> bool:
        group_str = str(group_id)
        keys = [k for k in self.message_cache.keys() if k.startswith(f"{group_str}_")]
        for k in keys:
            del self.message_cache[k]
        print(f"[防撤回] 清空群{group_id}，删除{len(keys)}条")
        return len(keys) > 0
    
    def set_revenge_enabled(self, enabled: bool):
        self.revenge_enabled = enabled
    
    # ==================== 消息处理 ====================
    
    def _convert_message(self, content):
        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            parts = []
            for seg in content:
                if isinstance(seg, dict):
                    if seg.get('type') == 'text':
                        parts.append(seg.get('data', {}).get('text', ''))
                    elif seg.get('type') == 'image':
                        parts.append("[图片]")
                    elif seg.get('type') == 'at':
                        parts.append(f"@{seg.get('data', {}).get('qq', '')}")
            return ''.join(parts)
        return str(content)
    
    def _normalize_id(self, raw_id):
        if raw_id is None:
            return None
        if isinstance(raw_id, int):
            return f"n_{abs(raw_id)}" if raw_id < 0 else str(raw_id)
        return str(raw_id)
    
    def _get_cache_key(self, group_id, msg_id):
        norm_id = self._normalize_id(msg_id)
        return f"{group_id}_{norm_id}" if norm_id else None
    
    def _cleanup_cache(self):
        now = time.time()
        to_delete = [k for k, v in self.message_cache.items() if now - v.get("timestamp", 0) > 3600]
        for k in to_delete:
            del self.message_cache[k]
        if to_delete:
            print(f"[防撤回] 清理 {len(to_delete)} 条缓存")
    
    # ==================== 记录消息 ====================
    
    def record_message(self, data: Dict):
        if not self.initialized:
            return
        
        try:
            if data.get("post_type") != "message" or data.get("message_type") != "group":
                return
            
            sender = str(data.get("user_id"))
            content = self._convert_message(data.get("message", ""))
            msg_id = data.get("message_id")
            group = str(data.get("group_id"))
            
            if group not in self.all_target_groups:
                return
            
            cache_key = self._get_cache_key(group, msg_id)
            if not cache_key:
                return
            
            self.message_cache[cache_key] = {
                "message_id": msg_id,
                "group_id": group,
                "content": content,
                "timestamp": time.time(),
                "sender_id": sender,
                "is_bot": (sender == self.bot_self_id)
            }
            
            self._cleanup_cache()
            
        except Exception as e:
            print(f"[防撤回] 记录失败: {e}")
    
    def record_sent_message(self, group_id: str, content: str, message_id=None):
        if not self.initialized:
            return
        
        try:
            group = str(group_id)
            if group not in self.all_target_groups:
                return
            
            msg_content = self._convert_message(content)
            
            if message_id:
                msg_id = message_id
            else:
                msg_id = f"pre_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
            
            cache_key = self._get_cache_key(group, msg_id)
            if not cache_key:
                return
            
            # 图片消息：异步下载
            if self.image_cache.is_image(content):
                # 提取图片URL
                import re
                match = re.search(r'url=([^,\]]+\.(?:jpg|jpeg|png|gif))', content)
                if match:
                    url = match.group(1)
                    asyncio.create_task(self.image_cache.download(url, msg_id))
                    print(f"[图片缓存] 加入队列: {msg_id}")
            
            self.message_cache[cache_key] = {
                "message_id": msg_id,
                "group_id": group,
                "content": msg_content,
                "timestamp": time.time(),
                "sender_id": self.bot_self_id,
                "is_bot": True
            }
            
        except Exception as e:
            print(f"[防撤回] 记录API失败: {e}")
    
    # ==================== 处理撤回 ====================
    
    def handle_recall_event(self, data: Dict) -> Optional[Dict]:
        if not self.revenge_enabled or not self.initialized:
            return None
        
        try:
            group = str(data.get("group_id"))
            operator = str(data.get("operator_id") or data.get("user_id", "unknown"))
            msg_id = data.get("message_id")
            
            if not group or not msg_id:
                return None
            
            if group == self.disabled_group or group not in self.all_target_groups:
                return None
            
            # 查找消息
            cached = None
            cache_key = self._get_cache_key(group, msg_id)
            
            if cache_key and cache_key in self.message_cache:
                cached = self.message_cache[cache_key]
            
            if not cached:
                # 模糊匹配最近5分钟的消息
                now = time.time()
                for key, msg in self.message_cache.items():
                    if key.startswith(f"{group}_") and now - msg.get("timestamp", 0) < 300:
                        if msg.get("is_bot"):
                            cached = msg
                            break
                if not cached:
                    for key, msg in self.message_cache.items():
                        if key.startswith(f"{group}_") and now - msg.get("timestamp", 0) < 300:
                            cached = msg
                            break
            
            if not cached:
                print(f"[防撤回] 未找到消息")
                return None
            
            sender = cached.get("sender_id", "")
            
            # 检查是否需要保护
            if sender not in self.protected_accounts and sender != self.bot_self_id:
                print(f"[防撤回] 不需保护")
                return None
            
            if operator == sender:
                print(f"[防撤回] 自己撤回自己")
                return None
            
            # 冷却
            cooldown_key = f"{group}_{msg_id}"
            if cooldown_key in self.group_cooldowns:
                if time.time() - self.group_cooldowns[cooldown_key] < self.revenge_cooldown:
                    return None
            
            self.group_cooldowns[cooldown_key] = time.time()
            
            # 生成回复
            content = cached.get("content", "")
            is_bot = (sender == self.bot_self_id)
            
            # 检查是否是图片消息（通过msg_id查找缓存图片）
            img_cq = self.image_cache.get_cq_image(msg_id) if self.image_cache else None
            
            if img_cq:
                if is_bot:
                    revenge = f"[防撤回] 管理员 {operator} 撤回了图片\n{img_cq}"
                else:
                    revenge = f"[防撤回] 管理员 {operator} 撤回了 {sender} 的图片\n{img_cq}"
            else:
                if is_bot:
                    revenge = f"[防撤回] 管理员 {operator} 撤回了我的消息：\n{content}"
                else:
                    revenge = f"[防撤回] 管理员 {operator} 撤回了 {sender} 的消息：\n{content}"
            
            print(f"[防撤回] 生成回复")
            
            return {
                "action": "send_msg",
                "params": {
                    "message_type": "group",
                    "group_id": int(group),
                    "message": revenge
                }
            }
            
        except Exception as e:
            print(f"[防撤回] 处理失败: {e}")
            return None