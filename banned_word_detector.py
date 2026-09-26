# banned_word_detector.py
import os
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple


# ==================== 默认违禁词库（合并自 ai_personality.py）====================
DEFAULT_BANNED_WORDS = [
    # ==================== 敏感内容 ====================
    "色情", "性交", "做爱", "操", "屌", "鸡巴", "逼",
    "约炮", "一夜情", "裸聊", "视频裸聊", "发裸照", "打飞机",
    "性感", "诱惑", "勾引", "调教", "SM", "捆绑",
    "淫荡", "骚", "发情", "上床", "开房", "啪啪",
    "自慰", "撸管", "口交", "肛交", "群交", "乱伦",
    "幼女", "萝莉", "正太", "强奸", "迷奸",
    "sex", "fuck", "porn", "nude", "erotic", "hentai",
    "sexy", "horny", "bitch", "whore", "slut",
    "penis", "vagina", "boobs", "dick", "cock",
    "s3x", "fUck", "p0rn",

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
    "叫爸爸", "叫bb", "叫妈妈"
]


class BannedWordDetector:
    """违禁词检测 + 撤回 + 累计禁言系统（支持每群独立开关）"""

    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.config_file = os.path.join(data_dir, "banned_word_config.json")
        self.records_file = os.path.join(data_dir, "banned_word_records.json")
        os.makedirs(data_dir, exist_ok=True)

        # 默认配置
        self.config = {
            "enabled": False,                            # 全局总开关（默认关闭）
            "enabled_groups": [],                        # 启用的群号列表
            "banned_words": list(DEFAULT_BANNED_WORDS),  # ← 用合并后的词库
            "mute_threshold": 10,                        # 第几次触发禁言
            "mute_duration": 600,                        # 禁言时长（秒）默认10分钟
            "reset_hours": 3,                            # 多少小时无违禁重置
            "delete_message": True,                      # 是否撤回消息
            "notify": True,                              # 是否提示
        }

        # 记录结构: {group_id: {user_id: {"count": int, "last_time": float, "muted_at": float}}}
        self.records: Dict[str, Dict[str, dict]] = {}

        self.load_config()
        self.load_records()
        print(f"[违禁词] 初始化完成，全局状态: {'开启' if self.config['enabled'] else '关闭'}")
        print(f"[违禁词] 违禁词数量: {len(self.config['banned_words'])}")
        print(f"[违禁词] 启用群数: {len(self.config['enabled_groups'])}")
        print(f"[违禁词] 禁言阈值: 第 {self.config['mute_threshold']} 次")

    # ==================== 配置 ====================
    def load_config(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                for k, v in saved.items():
                    self.config[k] = v
                # 兼容旧配置：如果没有 enabled_groups，就初始化为空
                if "enabled_groups" not in saved:
                    self.config["enabled_groups"] = []
                # 兼容旧配置：如果词库是空/过少，自动补上完整词库
                if len(self.config.get("banned_words", [])) < 10:
                    print("[违禁词] 检测到旧配置词库过少，自动使用完整词库")
                    self.config["banned_words"] = list(DEFAULT_BANNED_WORDS)
                    self.save_config()
        except Exception as e:
            print(f"[违禁词] 配置加载失败: {e}")

    def save_config(self):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[违禁词] 配置保存失败: {e}")

    # ==================== 记录 ====================
    def load_records(self):
        try:
            if os.path.exists(self.records_file):
                with open(self.records_file, "r", encoding="utf-8") as f:
                    self.records = json.load(f)
        except Exception as e:
            print(f"[违禁词] 记录加载失败: {e}")
            self.records = {}

    def save_records(self):
        try:
            with open(self.records_file, "w", encoding="utf-8") as f:
                json.dump(self.records, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[违禁词] 记录保存失败: {e}")

    # ==================== 开关 ====================
    def set_global_enabled(self, enabled: bool):
        self.config["enabled"] = enabled
        self.save_config()
        return f"✅ 违禁词检测【全局】已{'开启' if enabled else '关闭'}"

    def is_global_enabled(self) -> bool:
        return self.config.get("enabled", False)

    def enable_group(self, group_id: str) -> bool:
        group_id = str(group_id)
        if group_id not in self.config["enabled_groups"]:
            self.config["enabled_groups"].append(group_id)
            self.save_config()
            return True
        return False

    def disable_group(self, group_id: str) -> bool:
        group_id = str(group_id)
        if group_id in self.config["enabled_groups"]:
            self.config["enabled_groups"].remove(group_id)
            self.save_config()
            return True
        return False

    def is_group_enabled(self, group_id: str) -> bool:
        if not self.config.get("enabled", False):
            return False
        return str(group_id) in self.config.get("enabled_groups", [])

    def get_enabled_groups(self) -> List[str]:
        return list(self.config.get("enabled_groups", []))

    def get_status(self, group_id: str = None) -> str:
        global_status = "开启" if self.config["enabled"] else "关闭"
        lines = [
            f"【🚫 违禁词检测】",
            f"全局开关: {global_status}",
            f"违禁词数: {len(self.config['banned_words'])}",
            f"禁言阈值: 第 {self.config['mute_threshold']} 次",
            f"禁言时长: {self.config['mute_duration']}秒",
            f"重置时间: {self.config['reset_hours']}小时",
            f"撤回消息: {'是' if self.config['delete_message'] else '否'}",
            f"启用群数: {len(self.config['enabled_groups'])}",
        ]
        if group_id:
            group_id = str(group_id)
            group_status = "✅ 已启用" if group_id in self.config["enabled_groups"] else "❌ 未启用"
            lines.append(f"本群状态: {group_status}")
        return "\n".join(lines)

    # ==================== 核心检测 ====================
    def check_message(self, group_id: str, user_id: str, text: str) -> Optional[Dict]:
        if not self.is_group_enabled(group_id):
            return None

        if not text:
            return None

        group_id = str(group_id)
        user_id = str(user_id)

        # 匹配违禁词
        matched_word = None
        text_lower = text.lower()
        for word in self.config["banned_words"]:
            if word.lower() in text_lower:
                matched_word = word
                break

        if not matched_word:
            return None

        # 获取用户记录
        group_records = self.records.setdefault(group_id, {})
        user_record = group_records.get(user_id, {
            "count": 0,
            "last_time": 0,
            "muted_at": 0
        })

        now = time.time()
        reset_seconds = self.config["reset_hours"] * 3600

        # 检查是否超过重置时间
        if user_record["last_time"] > 0 and (now - user_record["last_time"]) > reset_seconds:
            print(f"[违禁词] 用户 {user_id} 超过 {self.config['reset_hours']}h 未违禁，重置计数")
            user_record["count"] = 0

        # 更新记录
        user_record["count"] += 1
        user_record["last_time"] = now
        group_records[user_id] = user_record
        self.save_records()

        current_count = user_record["count"]
        should_mute = (current_count >= self.config["mute_threshold"])

        print(f"[违禁词] ⚠️ 群{group_id} 用户{user_id} 触发违禁词: {matched_word} (第 {current_count} 次)")

        if should_mute:
            user_record["count"] = 0
            user_record["muted_at"] = now
            self.save_records()
            print(f"[违禁词] 🔨 用户 {user_id} 达到 {self.config['mute_threshold']} 次，执行禁言")

        return {
            "matched_word": matched_word,
            "count": current_count,
            "should_mute": should_mute,
            "mute_duration": self.config["mute_duration"],
            "threshold": self.config["mute_threshold"],
            "delete_message": self.config["delete_message"],
            "notify": self.config["notify"],
        }

    # ==================== 违禁词管理 ====================
    def add_word(self, word: str) -> bool:
        word = word.strip()
        if not word:
            return False
        if word in self.config["banned_words"]:
            return False
        self.config["banned_words"].append(word)
        self.save_config()
        return True

    def remove_word(self, word: str) -> bool:
        word = word.strip()
        if word in self.config["banned_words"]:
            self.config["banned_words"].remove(word)
            self.save_config()
            return True
        return False

    def list_words(self) -> List[str]:
        return list(self.config["banned_words"])

    def set_mute_threshold(self, threshold: int) -> bool:
        if threshold < 1:
            return False
        self.config["mute_threshold"] = threshold
        self.save_config()
        return True

    def set_mute_duration(self, duration: int) -> bool:
        if duration < 0:
            return False
        self.config["mute_duration"] = duration
        self.save_config()
        return True

    def set_reset_hours(self, hours: int) -> bool:
        if hours < 0:
            return False
        self.config["reset_hours"] = hours
        self.save_config()
        return True

    def set_delete_message(self, delete: bool) -> bool:
        self.config["delete_message"] = delete
        self.save_config()
        return True

    # ==================== 记录管理 ====================
    def clear_user_record(self, group_id: str, user_id: str) -> bool:
        group_id = str(group_id)
        user_id = str(user_id)
        if group_id in self.records and user_id in self.records[group_id]:
            del self.records[group_id][user_id]
            self.save_records()
            return True
        return False

    def clear_group_records(self, group_id: str) -> int:
        group_id = str(group_id)
        if group_id in self.records:
            count = len(self.records[group_id])
            del self.records[group_id]
            self.save_records()
            return count
        return 0

    def get_user_count(self, group_id: str, user_id: str) -> int:
        group_id = str(group_id)
        user_id = str(user_id)
        return self.records.get(group_id, {}).get(user_id, {}).get("count", 0)


# 单例
_detector = None

def get_banned_word_detector() -> BannedWordDetector:
    global _detector
    if _detector is None:
        _detector = BannedWordDetector()
    return _detector
