"""
QQ AI机器人 - 稳定修复版
功能：AI对话 + 防撤回 + 黑名单 + 管理员系统 + 禁言复仇
"""

import asyncio
import websockets
import json
import logging
import aiohttp
import time
import os
import re
import random
from datetime import datetime

# ==================== 日志配置 ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# ==================== 防撤回模块（内置简单版） ====================
class SimpleAntiRecall:
    """内置防撤回模块 - 简单稳定"""
    
    def __init__(self):
        self.cache = {}
        self.enabled = True
        logger.info("防撤回模块初始化")
    
    def record_message(self, *args, **kwargs):
        """记录消息 - 万能参数适配"""
        try:
            message_id = None
            content = ""
            
            # 参数适配
            if args and isinstance(args[0], dict):
                # 方式1：传字典
                event = args[0]
                message_id = event.get("message_id")
                content = event.get("content", "")
            elif len(args) >= 4:
                # 方式2：传4个参数
                message_id = args[0]
                content = args[3] if len(args) > 3 else ""
            else:
                # 方式3：关键字参数
                message_id = kwargs.get("message_id")
                content = kwargs.get("content", "")
            
            if message_id:
                self.cache[message_id] = content[:200]
                # 限制缓存大小
                if len(self.cache) > 1000:
                    # 删除最旧的
                    oldest = list(self.cache.keys())[0]
                    del self.cache[oldest]
                return True
            return False
        except Exception as e:
            logger.error(f"记录消息失败: {e}")
            return False
    
    def handle_recall_event(self, event):
        """处理撤回事件"""
        if not self.enabled:
            return None
        
        message_id = event.get("message_id")
        if message_id in self.cache:
            content = self.cache[message_id]
            return {
                "action": "send_msg",
                "params": {
                    "message": f"🔍 检测到消息撤回\n内容: {content[:100]}",
                    "reply_to": message_id
                }
            }
        return None
    
    def handle_recall(self, event):
        """兼容旧方法"""
        return self.handle_recall_event(event)

# ==================== 黑名单系统 ====================
class BlacklistManager:
    """黑名单管理器"""
    
    def __init__(self, file_path="data/blacklist.json"):
        self.file_path = file_path
        self.blacklist = set()
        self.reasons = {}
        self.load()
    
    def load(self):
        """加载黑名单"""
        try:
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            if os.path.exists(self.file_path):
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.blacklist = set(data.get("users", []))
                    self.reasons = data.get("reasons", {})
                    logger.info(f"黑名单加载: {len(self.blacklist)} 用户")
            else:
                self.save()
        except Exception as e:
            logger.error(f"加载黑名单失败: {e}")
    
    def save(self):
        """保存黑名单"""
        try:
            data = {
                "users": list(self.blacklist),
                "reasons": self.reasons
            }
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存黑名单失败: {e}")
    
    def is_banned(self, user_id):
        """检查是否在黑名单"""
        user_id_str = str(user_id)
        return user_id_str in self.blacklist
    
    def add_user(self, user_id, reason="管理员封禁"):
        """添加用户"""
        user_id_str = str(user_id)
        if user_id_str not in self.blacklist:
            self.blacklist.add(user_id_str)
            self.reasons[user_id_str] = reason
            self.save()
            logger.info(f"添加黑名单: {user_id_str} - {reason}")
            return True
        return False
    
    def remove_user(self, user_id):
        """移除用户"""
        user_id_str = str(user_id)
        if user_id_str in self.blacklist:
            self.blacklist.remove(user_id_str)
            if user_id_str in self.reasons:
                del self.reasons[user_id_str]
            self.save()
            logger.info(f"移除黑名单: {user_id_str}")
            return True
        return False

# ==================== AI模块 ====================
class OllamaAI:
    """AI对话核心"""
    
    def __init__(self):
        self.base_url = "http://127.0.0.1:11434"
        self.model = "qwen2.5:3b"
        self.personality = """你是QQ群AI助手，活泼开朗，喜欢用表情包😊，说话带网络流行语。
        重要规则：
        1. 绝不讨论金钱借贷话题
        2. 不承认与用户有亲属关系
        3. 不参与敏感政治话题
        """
    
    async def chat(self, message: str, use_personality: bool = True) -> str:
        """调用AI"""
        try:
            messages = []
            if use_personality:
                messages.append({
                    "role": "system",
                    "content": self.personality
                })
            messages.append({"role": "user", "content": message})
            
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": 0.8}
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("message", {}).get("content", "思考中...").strip()
                    else:
                        return "AI服务暂时不可用"
        except Exception as e:
            logger.error(f"AI调用失败: {e}")
            return "AI服务有点小问题"

