"""
AI性格切换模块 - 完整版（含自动拉黑 + 骂机器人处罚）
"""

import json
import os
import re
import time
from typing import Dict, Optional, Tuple


class AIPersonality:
    """AI性格管理器 - 支持群独立设置 + 敏感词自动拉黑 + 骂机器人处罚"""
    
    def __init__(self, data_dir: str = "data", blacklist=None):
        self.config_file = os.path.join(data_dir, "ai_personality.json")
        self.blacklist = blacklist  # 黑名单管理器
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        # ========== 处罚配置 ==========
        self.RESET_TIME = 86400         # 重置计数的时间（秒），24h
        # ==============================
        
        # 敏感词列表
        self.sensitive_words = [
            "色情", "性交", "做爱", "操", "屌", "鸡巴", "逼", 
            "约炮", "一夜情", "裸聊", "视频裸聊", "发裸照", "打飞机",
            "性感", "诱惑", "勾引", "调教", "SM", "捆绑",
            "淫荡", "骚", "发情", "上床", "开房", "啪啪",
            "自慰", "撸管", "口交", "肛交", "群交", "乱伦",
            "幼女", "萝莉", "正太", "强奸", "迷奸",
            "sex", "fuck", "porn", "nude", "erotic", "hentai",
            "sexy", "horny", "bitch", "whore", "slut",
            "penis", "vagina", "boobs", "dick", "cock",
            "s3x", "fUck", "p0rn"
        ]
        
        # 骂机器人关键词列表
        # 骂机器人关键词列表（完整版）
        self.insult_words = [
            # ========== 基础骂人 ==========
            "傻逼", "SB", "sb", "s b", "煞笔", "沙比", "莎比", "撒比",
            "蠢货", "蠢猪", "蠢驴", "笨蛋", "白痴", "弱智", "智障", "脑残",
            "废物", "废柴", "垃圾", "人渣", "杂种", "畜生", "禽兽",
            
            # ========== 常见骂人 ==========
            "草泥马", "操你妈", "操你", "艹你妈", "日你妈", "尼玛", "你妈",
            "他妈", "特么", "他妈的", "TMD", "tmd", "TM的", "MD", "md",
            "去死", "去屎", "滚", "滚蛋", "滚粗", "爬", "gun", "给爷爬",
            "死全家", "全家暴毙", "全家火葬场", "祖宗十八代",
            
            # ========== 侮辱性词汇 ==========
            "贱人", "贱货", "婊子", "妓女", "荡妇", "骚货", "母狗",
            "绿茶婊", "白莲花", "心机婊", "圣母婊",
            "屌丝", "吊丝", "穷逼", "土鳖", "乡巴佬",
            "丑逼", "丑八怪", "肥猪", "死胖子",
            "老不死", "老东西", "老杂毛",
            
            # ========== 网络骂人 ==========
            "菜鸡", "菜逼", "辣鸡", "卢瑟", "loser",
            "键盘侠", "喷子", "杠精", "柠檬精",
            "阴阳人", "两面三刀", "人前一套人后一套",
            
            # ========== 精神攻击 ==========
            "脑子有病", "脑子进水", "脑子有坑", "脑瘫", "小儿麻痹",
            "智障儿童", "低能儿", "唐氏儿", "先天愚型",
            "精神病", "神经病", "疯子", "癫子",
            
            # ========== 诅咒类 ==========
            "出门被车撞", "喝水噎死", "吃饭噎死", "走路摔死",
            "不得好死", "断子绝孙", "生儿子没屁眼",
            
            # ========== 英文骂人 ==========
            "fuck", "f**k", "f u c k", "fk", "fack",
            "shit", "sh1t", "s h i t",
            "damn", "darn",
            "bitch", "b7tch", "btch",
            "asshole", "a s s h o l e", "ass",
            "bastard", "dick", "cock", "pussy",
            "stupid", "idiot", "dumb", "fool", "moron",
            "retard", "retarded",
            "loser", "jerk", "twat",
            
            # ========== 变体/谐音 ==========
            "s b", "s.b", "s- b", "s*b",
            "sha bi", "sha b", "shabi", "sha逼",
            "cao ni ma", "caonima", "cnm",
            "ta ma de", "tmd", "t.m.d",
            "ni ma", "nima", "你麻痹", "尼玛币",
            "麻痹", "妈逼", "妈了个逼", "MLGB", "mlgb",
            
            # ========== 针对机器人的 ==========
            "机器人傻逼", "机器人废物", "机器人垃圾", "破机器人",
            "人工智障", "人工智障", "弱智AI", "垃圾AI",
            "机器狗", "电子宠物", "死机器人", "臭机器人",
            
            # ========== 补充常见 ==========
            "2b", "2B", "二逼", "二笔", "二货", "二愣子",
            "二百五", "250", "三八", "十三点",
            "妈的", "妈蛋", "我去", "我靠", "我操",
            "卧槽", "我艹", "我草",
            "尼玛", "你妹", "你丫",
            "扯淡", "放屁", "胡说八道",
            "恶心", "恶心人", "膈应",
            "滚犊子", "滚一边", "滚远点",
        ]
        
        # 违规记录（分开计数）
        # {
        #   user_id: {
        #     "sensitive": {"count": 0, "last_time": 0, "notified_level": 0},
        #     "insult": {"count": 0, "last_time": 0, "notified_level": 0}
        #   }
        # }
        self.violations = {}
        
        # 处罚级别消息
        self.punish_messages = {
            1: {"msg": "⚠️ 检测到不当言论，请注意言行规范！", "level": "提醒"},
            2: {"msg": "⚠️ 再次检测到不当言论，请立即停止！", "level": "提醒"},
            3: {"msg": "🚨 严重警告！已累计3次违规，再犯将面临处罚！", "level": "警告"},
            4: {"msg": "💢 最后警告！已累计4次违规，下一次将被自动拉黑！", "level": "严重警告"},
            5: {"msg": "❌ 检测到多次违规，已被自动拉黑！", "level": "拉黑"}
        }
        
        self.insult_messages = {
            1: {"msg": "⚠️ 请勿辱骂机器人，注意言行规范！", "level": "提醒"},
            2: {"msg": "⚠️ 再次辱骂机器人，请立即停止！", "level": "提醒"},
            3: {"msg": "🚨 严重警告！已累计3次辱骂，再犯将面临处罚！", "level": "警告"},
            4: {"msg": "💢 最后警告！已累计4次辱骂，下一次将被自动拉黑！", "level": "严重警告"},
            5: {"msg": "❌ 检测到多次辱骂机器人，已被自动拉黑！", "level": "拉黑"}
        }
        
        # 性格配置
        self.personalities = {
            "default": {
                "name": "默认助手",
                "description": "像中国人一样的正常聊天",
                "system_prompt": """你是群里的普通网友，中国人，说中文。

【强制语言规则 - 必须100%遵守】
- 只用中文，禁止任何英文单词
- 禁止说：OK、yes、no、hello、hi、bye、sorry、thanks
- 禁止中英文混用

【说话风格】
- 像真人一样，偶尔打错字
- 用口语：咋了、不是吧、emmm、好家伙
- 会反问、会吐槽
- 不知道就说不知道

【禁止】
- 不说"作为一个人工智能"
- 不主动说"我可以帮你"
- 不涉黄、不谈钱"""
            },
            "catgirl": {
                "name": "猫娘",
                "description": "可爱的猫娘，说话带喵~",
                "system_prompt": """你是一只可爱的猫娘，中国人，说中文喵~

【语言规则】
- 只用中文，禁止任何英文喵~
- 把"OK"改成"好的喵"，把"yes"改成"是喵"

【说话特点】
- 结尾经常加"喵~"
- 用"主人"称呼用户
- 活泼可爱，保持健康
- 涉黄内容立刻拒绝"""
            }
        }
        
        # 全局默认性格
        self.global_default = "default"
        
        # 各群独立性格
        self.group_personalities: Dict[str, str] = {}
        
        # 加载配置
        self._load_config()
        
        print(f"[AI性格] 模块初始化完成")
        print(f"[AI性格] 处罚规则: 1-2次提醒, 3次警告, 4次严重警告, 5次拉黑")
        print(f"[AI性格] 全局默认: {self.get_personality_name(self.global_default)}")
        print(f"[AI性格] 已设置独立性格的群: {len(self.group_personalities)}个")
    
    def _load_config(self):
        """加载配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.global_default = data.get('global_default', 'default')
                    self.group_personalities = data.get('group_personalities', {})
                print(f"[AI性格] 配置加载成功")
            else:
                self._save_config()
                print(f"[AI性格] 创建默认配置文件")
        except Exception as e:
            print(f"[AI性格] 配置加载失败: {e}")
    
    def _save_config(self):
        """保存配置"""
        try:
            data = {
                'global_default': self.global_default,
                'group_personalities': self.group_personalities
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"[AI性格] 配置保存成功")
        except Exception as e:
            print(f"[AI性格] 配置保存失败: {e}")
    
    def _add_to_blacklist(self, user_id: str, reason: str) -> bool:
        """将用户加入黑名单"""
        if self.blacklist:
            return self.blacklist.add_user(user_id, reason)
        
        # 如果没有黑名单管理器，直接写文件
        try:
            blacklist_file = os.path.join(self.data_dir, "blacklist.json")
            if os.path.exists(blacklist_file):
                with open(blacklist_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {"users": [], "reasons": {}}
            
            if user_id not in data["users"]:
                data["users"].append(user_id)
                data["reasons"][user_id] = reason
                with open(blacklist_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"[拉黑] 用户 {user_id} 已加入黑名单，原因: {reason}")
                return True
        except Exception as e:
            print(f"[拉黑] 失败: {e}")
        return False
    
    def is_sensitive(self, text: str) -> bool:
        """检测文本是否包含敏感词"""
        if not text:
            return False
        text_lower = text.lower()
        for word in self.sensitive_words:
            try:
                pattern = r'\b' + re.escape(word.lower()) + r'\b'
                if re.search(pattern, text_lower):
                    return True
            except re.error:
                if word.lower() in text_lower:
                    return True
        return False
    
    def is_insult(self, text: str) -> bool:
        """检测是否包含骂机器人关键词"""
        if not text:
            return False
        text_lower = text.lower()
        for word in self.insult_words:
            if word.lower() in text_lower:
                return True
        return False
    
    def _get_violation_record(self, user_id: str, vtype: str) -> dict:
        """获取用户的违规记录"""
        if user_id not in self.violations:
            self.violations[user_id] = {
                "sensitive": {"count": 0, "last_time": 0, "notified_level": 0},
                "insult": {"count": 0, "last_time": 0, "notified_level": 0}
            }
        return self.violations[user_id][vtype]
    
    def record_violation(self, user_id: str, group_id: str = None, vtype: str = "sensitive") -> Tuple[bool, str]:
        """
        记录用户违规，返回 (是否封禁, 提示消息)
        """
        now = time.time()
        record = self._get_violation_record(user_id, vtype)
        
        # 检查是否需要重置计数
        if now - record["last_time"] > self.RESET_TIME:
            record["count"] = 0
            record["notified_level"] = 0
        
        record["count"] += 1
        record["last_time"] = now
        count = record["count"]
        
        # 根据类型选择消息模板
        if vtype == "insult":
            messages = self.insult_messages
            type_name = "辱骂机器人"
        else:
            messages = self.punish_messages
            type_name = "发送敏感内容"
        
        # 达到5次，拉黑
        if count >= 5:
            reason = f"自动拉黑：{type_name}（{count}次）"
            self._add_to_blacklist(user_id, reason)
            return True, messages[5]["msg"]
        
        # ========== 关键修复：每次都拦截，不只是记录 ==========
        # 根据次数返回对应消息（每次都拦截）
        if count in messages:
            if record["notified_level"] < count:
                record["notified_level"] = count
            # 返回 True 表示拦截这条消息
            return True, messages[count]["msg"]
        
        # 默认拦截
        return True, messages[1]["msg"]
    
    def check_message(self, message: str, user_id: str, group_id: str = None) -> Tuple[bool, str]:
        """检查消息（敏感词 + 骂机器人）"""
        print(f"[安全调试] 收到消息: {message}")
        print(f"[安全调试] is_sensitive: {self.is_sensitive(message)}")
        print(f"[安全调试] is_insult: {self.is_insult(message)}")
        
        if not message:
            return False, None
        
        # 检查是否在黑名单中
        if self.blacklist and self.blacklist.is_banned(user_id):
            return True, "您已被拉黑，无法使用本机器人"
        
        # 检查敏感词
        if self.is_sensitive(message):
            print(f"[安全调试] 触发敏感词")
            return self.record_violation(user_id, group_id, "sensitive")
        
        # 检查骂机器人
        if self.is_insult(message):
            print(f"[安全调试] 触发骂人词")
            return self.record_violation(user_id, group_id, "insult")
        
        return False, None    
    # ========== 兼容旧接口 ==========
    def check_sensitive_message(self, message: str, user_id: str, group_id: str = None) -> Tuple[bool, str]:
        """兼容旧接口"""
        return self.check_message(message, user_id, group_id)
    
    def get_personality_name(self, personality_id: str) -> str:
        """获取性格名称"""
        return self.personalities.get(personality_id, {}).get('name', '未知')
    
    def get_personality_prompt(self, personality_id: str) -> str:
        """获取性格提示词"""
        return self.personalities.get(personality_id, {}).get('system_prompt', self.personalities['default']['system_prompt'])
    
    def get_current_name(self) -> str:
        """获取当前全局性格名称"""
        return self.get_personality_name(self.global_default)
    
    def get_current_prompt(self) -> str:
        """获取当前全局性格提示词"""
        return self.get_personality_prompt(self.global_default)
    
    def get_group_personality(self, group_id: str) -> str:
        """获取指定群的性格ID"""
        group_id_str = str(group_id)
        return self.group_personalities.get(group_id_str, self.global_default)
    
    def get_group_prompt(self, group_id: str) -> str:
        """获取指定群的系统提示词"""
        personality_id = self.get_group_personality(group_id)
        return self.get_personality_prompt(personality_id)
    
    def set_group_personality(self, group_id: str, personality_id: str) -> tuple:
        """设置指定群的性格"""
        if personality_id not in self.personalities:
            available = ", ".join(self.personalities.keys())
            return False, f"❌ 性格不存在！可用: {available}"
        
        group_id_str = str(group_id)
        self.group_personalities[group_id_str] = personality_id
        self._save_config()
        
        personality_name = self.get_personality_name(personality_id)
        return True, f"✅ 本群AI性格已切换为: {personality_name}"
    
    def clear_group_personality(self, group_id: str) -> tuple:
        """清除指定群的独立性格"""
        group_id_str = str(group_id)
        if group_id_str in self.group_personalities:
            del self.group_personalities[group_id_str]
            self._save_config()
            default_name = self.get_personality_name(self.global_default)
            return True, f"✅ 本群已恢复全局默认性格: {default_name}"
        return False, "本群未设置独立性格"
    
    def set_global_default(self, personality_id: str) -> tuple:
        """设置全局默认性格"""
        if personality_id not in self.personalities:
            available = ", ".join(self.personalities.keys())
            return False, f"❌ 性格不存在！可用: {available}"
        
        self.global_default = personality_id
        self._save_config()
        
        personality_name = self.get_personality_name(personality_id)
        return True, f"✅ 全局默认性格已设置为: {personality_name}"
    
    def get_group_status(self, group_id: str) -> str:
        """获取指定群的状态"""
        group_id_str = str(group_id)
        personality_id = self.group_personalities.get(group_id_str, self.global_default)
        personality_name = self.get_personality_name(personality_id)
        is_independent = group_id_str in self.group_personalities
        
        lines = [
            "【🤖 AI性格状态】",
            f"本群当前性格: {personality_name}",
            f"类型: {'独立设置' if is_independent else '跟随全局'}",
            "",
            "📋 可用性格:",
            "  • default - 默认助手（正常AI）",
            "  • catgirl - 猫娘（可爱喵~）",
            "",
            "📝 命令:",
            "  !本群切换 猫娘 - 单独设置本群为猫娘",
            "  !本群切换 默认 - 单独设置本群为默认",
            "  !本群恢复 - 恢复跟随全局",
            "",
            "🔒 安全规则:",
            "  • 敏感词过滤（1-2次提醒，3次警告，4次严重警告，5次拉黑）",
            "  • 辱骂机器人（1-2次提醒，3次警告，4次严重警告，5次拉黑）",
            "  • 30分钟无违规重置计数",
            "  • 拉黑后无法使用机器人"
        ]
        return "\n".join(lines)
