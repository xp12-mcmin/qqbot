"""
独立防撤回模块 - 启动即运行版
功能：保护机器人在指定群的消息不被撤回，自动重发
配置：直接修改下面的 CONFIG 字典
"""

import asyncio
import websockets
import json
import time
from datetime import datetime

# ==================== 配置区域（直接修改这里）====================
CONFIG = {
    # LLOneBot WebSocket 地址
    "ws_url": "ws://127.0.0.1:5678",
    
    # 是否启用防撤回（True=开启，False=关闭）
    "enabled": True,
    
    # 需要保护的群列表（机器人在这些群的消息被撤回时会重发）
    "protected_groups": [
        "170569687",  # 群1
        # "123456789",  # 群2（取消注释即可添加）
        # "987654321",  # 群3
    ],
    
    # 是否打印所有消息（True=打印，False=不打印）
    "print_all_messages": True,
    
    # 是否打印撤回事件
    "print_recall_events": True,
}
# ================================================================

class AntiRecall:
    def __init__(self):
        self.message_cache = {}
        self.bot_self_id = None
        self.enabled = CONFIG["enabled"]
        self.running = True
        self.protected_groups = CONFIG["protected_groups"]
        self.print_all = CONFIG["print_all_messages"]
        self.print_recall = CONFIG["print_recall_events"]
    
    def log(self, msg, level="INFO"):
        time_str = datetime.now().strftime("%H:%M:%S")
        print(f"[{time_str}] [{level}] {msg}")
    
    def format_message(self, data):
        """格式化消息内容"""
        try:
            raw_msg = data.get("message", "")
            if isinstance(raw_msg, list):
                text_parts = []
                for seg in raw_msg:
                    if seg.get("type") == "text":
                        text_parts.append(seg.get("data", {}).get("text", ""))
                    elif seg.get("type") == "image":
                        text_parts.append("[图片]")
                    elif seg.get("type") == "face":
                        text_parts.append("[表情]")
                    elif seg.get("type") == "at":
                        text_parts.append(f"@{seg.get('data', {}).get('qq', '')}")
                return "".join(text_parts)
            return str(raw_msg)
        except:
            return "解析失败"
    
    async def send_message(self, websocket, group_id, message):
        """发送群消息"""
        try:
            await websocket.send(json.dumps({
                "action": "send_msg",
                "params": {
                    "message_type": "group",
                    "group_id": int(group_id),
                    "message": message
                }
            }))
            return True
        except Exception as e:
            self.log(f"发送失败: {e}", "ERROR")
            return False
    
    async def handle_message(self, websocket, data):
        """处理消息"""
        try:
            if data.get("post_type") != "message":
                return
            
            msg_type = data.get("message_type")
            group_id = str(data.get("group_id")) if msg_type == "group" else None
            
            # 打印消息（如果开启）
            if self.print_all:
                nickname = data.get("sender", {}).get("nickname", "未知")
                user_id = data.get("user_id")
                content = self.format_message(data)
                
                if msg_type == "group":
                    self.log(f"📩 [群:{group_id}] {nickname}({user_id}): {content[:100]}")
                elif msg_type == "private":
                    self.log(f"💬 [私聊] {nickname}({user_id}): {content[:100]}")
            
            # 只缓存机器人自己的消息（用于防撤回）
            if msg_type != "group":
                return
            
            if group_id not in self.protected_groups:
                return
            
            sender_id = str(data.get("user_id"))
            message_id = data.get("message_id")
            
            if self.bot_self_id and sender_id == self.bot_self_id:
                content = self.format_message(data)
                self.message_cache[message_id] = {
                    "group_id": group_id,
                    "content": content,
                    "time": time.time()
                }
                self.log(f"💾 缓存机器人消息: {content[:50]}...")
                
                # 清理旧缓存
                self._cleanup_cache()
                
        except Exception as e:
            self.log(f"处理消息失败: {e}", "ERROR")
    
    def _cleanup_cache(self):
        """清理超过5分钟的缓存"""
        current_time = time.time()
        to_delete = [mid for mid, msg in self.message_cache.items() 
                     if current_time - msg["time"] > 300]
        for mid in to_delete:
            del self.message_cache[mid]
    
    async def handle_recall(self, websocket, data):
        """处理撤回事件"""
        if not self.enabled:
            return
        
        try:
            if data.get("post_type") != "notice":
                return
            if data.get("notice_type") != "group_recall":
                return
            
            group_id = str(data.get("group_id"))
            
            if group_id not in self.protected_groups:
                return
            
            message_id = data.get("message_id")
            operator_id = str(data.get("operator_id", ""))
            
            if self.print_recall:
                self.log(f"⚠️ [撤回] 群:{group_id} 操作者:{operator_id}")
            
            if message_id not in self.message_cache:
                return
            
            msg = self.message_cache[message_id]
            
            if self.bot_self_id and operator_id == self.bot_self_id:
                self.log(f"机器人自己撤回，跳过")
                return
            
            self.log(f"🚨 机器人消息被撤回！群:{group_id}")
            self.log(f"📝 原消息: {msg['content'][:100]}...")
            
            revenge_msg = f"[防撤回] 管理员 {operator_id} 撤回了我的消息：\n{msg['content']}"
            await self.send_message(websocket, int(group_id), revenge_msg)
            self.log(f"✅ 已重发")
            
            del self.message_cache[message_id]
            
        except Exception as e:
            self.log(f"处理撤回失败: {e}", "ERROR")
    
    async def run(self):
        """主运行循环"""
        self.log(f"防撤回模块启动")
        self.log(f"保护群: {', '.join(self.protected_groups) if self.protected_groups else '无'}")
        self.log(f"打印消息: {'开启' if self.print_all else '关闭'}")
        
        while self.running:
            try:
                self.log(f"正在连接 {CONFIG['ws_url']}...")
                async with websockets.connect(CONFIG['ws_url']) as websocket:
                    self.log("连接成功！开始监听...")
                    
                    # 获取机器人ID
                    try:
                        init_msg = await asyncio.wait_for(websocket.recv(), timeout=5)
                        data = json.loads(init_msg)
                        if data.get("post_type") == "meta_event":
                            self.bot_self_id = str(data.get("self_id", ""))
                            self.log(f"机器人ID: {self.bot_self_id}")
                    except:
                        pass
                    
                    # 消息循环
                    async for raw_msg in websocket:
                        try:
                            data = json.loads(raw_msg)
                            await self.handle_message(websocket, data)
                            await self.handle_recall(websocket, data)
                        except Exception as e:
                            self.log(f"处理异常: {e}", "ERROR")
                    
            except ConnectionRefusedError:
                self.log(f"连接失败！请确保 LLOneBot 已启动，端口正确", "ERROR")
                await asyncio.sleep(5)
            except Exception as e:
                self.log(f"连接异常: {e}", "ERROR")
                await asyncio.sleep(5)

# ==================== 启动 ====================
if __name__ == "__main__":
    print("="*60)
    print("       独立防撤回模块")
    print("="*60)
    print(f"启动即运行，修改代码中的 CONFIG 来配置")
    print(f"当前配置:")
    print(f"  WebSocket: {CONFIG['ws_url']}")
    print(f"  防撤回开关: {'开启' if CONFIG['enabled'] else '关闭'}")
    print(f"  保护群: {CONFIG['protected_groups']}")
    print(f"  打印消息: {'开启' if CONFIG['print_all_messages'] else '关闭'}")
    print("="*60)
    
    asyncio.run(AntiRecall().run())
