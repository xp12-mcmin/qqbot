

import time
import json
import random
import os
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
import sys
import builtins 
# ==================== 授权验证 ====================
def _verify_module():
    """验证模块授权"""
    module_name = "anti_recall"
    
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
# 🆕 导入媒体下载器
from media_downloader import MediaDownloader


class AntiRecallLogger:
    """防撤回系统 - 完整版（支持图片/语音缓存重发）"""
    
    def __init__(self):
        # ==================== 配置文件路径 ====================
        self.data_dir = "data"
        self.config_file = os.path.join(self.data_dir, "anti_recall_config.json")
        self.protected_accounts_file = os.path.join(self.data_dir, "protected_accounts.json")
        
        # ==================== 确保目录存在 ====================
        self._ensure_data_dir()
        
        # ==================== 加载配置 ====================
        self._load_config()
        self._load_protected_accounts()
        
        # ==================== 系统状态 ====================
        self.bot_self_id = None
        self.initialized = False
        self.revenge_enabled = True
        
        # ==================== 消息缓存 ====================
        self.message_cache: Dict[str, Dict] = {}
        self.id_mapping: Dict[str, str] = {}
        self.image_cache = None
        
        # ==================== 🆕 媒体缓存 ====================
        self.media_downloader = MediaDownloader()
        self.media_cache: Dict[str, Dict] = {}  # {message_id: {"image": "path", "voice": "path"}}
        
        # ==================== 冷却机制 ====================
        self.revenge_cooldown = 1
        self.group_cooldowns: Dict[str, float] = {}
        
        # ==================== 特殊监控 ====================
        self.special_qq_messages: Dict[str, List[Dict]] = {}
        self.media_cache: Dict[str, Dict] = {}
        print(f"[防撤回] 系统初始化完成")
        print(f"[防撤回] 目标群: {self.all_target_groups}")
        print(f"[防撤回] 受保护账号: {self.protected_accounts}")
        print(f"[防撤回] 媒体缓存目录: data/media_cache/")
    
    # ==================== 目录和文件管理 ====================
    
    def _ensure_data_dir(self):
        try:
            if not os.path.exists(self.data_dir):
                os.makedirs(self.data_dir)
        except Exception as e:
            print(f"[防撤回] 创建数据目录失败: {e}")
    
    def _ensure_config_file(self, file_path: str, default_content: dict):
        try:
            if not os.path.exists(file_path):
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(default_content, f, ensure_ascii=False, indent=2)
                return True
            return False
        except Exception as e:
            print(f"[防撤回] 创建配置文件失败: {e}")
            return False
    
    # ==================== 配置加载与保存 ====================
    
    def _load_config(self):
        default_config = {
            "target_group": "1009018182",
            "additional_groups": ["1085287072", "158853515", "1080663142", "655450225", "743645787", "1087384403"],
            "disabled_group": "597105096",
            "special_qq_monitor": {
                "2249528587": {
                    "enabled": True,
                    "auto_resend": True,
                    "cache_limit": 40
                }
            }
        }
        
        self._ensure_config_file(self.config_file, default_config)
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.target_group = config.get("target_group", default_config["target_group"])
                self.additional_groups = config.get("additional_groups", default_config["additional_groups"])
                self.disabled_group = config.get("disabled_group", default_config["disabled_group"])
                self.special_qq_monitor = config.get("special_qq_monitor", default_config["special_qq_monitor"])
        except Exception as e:
            self.target_group = default_config["target_group"]
            self.additional_groups = default_config["additional_groups"]
            self.disabled_group = default_config["disabled_group"]
            self.special_qq_monitor = default_config["special_qq_monitor"]
        
        self.all_target_groups = [self.target_group] + self.additional_groups
    
    def _save_config(self):
        try:
            config = {
                "target_group": self.target_group,
                "additional_groups": self.additional_groups,
                "disabled_group": self.disabled_group,
                "special_qq_monitor": self.special_qq_monitor
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[防撤回] 配置保存失败: {e}")
    
    def _load_protected_accounts(self):
        default_accounts = ["2249528587"]
        self._ensure_config_file(self.protected_accounts_file, {"accounts": default_accounts})
        
        try:
            with open(self.protected_accounts_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.protected_accounts = data.get("accounts", default_accounts)
        except Exception as e:
            self.protected_accounts = default_accounts
    
    def _save_protected_accounts(self):
        try:
            with open(self.protected_accounts_file, 'w', encoding='utf-8') as f:
                json.dump({"accounts": self.protected_accounts}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[防撤回] 保存受保护账号失败: {e}")
    
    # ==================== 管理方法 ====================
    
    def set_bot_id(self, bot_id: str):
        if bot_id and str(bot_id).strip():
            self.bot_self_id = str(bot_id).strip()
            self.initialized = True
            print(f"[防撤回] ✅ 机器人ID已设置: {self.bot_self_id}")
    
    def add_target_group(self, group_id: str) -> bool:
        group_id = str(group_id)
        if group_id not in self.all_target_groups:
            self.all_target_groups.append(group_id)
            if group_id != self.target_group:
                self.additional_groups.append(group_id)
            self._save_config()
            print(f"[防撤回] 添加目标群: {group_id}")
            return True
        return False
    
    def remove_target_group(self, group_id: str) -> bool:
        group_id = str(group_id)
        if group_id in self.all_target_groups and group_id != self.target_group:
            self.all_target_groups.remove(group_id)
            if group_id in self.additional_groups:
                self.additional_groups.remove(group_id)
            self._save_config()
            print(f"[防撤回] 移除目标群: {group_id}")
            return True
        return False
    
    def add_protected_account(self, account: str) -> bool:
        account = str(account)
        if account not in self.protected_accounts:
            self.protected_accounts.append(account)
            self._save_protected_accounts()
            print(f"[防撤回] 添加受保护账号: {account}")
            return True
        return False
    
    def remove_protected_account(self, account: str) -> bool:
        account = str(account)
        if account in self.protected_accounts and account != "2249528587":
            self.protected_accounts.remove(account)
            self._save_protected_accounts()
            print(f"[防撤回] 移除受保护账号: {account}")
            return True
        return False
    
    def get_protected_accounts(self) -> List[str]:
        return self.protected_accounts.copy()
    
    def get_target_groups_info(self) -> str:
        result = ["[防撤回目标群]"]
        result.append(f"主要目标群: {self.target_group}")
        if self.additional_groups:
            result.append(f"额外目标群 ({len(self.additional_groups)}个):")
            for i, group in enumerate(self.additional_groups, 1):
                result.append(f"  {i}. 群{group}")
        return "\n".join(result)
    
    def clear_group_messages(self, group_id: str) -> bool:
        group_str = str(group_id)
        keys_to_delete = [k for k in self.message_cache.keys() if k.startswith(f"{group_str}_")]
        for key in keys_to_delete:
            del self.message_cache[key]
        print(f"[防撤回] 清空群{group_id}消息记录，删除{len(keys_to_delete)}条")
        return len(keys_to_delete) > 0
    
    def set_revenge_enabled(self, enabled: bool):
        self.revenge_enabled = enabled
        print(f"[防撤回] 反撤回开关: {'开启' if enabled else '关闭'}")
    
    def get_status(self) -> str:
        if not self.initialized:
            return "❌ 防撤回系统未初始化"
        return f"【防撤回系统】\n机器人ID: {self.bot_self_id}\n目标群: {len(self.all_target_groups)}个\n缓存消息: {len(self.message_cache)}条\n媒体缓存: {len(self.media_cache)}条"
    
    # ==================== 消息处理 ====================
    
    def _convert_message_segments(self, message_content):
        if isinstance(message_content, str):
            return message_content
        elif isinstance(message_content, list):
            text_parts = []
            for segment in message_content:
                if isinstance(segment, dict):
                    seg_type = segment.get('type')
                    data = segment.get('data', {})
                    if seg_type == 'text':
                        text_parts.append(data.get('text', ''))
                    elif seg_type == 'at':
                        text_parts.append(f"@{data.get('qq', '')}")
                    elif seg_type == 'image':
                        text_parts.append("[图片]")
                    elif seg_type == 'record':
                        text_parts.append("[语音]")
                    else:
                        text_parts.append(f"[{seg_type}]")
                elif isinstance(segment, str):
                    text_parts.append(segment)
            return ''.join(text_parts)
        return str(message_content)
    
    def _normalize_id(self, raw_id) -> str:
        if raw_id is None:
            return None
        if isinstance(raw_id, int):
            return f"n_{abs(raw_id)}" if raw_id < 0 else str(raw_id)
        # 🆕 字符串 ID 也统一处理
        if isinstance(raw_id, str):
            if raw_id.startswith("-"):
                return f"n_{raw_id[1:]}"
            return raw_id
        return str(raw_id)
    
    def _get_cache_key(self, group_id: str, raw_message_id) -> str:
        norm_id = self._normalize_id(raw_message_id)
        if not norm_id:
            return None
        return f"{group_id}_{norm_id}"
    
    def _cleanup_old_cache(self):
        current_time = time.time()
        keys_to_delete = []
        for key, msg in self.message_cache.items():
            if current_time - msg.get("timestamp", 0) > 3600:
                keys_to_delete.append(key)
        for key in keys_to_delete:
            del self.message_cache[key]
        if keys_to_delete:
            print(f"[防撤回] 清理了 {len(keys_to_delete)} 条旧缓存")
    
    # ==================== 消息记录 ====================
    
    def record_message(self, data: Dict):
        """记录所有群消息（升级版 - 支持图片/语音缓存）"""
        if not self.initialized:
            return
        
        try:
            # 只处理群消息
            if data.get("post_type") != "message" or data.get("message_type") != "group":
                return
            
            sender_id = str(data.get("user_id"))
            message_content = self._convert_message_segments(data.get("message", ""))
            raw_message = data.get("message", [])
            raw_message_id = data.get("message_id")
            group_id = str(data.get("group_id"))
            
            # 检查是否是反撤回消息
            is_revenge_message = False
            revenge_source = None
            revenge_keywords = ["撤回了", "重新发", "手滑了", "检测到消息被撤回", "防撤回保护"]
            if any(keyword in message_content for keyword in revenge_keywords):
                is_revenge_message = True
                if "撤回了" in message_content and "的消息" in message_content:
                    import re
                    pattern = r"撤回了(\d+)的消息"
                    match = re.search(pattern, message_content)
                    if match:
                        revenge_source = match.group(1)
            
            # 记录特定QQ的消息
            if sender_id in self.special_qq_monitor:
                if sender_id not in self.special_qq_messages:
                    self.special_qq_messages[sender_id] = []
                
                self.special_qq_messages[sender_id].append({
                    "message_id": raw_message_id,
                    "group_id": group_id,
                    "content": message_content,
                    "timestamp": time.time(),
                    "sender_id": sender_id
                })
                
                cache_limit = self.special_qq_monitor[sender_id].get("cache_limit", 40)
                if len(self.special_qq_messages[sender_id]) > cache_limit:
                    self.special_qq_messages[sender_id] = self.special_qq_messages[sender_id][-cache_limit:]
            
            # 只处理目标群
            if group_id not in self.all_target_groups:
                return
            
            # 生成缓存键
            cache_key = self._get_cache_key(group_id, raw_message_id)
            if not cache_key:
                return
            
            # 保存ID映射
            self.id_mapping[str(raw_message_id)] = cache_key
            
            # 构建消息详情
            self.message_cache[cache_key] = {
                "message_id": raw_message_id,
                "normalized_id": self._normalize_id(raw_message_id),
                "group_id": group_id,
                "content": message_content,
                "timestamp": time.time(),
                "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "sender_id": sender_id,
                "is_bot_message": (sender_id == self.bot_self_id),
                "is_revenge_message": is_revenge_message,
                "revenge_source": revenge_source
            }
            
            # ===== 🆕 检测图片/语音并下载缓存 =====
            if isinstance(raw_message, list):
                for seg in raw_message:
                    if isinstance(seg, dict):
                        seg_type = seg.get("type", "")
                        seg_data = seg.get("data", {})
                        
                        if seg_type == "image":
                            file_id = seg_data.get("file", "")
                            if file_id:
                                # 异步下载图片
                                asyncio.create_task(self._cache_media(file_id, raw_message_id, "image"))
                                print(f"[防撤回] 📸 检测到图片: {file_id}")
                        
                        elif seg_type == "record":
                            file_id = seg_data.get("file", "")
                            if file_id:
                                # 异步下载语音
                                asyncio.create_task(self._cache_media(file_id, raw_message_id, "voice"))
                                print(f"[防撤回] 🎤 检测到语音: {file_id}")
            
            # 清理旧缓存
            self._cleanup_old_cache()
            
            if is_revenge_message:
                print(f"[防撤回] 记录反撤回消息 - 群{group_id}")
            elif sender_id == self.bot_self_id:
                print(f"[防撤回] 记录机器人消息 - 群{group_id}")
            else:
                print(f"[防撤回] 记录用户消息 - 群{group_id}, 用户:{sender_id}")
            
        except Exception as e:
            print(f"[防撤回] 记录消息失败: {e}")
            import traceback
            traceback.print_exc()
    
    def record_sent_message(self, group_id: str, content: str, message_id: Optional[Any] = None):
        """记录机器人通过API发送的消息（支持图片缓存）"""
        if not self.initialized:
            return
    
        try:
            group_str = str(group_id)
            if group_str not in self.all_target_groups:
                return
        
            # 转换消息格式
            message_content = self._convert_message_segments(content)
        
            # 生成消息ID
            if message_id is not None:
                cache_key = self._get_cache_key(group_str, message_id)
                msg_id = message_id
            else:
                msg_id = f"pre_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
                cache_key = self._get_cache_key(group_str, msg_id)
        
            if not cache_key:
                return
        
            # ========== 图片缓存（新增）==========
            if hasattr(self, 'image_cache') and self.image_cache:
                if self.image_cache.is_image(message_content):
                    url = self.image_cache.extract_url(message_content)
                    if url:
                        # 异步下载图片，不阻塞
                        asyncio.create_task(self.image_cache.download(url, msg_id))
                        print(f"[图片缓存] 已加入下载队列: {msg_id}")
        
            # 构建消息详情
            message_info = {
                "message_id": msg_id,
                "normalized_id": self._normalize_id(msg_id),
                "group_id": group_str,
                "content": message_content,
                "original_content": content,
                "timestamp": time.time(),
                "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "sender_id": self.bot_self_id,
                "is_bot_message": True,
                "source": "api"
            }
        
            # 存入缓存
            self.message_cache[cache_key] = message_info
        
            # 保存ID映射
            self.id_mapping[str(msg_id)] = cache_key
        
            print(f"[防撤回] 记录API消息 - 群{group_id}, ID:{msg_id}")
            if self.image_cache and self.image_cache.is_image(message_content):
                print(f"[防撤回] 图片消息已记录")
        
            # 清理旧缓存
            self._cleanup_old_cache()
        
        except Exception as e:
            print(f"[防撤回] 记录API消息失败: {e}")
            import traceback
            traceback.print_exc()
    
    # ==================== 🆕 媒体缓存方法 ====================
    
    async def _cache_media(self, file_id: str, message_id: Any, media_type: str):
        """下载并缓存媒体文件"""
        try:
            # 🆕 用归一化后的 ID 作为 key
            norm_id = self._normalize_id(message_id)
            cache_key = str(norm_id) if norm_id else str(message_id)
            
            if cache_key in self.media_cache and media_type in self.media_cache[cache_key]:
                print(f"[防撤回] 💾 媒体已存在缓存: {media_type}")
                return
            
            # 下载
            if media_type == "image":
                filepath = await self.media_downloader.download_image(file_id)
            else:
                filepath = await self.media_downloader.download_voice(file_id)
            
            if filepath:
                if cache_key not in self.media_cache:
                    self.media_cache[cache_key] = {}
                self.media_cache[cache_key][media_type] = filepath
                print(f"[防撤回] 💾 媒体已缓存: {media_type} -> {filepath}")
            else:
                print(f"[防撤回] ❌ 媒体下载失败: {media_type} -> {file_id}")
                
        except Exception as e:
            print(f"[防撤回] 媒体缓存异常: {e}")
            import traceback
            traceback.print_exc()
    
    # ==================== 撤回事件处理 ====================
    
    def handle_recall_event(self, data: Dict) -> Optional[Dict]:
        """处理撤回事件（升级版 - 支持图片/语音重发）"""
        if not self.revenge_enabled or not self.initialized:
            return None
        
        try:
            group_id = str(data.get("group_id"))
            operator_id = str(data.get("operator_id") or data.get("user_id", "unknown"))
            raw_message_id = data.get("message_id")
            
            print(f"[防撤回] 收到撤回事件 - 群:{group_id}, 操作者:{operator_id}, ID:{raw_message_id}")
            
            # 基础检查
            if not group_id or not raw_message_id:
                return None
            
            if group_id == self.disabled_group or group_id not in self.all_target_groups:
                return None
            
            # 查找被撤回的消息
            cached_message = None
            cache_key = self._get_cache_key(group_id, raw_message_id)
            
            # 方法1：精确匹配
            if cache_key in self.message_cache:
                cached_message = self.message_cache[cache_key]
                print(f"[防撤回] 精确匹配到消息，发送者:{cached_message.get('sender_id')}")
            
            # 方法2：特殊QQ缓存
            if not cached_message and hasattr(self, 'special_qq_messages'):
                for qq_id, msgs in self.special_qq_messages.items():
                    for msg in msgs:
                        if (str(msg.get("group_id")) == group_id and 
                            str(msg.get("message_id")) == str(raw_message_id)):
                            cached_message = msg
                            cached_message["sender_id"] = qq_id
                            cached_message["is_bot_message"] = False
                            print(f"[防撤回] 特殊缓存匹配到消息，QQ:{qq_id}")
                            break
                    if cached_message:
                        break
            
            # 方法3：模糊匹配（优先机器人消息）
            if not cached_message:
                search_start = time.time() - 300
                recent_messages = []
                bot_messages = []
                
                for key, msg in self.message_cache.items():
                    if (key.startswith(f"{group_id}_") and 
                        msg.get("timestamp", 0) > search_start):
                        recent_messages.append((key, msg))
                        if msg.get("is_bot_message"):
                            bot_messages.append((key, msg))
                
                if bot_messages:
                    bot_messages.sort(key=lambda x: x[1]["timestamp"], reverse=True)
                    cached_message = bot_messages[0][1]
                    print(f"[防撤回] 模糊匹配到机器人消息")
                elif recent_messages:
                    recent_messages.sort(key=lambda x: x[1]["timestamp"], reverse=True)
                    cached_message = recent_messages[0][1]
                    print(f"[防撤回] 模糊匹配到最近消息")
            
            if not cached_message:
                print(f"[防撤回] 未找到被撤回的消息")
                return None
            
            sender_id = cached_message.get("sender_id", "")
            is_revenge_message = cached_message.get("is_revenge_message", False)
            revenge_source = cached_message.get("revenge_source")
            
            # 判断是否需要保护
            need_protect = False
            target_to_protect = None
            
            # 情况1：普通消息被撤回
            if not is_revenge_message:
                # 检查发送者是否在受保护列表中（包括机器人自己）
                if sender_id in self.protected_accounts or sender_id == self.bot_self_id:
                    if operator_id == sender_id:
                        print(f"[防撤回] 受保护账号 {operator_id} 撤回自己的消息，跳过")
                        if cache_key in self.message_cache:
                            del self.message_cache[cache_key]
                        return None
                    else:
                        need_protect = True
                        target_to_protect = sender_id
                        print(f"[防撤回] 需要保护: {target_to_protect}")
            
            # 情况2：反撤回消息被撤回
            elif is_revenge_message and revenge_source:
                need_protect = True
                target_to_protect = revenge_source
                print(f"[防撤回] 反撤回消息被撤回，保护来源: {target_to_protect}")
            
            # 情况3：反撤回消息被撤回（无来源）
            elif is_revenge_message:
                need_protect = True
                target_to_protect = self.bot_self_id
                print(f"[防撤回] 反撤回消息被撤回，默认保护机器人")
            
            if not need_protect:
                print(f"[防撤回] 不需要保护")
                if cache_key in self.message_cache:
                    del self.message_cache[cache_key]
                return None
            
            # 冷却检查
            cooldown_key = f"{group_id}_{raw_message_id}"
            current_time = time.time()
            if cooldown_key in self.group_cooldowns:
                if current_time - self.group_cooldowns[cooldown_key] < self.revenge_cooldown:
                    print(f"[防撤回] 冷却中，跳过")
                    return None
            
            # 清理缓存
            if cache_key in self.message_cache:
                del self.message_cache[cache_key]
            
            # 更新冷却
            self.group_cooldowns[cooldown_key] = current_time
            
            # ===== 🆕 检查是否有缓存的媒体 =====
            msg_id_key = str(raw_message_id)
            cached_media = self.media_cache.get(msg_id_key, {})
            
            # 构建反撤回内容
            if cached_media:
                # 有图片/语音 → 发送媒体
                print(f"[防撤回] 📸 检测到缓存媒体: {list(cached_media.keys())}")
                revenge_content = self._build_media_revenge(
                    cached_media, 
                    operator_id, 
                    target_to_protect if target_to_protect != self.bot_self_id else None
                )
                # 发送后清理媒体缓存
                if msg_id_key in self.media_cache:
                    del self.media_cache[msg_id_key]
            else:
                # 只有文字 → 发送文字
                revenge_content = self._generate_revenge_content(
                    cached_message.get("content", ""),
                    operator_id,
                    is_bot=(target_to_protect == self.bot_self_id),
                    target_qq=target_to_protect if target_to_protect != self.bot_self_id else None
                )
            
            print(f"[防撤回] 生成反撤回消息: {revenge_content[:50]}...")
            
            return {
                "action": "send_msg",
                "params": {
                    "message_type": "group",
                    "group_id": int(group_id),
                    "message": revenge_content
                }
            }
            
        except Exception as e:
            print(f"[防撤回] 处理撤回事件失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _build_media_revenge(self, cached_media: Dict, operator_id: str, target_qq: str = None) -> str:
        """构建带媒体的反撤回消息"""
        parts = []
        
        # 文字说明
        if target_qq:
            parts.append(f"[防撤回] 管理员 {operator_id} 撤回了 {target_qq} 的媒体消息：")
        else:
            parts.append(f"[防撤回] 管理员 {operator_id} 撤回了媒体消息：")
        
        # 添加图片 CQ 码
        if "image" in cached_media:
            img_path = cached_media["image"]
            if os.path.exists(img_path):
                parts.append(f"[CQ:image,file=file:///{os.path.abspath(img_path)}]")
            else:
                print(f"[防撤回] ⚠️ 图片文件不存在: {img_path}")
        
        # 添加语音 CQ 码
        if "voice" in cached_media:
            voice_path = cached_media["voice"]
            if os.path.exists(voice_path):
                parts.append(f"[CQ:record,file=file:///{os.path.abspath(voice_path)}]")
            else:
                print(f"[防撤回] ⚠️ 语音文件不存在: {voice_path}")
        
        return "\n".join(parts)
    
    def _generate_revenge_content(self, original_content: str, operator_id: str,
                                  is_bot: bool = True, target_qq: str = None) -> str:
        """生成文字反撤回消息"""
        # 检查是否是图片占位符
        if "[图片]" in original_content:
            if is_bot:
                return f"[防撤回] 管理员 {operator_id} 撤回了我的图片消息"
            else:
                return f"[防撤回] 管理员 {operator_id} 撤回了 {target_qq} 的图片消息"
        
        # 检查是否是语音占位符
        if "[语音]" in original_content:
            if is_bot:
                return f"[防撤回] 管理员 {operator_id} 撤回了我的语音消息"
            else:
                return f"[防撤回] 管理员 {operator_id} 撤回了 {target_qq} 的语音消息"
        
        # 普通文字消息
        if is_bot:
            return f"[防撤回] 管理员 {operator_id} 撤回了我的消息：\n{original_content}"
        else:
            return f"[防撤回] 管理员 {operator_id} 撤回了 {target_qq} 的消息：\n{original_content}"
