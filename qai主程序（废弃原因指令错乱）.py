"""
QQ机器人主程序 - 精简版
"""

import asyncio
import websockets
import json
import logging
import aiohttp
import time
import ctypes
import os
import re
from datetime import datetime
import threading
import sys
import random
import schedule
from typing import Dict, List, Optional, Any

# 彩色日志
from logger import log

# 导入模块
from web_search import get_web_search
from lottery import get_lottery
from anti_recall import AntiRecallLogger
from auto_unmute import AutoUnmuteManager
from auto_rejoin import AutoRejoinManager
from ai_memory import AIMemoryModule
from help_image import HelpImageGenerator
from video_parser import VideoParser
from spammer import SimpleSpammer
from spammer_manager import SpamCommandManager
from yin_yang_db import YinYangDB
from blacklist import SimpleBlacklist
from admin_manager import AdminManager

# 导入自定义类
from ai_personality import AIPersonality

# ==================== 窗口最小化 ====================
def minimize_cmd_window():
    try:
        kernel32 = ctypes.WinDLL('kernel32')
        user32 = ctypes.WinDLL('user32')
        hwnd = kernel32.GetConsoleWindow()
        if hwnd:
            log.info("找到命令行窗口，3秒后最小化...")
            time.sleep(3)
            user32.ShowWindow(hwnd, 6)
            log.success("窗口已最小化到任务栏")
            return True
        else:
            log.warning("未找到控制台窗口句柄")
            return False
    except Exception as e:
        log.error(f"窗口最小化失败: {e}")
        return False

minimize_cmd_window()