# ==================== 管理员系统（简化版） ====================
class AdminManager:
    """管理员管理器"""
    
    def __init__(self, admin_file="data/admins.json"):
        self.admin_file = admin_file
        self.admins = self._load_admins()
    
    def _load_admins(self):
        """加载管理员"""
        try:
            if os.path.exists(self.admin_file):
                with open(self.admin_file, 'r', encoding='utf-8') as f:
                    return set(json.load(f))
        except:
            pass
        return {"123456789"}  # 默认管理员
    
    def is_admin(self, user_id):
        """检查是否是管理员"""
        return str(user_id) in self.admins

# ==================== 消息处理器 ====================
class MessageHandler:
    """核心消息处理器"""
    
    def __init__(self):
        # 初始化模块
        self.anti_recall = SimpleAntiRecall()
        self.blacklist = BlacklistManager()
        self.ai = OllamaAI()
        self.admin_manager = AdminManager()
        # 图片缓存
        self.image_cache = None
        
        # 防撤回系统
        self.anti_recall = AntiRecallLogger()
        self.anti_recall.image_cache = self.image_cache  # 注入        
        # 骂人配置
        self.scolding_config = {
            'enabled': True,
            'keywords': ['大鹏', 'dapeng', '鹏'],
            'allowed_groups': ['1009018182', '655450225', '823617758'],
            'messages': [
                "你叫谁大鹏呢？没大没小的！@",
                "大鹏是你叫的？叫我星！@",
                "注意你的称呼！@"
            ]
        }
        
        # 刷屏检测
        self.spam_config = {
            'enabled': True,
            'time_window': 10,
            'max_messages': 15
        }
        self.user_message_timestamps = {}
        
        logger.info("消息处理器初始化完成")
    
    # ========== 工具方法 ==========
    def is_at_bot(self, data):
        """检查是否@了机器人"""
        try:
            raw_message = data.get("message", "")
            bot_qq = str(data.get("self_id", ""))
            
            if isinstance(raw_message, str):
                return f"[CQ:at,qq={bot_qq}]" in raw_message
            elif isinstance(raw_message, list):
                for item in raw_message:
                    if isinstance(item, dict) and item.get("type") == "at":
                        at_qq = str(item.get("data", {}).get("qq", ""))
                        if at_qq == bot_qq:
                            return True
            return False
        except:
            return False
    
    def extract_text(self, data):
        """提取纯文本"""
        try:
            raw_message = data.get("message", "")
            text = ""
            
            if isinstance(raw_message, str):
                # 移除CQ码
                text = re.sub(r'\[CQ:[^\]]+\]', '', raw_message)
            elif isinstance(raw_message, list):
                for item in raw_message:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text += item.get("data", {}).get("text", "")
            
            return text.strip()
        except:
            return ""
    
    def should_reply(self, data):
        """判断是否需要回复"""
        message_type = data.get("message_type")
        
        # 私聊直接回复
        if message_type == "private":
            return True
        
        # 群聊需要@
        if message_type == "group":
            return self.is_at_bot(data)
        
        return False
    
    def check_spam(self, data):
        """检查刷屏"""
        if not self.spam_config['enabled']:
            return False
        
        user_id = str(data.get('user_id', ''))
        if not user_id:
            return False
        
        current_time = time.time()
        
        # 初始化记录
        if user_id not in self.user_message_timestamps:
            self.user_message_timestamps[user_id] = []
        
        # 添加时间戳
        self.user_message_timestamps[user_id].append(current_time)
        
        # 清理过期记录
        window = self.spam_config['time_window']
        self.user_message_timestamps[user_id] = [
            ts for ts in self.user_message_timestamps[user_id]
            if current_time - ts <= window
        ]
        
        # 检查数量
        count = len(self.user_message_timestamps[user_id])
        max_msgs = self.spam_config['max_messages']
        
        if count > max_msgs:
            logger.warning(f"刷屏检测: 用户 {user_id} 在 {window}秒内发送了 {count} 条消息")
            # 加入黑名单
            self.blacklist.add_user(user_id, "刷屏骚扰")
            return True
        
        return False
    
    def check_scolding(self, data):
        """检查是否需要骂人"""
        if not self.scolding_config['enabled']:
            return None
        
        # 群聊过滤
        if data.get("message_type") == "group":
            group_id = str(data.get("group_id", ""))
            allowed = self.scolding_config['allowed_groups']
            if allowed and group_id not in allowed:
                return None
        
        # 检查关键词
        text = self.extract_text(data).lower()
        for keyword in self.scolding_config['keywords']:
            if keyword.lower() in text:
                user_id = data.get("user_id")
                message = random.choice(self.scolding_config['messages'])
                return message.replace('@', f'[CQ:at,qq={user_id}]')
        
        return None
    
    # ========== 核心处理方法 ==========
    async def handle_message(self, data: Dict) -> Optional[Dict]:
        try:
            post_type = data.get("post_type", "")
    
            # 确保有self_id
            if "self_id" not in data and self.bot_self_id:
                data["self_id"] = self.bot_self_id
    
            # 所有消息都传给防撤回系统
            try:
                self.anti_recall.record_message(data)
            except Exception as e:
                print(f"[防撤回] 记录消息失败: {e}")
    
            # 提取变量
            message_type = data.get("message_type", "")
            user_id = str(data.get("user_id", "unknown"))
            group_id = data.get("group_id")
    
            # 处理非消息事件
            if post_type != "message":
                return self._handle_non_message(data)
    
            # 输出消息
            if message_type == "group":
                pure_text = self._extract_pure_text(data)
                print(f"[消息] 群{group_id} ← {user_id}: {pure_text[:50]}...")
            elif message_type == "private":
                pure_text = self._extract_pure_text(data)
                print(f"[消息] 私聊 ← {user_id}: {pure_text[:50]}...")

            # ====== 互斥骂人逻辑 ======
            new_system_triggered = False
            scolding_msg = None
    
            # 1. 先检查新系统（目标QQ骂人）
            if (hasattr(self, 'scolding_system') and 
                message_type == "group" and 
                group_id and 
                self.scolding_enabled and
                self.scolding_system.should_scold(str(group_id), user_id)):
        
                print(f"[新系统] 触发目标{user_id}")
                target_message = self._extract_pure_text(data)
                scolding_msg = self.scolding_system.generate_scolding(user_id, target_message)
                new_system_triggered = True

            # 2. 如果新系统没触发，检查旧系统（关键词骂人）
            old_system_triggered = False

            if not new_system_triggered and hasattr(self, 'scolding_config'):
                if self.scolding_enabled and self.scolding_config.get('enabled', False):
                    if self._should_scold(data):
                        print(f"[旧系统] 触发关键词检测")
                        scolding_msg = self._get_scolding_message(user_id, data)
                        old_system_triggered = True
    
            # ====== 骂人回复 ======
            if new_system_triggered or old_system_triggered:
                print(f"[骂人] 使用{'新' if new_system_triggered else '旧'}系统回复")
                return self._create_reply(
                    message_type="group",
                    user_id=user_id,
                    group_id=group_id,
                    message=scolding_msg
                )
    
            # ====== 继续原有逻辑 ======
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
    
            # ========== 视频解析 ==========
            if hasattr(self, 'video_parser') and self.video_parser and self.video_parser.config.get("enabled", False):
                raw_message = data.get("message", "")
                if isinstance(raw_message, str):
                    raw_text = raw_message
                else:
                    raw_text = self._extract_pure_text(data)
        
                import re
                url_match = re.search(r'https?://[^\s]+', raw_text)
                if url_match:
                    url = url_match.group(0)
                    platform = self.video_parser.detect_platform(url)
                    if platform:
                        print(f"[视频解析] 检测到 {platform} 链接: {url}")
                        info = await self.video_parser.parse_video(url)
                        if info:
                            msg = self.video_parser.format_message(info)
                            reply = self._create_reply(message_type, user_id, group_id, msg)
                            return reply
    
            # ========== 检查是否需要回复（@机器人）==========
            if message_type == "private":
                should_reply = True
            elif message_type == "group":
                should_reply = self.is_at_bot(data)
            else:
                should_reply = False
    
            if not should_reply:
                return None
    
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
    
            # ========== 长文本检查 ==========
            if len(text) > 100:
                skip_msg = "检测到长文本，已取消调用"
                if message_type == "group":
                    skip_msg = f"[CQ:at,qq={user_id}] {skip_msg}"
                return self._create_reply(message_type, user_id, group_id, skip_msg)
    
            # ========== 处理命令 ==========
            command_response = await self._process_commands(text, user_id, message_type, group_id)
            if command_response:
                return command_response

            # ========== 联网搜索 ==========
            if text.lower().startswith(("!搜索", "！搜索", "!搜", "！搜")):
                parts = text.split()
                if len(parts) >= 2:
                    query = " ".join(parts[1:])
                
                    try:
                        await self.websocket.send(json.dumps({
                            "action": "send_msg",
                            "params": {
                                "message_type": message_type,
                                "group_id": int(group_id) if message_type == "group" else None,
                                "user_id": int(user_id) if message_type == "private" else None,
                                "message": f"[CQ:at,qq={user_id}] 🔍 正在搜索: {query}... 请稍候（约5-10秒）"
                            }
                        }))
                    except:
                        pass
                
                    img_path = await self.web_search.search(query)
                
                    if not img_path or not os.path.exists(img_path):
                        return self._create_reply(message_type, user_id, group_id, "❌ 搜索失败，请稍后再试")
                
                    return {
                        "action": "send_msg",
                        "params": {
                            "message_type": message_type,
                            "group_id": int(group_id) if message_type == "group" else None,
                            "user_id": int(user_id) if message_type == "private" else None,
                            "message": f"[CQ:image,file=file:///{img_path}]"
                        }
                    }
    
            # ========== 绿茶反击检测 ==========
            if hasattr(self, 'green_tea') and message_type == "group" and group_id:
                pure_text = self._extract_pure_text(data)
                if self.green_tea.should_counter(str(group_id), user_id, pure_text):
                    print(f"[绿茶反击] 触发，回复用户 {user_id}")
                    green_tea_msg = self.green_tea.generate_response(user_id, pure_text)
                    return self._create_reply(
                        message_type="group",
                        user_id=user_id,
                        group_id=group_id,
                        message=green_tea_msg
                    )

            # ========== 防重复回复检查（2秒内同一用户同一群不重复回复）==========
            if message_type == "group" and group_id:
                key = f"{group_id}_{user_id}"
                now = time.time()
                if key in self.last_reply_time:
                    if now - self.last_reply_time[key] < self.reply_cooldown:
                        print(f"[防重复] 用户{user_id}在群{group_id}的回复冷却中，跳过")
                        return None
                self.last_reply_time[key] = now

            # ========== AI聊天 ==========
            # 获取原始消息（用于图片检测）
            raw_message = data.get("message", "")
            return await self._handle_ai_chat(text, user_id, message_type, group_id, raw_message)
    
        except Exception as e:
            print(f"[错误] handle_message异常: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _create_reply(self, message_type, message, user_id=None, group_id=None):
        """创建回复消息"""
        params = {
            "message_type": message_type,
            "message": message
        }
        
        if message_type == "private" and user_id:
            params["user_id"] = user_id
        elif message_type == "group" and group_id:
            params["group_id"] = group_id
        
        return {
            "action": "send_msg",
            "params": params
        }

# ==================== 主程序 ====================
async def run_bot():
    """运行机器人"""
    uri = "ws://127.0.0.1:8765"
    handler = MessageHandler()
    
    logger.info("🤖 QQ机器人启动")
    logger.info(f" 连接: {uri}")
    logger.info(" 规则: 私聊直接发，群聊需要@机器人")
    
    while True:
        try:
            logger.info("正在连接LLOneBot...")
            
            async with websockets.connect(uri) as websocket:
                logger.info("✅ 连接成功")
                
                while True:
                    try:
                        raw_data = await websocket.recv()
                        data = json.loads(raw_data)
                        
                        # 处理消息
                        if data.get("post_type") == "message":
                            if handler.should_reply(data):
                                reply = await handler.handle_message(data)
                                if reply:
                                    await websocket.send(json.dumps(reply))
                                    reply_text = reply["params"]["message"]
                                    logger.info(f"📤 已回复: {reply_text[:50]}...")
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON解析失败: {e}")
                    except Exception as e:
                        logger.error(f"处理消息异常: {e}")
                        
        except ConnectionRefusedError:
            logger.error("❌ 连接被拒绝，5秒后重试...")
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"连接异常: {e}, 5秒后重试...")
            await asyncio.sleep(5)

# ==================== 启动 ====================
async def main():
    print("=" * 60)
    print("🤖 QQ AI机器人 - 稳定修复版")
    print("=" * 60)
    print("功能:")
    print("  ✅ AI对话 (Ollama)")
    print("  ✅ 防撤回")
    print("  ✅ 黑名单系统")
    print("  ✅ 骂人功能 (关键词触发)")
    print("  ✅ 刷屏检测")
    print("=" * 60)
    
    await run_bot()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 程序停止")
    except Exception as e:
        logger.error(f"💥 程序崩溃: {e}")
        input("按Enter键退出...")
