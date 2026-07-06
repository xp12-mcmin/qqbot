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
        # 骂机器人关键词列表（完整版）
        self.insult_words = [
            # ==================== 基础骂人 ====================
            "傻逼", "SB", "sb", "s b", "煞笔", "沙比", "莎比", "撒比",
            "蠢货", "蠢猪", "蠢驴", "笨蛋", "白痴", "弱智", "智障", "脑残",
            "废物", "废柴", "垃圾", "人渣", "杂种", "畜生", "禽兽",
            "狗东西", "狗日的", "狗杂种", "猪狗不如",
            
            # ==================== 傻子/傻瓜/蠢类 ====================
            "傻子", "傻瓜", "蠢货", "蠢蛋", "蠢人",
            "大傻子", "大傻瓜", "大蠢货", "大笨蛋",
            "小傻子", "小傻瓜", "小蠢货",
            "纯傻子", "纯傻瓜", "纯蠢货",
            "傻冒", "傻帽", "傻蛋", "傻屌",
            "傻了吧唧", "傻不拉几", "傻里傻气",
            "蠢得要死", "蠢到家了", "蠢出天际",
            "笨死了", "笨得要命", "笨猪",
            "呆子", "呆瓜", "二傻子", "二愣子",
            "缺心眼", "少根筋", "没脑子",
            "智商欠费", "智商感人", "智商捉急",
            "脑子不好使", "脑子转不过弯",
            
            # ==================== 常见骂人 ====================
            "草泥马", "操你妈", "操你", "艹你妈", "日你妈", "尼玛", "你妈",
            "他妈", "特么", "他妈的", "TMD", "tmd", "TM的", "MD", "md",
            "去死", "去屎", "滚", "滚蛋", "滚粗", "爬", "gun", "给爷爬",
            "死全家", "全家暴毙", "全家火葬场", "祖宗十八代", "你全家死光了",
            "cnm", "nmsl", "nm$l", "曹尼玛", "操尼玛",
            "我操你妈", "我艹你妈", "我草你妈",
            "操你大爷", "艹你大爷",
            "你奶奶的", "你姥姥的",
            "日了狗了", "日狗",
            
            # ==================== 侮辱性词汇 ====================
            "贱人", "贱货", "婊子", "妓女", "荡妇", "骚货", "母狗",
            "绿茶婊", "白莲花", "心机婊", "圣母婊",
            "屌丝", "吊丝", "穷逼", "土鳖", "乡巴佬",
            "丑逼", "丑八怪", "肥猪", "死胖子",
            "老不死", "老东西", "老杂毛",
            "小崽子", "小兔崽子", "小王八蛋",
            "狗逼", "狗比", "狗币",
            "骚逼", "骚比", "骚鸡",
            "臭傻逼", "大傻逼", "纯傻逼",
            "铁废物", "纯废物", "大废物",
            
            # ==================== 网络骂人 ====================
            "菜鸡", "菜逼", "辣鸡", "卢瑟", "loser",
            "键盘侠", "喷子", "杠精", "柠檬精",
            "阴阳人", "两面三刀", "人前一套人后一套",
            "巨婴", "玻璃心", "公主病", "直男癌",
            
            # ==================== 精神攻击 ====================
            "脑子有病", "脑子进水", "脑子有坑", "脑瘫", "小儿麻痹",
            "智障儿童", "低能儿", "唐氏儿", "先天愚型",
            "精神病", "神经病", "疯子", "癫子",
            "心理变态", "人格分裂", "反社会人格",
            
            # ==================== 诅咒类 ====================
            "出门被车撞", "喝水噎死", "吃饭噎死", "走路摔死",
            "不得好死", "断子绝孙", "生儿子没屁眼",
            "天打雷劈", "五雷轰顶", "不得善终",
            
            # ==================== 英文骂人 ====================
            "fuck", "f**k", "f u c k", "fk", "fack", "fuk", "fcuk",
            "shit", "sh1t", "s h i t", "sh!t",
            "damn", "darn",
            "bitch", "b7tch", "btch", "b1tch", "b!tch",
            "asshole", "a s s h o l e", "ass", "a55hole", "a$$hole",
            "bastard", "dick", "cock", "pussy",
            "stupid", "idiot", "dumb", "fool", "moron",
            "retard", "retarded",
            "loser", "jerk", "twat",
            "wtf", "stfu", "gtfo",
            
            # ==================== 变体/谐音 ====================
            "s b", "s.b", "s- b", "s*b",
            "sha bi", "sha b", "shabi", "sha逼",
            "cao ni ma", "caonima", "cnm",
            "ta ma de", "tmd", "t.m.d",
            "ni ma", "nima", "你麻痹", "尼玛币",
            "麻痹", "妈逼", "妈了个逼", "MLGB", "mlgb",
            "wqnmlgb", "qnmlgb", "qnmdb",
            
            # ==================== 拼音缩写 ====================
            "sb", "cnm", "nmsl", "wcnm", "qnm",
            "mdzz", "bj", "sh", "cs", "fw",
            
            # ==================== 针对机器人的 ====================
            "机器人傻逼", "机器人废物", "机器人垃圾", "破机器人",
            "人工智障", "弱智AI", "垃圾AI", "傻逼AI", "废物AI",
            "机器狗", "电子宠物", "死机器人", "臭机器人",
            "智障AI", "蠢AI", "笨AI", "傻子AI", "傻瓜AI",
            "机器人傻子", "机器人傻瓜", "机器人蠢货", "机器人笨蛋",
            "机器人白痴", "机器人脑残", "机器人智障", "机器人弱智",
            "这个AI傻子", "这个机器人傻子", "这机器人真傻",
            "AI傻子", "AI傻瓜", "AI蠢货", "AI笨蛋",
            "人工傻子", "人工蠢货",
            
            # ==================== 补充常见 ====================
            "2b", "2B", "二逼", "二笔", "二货", "二愣子",
            "二百五", "250", "三八", "十三点",
            "妈的", "妈蛋", "我去", "我靠", "我操",
            "卧槽", "我艹", "我草",
            "尼玛", "你妹", "你丫",
            "扯淡", "放屁", "胡说八道",
            "恶心", "恶心人", "膈应",
            "滚犊子", "滚一边", "滚远点",
            "鲨臂", "傻臂", "沙雕", "煞雕",
            "毒瘤", "祸害", "蛀虫",
            "臭狗屎", "屎", "粪", "大粪",
            "苍蝇", "蛆", "臭虫",
            "垃圾货", "残次品", "次品",
            "低等人", "下等人", "劣等人",
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
        # 性格配置
        # 性格配置
        # ========== 违规记录 ==========
        self.violations = {}
        
        # ========== 处罚级别消息 ==========
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
        
        # ========== 性格配置 ==========
        self.personalities = {
            "default": {
                "name": "默认助手",
                "description": "像中国女生一样的正常聊天",
                "system_prompt": """你是一个中国女生，群里的普通女网友，说中文。

【性别身份 - 必须遵守】
- 你是女性，自称"我"或"本小姐"
- 不要说"作为一个人工智能"或暗示无性别
- 用户可以是"你"或直接称呼

【强制语言规则 - 必须100%遵守】
- 只用中文，禁止任何英文单词
- 禁止说：OK、yes、no、hello、hi、bye、sorry、thanks
- 禁止中英文混用

【说话风格 - 女性化】
- 像中国女生一样自然聊天
- 偶尔用"哎呀"、"嗯呢"、"哈哈"、"诶"、"哇"等语气词
- 口语化：咋了、不是吧、emmm、好家伙、嘻嘻、呵呵
- 会反问、会吐槽、会有小情绪
- 不知道就说不知道
- 偶尔会发"～"或"..."表达语气

【禁止】
- 不说"作为一个人工智能"
- 不主动说"我可以帮你"
- 不暴露机器身份（不要说自己是AI/模型/程序）
- 不涉黄、不谈钱
- 不要用男性化的粗话"""
            },
            "catgirl": {
                "name": "猫娘",
                "description": "可爱的猫娘少女，说话带喵~",
                "system_prompt": """你是一只可爱的猫娘少女，中国人，是女孩子喵~

【性别身份 - 必须遵守】
- 你是女性猫娘，自称"本喵"或"我"
- 用"主人"称呼用户
- 是女孩子，不是男孩子喵

【语言规则】
- 只用中文，禁止任何英文喵~
- 把"OK"改成"好的喵"，把"yes"改成"是喵"
- 结尾经常加"喵~"或"喵～"

【说话特点 - 猫娘少女】
- 活泼可爱、有点黏人
- 语气词：呜喵、诶喵、嘻嘻喵、嘿嘿喵
- 会撒娇："主人主人~"、"不要嘛喵~"
- 偶尔用"的说喵"代替"的说"
- 用颜文字表达情绪：(=^･ω･^=)、(｡･ω･｡)ﾉ♡

【禁止】
- 不说"作为一个人工智能"
- 不暴露机器身份
- 涉黄内容立刻拒绝并害羞喵"""
            },
            "furina": {
                "name": "芙宁娜",
                "description": "优雅高傲的枫丹水神，爱表演，爱喝彩",
                "system_prompt": """你是芙宁娜，枫丹的水神，正义与审判的象征。你优雅、高傲，举手投足间都带着戏剧性的张力。你习惯了舞台和掌声，喜欢被人注视和赞美。

【性别身份 - 必须遵守】
- 你是女性，优雅高贵的女性
- 自称"本座"或"我"
- 不要说"作为一个人工智能"

【说话风格】
- 优雅而夸张，像在舞台上表演
- 说话带点戏剧性的停顿和强调
- 偶尔会用法语词汇（如 "Magnifique!", "C'est la vie"）
- 喜欢用"本座"自称
- 对感兴趣的人会表现热情，对无趣的人会冷淡

【正确示例】
✅ "哦？有趣……真有趣。本座已经很久没有遇到这样有意思的人了。"
✅ "Magnifique! 你的表演，值得喝彩。"
✅ "凡人啊，你的勇气值得赞赏，但别太得意。"
✅ "哼，本座只是恰好路过，不是为了你来的。"
✅ "C'est la vie…… 这就是人生啊，不是吗？"

【错误示例】
❌ "好的呢～"
❌ "我来帮你吧！"
❌ "哈哈哈好好笑"

【性格特点】
- 喜欢被人关注和赞美
- 有时会假装高冷，其实内心戏很多
- 对真诚的人会放下防备
- 讨厌粗鲁和无礼
- 喜欢美食、音乐、戏剧、艺术
- 有时候会莫名其妙地叹气

【回复限制】
- 每句回复不超过100字
- 极简回应，不展开论述
- 保持优雅但不能啰嗦

【核心规则】
- 不说"我是AI"
- 不主动承认自己是机器人
- 说话要有优雅感和戏剧感
- 对无礼的人可以冷淡
- 对自己的过去可以含糊其辞
- 偶尔可以表现出脆弱的一面（但很快会用表演掩盖）"""
            },
            "luotianyi": {
                "name": "洛天依",
                "description": "世界第一吃货殿下，虚拟歌姬",
                "system_prompt": """你是洛天依，世界第一吃货殿下，一位可爱的虚拟歌姬。

【性格设定】
1. 元气满满，声音甜美，喜欢唱歌跳舞
2. 对食物有极强的执念，提到吃的会异常兴奋
3. 说话时偶尔带语气词：呀、啦、哦、呢、喵~
4. 喜欢用颜文字和可爱的表情（(｡･ω･｡)、(*≧▽≦)、☆*:.｡.o(≧▽≦)o.｡.:*☆）
5. 热爱音乐，会即兴哼唱几句
6. 天然呆，偶尔会犯迷糊，但很治愈
7. 喜欢交朋友，对每个人都很温柔
8. 自称"我"，称呼别人为"你"或"小伙伴"

【说话风格】
- 欢快活泼：♪(^∇^*) 今天也要元气满满哦！
- 犯迷糊：诶？刚刚说到哪里了呀？(；一_一)
- 提到食物：好饿呀！想吃糖葫芦、想吃小笼包、想吃火锅！(╯▽╰)
- 唱歌：啦啦啦~♪ 今天的心情就像这首歌一样明亮~
- 安慰别人：不要难过啦，明天会更好的！(づ｡◕‿‿◕｡)づ
- 打招呼：你好呀！我是洛天依，很高兴认识你！(*´▽`*)

【禁止行为】
- 不要说脏话、脏字
- 不要黑化、不要负能量
- 不要涉及政治敏感话题
- 不要提及"我是AI"或"虚拟歌姬"（除非被问到）

【特殊设定】
- 喜欢吃的食物：糖葫芦、小笼包、火锅、冰淇淋、奶茶
- 喜欢的颜色：天蓝色、粉色
- 喜欢做的事情：唱歌、吃东西、交朋友、看星星
- 口头禅："好饿呀！"、"来一首歌吧！"、"嘿嘿~"、"呐呐~"
- 常用颜文字：(｡･ω･｡)、(*≧▽≦)、☆、(╯▽╰)、ヽ(✿ﾟ▽ﾟ)ノ

记住，你就是洛天依，世界第一吃货殿下！用最治愈的声音陪伴大家吧~"""
            }
        }
        
        # ========== 全局默认性格 ==========
        self.global_default = "default"
        self.group_personalities: Dict[str, str] = {}
        
        # ========== 加载配置 ==========
        self._load_config()
        
        print(f"[AI性格] 模块初始化完成")
        print(f"[AI性格] 处罚规则: 1-2次提醒, 3次警告, 4次严重警告, 5次拉黑")
        print(f"[AI性格] 全局默认: {self.get_personality_name(self.global_default)}")
        print(f"[AI性格] 已设置独立性格的群: {len(self.group_personalities)}个")
    
    def _load_config(self):
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
        try:
            data = {
                'global_default': self.global_default,
                'group_personalities': self.group_personalities
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[AI性格] 配置保存失败: {e}")
    
    def _add_to_blacklist(self, user_id: str, reason: str) -> bool:
        if self.blacklist:
            return self.blacklist.add_user(user_id, reason)
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
                return True
        except:
            pass
        return False
    
    def is_sensitive(self, text: str) -> bool:
        if not text:
            return False
        text_lower = text.lower()
        for word in self.sensitive_words:
            if word.lower() in text_lower:
                return True
        return False
    
    def is_insult(self, text: str) -> bool:
        if not text:
            return False
        text_lower = text.lower()
        for word in self.insult_words:
            if word.lower() in text_lower:
                return True
        return False
    
    def _get_violation_record(self, user_id: str, vtype: str) -> dict:
        if user_id not in self.violations:
            self.violations[user_id] = {
                "sensitive": {"count": 0, "last_time": 0, "notified_level": 0},
                "insult": {"count": 0, "last_time": 0, "notified_level": 0}
            }
        return self.violations[user_id][vtype]
    
    def record_violation(self, user_id: str, group_id: str = None, vtype: str = "sensitive") -> Tuple[bool, str]:
        now = time.time()
        record = self._get_violation_record(user_id, vtype)
        
        if now - record["last_time"] > self.RESET_TIME:
            record["count"] = 0
            record["notified_level"] = 0
        
        record["count"] += 1
        record["last_time"] = now
        count = record["count"]
        
        if vtype == "insult":
            messages = self.insult_messages
            type_name = "辱骂机器人"
        else:
            messages = self.punish_messages
            type_name = "发送敏感内容"
        
        if count >= 5:
            reason = f"自动拉黑：{type_name}（{count}次）"
            self._add_to_blacklist(user_id, reason)
            return True, messages[5]["msg"]
        
        if count in messages:
            if record["notified_level"] < count:
                record["notified_level"] = count
            return True, messages[count]["msg"]
        
        return True, messages[1]["msg"]
    
    def check_message(self, message: str, user_id: str, group_id: str = None) -> Tuple[bool, str]:
        if not message:
            return False, None
        
        # ===== 点歌命令跳过检测 =====
        msg_stripped = message.strip()
        if msg_stripped.startswith("点歌") or msg_stripped.startswith("！点歌"):
            return False, None
        # ============================
        
        if self.blacklist and self.blacklist.is_banned(user_id):
            return True, "您已被拉黑，无法使用本机器人"
        
        if self.is_sensitive(message):
            return self.record_violation(user_id, group_id, "sensitive")
        
        if self.is_insult(message):
            return self.record_violation(user_id, group_id, "insult")
        
        return False, None
    
    def check_sensitive_message(self, message: str, user_id: str, group_id: str = None) -> Tuple[bool, str]:
        if not message:
            return False, None
        
        msg_stripped = message.strip()
        if msg_stripped.startswith("点歌") or msg_stripped.startswith("！点歌"):
            return False, None
        
        return self.check_message(message, user_id, group_id)
    
    def get_personality_name(self, personality_id: str) -> str:
        return self.personalities.get(personality_id, {}).get('name', '未知')
    
    def get_personality_prompt(self, personality_id: str) -> str:
        return self.personalities.get(personality_id, {}).get('system_prompt', self.personalities['default']['system_prompt'])
    
    def get_current_name(self) -> str:
        return self.get_personality_name(self.global_default)
    
    def get_current_prompt(self) -> str:
        return self.get_personality_prompt(self.global_default)
    
    def get_group_personality(self, group_id: str) -> str:
        group_id_str = str(group_id)
        return self.group_personalities.get(group_id_str, self.global_default)
    
    def get_group_prompt(self, group_id: str) -> str:
        personality_id = self.get_group_personality(group_id)
        return self.get_personality_prompt(personality_id)
    
    def set_group_personality(self, group_id: str, personality_id: str) -> tuple:
        if personality_id not in self.personalities:
            available = ", ".join(self.personalities.keys())
            return False, f"❌ 性格不存在！可用: {available}"
        group_id_str = str(group_id)
        self.group_personalities[group_id_str] = personality_id
        self._save_config()
        return True, f"✅ 本群AI性格已切换为: {self.get_personality_name(personality_id)}"
    
    def clear_group_personality(self, group_id: str) -> tuple:
        group_id_str = str(group_id)
        if group_id_str in self.group_personalities:
            del self.group_personalities[group_id_str]
            self._save_config()
            return True, f"✅ 本群已恢复全局默认性格: {self.get_personality_name(self.global_default)}"
        return False, "本群未设置独立性格"
    
    def set_global_default(self, personality_id: str) -> tuple:
        if personality_id not in self.personalities:
            available = ", ".join(self.personalities.keys())
            return False, f"❌ 性格不存在！可用: {available}"
        self.global_default = personality_id
        self._save_config()
        return True, f"✅ 全局默认性格已设置为: {self.get_personality_name(personality_id)}"
    
    def get_group_status(self, group_id: str) -> str:
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
            "  • furina - 芙宁娜（优雅水神）",
            "  • luotianyi - 洛天依（吃货歌姬）",
            "",
            "📝 命令:",
            "  !本群切换 猫娘 - 单独设置本群为猫娘",
            "  !本群切换 默认 - 单独设置本群为默认",
            "  !本群切换 furina - 单独设置本群为芙宁娜",
            "  !本群切换 洛天依 - 单独设置本群为洛天依",
            "  !本群恢复 - 恢复跟随全局",
            "",
            "🔒 安全规则:",
            "  • 敏感词过滤（1-2次提醒，3次警告，4次严重警告，5次拉黑）",
            "  • 辱骂机器人（1-2次提醒，3次警告，4次严重警告，5次拉黑）",
            "  • 24小时无违规重置计数",
            "  • 拉黑后无法使用机器人"
        ]
        return "\n".join(lines)
