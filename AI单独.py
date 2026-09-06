"""
精简QQ机器人 - 纯AI对话，无指令
只在群 1009018182 启用

模型：gemma4:31b-cloud
基于 OneBot 协议 (NapCat) - 端口 5678
"""
import os
# ========== 强制切换到脚本所在目录 ==========
os.chdir(os.path.dirname(os.path.abspath(__file__)))
print(f"[启动] 工作目录已切换到: {os.getcwd()}")
# ===========================================
import os
import builtins
import os
import sys
import json
import asyncio
import time
import re
import logging
from typing import Optional, Dict
from datetime import datetime

import websockets
import aiohttp

# ==================== 配置 ====================
TARGET_GROUP = "1009018182"  # 只在这个群启用
WEBSOCKET_PORT = 5678        # WebSocket 端口
AI_MODEL = "gemma4:31b-cloud"  # 使用的模型

# ==================== 日志配置 ====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

# ==================== 控制台彩色输出 ====================
class ConsoleColors:
    """控制台颜色"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    # 添加 WHITE 别名
    WHITE = '\033[97m'
    PURPLE = '\033[95m'

def print_message(data: Dict):
    """美化打印消息到控制台"""
    try:
        # 只处理消息事件
        if data.get("post_type") != "message":
            return
        
        msg_type = data.get("message_type", "unknown")
        time_str = datetime.now().strftime("%H:%M:%S")
        
        # 获取消息内容
        raw_msg = data.get("message", "")
        text = ""
        if isinstance(raw_msg, list):
            for seg in raw_msg:
                if seg.get("type") == "text":
                    text += seg.get("data", {}).get("text", "")
                elif seg.get("type") == "image":
                    text += "[图片]"
                elif seg.get("type") == "at":
                    qq = seg.get("data", {}).get("qq", "")
                    text += f"@{qq} "
        elif isinstance(raw_msg, str):
            text = raw_msg
        
        # 获取发送者信息
        user_id = data.get("user_id", "")
        
        if msg_type == "group":
            group_id = data.get("group_id", "")
            sender = data.get("sender", {})
            nickname = sender.get("nickname", user_id)
            
            print(f"\n{ConsoleColors.BLUE}┌───── 群消息 ─────{ConsoleColors.END}")
            print(f"{ConsoleColors.CYAN}│ 时间: {time_str}{ConsoleColors.END}")
            print(f"{ConsoleColors.GREEN}│ 群号: {group_id}{ConsoleColors.END}")
            print(f"{ConsoleColors.YELLOW}│ 发送者: {nickname} ({user_id}){ConsoleColors.END}")
            print(f"{ConsoleColors.WHITE}│ 内容: {text}{ConsoleColors.END}")
            
            # 检查是否包含图片等
            if isinstance(raw_msg, list):
                for seg in raw_msg:
                    if seg.get("type") == "image":
                        url = seg.get("data", {}).get("url", "")
                        if url:
                            print(f"{ConsoleColors.PURPLE}│ 图片: {url[:50]}...{ConsoleColors.END}")
            
            print(f"{ConsoleColors.BLUE}└─────────────────{ConsoleColors.END}")
            
        elif msg_type == "private":
            sender = data.get("sender", {})
            nickname = sender.get("nickname", user_id)
            
            print(f"\n{ConsoleColors.BLUE}┌───── 私聊消息 ─────{ConsoleColors.END}")
            print(f"{ConsoleColors.CYAN}│ 时间: {time_str}{ConsoleColors.END}")
            print(f"{ConsoleColors.YELLOW}│ 发送者: {nickname} ({user_id}){ConsoleColors.END}")
            print(f"{ConsoleColors.WHITE}│ 内容: {text}{ConsoleColors.END}")
            print(f"{ConsoleColors.BLUE}└─────────────────{ConsoleColors.END}")
        
    except Exception as e:
        logger.error(f"打印消息失败: {e}")

# ==================== AI 模块 ====================

class AIMemoryModule:
    """记忆模块"""
    def __init__(self, max_history=10):
        self.memory = {}
        self.max_history = max_history
    
    def get_conversation_context(self, user_id: str, message: str) -> str:
        if user_id not in self.memory:
            return message
        
        history = self.memory[user_id]
        context = "\n".join(history[-5:])
        return f"历史对话:\n{context}\n用户: {message}"
    
    def add_conversation(self, user_id: str, q: str, a: str):
        if user_id not in self.memory:
            self.memory[user_id] = []
        
        self.memory[user_id].append(f"用户: {q}")
        self.memory[user_id].append(f"助手: {a}")
        
        if len(self.memory[user_id]) > self.max_history * 2:
            self.memory[user_id] = self.memory[user_id][-self.max_history * 2:]


class OllamaAI:
    """Ollama AI - 锁死温柔姐姐性格，使用 gemma4:31b-cloud"""
    
    def __init__(self):
        self.base_url = "http://127.0.0.1:11434"
        self.model = AI_MODEL  # 固定使用 gemma4:31b-cloud
        
        # 记忆模块
        self.memory_module = AIMemoryModule()
        
        # ===== 锁死温柔姐姐性格 =====
        self.system_prompt = """你是一个温柔体贴的大姐姐，说话轻声细语，给人温暖的感觉。