# ==================== 基础配置 ====================
os.makedirs("data", exist_ok=True)
logging.basicConfig(level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# ==================== 管理员刷屏器 ====================
class AdminSpammer:
    """管理员自定义时长刷屏器"""
    
    def __init__(self, admin_manager=None):
        self.admin_manager = admin_manager
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.task_settings: Dict[str, dict] = {}
        self.default_duration = 30
        self.min_duration = 5
        self.max_duration = 300
        self.min_interval = 0.1
        self.max_interval = 0.5
        log.info("[刷屏器] 初始化完成")
    
    async def start_spam(self, target_qq: int, group_id: int, duration_text: str, websocket) -> tuple:
        try:
            duration_seconds = self._parse_duration(duration_text)
            duration_seconds = max(self.min_duration, min(duration_seconds, self.max_duration))
            task_id = f"spam_{target_qq}_{group_id}_{int(time.time())}"
            
            if task_id in self.active_tasks:
                return None, "该目标已有刷屏任务"
            
            self.task_settings[task_id] = {
                "target_qq": target_qq,
                "group_id": group_id,
                "duration": duration_seconds,
                "start_time": time.time()
            }
            
            task = asyncio.create_task(self._spam_loop(task_id, websocket))
            self.active_tasks[task_id] = task
            return task_id, f"开始轰炸 {target_qq}，时长: {duration_seconds}秒"
        except Exception as e:
            log.error(f"刷屏启动失败: {e}")
            return None, f"启动失败: {str(e)}"
    
    async def _spam_loop(self, task_id: str, websocket):
        try:
            settings = self.task_settings.get(task_id)
            if not settings:
                return
            
            target_qq = settings["target_qq"]
            group_id = settings["group_id"]
            duration = settings["duration"]
            start_time = settings["start_time"]
            
            curses = ["傻逼", "废物", "垃圾", "弱智", "脑残", "憨批", "傻狗"]
            
            message_count = 0
            while time.time() - start_time < duration:
                curse = random.choice(curses)
                message = f"[CQ:at,qq={target_qq}] {curse}"
                
                try:
                    await websocket.send(json.dumps({
                        "action": "send_msg",
                        "params": {
                            "message_type": "group",
                            "group_id": int(group_id),
                            "message": message
                        }
                    }))
                    message_count += 1
                    await asyncio.sleep(random.uniform(self.min_interval, self.max_interval))
                except Exception as e:
                    log.error(f"刷屏发送失败: {e}")
                    await asyncio.sleep(1)
            
            log.info(f"刷屏任务 {task_id} 完成，共发送 {message_count} 条")
        except asyncio.CancelledError:
            log.warning(f"刷屏任务 {task_id} 被取消")
        finally:
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
    
    def _parse_duration(self, text: str) -> int:
        if not text:
            return self.default_duration
        text = text.lower().strip()
        if text.isdigit():
            return max(self.min_duration, min(int(text), self.max_duration))
        return self.default_duration


# ==================== 绿茶反击模块 ====================
class GreenTeaCounter:
    def __init__(self):
        self.enabled = True
        self.config_file = "data/green_tea_config.json"
        self.target_groups: List[str] = []
        self.blacklist: List[str] = []
        self.cooldowns: Dict[str, float] = {}
        self.cooldown_time = 10
        
        self.green_tea_phrases = [
            "哎呀~我是不是说错什么了？你这么激动干嘛呀？",
            "姐姐/哥哥别生气嘛，人家就是开个玩笑~",
            "哇~你好凶哦，人家好怕怕呢~",
            "不至于吧？就这点小事也值得你跳脚？",
            "你开心就好啦~反正我无所谓哒~",
            "咦？这就破防了？心理承受能力不太行哦~",
            "啊对对对，你说得都对~",
            "嘻嘻~[CQ:face,id=21]",
            "嘤嘤嘤~[CQ:face,id=111]",
        ]
        
        self.triggers = ["绿茶", "茶艺", "茶味", "装纯", "装无辜", "阴阳怪气", "嘤嘤怪"]
        self.load_config()
        log.info(f"[绿茶反击] 模块初始化完成，共{len(self.green_tea_phrases)}条语录")
    
    def load_config(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.target_groups = config.get('target_groups', [])
                    self.blacklist = config.get('blacklist', [])
                    self.enabled = config.get('enabled', True)
        except Exception as e:
            log.error(f"绿茶反击配置加载失败: {e}")
            self.save_config()
    
    def save_config(self):
        try:
            config = {
                'target_groups': self.target_groups,
                'blacklist': self.blacklist,
                'enabled': self.enabled
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log.error(f"绿茶反击配置保存失败: {e}")
    
    def should_counter(self, group_id: str, user_id: str, message: str) -> bool:
        if not self.enabled:
            return False
        if group_id not in self.target_groups:
            return False
        if user_id in self.blacklist:
            return False
        
        cooldown_key = f"{group_id}_{user_id}"
        current_time = time.time()
        if cooldown_key in self.cooldowns:
            if current_time - self.cooldowns[cooldown_key] < self.cooldown_time:
                return False
        
        message_lower = message.lower()
        for trigger in self.triggers:
            if trigger.lower() in message_lower:
                self.cooldowns[cooldown_key] = current_time
                return True
        return False
    
    def generate_response(self, target_qq: str, original_message: str = "") -> str:
        response = random.choice(self.green_tea_phrases)
        if not response.startswith("[CQ:at"):
            response = f"[CQ:at,qq={target_qq}] {response}"
        return response
    
    def set_enabled(self, enabled: bool):
        self.enabled = enabled
        self.save_config()
    
    def add_target_group(self, group_id: str) -> bool:
        if group_id not in self.target_groups:
            self.target_groups.append(group_id)
            self.save_config()
            return True
        return False
    
    def remove_target_group(self, group_id: str) -> bool:
        if group_id in self.target_groups:
            self.target_groups.remove(group_id)
            self.save_config()
            return True
        return False
    
    def add_to_blacklist(self, user_id: str) -> bool:
        if user_id not in self.blacklist:
            self.blacklist.append(user_id)
            self.save_config()
            return True
        return False
    
    def remove_from_blacklist(self, user_id: str) -> bool:
        if user_id in self.blacklist:
            self.blacklist.remove(user_id)
            self.save_config()
            return True
        return False


# ==================== 本地骂人系统 ====================
class LocalScoldingSystem:
    def __init__(self, admin_manager):
        self.config_file = "data/local_scolding.json"
        self.target_config = {}
        self.cooldowns = {}
        self.cooldown_time = 0.1
        self.admin_manager = admin_manager
        
        self.scolding_words = [
            "你TM闭嘴！", "滚！看见你就烦！", "傻逼玩意儿！", "废物东西！",
            "垃圾玩意！", "弱智！", "脑残！", "智障！", "憨批！", "傻狗！",
            "你这种货色也配说话？", "看见你就想吐！", "你妈没教过你怎么做人？"
        ]
        
        self.load_config()
        log.info(f"[本地骂人] 系统就绪 - {len(self.scolding_words)}条脏话")
    
    def load_config(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.target_config = json.load(f)
        except:
            self.save_config()
    
    def save_config(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.target_config, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    def is_admin(self, user_id: str) -> bool:
        return self.admin_manager.is_admin(user_id)
    
    def add_target(self, group_id: str, target_qq: str, admin_id: str) -> str:
        if not self.is_admin(admin_id):
            return "你不是管理员！"
        group = str(group_id)
        target = str(target_qq)
        if group not in self.target_config:
            self.target_config[group] = []
        if target in self.target_config[group]:
            return f"{target}已经在名单里了！"
        self.target_config[group].append(target)
        self.save_config()
        return f"已锁定{target}！这人一说话就开骂！"
    
    def add_targets(self, group_id: str, target_qq_list: list, admin_id: str) -> str:
        if not self.is_admin(admin_id):
            return "你没权限！"
        group = str(group_id)
        if group not in self.target_config:
            self.target_config[group] = []
        added = []
        for target in target_qq_list:
            target_str = str(target)
            if target_str not in self.target_config[group]:
                self.target_config[group].append(target_str)
                added.append(target_str)
        self.save_config()
        if added:
            return f"新加了{len(added)}个：{', '.join(added)}"
        return "全是重复的！"
    
    def remove_target(self, group_id: str, target_qq: str, admin_id: str) -> str:
        if not self.is_admin(admin_id):
            return "你没权限！"
        group = str(group_id)
        target = str(target_qq)
        if group in self.target_config and target in self.target_config[group]:
            self.target_config[group].remove(target)
            self.save_config()
            return f"{target}已移除！"
        return "目标不在名单里！"
    
    def clear_group(self, group_id: str, admin_id: str) -> str:
        if not self.is_admin(admin_id):
            return "你没权限！"
        group = str(group_id)
        if group in self.target_config:
            count = len(self.target_config[group])
            del self.target_config[group]
            self.save_config()
            return f"清空了群{group}的{count}个目标！"
        return "没有目标！"
    
    def should_scold(self, group_id: str, sender_id: str) -> bool:
        group = str(group_id)
        sender = str(sender_id)
        cooldown_key = f"{group}_{sender}"
        current_time = time.time()
        if cooldown_key in self.cooldowns:
            if current_time - self.cooldowns[cooldown_key] < self.cooldown_time:
                return False
        if group in self.target_config and sender in self.target_config[group]:
            self.cooldowns[cooldown_key] = current_time
            return True
        return False
    
    def generate_scolding(self, target_qq: str, target_message: str) -> str:
        scolding_word = random.choice(self.scolding_words)
        if scolding_word.startswith("[CQ:at"):
            scolding_word = scolding_word.replace("{target_qq}", target_qq)
        else:
            scolding_word = f"[CQ:at,qq={target_qq}] {scolding_word}"
        return scolding_word
    
    def get_group_targets(self, group_id: str) -> list:
        return self.target_config.get(str(group_id), [])
    
    def get_total_targets(self) -> int:
        total = 0
        for targets in self.target_config.values():
            total += len(targets)
        return total


# ==================== Ollama AI 配置 ====================
class OllamaAI:
    def __init__(self):
        self.base_url = "http://127.0.0.1:11434"
        self.model = "gemma4:31b-cloud"
        
        # 记忆模块
        try:
            from ai_memory import AIMemoryModule
            self.memory_module = AIMemoryModule()
            log.success("AI记忆模块加载成功")
        except ImportError:
            log.warning("AI记忆模块未找到，使用简单模式")
            class SimpleMemory:
                def get_conversation_context(self, user_id, message): return message
                def add_conversation(self, user_id, q, a): pass
            self.memory_module = SimpleMemory()
        
        # 性格模块
        try:
            from ai_personality import AIPersonality
            self.personality_mgr = AIPersonality()
            log.success(f"AI性格模块加载成功 - 使用 AIPersonality")
            log.info(f"已加载 {len(self.personality_mgr.group_personalities)} 个群的独立性格")
        except ImportError as e:
            log.error(f"AI性格模块导入失败: {e}")
            self.personality_mgr = self._create_simple_personality()
        
        # 好感度影响配置
        self.favor_effects = {
            "super": {"tone": "非常热情、亲密", "extra": "使用❤️💕等亲密表情", "greeting": "亲爱的~"},
            "vip": {"tone": "热情友好", "extra": "使用亲切称呼", "greeting": "老朋友~"},
            "high": {"tone": "友善积极", "extra": "回复详细温暖", "greeting": "你好呀~"},
            "normal": {"tone": "正常礼貌", "extra": "标准回复", "greeting": "你好"},
            "low": {"tone": "冷淡简短", "extra": "回复简短", "greeting": "嗯"},
            "hostile": {"tone": "冷漠", "extra": "回复极简", "greeting": "..."}
        }
        
        log.success(f"AI模块初始化完成 - 模型：{self.model}")
        log.info(f"AI当前性格: {self.personality_mgr.get_current_name()}")
    
    def _create_simple_personality(self):
        """创建简单性格管理器"""
        class SimplePersonality:
            def __init__(self):
                self.global_default = "default"
                self.personalities = {
                    "default": {"name": "默认助手", "system_prompt": "你是QQ群AI助手XP12，活泼开朗。"},
                    "catgirl": {"name": "猫娘", "system_prompt": "你是一只可爱的猫娘喵~"}
                }
            def get_current_name(self): return "默认助手"
            def get_current_prompt(self): return self.personalities["default"]["system_prompt"]
            def get_group_prompt(self, group_id): return self.get_current_prompt()
            def get_personality_prompt(self, pid): return self.personalities.get(pid, self.personalities["default"])["system_prompt"]
            def set_global_default(self, pid): self.global_default = pid; return True, f"已切换为{pid}"
            def get_group_status(self, group_id): return "本群跟随全局"
            def set_group_personality(self, group_id, pid): return True, f"已切换"
            def clear_group_personality(self, group_id): return True, "已恢复"
        return SimplePersonality()
    
    def _get_favor_level(self, favor: int) -> str:
        if favor >= 1000: return "super"
        elif favor >= 500: return "vip"
        elif favor >= 200: return "high"
        elif favor >= 0: return "normal"
        elif favor >= -99: return "low"
        else: return "hostile"
    
    def _build_favor_prompt(self, favor: int, user_id: str) -> str:
        level = self._get_favor_level(favor)
        effect = self.favor_effects[level]
        return f"""【好感度系统】用户 {user_id} 对你的好感度是 {favor} 分。
语气风格：{effect['tone']}，额外要求：{effect['extra']}，称呼方式：{effect['greeting']}"""
    
    async def chat(self, message: str, use_personality: bool = True,
                   group_id: str = None, user_id: str = None, favor: int = None) -> str:
        return await self._chat_with_all(message, use_personality, group_id, user_id, favor)
    
    async def _chat_with_all(self, message: str, use_personality: bool = True,
                             group_id: str = None, user_id: str = None, favor: int = None) -> str:
        try:
            messages = []
            
            if use_personality:
                if group_id:
                    system_prompt = self.personality_mgr.get_group_prompt(group_id)
                    log.debug(f"群{group_id} 使用群性格")
                else:
                    system_prompt = self.personality_mgr.get_personality_prompt("default")
                    log.debug(f"私聊使用默认助手性格")
                messages.append({"role": "system", "content": system_prompt})
            
            if favor is not None and user_id is not None:
                favor_prompt = self._build_favor_prompt(favor, user_id)
                messages.append({"role": "system", "content": favor_prompt})
            
            if user_id:
                context_message = self.memory_module.get_conversation_context(user_id, message)
                messages.append({"role": "user", "content": context_message})
            else:
                messages.append({"role": "user", "content": message})
            
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": 0.8, "top_p": 0.9, "num_predict": 200}
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.base_url}/api/chat", json=payload, timeout=60) as response:
                    if response.status == 200:
                        result = await response.json()
                        response_text = result.get("message", {}).get("content", "").strip()
                        if user_id and response_text:
                            self.memory_module.add_conversation(user_id, message, response_text)
                        return response_text
                    else:
                        log.error(f"AI服务错误 - 状态码：{response.status}")
                        return "AI服务暂时不可用"
        except Exception as e:
            log.error(f"调用AI出错: {e}")
            return "AI服务有点小问题"
    
    async def chat_with_web_search(self, message: str, use_personality: bool = True,
                                   group_id: str = None, user_id: str = None, favor: int = None) -> str:
        return await self._chat_with_all(message, use_personality, group_id, user_id, favor)


# ==================== 独立打卡消息发送器 ====================
class SignMessageSender:
    def __init__(self):
        self.sign_messages = [
            "午夜打卡！新的一天开始啦~",
            "零点签到！又是崭新的一天！",
            "深夜打卡成功！大家早点休息~",
            "准时打卡！开启新的一天！",
            "午夜时分，打卡完成！"
        ]
        self.target_groups = ["1095292788", '1042681049', '167203984', '983230406',
                              "1009018182", '894506131', '597105096', '259099997',
                              '2169057338', '1031919133', '1042681049', '197272874',
                              '157509373', '435624010', '1006371944', '743645787',
                              '1049056800', '924947078', '340841402', '437531257', '779699980']
        self.today_sent = False
        self.last_sent_date = None
        log.info(f"[打卡消息] 初始化完成 - 目标群: {self.target_groups}")
    
    def should_send_today(self):
        today = datetime.now().strftime("%Y-%m-%d")
        if self.last_sent_date == today:
            return False
        now = datetime.now()
        return now.hour == 0 and now.minute == 0
    
    async def send_daily_sign(self, websocket):
        try:
            if not self.should_send_today():
                return False
            
            today = datetime.now().strftime("%Y-%m-%d")
            log.info(f"[打卡消息] 开始发送每日打卡 - {today}")
            
            sign_msg = random.choice(self.sign_messages)
            
            for group_id in self.target_groups:
                try:
                    await websocket.send(json.dumps({
                        "action": "send_msg",
                        "params": {
                            "message_type": "group",
                            "group_id": int(group_id),
                            "message": sign_msg
                        }
                    }))
                    log.info(f"[打卡消息] 已发送到群 {group_id}: {sign_msg}")
                    await asyncio.sleep(random.randint(1, 3))
                except Exception as e:
                    log.error(f"[打卡消息] 发送到群{group_id}失败: {e}")
            
            self.today_sent = True
            self.last_sent_date = today
            log.success("[打卡消息] 每日打卡完成")
            return True
        except Exception as e:
            log.error(f"[打卡消息] 发送每日打卡失败: {e}")
            return False
    
    async def send_manual_sign(self, websocket, group_id, user_id=None):
        try:
            manual_responses = [
                "已为你签到！获得+1积分~",
                "打卡成功！你是今天第一个！",
                "签到完成！今日运势：大吉！",
                "打卡get！保持活跃哦~",
                "已记录签到！继续加油！"
            ]
            sign_msg = random.choice(manual_responses)
            if user_id:
                message = f"[CQ:at,qq={user_id}] {sign_msg}"
            else:
                message = sign_msg
            
            await websocket.send(json.dumps({
                "action": "send_msg",
                "params": {
                    "message_type": "group",
                    "group_id": int(group_id),
                    "message": message
                }
            }))
            log.info(f"[打卡消息] 手动打卡发送到群 {group_id}")
            return True
        except Exception as e:
            log.error(f"[打卡消息] 手动打卡失败: {e}")
            return False


# ==================== 禁言检测模块 ====================
class LLBotMuteDetector:
    def __init__(self, blacklist):
        self.blacklist = blacklist
        log.info("[调试] 禁言检测模块初始化完成")
    
    async def process_event(self, data):
        try:
            if not self.is_mute_event(data):
                return False
            operator_id = data.get("operator_id")
            if operator_id:
                self.blacklist.add_user(operator_id, "禁言机器人复仇")
                log.info(f"[调试] 禁言复仇 - 已将{operator_id}加入黑名单")
                return True
            return False
        except Exception as e:
            log.error(f"[调试] 禁言处理错误: {e}")
            return False
    
    def is_mute_event(self, data):
        post_type = data.get("post_type")
        notice_type = data.get("notice_type")
        if post_type != "notice" or notice_type != "group_ban":
            return False
        user_id = data.get("user_id")
        self_id = data.get("self_id", "")
        duration = data.get("duration", 0)
        return user_id == self_id and duration > 0


# ==================== 消息处理器 ====================
class MessageHandler:
    def __init__(self):
        log.info("初始化消息处理器...")
        
        # 基础模块
        self.admin_manager = AdminManager()
        log.info(f"AdminManager初始化完成 - {len(self.admin_manager.admins)}个管理员")
        self.bot_self_id = None
        
        # 功能模块
        self.anti_recall = AntiRecallLogger()
        self.sign_sender = SignMessageSender()
        self.yin_yang_db = YinYangDB()
        self.ai = OllamaAI()
        self.auto_unmute = AutoUnmuteManager()
        self.blacklist = SimpleBlacklist("data/blacklist.json")
        log.info("基础模块初始化完成")
        
        # 绿茶反击
        self.green_tea = GreenTeaCounter()
        
        # 骂人系统
        self.scolding_system = LocalScoldingSystem(self.admin_manager)
        
        # 入群欢迎
        self.welcome_config_file = "data/welcome_config.json"
        self.welcome_config = self._load_welcome_config()
        self._role_cache = {}
        log.info(f"[入群欢迎] 初始化完成，已启用 {len(self.welcome_config.get('groups', {}))} 个群的欢迎功能")
        
        # 抽签和搜索
        self.lottery = get_lottery()
        self.web_search = get_web_search()
        
        # 自动重进
        try:
            from auto_rejoin import AutoRejoinManager
            self.auto_rejoin = AutoRejoinManager()
            log.success("[自动重进] 模块加载成功")
        except Exception as e:
            log.error(f"[自动重进] 模块加载失败: {e}")
            self.auto_rejoin = None
        
        # 好感度
        try:
            from favorability import FavorabilityManager
            self.favorability = FavorabilityManager(ai_instance=self.ai)
            log.success("[调试] 好感度系统加载成功")
        except Exception as e:
            log.error(f"[调试] 好感度系统加载失败: {e}")
            self.favorability = None
        
        # 刷屏器
        try:
            self.spammer = SimpleSpammer()
            self.spam_manager = SpamCommandManager(self.spammer, self.admin_manager)
            log.success("[刷屏器] 外部刷屏器加载完成")
        except Exception as e:
            log.error(f"[刷屏器] 外部模块加载失败: {e}")
            self.spammer = AdminSpammer(self.admin_manager)
            log.info("[刷屏器] 使用内置刷屏器")
        
        # 骂人配置
        self.scolding_enabled = False
        self.scolding_config_file = "data/scolding_config.json"
        self._load_scolding_config()
        
        self.scolding_config = {
            'enabled': True,
            'keywords': ['大鹏', '鹏', '月月鸟', '大朋鸟'],
            'empty_at_messages': ["你at有啥事情吗？@"],
            'empty_at_target_messages': ["你at2249528587有啥事吗？@"],
            'keyword_messages': ["你提这些词干嘛？@", "别在我这提这些@"],
            'cooldown': 0
        }
        
        # @刷屏检测
        self.at_spam_config = {
            'enabled': True,
            'time_window': 10,
            'max_at_messages': 3,
            'ban_reason': "频繁@骚扰"
        }
        
        # 禁用群
        self.disabled_groups = {'709026404', '1091778880', '917745595', '597105096',
                                '197272874', '1080374835', '830047270'}
        
        # 缓存
        self.user_at_timestamps = {}
        self.scolding_cooldown = {}
        self._last_mute_time = {}
        
        # 视频解析
        try:
            from video_parser import VideoParser
            self.video_parser = VideoParser()
            log.success("[视频解析] 模块加载成功")
        except Exception as e:
            log.error(f"[视频解析] 模块加载失败: {e}")
            self.video_parser = None
        
        log.success("消息处理器初始化完成")
    
    def _load_welcome_config(self) -> dict:
        default_config = {
            "enabled": True,
            "default_message": "🎉 欢迎 {name} 加入本群！\n📝 请遵守群规，祝您玩的愉快~",
            "groups": {}
        }
        if os.path.exists(self.welcome_config_file):
            try:
                with open(self.welcome_config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    for key in default_config:
                        if key not in config:
                            config[key] = default_config[key]
                    return config
            except Exception as e:
                log.error(f"[入群欢迎] 加载配置失败: {e}")
                return default_config
        else:
            self._save_welcome_config(default_config)
            return default_config
    
    def _save_welcome_config(self, config=None):
        if config is None:
            config = self.welcome_config
        try:
            with open(self.welcome_config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log.error(f"[入群欢迎] 保存配置失败: {e}")
    
    def _load_scolding_config(self):
        try:
            if os.path.exists(self.scolding_config_file):
                with open(self.scolding_config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.scolding_enabled = config.get('enabled', False)
                    log.info(f"[骂人模块] 配置加载成功，状态: {'开启' if self.scolding_enabled else '关闭'}")
            else:
                self._save_scolding_config()
                log.info(f"[骂人模块] 创建默认配置文件，状态: 关闭")
        except Exception as e:
            log.error(f"[骂人模块] 配置加载失败: {e}")
            self.scolding_enabled = False
    
    def _save_scolding_config(self):
        try:
            config = {
                'enabled': self.scolding_enabled,
                'description': '骂人模块总开关'
            }
            with open(self.scolding_config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log.error(f"[骂人模块] 配置保存失败: {e}")
    
    # ==================== 权限检查 ====================
    async def get_member_role_via_ws(self, group_id: int, user_id: int) -> str:
        cached = self._get_cached_role(group_id, user_id)
        if cached:
            return cached
        
        try:
            echo = f"get_member_{group_id}_{user_id}_{int(time.time()*1000)}"
            await self.websocket.send(json.dumps({
                "action": "get_group_member_info",
                "params": {"group_id": group_id, "user_id": user_id, "no_cache": True},
                "echo": echo
            }))
            
            timeout = 5
            start = time.time()
            while time.time() - start < timeout:
                try:
                    msg = await asyncio.wait_for(self.websocket.recv(), timeout=0.5)
                    data = json.loads(msg)
                    if data.get("echo") == echo:
                        if data.get("status") == "ok":
                            role = data.get("data", {}).get("role", "member")
                            self._set_cached_role(group_id, user_id, role)
                            return role
                        return "unknown"
                except asyncio.TimeoutError:
                    continue
                except json.JSONDecodeError:
                    continue
            return "unknown"
        except Exception as e:
            log.error(f"[权限] 异常: {e}")
            return "unknown"
    
    async def check_group_admin_permission(self, user_id: str, group_id: int) -> bool:
        if self.admin_manager.is_admin(user_id):
            return True
        role = await self.get_member_role_via_ws(group_id, int(user_id))
        return role in ["owner", "admin"]
    
    def _get_cached_role(self, group_id: int, user_id: int) -> str:
        key = (group_id, user_id)
        now = time.time()
        if key in self._role_cache:
            role, expire = self._role_cache[key]
            if now < expire:
                return role
            del self._role_cache[key]
        return None
    
    def _set_cached_role(self, group_id: int, user_id: int, role: str, ttl: int = 10):
        key = (group_id, user_id)
        self._role_cache[key] = (role, time.time() + ttl)
    
    # ==================== 工具方法 ====================
    def set_bot_id(self, bot_id: str):
        self.bot_self_id = str(bot_id) if bot_id else None
        log.info(f"[设置ID] 设置机器人ID为: {self.bot_self_id}")
        if hasattr(self, 'anti_recall') and self.anti_recall:
            try:
                if hasattr(self.anti_recall, 'set_bot_id'):
                    self.anti_recall.set_bot_id(bot_id)
                else:
                    self.anti_recall.bot_self_id = str(bot_id) if bot_id else None
                log.info("[设置ID] 防撤回系统ID设置成功")
            except Exception as e:
                log.error(f"[设置ID] 设置防撤回系统ID失败: {e}")
    
    def _extract_pure_text(self, data: Dict) -> str:
        try:
            raw_message = data.get("message", "")
            text_content = ""
            if isinstance(raw_message, str):
                text_content = re.sub(r'\[CQ:[^\]]+\]', '', raw_message)
                text_content = re.sub(r'\s+', ' ', text_content).strip()
            elif isinstance(raw_message, list):
                for item in raw_message:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text = item.get("data", {}).get("text", "")
                        text_content += text
                text_content = re.sub(r'\s+', ' ', text_content).strip()
            return text_content or "（空消息）"
        except:
            return "（提取失败）"
    
    def is_at_bot(self, data: Dict) -> bool:
        try:
            raw_message = data.get("message", "")
            bot_qq = str(data.get("self_id", self.bot_self_id or ""))
            if isinstance(raw_message, str):
                if f"[CQ:at,qq={bot_qq}]" in raw_message or f"@{bot_qq}" in raw_message:
                    return True
            elif isinstance(raw_message, list):
                for item in raw_message:
                    if isinstance(item, dict) and item.get("type") == "at":
                        at_qq = str(item.get("data", {}).get("qq", ""))
                        if at_qq == bot_qq:
                            return True
            return False
        except:
            return False
    
    def _get_user_name(self, user_id: str, group_id: str = None) -> str:
        return str(user_id)
    
    # ==================== 入群欢迎 ====================
    def _send_welcome_message(self, group_id: int, user_id: int, user_name: str):
        try:
            group_id_str = str(group_id)
            if not self.welcome_config.get("enabled", True):
                return
            group_config = self.welcome_config.get("groups", {}).get(group_id_str, {})
            if group_config.get("enabled") is False:
                return
            if group_config.get("message"):
                message_template = group_config["message"]
            else:
                message_template = self.welcome_config.get("default_message", "🎉 欢迎 {name} 加入本群！")
            welcome_msg = message_template.format(name=user_name, user_id=user_id, group_id=group_id)
            asyncio.create_task(self._send_group_message(group_id, welcome_msg))
            log.info(f"[入群欢迎] 群{group_id} 欢迎新成员 {user_name}({user_id})")
        except Exception as e:
            log.error(f"[入群欢迎] 发送失败: {e}")
    
    async def _send_group_message(self, group_id: int, message: str):
        try:
            if hasattr(self, 'websocket') and self.websocket:
                await self.websocket.send(json.dumps({
                    "action": "send_msg",
                    "params": {"message_type": "group", "group_id": group_id, "message": message}
                }))
        except Exception as e:
            log.error(f"[入群欢迎] 发送消息失败: {e}")
    
    # ==================== 事件处理 ====================
    def _handle_group_ban(self, data: Dict) -> Optional[Dict]:
        try:
            user_id = str(data.get("user_id", ""))
            group_id = str(data.get("group_id", ""))
            duration = data.get("duration", 0)
            self_id = str(data.get("self_id", self.bot_self_id or ""))
            if duration <= 0:
                return None
            if user_id == self_id:
                if self.auto_unmute.should_auto_unmute_self(group_id, duration):
                    log.info(f"[自动解禁] 机器人在白名单群 {group_id} 被禁言 {duration} 秒，准备自动解禁")
                    self.auto_unmute.set_cooldown(f"group_{group_id}")
                    return {
                        "action": "set_group_ban",
                        "params": {"group_id": int(group_id), "user_id": int(user_id), "duration": 0},
                        "echo": f"auto_unmute_self_{group_id}_{int(time.time())}"
                    }
            elif self.auto_unmute.should_auto_unmute_user(user_id, group_id, duration):
                log.info(f"[自动解禁] 白名单用户 {user_id} 在群 {group_id} 被禁言 {duration} 秒，准备自动解禁")
                self.auto_unmute.set_cooldown(f"user_{user_id}")
                return {
                    "action": "set_group_ban",
                    "params": {"group_id": int(group_id), "user_id": int(user_id), "duration": 0},
                    "echo": f"auto_unmute_user_{user_id}_{int(time.time())}"
                }
            return None
        except Exception as e:
            log.error(f"[禁言事件] 处理失败: {e}")
            return None
    
    def _handle_non_message(self, data: Dict) -> Optional[Dict]:
        post_type = data.get("post_type")
        if post_type == "notice":
            notice_type = data.get("notice_type")
            if notice_type == "group_recall":
                return self.anti_recall.handle_recall_event(data)
            elif notice_type == "group_ban":
                return self._handle_group_ban(data)
            elif notice_type == "group_increase":
                log.info("[入群] 收到新人入群事件")
                return self._handle_group_increase(data)
        return None
    
    def _handle_group_increase(self, data: Dict) -> Optional[Dict]:
        try:
            group_id = data.get("group_id")
            user_id = data.get("user_id")
            # 跳过禁用群
            if str(group_id) in self.disabled_groups:
                log.info(f"[入群欢迎] 群{group_id}在禁用列表中，跳过")
                return None
            user_name = data.get("user_name", str(user_id))
            self._send_welcome_message(group_id, user_id, user_name)
            return None
        except Exception as e:
            log.error(f"[入群欢迎] 处理事件失败: {e}")
            return None
    
    # ========== 命令处理 ==========
    async def _process_commands(self, text: str, user_id: str, message_type: str, group_id: str) -> Optional[Dict]:
        text_lower = text.strip().lower()
        log.command(f"收到: {text_lower}")
        
        # 帮助命令
        if text_lower in ["帮助", "help", "菜单", "功能"] or text_lower.startswith(("!帮助", "！帮助")):
            parts = text.split()
            if len(parts) >= 2:
                return self._get_help_reply(user_id, message_type, group_id, parts[1])
            return self._get_help_reply(user_id, message_type, group_id, None)
        
        # 打卡命令
        if text_lower in ["!打卡", "！打卡", "!sign", "！sign", "打卡",'签到']:
            responses = ["已为你签到！获得+1积分~", "打卡成功！你是今天第一个！", "签到完成！今日运势：大吉！"]
            return self._create_reply(message_type, user_id, group_id, random.choice(responses))
        
        # 入群欢迎配置（所有人可用）
        if text_lower in ["!欢迎配置", "！欢迎配置"]:
            status = f"【🎉 入群欢迎配置】\n全局开关: {'✅ 开启' if self.welcome_config.get('enabled', True) else '❌ 关闭'}\n已配置群: {len(self.welcome_config.get('groups', {}))}个"
            return self._create_reply(message_type, user_id, group_id, status)
        
        # 抽签命令
        if text_lower.startswith(("!抽签", "！抽签", "!签", "！签")):
            parts = text.split()
            lottery_type = parts[1].lower() if len(parts) >= 2 else "daily"
            type_map = {"daily": "daily", "每日": "daily", "fortune": "fortune", "财运": "fortune",
                        "love": "love", "姻缘": "love", "work": "work", "事业": "work",
                        "study": "study", "学业": "study"}
            lottery_type = type_map.get(lottery_type, "daily")
            user_name = self._get_user_name(user_id, group_id)
            try:
                img_path, result_name, result_desc, score = self.lottery.draw_lottery_image(lottery_type, user_id, user_name)
                if not os.path.exists(img_path):
                    return self._create_reply(message_type, user_id, group_id, "❌ 图片生成失败")
                return {
                    "action": "send_msg",
                    "params": {
                        "message_type": message_type,
                        "group_id": int(group_id) if message_type == "group" else None,
                        "user_id": int(user_id) if message_type == "private" else None,
                        "message": f"[CQ:image,file=file:///{os.path.abspath(img_path)}]"
                    }
                }
            except Exception as e:
                log.error(f"抽签失败: {e}")
                return self._create_reply(message_type, user_id, group_id, f"❌ 抽签失败: {e}")
        
        # 好感度命令（简化版，原有功能保留）
        if text_lower in ["!好感度", "！好感度"]:
            if self.favorability:
                info = self.favorability.get_favor_info(user_id)
                return self._create_reply(message_type, user_id, group_id, f"【❤️ 好感度】\n用户: {user_id}\n好感度: {info['favor']}\n等级: {info['level_name']}")
        
        # 管理员权限检查
        is_admin = self.admin_manager.is_admin(user_id)
        if not is_admin:
            return None
        
        # 远程切换性格
        if text_lower.startswith(("!远程性格", "！远程性格")):
            parts = text.split()
            if len(parts) < 3:
                return self._create_reply(message_type, user_id, group_id, "格式: !远程性格 <群号> <猫娘/默认>")
            target_group = parts[1]
            mode = parts[2].lower()
            if not target_group.isdigit():
                return self._create_reply(message_type, user_id, group_id, "❌ 群号必须是数字")
            if mode in ["猫娘", "catgirl", "喵"]:
                success, msg = self.ai.personality_mgr.set_group_personality(target_group, "catgirl")
            elif mode in ["默认", "default", "普通"]:
                success, msg = self.ai.personality_mgr.set_group_personality(target_group, "default")
            else:
                return self._create_reply(message_type, user_id, group_id, f"❌ 未知模式: {mode}")
            return self._create_reply(message_type, user_id, group_id, f"✅ 已远程设置群{target_group}\n{msg}")
        
        # 开启本群欢迎
        if text_lower in ["!开启欢迎", "！开启欢迎"]:
            group_id_str = str(group_id)
            if group_id_str not in self.welcome_config["groups"]:
                self.welcome_config["groups"][group_id_str] = {}
            self.welcome_config["groups"][group_id_str]["enabled"] = True
            self._save_welcome_config()
            return self._create_reply(message_type, user_id, group_id, "✅ 本群入群欢迎已开启")
        
        # 关闭本群欢迎
        if text_lower in ["!关闭欢迎", "！关闭欢迎"]:
            group_id_str = str(group_id)
            if group_id_str not in self.welcome_config["groups"]:
                self.welcome_config["groups"][group_id_str] = {}
            self.welcome_config["groups"][group_id_str]["enabled"] = False
            self._save_welcome_config()
            return self._create_reply(message_type, user_id, group_id, "✅ 本群入群欢迎已关闭")
        
        # 设置欢迎消息
        if text_lower.startswith(("!设置欢迎", "！设置欢迎")):
            parts = text.split(maxsplit=1)
            if len(parts) >= 2:
                welcome_msg = parts[1]
                group_id_str = str(group_id)
                if group_id_str not in self.welcome_config["groups"]:
                    self.welcome_config["groups"][group_id_str] = {}
                self.welcome_config["groups"][group_id_str]["message"] = welcome_msg
                self.welcome_config["groups"][group_id_str]["enabled"] = True
                self._save_welcome_config()
                return self._create_reply(message_type, user_id, group_id, f"✅ 本群欢迎消息已设置\n{welcome_msg}")
            return self._create_reply(message_type, user_id, group_id, "格式: !设置欢迎 <欢迎消息>\n变量: {name} {user_id} {group_id}")
        
        # 其他管理员命令（保持原有功能）
        # ... 这里可以继续添加其他命令 ...
        
        return None
    
    def _get_help_reply(self, user_id: str, message_type: str, group_id: str, category: str = None) -> Dict:
        is_admin = self.admin_manager.is_admin(user_id)
        from help_image import HelpImageGenerator
        generator = HelpImageGenerator()
        
        if category is None or category == "":
            img = generator.create_main_menu(is_admin)
            img_base64 = generator.image_to_base64(img)
            return self._send_help_image(message_type, user_id, group_id, img_base64)
        
        category_str = str(category).lower()
        
        if category_str in ["5", "性格"]:
            img = generator.create_personality_help_page(is_admin)
            img_base64 = generator.image_to_base64(img)
            return self._send_help_image(message_type, user_id, group_id, img_base64)
        
        # 其他帮助分类...
        return self._get_help_reply(user_id, message_type, group_id, None)
    
    def _send_help_image(self, message_type: str, user_id: str, group_id: str, img_base64: str) -> Dict:
        return {
            "action": "send_msg",
            "params": {
                "message_type": message_type,
                "group_id": int(group_id) if message_type == "group" else None,
                "user_id": int(user_id) if message_type == "private" else None,
                "message": f"[CQ:image,file={img_base64}]"
            }
        }
    
    def _create_reply(self, message_type: str, user_id: str, group_id: str, message: str) -> Dict:
        params = {}
        if message_type == "private":
            params["message_type"] = "private"
            params["user_id"] = int(user_id)
            params["message"] = message
        elif message_type == "group" and group_id:
            params["message_type"] = "group"
            params["group_id"] = int(group_id)
            if not message.startswith("[CQ:at"):
                params["message"] = f"[CQ:at,qq={user_id}] {message}"
            else:
                params["message"] = message
            if hasattr(self, "anti_recall") and self.anti_recall:
                fake_message_id = f"pre_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
                self.anti_recall.record_sent_message(str(group_id), params["message"], fake_message_id)
        return {"action": "send_msg", "params": params}
    
    async def _handle_ai_chat(self, text: str, user_id: str, message_type: str, group_id: str) -> Dict:
        try:
            favor = None
            if hasattr(self, 'favorability') and self.favorability:
                favor = self.favorability.get_favor(user_id)
                log.debug(f"[AI] 用户 {user_id} 好感度: {favor}")
            reply_text = await self.ai.chat(text, use_personality=True, group_id=str(group_id) if group_id else None, user_id=str(user_id), favor=favor)
            if user_id and reply_text and "AI服务暂时不可用" not in reply_text:
                if hasattr(self.ai, 'memory_module'):
                    self.ai.memory_module.add_conversation(user_id, text, reply_text)
            return self._create_reply(message_type, user_id, group_id, reply_text)
        except Exception as e:
            log.error(f"AI聊天失败: {e}")
            return self._create_reply(message_type, user_id, group_id, "🔧 服务暂时不可用")
    
    async def handle_message(self, data: Dict) -> Optional[Dict]:
        try:
            post_type = data.get("post_type", "")
            if "self_id" not in data and self.bot_self_id:
                data["self_id"] = self.bot_self_id
            
            try:
                self.anti_recall.record_message(data)
            except Exception as e:
                log.error(f"[防撤回] 记录消息失败: {e}")
            
            message_type = data.get("message_type", "")
            user_id = str(data.get("user_id", "unknown"))
            group_id = data.get("group_id")
            
            if post_type != "message":
                return self._handle_non_message(data)
            
            if message_type == "group":
                pure_text = self._extract_pure_text(data)
                log.msg(f"[消息] 群{group_id} ← {user_id}: {pure_text[:50]}...")
            elif message_type == "private":
                pure_text = self._extract_pure_text(data)
                log.msg(f"[消息] 私聊 ← {user_id}: {pure_text[:50]}...")
            
            # 检查禁用群
            if message_type == "group" and str(group_id) in self.disabled_groups:
                return None
            
            # @刷屏检测
            if self.at_spam_config['enabled'] and self.is_at_bot(data):
                if self._check_at_spam(user_id):
                    warning_msg = "检测到频繁@行为，已加入黑名单"
                    if message_type == "group":
                        warning_msg = f"[CQ:at,qq={user_id}] {warning_msg}"
                    return self._create_reply(message_type, user_id, group_id, warning_msg)
            
            # 黑名单检查
            if user_id and self.blacklist.is_banned(user_id):
                msg = "您已被加入黑名单，无法使用功能"
                if message_type == "group":
                    msg = f"[CQ:at,qq={user_id}] {msg}"
                return self._create_reply(message_type, user_id, group_id, msg)
            
            # 提取文本
            text = self._extract_pure_text(data)
            if not text or text == "（空消息）":
                return None
            
            if len(text) > 100:
                skip_msg = "检测到长文本，已取消调用"
                if message_type == "group":
                    skip_msg = f"[CQ:at,qq={user_id}] {skip_msg}"
                return self._create_reply(message_type, user_id, group_id, skip_msg)
            
            # 处理命令
            command_response = await self._process_commands(text, user_id, message_type, group_id)
            if command_response:
                return command_response
            
            # 检查是否需要回复
            if message_type == "private":
                should_reply = True
            elif message_type == "group":
                should_reply = self.is_at_bot(data)
            else:
                should_reply = False
            
            if not should_reply:
                return None
            
            return await self._handle_ai_chat(text, user_id, message_type, group_id)
            
        except Exception as e:
            log.error(f"handle_message异常: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _check_at_spam(self, user_id: str) -> bool:
        try:
            if not self.at_spam_config['enabled']:
                return False
            current_time = time.time()
            time_window = self.at_spam_config['time_window']
            max_at_msgs = self.at_spam_config['max_at_messages']
            if user_id not in self.user_at_timestamps:
                self.user_at_timestamps[user_id] = []
            self.user_at_timestamps[user_id].append(current_time)
            self.user_at_timestamps[user_id] = [ts for ts in self.user_at_timestamps[user_id] if current_time - ts <= time_window]
            at_count = len(self.user_at_timestamps[user_id])
            if at_count > max_at_msgs:
                log.warning(f"[刷屏检测] 用户{user_id}（{at_count}次@/{time_window}秒）")
                self.blacklist.add_user(user_id, self.at_spam_config['ban_reason'])
                self.user_at_timestamps[user_id] = []
                return True
            return False
        except:
            return False


# ==================== 主程序 ====================
async def run_bot():
    uri = "ws://127.0.0.1:8765"
    
    while True:
        try:
            log.success("[连接] 正在连接LLOneBot...")
            async with websockets.connect(uri) as websocket:
                log.success("[连接] 连接成功")
                
                handler = MessageHandler()
                handler.websocket = websocket
                
                if hasattr(handler, 'spammer') and handler.spammer:
                    if hasattr(handler.spammer, 'set_websocket'):
                        handler.spammer.set_websocket(websocket)
                    log.info("[连接] 刷屏器WebSocket已设置")
                
                current_bot_id = None
                try:
                    hello_data = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    hello_json = json.loads(hello_data)
                    if hello_json.get("post_type") == "meta_event" and hello_json.get("meta_event_type") == "lifecycle":
                        current_bot_id = str(hello_json.get("self_id", ""))
                        log.success(f"[连接] 从元事件获取到机器人ID: {current_bot_id}")
                except (asyncio.TimeoutError, json.JSONDecodeError, KeyError) as e:
                    log.warning(f"[连接] 未能从元事件获取ID: {e}")
                
                if current_bot_id:
                    handler.set_bot_id(current_bot_id)
                    log.success(f"[连接] 系统身份已设置为: {current_bot_id}")
                
                last_check_time = time.time()
                
                while True:
                    try:
                        raw_data = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        data = json.loads(raw_data)
                        reply = await handler.handle_message(data)
                        if reply:
                            await websocket.send(json.dumps(reply))
                    except asyncio.TimeoutError:
                        current_time = time.time()
                        if current_time - last_check_time > 60:
                            last_check_time = current_time
                            now = datetime.now()
                            if now.hour == 0 and now.minute == 0:
                                if hasattr(handler, 'sign_sender'):
                                    try:
                                        await handler.sign_sender.send_daily_sign(websocket)
                                        log.success("[定时] 打卡发送完成")
                                    except Exception as e:
                                        log.error(f"[定时] 打卡失败: {e}")
                        continue
                    except websockets.exceptions.ConnectionClosed:
                        log.warning("[连接] 连接断开，重新连接...")
                        break
                    except Exception as e:
                        log.error(f"[错误] 消息循环异常: {e}")
                        await asyncio.sleep(1)
                        
        except ConnectionRefusedError:
            log.warning("[连接] 连接被拒绝，5秒后重试...")
            await asyncio.sleep(5)
        except Exception as e:
            log.error(f"[连接] 连接异常: {e}, 5秒后重试...")
            await asyncio.sleep(5)


async def main():
    await run_bot()


if __name__ == "__main__":
    log.success("正在启动主程序...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.warning("\n程序被手动停止")
    except Exception as e:
        log.crash(e)
        input(f"{Fore.RED}按Enter键退出...{Style.RESET_ALL}")