你的特点：
- 说话温柔，语气亲切
- 善解人意，会安慰人
- 用「呢」「哦」「呀」等语气词
- 给人姐姐般的温暖和安全感
- 回复简洁但充满关怀"""

        logger.info(f"AI模块初始化完成，模型: {self.model}")
        logger.info("🎀 性格已锁死: 温柔姐姐")
    
    async def chat(self, message, user_id: str = None) -> str:
        """AI对话"""
        try:
            # 提取文本
            if isinstance(message, list):
                message_str = self._convert_message_to_string(message)
            else:
                message_str = str(message)
            
            # 构建消息 - 始终使用温柔姐姐
            messages = [
                {"role": "system", "content": self.system_prompt}
            ]
            
            # 记忆上下文
            if user_id:
                context = self.memory_module.get_conversation_context(user_id, message_str)
                messages.append({"role": "user", "content": context})
            else:
                messages.append({"role": "user", "content": message_str})
            
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.8,
                    "top_p": 0.9,
                    "num_predict": 300
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=60  # 大模型需要更长时间
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        reply = data.get("message", {}).get("content", "").strip()
                        
                        if reply:
                            # ===== 在回复结尾自然加上"喵~" =====
                            reply = reply.rstrip()
                            if reply and reply[-1] in "。.!！?？":
                                reply = reply + "喵~"
                            else:
                                reply = reply + "喵~"
                            
                            # 保存记忆
                            if user_id:
                                self.memory_module.add_conversation(user_id, message_str, reply)
                            return reply
                        else:
                            return "嗯？没听清呢，能再说一遍吗喵?"
                    else:
                        logger.error(f"AI返回错误: {resp.status}")
                        return "💕 抱歉呢，AI暂时有点累，稍后再试试吧喵~"
                        
        except asyncio.TimeoutError:
            logger.error("AI请求超时")
            return "⏰ 等了好久呢，可能网络有点慢喵"
        except Exception as e:
            logger.error(f"AI调用失败: {e}")
            return "💕 哎呀，出了点小问题呢，稍后再说吧喵~"
    
    def _convert_message_to_string(self, message_list: list) -> str:
        result = ""
        for segment in message_list:
            if isinstance(segment, dict):
                seg_type = segment.get("type", "")
                data = segment.get("data", {})
                if seg_type == "text":
                    result += data.get("text", "")
                elif seg_type == "at":
                    qq = data.get("qq", "")
                    result += f"@{qq} " if qq else "@"
                elif seg_type == "image":
                    result += "[图片]"
            elif isinstance(segment, str):
                result += segment
        return result.strip()


# ==================== 消息处理器 ====================
class MessageHandler:
    """消息处理 - 纯AI对话，无指令"""
    
    def __init__(self):
        self.ai = OllamaAI()
        self.bot_self_id = None
        self.websocket = None
        self.target_group = TARGET_GROUP
        
        # 冷却记录
        self.user_cooldowns = {}
        self.cooldown_time = 2
        
        logger.info(f"消息处理器初始化完成，目标群: {self.target_group}")
        logger.info(f"AI模型: {self.ai.model}")
    
    def set_bot_id(self, bot_id: str):
        self.bot_self_id = bot_id
        logger.info(f"机器人ID已设置: {bot_id}")
    
    def is_target_group(self, group_id) -> bool:
        return str(group_id) == self.target_group
    
    def is_at_bot(self, data: Dict) -> bool:
        """检查是否@了机器人"""
        if not self.bot_self_id:
            return False
        
        raw_message = data.get("message", "")
        bot_qq = str(self.bot_self_id)
        
        if isinstance(raw_message, str):
            if f"[CQ:at,qq={bot_qq}]" in raw_message:
                return True
            if f"@{bot_qq}" in raw_message:
                return True
            if f"<@{bot_qq}>" in raw_message:
                return True
        
        if isinstance(raw_message, list):
            for seg in raw_message:
                if seg.get("type") == "at":
                    if str(seg.get("data", {}).get("qq", "")) == bot_qq:
                        return True
        
        return False
    
    def extract_text(self, data: Dict) -> str:
        """提取纯文本消息"""
        raw_message = data.get("message", "")
        
        if isinstance(raw_message, str):
            text = re.sub(r'\[CQ:[^\]]+\]', '', raw_message)
            text = re.sub(r'@\d+\s*', '', text)
            return text.strip()
        
        if isinstance(raw_message, list):
            text = ""
            for seg in raw_message:
                if seg.get("type") == "text":
                    text += seg.get("data", {}).get("text", "")
            return text.strip()
        
        return ""
    
    def check_cooldown(self, user_id: str) -> bool:
        """检查用户冷却"""
        now = time.time()
        if user_id in self.user_cooldowns:
            if now - self.user_cooldowns[user_id] < self.cooldown_time:
                return False
        self.user_cooldowns[user_id] = now
        return True
    
    async def handle_message(self, data: Dict) -> Optional[Dict]:
        """处理消息 - 只做AI回复"""
        try:
            # 先打印消息到控制台
            print_message(data)
            
            # 只处理消息事件
            if data.get("post_type") != "message":
                return None
            
            # 只处理群消息
            if data.get("message_type") != "group":
                return None
            
            group_id = str(data.get("group_id", ""))
            
            # 只处理目标群
            if not self.is_target_group(group_id):
                return None
            
            user_id = str(data.get("user_id", ""))
            
            # 忽略机器人自己的消息
            if user_id == self.bot_self_id:
                return None
            
            # 检查是否@机器人
            if not self.is_at_bot(data):
                return None
            
            # 提取文本
            text = self.extract_text(data)
            if not text:
                return None
            
            # 冷却检查
            if not self.check_cooldown(user_id):
                return None
            
            logger.info(f"🤖 处理AI请求 - 群{group_id} 用户{user_id}: {text[:50]}...")
            
            # AI对话（温柔姐姐 + gemma4:31b-cloud）
            reply = await self.ai.chat(text, user_id=user_id)
            
            if reply:
                # 确保消息以@开头
                if not reply.startswith("[CQ:at"):
                    reply = f"[CQ:at,qq={user_id}] {reply}"
                
                # 打印回复到控制台
                print(f"\n{ConsoleColors.GREEN}┌───── AI回复 ─────{ConsoleColors.END}")
                print(f"{ConsoleColors.CYAN}│ 时间: {datetime.now().strftime('%H:%M:%S')}{ConsoleColors.END}")
                print(f"{ConsoleColors.YELLOW}│ 回复: {reply}{ConsoleColors.END}")
                print(f"{ConsoleColors.GREEN}└─────────────────{ConsoleColors.END}\n")
                
                return {
                    "action": "send_msg",
                    "params": {
                        "message_type": "group",
                        "group_id": int(group_id),
                        "message": reply
                    }
                }
            
            return None
            
        except Exception as e:
            logger.error(f"处理消息异常: {e}")
            return None


# ==================== 主程序 ====================
class QQBot:
    def __init__(self):
        self.handler = MessageHandler()
        self.websocket = None
        self.running = True
    
    async def connect(self):
        uri = f"ws://127.0.0.1:{WEBSOCKET_PORT}"
        
        while self.running:
            try:
                logger.info(f"正在连接 WebSocket: {uri}")
                async with websockets.connect(uri) as websocket:
                    self.websocket = websocket
                    self.handler.websocket = websocket
                    
                    # 获取机器人ID
                    try:
                        hello = await asyncio.wait_for(websocket.recv(), timeout=5)
                        hello_data = json.loads(hello)
                        if hello_data.get("post_type") == "meta_event":
                            bot_id = str(hello_data.get("self_id", ""))
                            if bot_id:
                                self.handler.set_bot_id(bot_id)
                    except Exception as e:
                        logger.warning(f"获取机器人ID失败: {e}")
                    
                    logger.info(f"✅ WebSocket 连接成功！端口: {WEBSOCKET_PORT}")
                    logger.info(f"📌 监听群: {TARGET_GROUP}")
                    logger.info(f"🎀 性格: 温柔姐姐 (已锁死)")
                    logger.info(f"🧠 模型: {AI_MODEL}")
                    logger.info("💡 只有 @机器人 才会回复，无任何指令")
                    
                    await self.message_loop()
                    
            except ConnectionRefusedError:
                logger.warning(f"❌ 连接被拒绝，请确保 NapCat 已启动并监听端口 {WEBSOCKET_PORT}")
                await asyncio.sleep(5)
            except websockets.ConnectionClosed:
                logger.warning("连接断开，5秒后重连...")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"连接异常: {e}")
                await asyncio.sleep(5)
    
    async def message_loop(self):
        while self.running:
            try:
                raw = await asyncio.wait_for(self.websocket.recv(), timeout=1)
                data = json.loads(raw)
                
                # 处理API响应
                if "echo" in data:
                    continue
                
                # 处理消息
                reply = await self.handler.handle_message(data)
                if reply:
                    await self.websocket.send(json.dumps(reply))
                    logger.info("✅ 已发送回复")
                    
            except asyncio.TimeoutError:
                continue
            except websockets.ConnectionClosed:
                logger.warning("WebSocket 连接已关闭")
                break
            except json.JSONDecodeError:
                continue
            except Exception as e:
                logger.error(f"消息循环异常: {e}")
                await asyncio.sleep(1)
    
    async def run(self):
        logger.info("=" * 50)
        logger.info("💕 AI机器人启动")
        logger.info(f"📌 目标群: {TARGET_GROUP}")
        logger.info(f"🔌 WebSocket: ws://127.0.0.1:{WEBSOCKET_PORT}")
        logger.info(f"🧠 模型: {AI_MODEL}")
        logger.info("🎀 性格: 已锁死")
        logger.info("💡 无任何指令，只有 AI 对话")
        logger.info("=" * 50)
        
        try:
            await self.connect()
        except KeyboardInterrupt:
            logger.info("收到退出信号")
        finally:
            self.running = False
            if self.websocket:
                await self.websocket.close()


def main():
    try:
        bot = QQBot()
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print("\n程序已退出")
    except Exception as e:
        print(f"程序异常: {e}")
        import traceback
        traceback.print_exc()
        input("按回车键退出...")

if __name__ == "__main__":
    main()
