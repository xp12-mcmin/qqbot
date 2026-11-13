# banned_word_detector.py
import os
import json
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple


# ==================== 默认违禁词库 ====================
# 规则：
#   1. 只保留 2 字以上的组合词，单字和 2 字母缩写一律不加（会误杀）
#   2. Emoji / 符号词走精确匹配（不归一化）
#   3. 混合词（汉字 + Emoji，如 "没🐴"）走精确匹配
DEFAULT_BANNED_WORDS = [
    # ==================== 色情/敏感 ====================
    "色情", "性交", "做爱", "约炮", "一夜情", "裸聊",
    "打飞机", "自慰", "撸管", "口交", "肛交", "群交", "乱伦",
    "幼女", "正太", "强奸", "迷奸", "调教", "SM调教", "sm调教",
    "发裸照", "视频裸聊", "裸照", "淫荡", "发情",
    "sex", "fuck", "porn", "nude", "erotic", "hentai",
    "sexy", "horny", "bitch", "whore", "slut",
    "penis", "vagina", "boobs", "dick", "cock",

    # ==================== 基础骂人 ====================
    "傻逼", "煞笔", "沙比", "莎比", "撒比", "shabi",
    "蠢货", "蠢猪", "蠢驴", "白痴", "弱智", "智障", "脑残",
    "废物", "废柴", "垃圾", "人渣", "杂种", "畜生", "禽兽",
    "狗东西", "狗日的", "狗杂种", "猪狗不如",

    # ==================== 傻子/傻瓜/蠢类 ====================
    "傻子", "傻瓜", "蠢蛋", "蠢人",
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

    # ==================== 常见骂人 ====================
    "草泥马", "操你妈", "操你", "艹你妈", "日你妈",
    "尼玛", "你妈", "他妈", "特么", "他妈的",
    "TMD", "tmd", "TM的",
    "去死", "去屎", "滚蛋", "滚粗", "给爷爬",
    "死全家", "全家暴毙", "全家火葬场", "祖宗十八代",
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
    "阴阳人", "两面三刀",
    "巨婴", "玻璃心", "公主病", "直男癌",

    # ==================== 精神攻击 ====================
    "脑子有病", "脑子进水", "脑子有坑", "脑瘫", "小儿麻痹",
    "智障儿童", "低能儿", "唐氏儿", "先天愚型",
    "精神病", "神经病", "疯子", "癫子",
    "心理变态", "人格分裂",

    # ==================== 诅咒类 ====================
    "出门被车撞", "喝水噎死", "吃饭噎死", "走路摔死",
    "不得好死", "断子绝孙", "生儿子没屁眼",
    "天打雷劈", "五雷轰顶", "不得善终",

    # ==================== 英文骂人（3 字母以上）====================
    "fuck", "fack", "fuk", "fcuk",
    "shit",
    "damn", "darn",
    "bitch", "btch",
    "asshole", "bastard",
    "stupid", "idiot", "moron",
    "retard", "retarded",
    "loser", "jerk", "twat",
    "wtf", "stfu", "gtfo",

    # ==================== 变体/谐音 ====================
    "sha逼", "sha逼",
    "caonima",
    "你麻痹", "尼玛币",
    "麻痹", "妈逼", "妈了个逼",
    "MLGB", "mlgb",
    "wqnmlgb", "qnmlgb", "qnmdb",

    # ==================== 拼音缩写（3 字母以上）====================
    "cnm", "nmsl", "wcnm",
    "mdzz",

    # ==================== 针对机器人的 ====================
    "机器人傻逼", "机器人废物", "机器人垃圾", "破机器人",
    "人工智障", "弱智AI", "垃圾AI", "傻逼AI", "废物AI",
    "机器狗", "电子宠物", "死机器人", "臭机器人",
    "智障AI", "蠢AI", "笨AI", "傻子AI", "傻瓜AI",
    "机器人傻子", "机器人傻瓜", "机器人蠢货", "机器人笨蛋",
    "机器人白痴", "机器人脑残", "机器人智障", "机器人弱智",
    "AI傻子", "AI傻瓜", "AI蠢货", "AI笨蛋",
    "人工傻子", "人工蠢货",

    # ==================== 补充常见 ====================
    "二逼", "二笔", "二货", "二百五",
    "妈的", "妈蛋",
    "卧槽", "我艹", "我草",
    "你妹", "你丫",
    "扯淡", "放屁", "胡说八道",
    "滚犊子", "滚一边", "滚远点",
    "鲨臂", "傻臂", "沙雕", "煞雕",
    "毒瘤", "祸害", "蛀虫",
    "臭狗屎", "大粪",
    "苍蝇", "臭虫",
    "垃圾货", "残次品",
    "低等人", "下等人", "劣等人",
    "叫爸爸", "叫妈妈",

    # ==================== Emoji 违禁词（精确匹配）====================
    "🖕", "🖕🏻", "🖕🏼", "🖕🏽", "🖕🏾", "🖕🏿",
    "🐷", "🐖", "🐽",
    "🐶", "🐕", "🐩",
    "🤡",
    "💩",
    "🤮", "🤢",
    "👎", "👎🏻", "👎🏼", "👎🏽", "👎🏾", "👎🏿",
    "💀", "☠️",
    "🦆",
    "🐔",
    "🌿",

    # ==================== Emoji 混合词（精确匹配）====================
    "没🐴", "没马", "没妈", "沒🐴", "沒妈",
    "你🐴", "你马", "你妈死了", "尼🐴",
    "草🐴", "草马",
]


class BannedWordDetector:
    """
    违禁词检测 + 撤回 + 累计禁言 + 黑名单系统

    黑名单特性：
      - 每群独立开关（blacklist_groups: {群号: True/False}，未设置的群默认启用）
      - 全局黑名单（跨群共享，用特殊 key "__global__" 存储）
      - 达到阈值自动拉黑 + 踢出
      - 黑名单用户进群即踢
    """

    GLOBAL_BL_KEY = "__global__"   # 全局黑名单特殊 key

    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.config_file = os.path.join(data_dir, "banned_word_config.json")
        self.records_file = os.path.join(data_dir, "banned_word_records.json")
        self.blacklist_file = os.path.join(data_dir, "banned_word_blacklist.json")
        os.makedirs(data_dir, exist_ok=True)

        self.config = {
            "enabled": True,                             # 违禁词检测全局总开关
            "enabled_groups": [],                        # 启用的群号列表
            "banned_words": list(DEFAULT_BANNED_WORDS),  # 违禁词库
            "mute_threshold": 10,                        # 第几次触发禁言
            "mute_duration": 600,                        # 禁言时长（秒）
            "reset_hours": 3,                            # 多少小时无违禁重置计数
            "delete_message": True,                      # 是否撤回消息
            "notify": True,                              # 是否提示

            # ===== 黑名单相关 =====
            "blacklist_enabled": True,                   # 黑名单全局总开关（关掉=所有群都不生效）
            "blacklist_groups": {},                      # 每群独立开关 {群号: True/False}，未设置=默认启用
            "blacklist_threshold": 50,                   # 统计窗口内累计多少次进黑名单
            "blacklist_window_hours": 3,                 # 统计窗口（小时）
            "blacklist_kick_on_join": True,              # 黑名单用户进群即踢
        }

        self.records: Dict[str, Dict[str, dict]] = {}
        # 黑名单结构: {group_id 或 "__global__": {user_id: {...}}}
        self.blacklist: Dict[str, Dict[str, dict]] = {}

        self.load_config()
        self.load_records()
        self.load_blacklist()

        print(f"[违禁词] 初始化完成，全局状态: {'开启' if self.config['enabled'] else '关闭'}")
        print(f"[违禁词] 违禁词数量: {len(self.config['banned_words'])}")
        print(f"[违禁词] 启用群数: {len(self.config['enabled_groups'])}")
        print(f"[违禁词] 禁言阈值: 第 {self.config['mute_threshold']} 次")
        print(f"[违禁词] 黑名单: {'开启' if self.config['blacklist_enabled'] else '关闭'}"
              f"（{self.config['blacklist_window_hours']}h 内 {self.config['blacklist_threshold']} 次触发）")
        print(f"[违禁词] 单独设置过黑名单开关的群数: {len(self.config.get('blacklist_groups', {}))}")

    # ==================== 配置持久化 ====================
    def load_config(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                for k, v in saved.items():
                    self.config[k] = v
                if "enabled_groups" not in saved:
                    self.config["enabled_groups"] = []
                # 旧配置词库过少 → 自动补全
                if len(self.config.get("banned_words", [])) < 10:
                    print("[违禁词] 检测到旧配置词库过少，自动使用完整词库")
                    self.config["banned_words"] = list(DEFAULT_BANNED_WORDS)
                    self.save_config()
        except Exception as e:
            print(f"[违禁词] 配置加载失败: {e}")

        # 兼容旧配置
        self.config.setdefault("blacklist_enabled", True)
        self.config.setdefault("blacklist_groups", {})
        self.config.setdefault("blacklist_threshold", 50)
        self.config.setdefault("blacklist_window_hours", 3)
        self.config.setdefault("blacklist_kick_on_join", True)

    def save_config(self):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[违禁词] 配置保存失败: {e}")

    # ==================== 记录持久化 ====================
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

    # ==================== 黑名单持久化 ====================
    def load_blacklist(self):
        try:
            if os.path.exists(self.blacklist_file):
                with open(self.blacklist_file, "r", encoding="utf-8") as f:
                    self.blacklist = json.load(f)
        except Exception as e:
            print(f"[违禁词] 黑名单加载失败: {e}")
            self.blacklist = {}

    def save_blacklist(self):
        try:
            with open(self.blacklist_file, "w", encoding="utf-8") as f:
                json.dump(self.blacklist, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[违禁词] 黑名单保存失败: {e}")

    # ==================== 开关：违禁词检测 ====================
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
        groups = self.config.get("enabled_groups", [])
        if not groups:
            return True
        return str(group_id) in groups

    def get_enabled_groups(self) -> List[str]:
        return list(self.config.get("enabled_groups", []))

    def get_status(self, group_id: str = None) -> str:
        global_status = "开启" if self.config["enabled"] else "关闭"
        lines = [
            f"【🚫 违禁词检测】",
            f"⚠️ 全局开关: {global_status}" + ("  ← 关着时所有群都不生效！" if not self.config["enabled"] else ""),
            f"违禁词数: {len(self.config['banned_words'])}",
            f"禁言阈值: 第 {self.config['mute_threshold']} 次",
            f"禁言时长: {self.config['mute_duration']}秒",
            f"重置时间: {self.config['reset_hours']}小时",
            f"撤回消息: {'是' if self.config['delete_message'] else '否'}",
            f"启用群数: {len(self.config['enabled_groups'])}",
            # ===== 黑名单 =====
            f"黑名单总开关: {'开启' if self.config['blacklist_enabled'] else '关闭'}",
            f"黑名单阈值: {self.config['blacklist_window_hours']}h 内 {self.config['blacklist_threshold']} 次",
            f"进群即踢: {'是' if self.config['blacklist_kick_on_join'] else '否'}",
        ]
        if group_id:
            group_id = str(group_id)
            group_status = "✅ 已启用" if self.is_group_enabled(group_id) else "❌ 未启用"
            lines.append(f"本群违禁词检测: {group_status}")
            bl_active = self.is_blacklist_active_in_group(group_id)
            bl_setting = self.config.get("blacklist_groups", {}).get(group_id, "默认")
            lines.append(f"本群黑名单: {'✅ 生效' if bl_active else '❌ 失效'}（设置: {bl_setting}）")
            lines.append(f"本群黑名单人数: {len(self.blacklist.get(group_id, {}))}")
            lines.append(f"全局黑名单人数: {len(self.blacklist.get(self.GLOBAL_BL_KEY, {}))}")
        return "\n".join(lines)

    # ==================== 核心检测 ====================
    def check_message(self, group_id: str, user_id: str, text: str) -> Optional[Dict]:
        if not self.is_group_enabled(group_id):
            return None

        if not text:
            return None

        group_id = str(group_id)
        user_id = str(user_id)

        # 去掉 URL
        text = re.sub(r'https?://\S+', '', text)
        text = re.sub(r'www\.\S+', '', text)
        text = re.sub(r'[a-zA-Z0-9.-]+\.(com|cn|net|org|io|xyz|top|cc|tv)\S*', '', text)

        def normalize(s):
            s = s.lower()
            return re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', s)

        def has_emoji(s):
            return bool(re.search(r'[^\u4e00-\u9fa5a-zA-Z0-9]', s))

        text_norm = normalize(text)

        matched_word = None
        for word in self.config["banned_words"]:
            if has_emoji(word):
                if word in text:
                    matched_word = word
                    break
            else:
                word_norm = normalize(word)
                if len(word_norm) >= 2 and word_norm in text_norm:
                    matched_word = word
                    break

        if not matched_word:
            return None

        group_records = self.records.setdefault(group_id, {})
        user_record = group_records.get(user_id, {
            "count": 0,
            "last_time": 0,
            "muted_at": 0,
            "total_strikes": 0,
            "strike_window_start": 0,
        })

        now = time.time()
        reset_seconds = self.config["reset_hours"] * 3600

        # 短周期重置禁言计数
        if user_record["last_time"] > 0 and (now - user_record["last_time"]) > reset_seconds:
            print(f"[违禁词] 用户 {user_id} 超过 {self.config['reset_hours']}h 未违禁，重置禁言计数")
            user_record["count"] = 0

        # 黑名单统计窗口
        window_seconds = self.config["blacklist_window_hours"] * 3600
        if user_record.get("strike_window_start", 0) == 0 \
                or (now - user_record["strike_window_start"]) > window_seconds:
            user_record["strike_window_start"] = now
            user_record["total_strikes"] = 0

        user_record["count"] += 1
        user_record["last_time"] = now
        user_record["total_strikes"] = user_record.get("total_strikes", 0) + 1
        group_records[user_id] = user_record
        self.save_records()

        current_count = user_record["count"]
        total_strikes = user_record["total_strikes"]
        should_mute = (current_count >= self.config["mute_threshold"])

        # 是否进黑名单（本群黑名单生效时才判定）
        should_blacklist = (
            self.is_blacklist_active_in_group(group_id)
            and total_strikes >= self.config.get("blacklist_threshold", 50)
        )

        print(f"[违禁词] ⚠️ 群{group_id} 用户{user_id} 触发违禁词: {matched_word} "
              f"(禁言计数 {current_count}, 窗口累计 {total_strikes})")

        if should_mute:
            user_record["count"] = 0
            user_record["muted_at"] = now
            self.save_records()
            print(f"[违禁词] 🔨 用户 {user_id} 达到 {self.config['mute_threshold']} 次，执行禁言")

        if should_blacklist:
            self.add_to_blacklist(
                group_id, user_id,
                reason=f"{self.config['blacklist_window_hours']}h 内违规 {total_strikes} 次（最后触发词：{matched_word}）",
                is_global=False
            )
            user_record["total_strikes"] = 0
            user_record["strike_window_start"] = now
            user_record["count"] = 0
            self.save_records()
            print(f"[违禁词] 🚫 用户 {user_id} 达到黑名单阈值，已加入本群黑名单并踢出")

        return {
            "matched_word": matched_word,
            "count": current_count,
            "total_strikes": total_strikes,
            "should_mute": should_mute,
            "should_blacklist": should_blacklist,
            "mute_duration": self.config["mute_duration"],
            "threshold": self.config["mute_threshold"],
            "delete_message": self.config["delete_message"],
            "notify": self.config["notify"],
        }

    # ==================== 违禁词管理 ====================
    def record_violation(self, group_id: str, user_id: str, source: str) -> Optional[Dict]:
        """记录一次违规（供 AI 图片审核等非词库命中路径使用）。

        与 check_message 共享同一套计数 / 禁言 / 黑名单逻辑，
        但跳过词库匹配，直接把 source 作为 matched_word 返回。
        """
        if not self.is_group_enabled(group_id):
            return None

        group_id = str(group_id)
        user_id = str(user_id)
        matched_word = f"[AI图片审核] {source}"

        group_records = self.records.setdefault(group_id, {})
        user_record = group_records.get(user_id, {
            "count": 0,
            "last_time": 0,
            "muted_at": 0,
            "total_strikes": 0,
            "strike_window_start": 0,
        })

        now = time.time()
        reset_seconds = self.config["reset_hours"] * 3600

        # 短周期重置禁言计数
        if user_record["last_time"] > 0 and (now - user_record["last_time"]) > reset_seconds:
            print(f"[违禁词] 用户 {user_id} 超过 {self.config['reset_hours']}h 未违禁，重置禁言计数")
            user_record["count"] = 0

        # 黑名单统计窗口
        window_seconds = self.config["blacklist_window_hours"] * 3600
        if user_record.get("strike_window_start", 0) == 0 \
                or (now - user_record["strike_window_start"]) > window_seconds:
            user_record["strike_window_start"] = now
            user_record["total_strikes"] = 0

        user_record["count"] += 1
        user_record["last_time"] = now
        user_record["total_strikes"] = user_record.get("total_strikes", 0) + 1
        group_records[user_id] = user_record
        self.save_records()

        current_count = user_record["count"]
        total_strikes = user_record["total_strikes"]
        should_mute = (current_count >= self.config["mute_threshold"])

        should_blacklist = (
            self.is_blacklist_active_in_group(group_id)
            and total_strikes >= self.config.get("blacklist_threshold", 50)
        )

        print(f"[违禁词] ⚠️ 群{group_id} 用户{user_id} {source}违规 "
              f"(禁言计数 {current_count}, 窗口累计 {total_strikes})")

        if should_mute:
            user_record["count"] = 0
            user_record["muted_at"] = now
            self.save_records()
            print(f"[违禁词] 🔨 用户 {user_id} 达到 {self.config['mute_threshold']} 次，执行禁言")

        if should_blacklist:
            self.add_to_blacklist(
                group_id, user_id,
                reason=f"{self.config['blacklist_window_hours']}h 内违规 {total_strikes} 次（最后触发：{source}）",
                is_global=False
            )
            user_record["total_strikes"] = 0
            user_record["strike_window_start"] = now
            user_record["count"] = 0
            self.save_records()
            print(f"[违禁词] 🚫 用户 {user_id} 达到黑名单阈值，已加入本群黑名单并踢出")

        return {
            "matched_word": matched_word,
            "count": current_count,
            "total_strikes": total_strikes,
            "should_mute": should_mute,
            "should_blacklist": should_blacklist,
            "mute_duration": self.config["mute_duration"],
            "threshold": self.config["mute_threshold"],
            "delete_message": self.config["delete_message"],
            "notify": self.config["notify"],
        }

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

    # ==================== 每群黑名单开关 ====================
    def is_blacklist_active_in_group(self, group_id: str) -> bool:
        """
        某群黑名单是否生效：
        - 全局关 → 全群失效
        - 本群开关没设置 → 默认启用
        - 本群开关 False → 失效
        - 本群开关 True → 生效
        """
        if not self.config.get("blacklist_enabled", True):
            return False
        groups = self.config.get("blacklist_groups", {})
        val = groups.get(str(group_id))
        if val is None:
            return True
        return bool(val)

    def set_blacklist_group(self, group_id: str, enabled: bool) -> bool:
        """设置某群的黑名单开关，返回是否有变化"""
        gid = str(group_id)
        groups = self.config.setdefault("blacklist_groups", {})
        old = groups.get(gid)
        groups[gid] = bool(enabled)
        self.save_config()
        return old != groups[gid]

    def reset_blacklist_group(self, group_id: str) -> bool:
        """移除本群设置 → 恢复默认（启用）"""
        gid = str(group_id)
        groups = self.config.get("blacklist_groups", {})
        if gid in groups:
            del groups[gid]
            self.save_config()
            return True
        return False

    # ==================== 黑名单：添加 / 移除 ====================
    def add_to_blacklist(self, group_id: str, user_id: str, reason: str = "",
                         is_global: bool = False) -> bool:
        """
        加入黑名单
        :param group_id: 群号（is_global=True 时忽略）
        :param user_id: 用户QQ
        :param reason: 原因
        :param is_global: True=加入全局黑名单；False=加入本群黑名单
        """
        user_id = str(user_id)
        target_key = self.GLOBAL_BL_KEY if is_global else str(group_id)
        group_bl = self.blacklist.setdefault(target_key, {})

        if user_id in group_bl:
            group_bl[user_id]["reason"] = reason or group_bl[user_id].get("reason", "")
            group_bl[user_id]["updated_at"] = time.time()
            self.save_blacklist()
            return False

        group_bl[user_id] = {
            "added_at": time.time(),
            "updated_at": time.time(),
            "reason": reason,
            "strikes": self.records.get(str(group_id), {}).get(user_id, {}).get("total_strikes", 0),
            "scope": "global" if is_global else "group",
        }
        self.save_blacklist()
        return True

    def add_to_blacklist_remote(self, target_group: str, user_id: str, reason: str = "") -> bool:
        """远程往指定群黑名单加人"""
        return self.add_to_blacklist(target_group, user_id, reason, is_global=False)

    def remove_from_blacklist(self, group_id: str, user_id: str,
                              is_global: bool = False) -> bool:
        user_id = str(user_id)
        target_key = self.GLOBAL_BL_KEY if is_global else str(group_id)
        if target_key in self.blacklist and user_id in self.blacklist[target_key]:
            del self.blacklist[target_key][user_id]
            if not self.blacklist[target_key]:
                del self.blacklist[target_key]
            self.save_blacklist()
            return True
        return False

    def remove_from_blacklist_remote(self, target_group: str, user_id: str) -> bool:
        return self.remove_from_blacklist(target_group, user_id, is_global=False)

    def remove_from_global_blacklist(self, user_id: str) -> bool:
        return self.remove_from_blacklist("", user_id, is_global=True)

    # ==================== 黑名单：查询 ====================
    def is_blacklisted(self, group_id: str, user_id: str) -> bool:
        """判断是否被拉黑（含全局；本群黑名单开关生效才判定）"""
        if not self.is_blacklist_active_in_group(group_id):
            return False
        user_id = str(user_id)
        group_id = str(group_id)
        if user_id in self.blacklist.get(self.GLOBAL_BL_KEY, {}):
            return True
        return user_id in self.blacklist.get(group_id, {})

    def is_blacklisted_global_only(self, user_id: str) -> bool:
        if not self.config.get("blacklist_enabled", True):
            return False
        return str(user_id) in self.blacklist.get(self.GLOBAL_BL_KEY, {})

    def is_blacklisted_group_only(self, group_id: str, user_id: str) -> bool:
        if not self.is_blacklist_active_in_group(group_id):
            return False
        return str(user_id) in self.blacklist.get(str(group_id), {})

    def get_blacklist(self, group_id: str) -> Dict[str, dict]:
        """获取某群黑名单（不含全局）"""
        return dict(self.blacklist.get(str(group_id), {}))

    def get_global_blacklist(self) -> Dict[str, dict]:
        return dict(self.blacklist.get(self.GLOBAL_BL_KEY, {}))

    def get_blacklist_with_global(self, group_id: str) -> Dict[str, dict]:
        """某群黑名单 + 全局黑名单合并（全局优先展示）"""
        merged = {}
        for uid, info in self.get_global_blacklist().items():
            item = dict(info)
            item["_scope"] = "global"
            merged[uid] = item
        for uid, info in self.get_blacklist(group_id).items():
            item = dict(info)
            item["_scope"] = "group"
            merged[uid] = item
        return merged

    # ==================== 黑名单：清空 ====================
    def clear_group_blacklist(self, group_id: str) -> int:
        group_id = str(group_id)
        if group_id in self.blacklist:
            count = len(self.blacklist[group_id])
            del self.blacklist[group_id]
            self.save_blacklist()
            return count
        return 0

    def clear_global_blacklist(self) -> int:
        if self.GLOBAL_BL_KEY in self.blacklist:
            count = len(self.blacklist[self.GLOBAL_BL_KEY])
            del self.blacklist[self.GLOBAL_BL_KEY]
            self.save_blacklist()
            return count
        return 0

    # ==================== 黑名单：参数 ====================
    def set_blacklist_enabled(self, enabled: bool) -> bool:
        """全局黑名单总开关"""
        self.config["blacklist_enabled"] = enabled
        self.save_config()
        return True

    def set_blacklist_threshold(self, threshold: int) -> bool:
        if threshold < 1:
            return False
        self.config["blacklist_threshold"] = threshold
        self.save_config()
        return True

    def set_blacklist_window_hours(self, hours: int) -> bool:
        if hours < 1:
            return False
        self.config["blacklist_window_hours"] = hours
        self.save_config()
        return True

    def set_blacklist_kick_on_join(self, enabled: bool) -> bool:
        self.config["blacklist_kick_on_join"] = enabled
        self.save_config()
        return True
    # ==================== 帮助图片 ====================
    def render_help_image(self, is_admin: bool = True):
        """
        渲染帮助图片，返回 PIL.Image 对象
        复用项目里已有的 help_image 风格
        """
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            print("[违禁词] PIL 未安装，无法生成帮助图片")
            return None

        # ---------- 画布参数 ----------
        W = 900
        PAD = 30
        LINE_H = 32
        SECTION_GAP = 18
        TITLE_H = 90

        # ---------- 配色 ----------
        BG = (30, 33, 40)
        CARD_BG = (42, 46, 54)
        TITLE_FG = (255, 255, 255)
        SUB_FG = (160, 165, 175)
        SECTION_FG = (255, 200, 90)
        CMD_FG = (140, 220, 255)
        DESC_FG = (200, 205, 215)
        WARN_FG = (255, 130, 130)
        BORDER = (70, 75, 85)

        # ---------- 字体 ----------
        def _font(size, bold=False):
            candidates = (
                ["msyhbd.ttc", "msyh.ttc", "simhei.ttf"]
                if bold else
                ["msyh.ttc", "simhei.ttf", "simsun.ttc"]
            )
            for name in candidates:
                try:
                    return ImageFont.truetype(name, size)
                except Exception:
                    continue
            return ImageFont.load_default()

        f_title   = _font(30, bold=True)
        f_sub     = _font(16)
        f_section = _font(20, bold=True)
        f_cmd     = _font(17, bold=True)
        f_desc    = _font(16)
        f_warn    = _font(16, bold=True)

        # ---------- 内容定义 ----------
        # 每条: (分类标题 or None, [(cmd, desc), ...])
        sections = [
            ("🔌 违禁词检测 · 开关", [
                ("!违禁词 全局 开/关", "全局总开关（关掉=所有群失效）"),
                ("!违禁词 启用", "启用本群检测"),
                ("!违禁词 禁用", "禁用本群检测"),
                ("!违禁词 启用群 <群号>", "远程启用指定群"),
                ("!违禁词 禁用群 <群号>", "远程禁用指定群"),
                ("!违禁词 群列表", "查看所有已启用群"),
            ]),
            ("📚 词库管理", [
                ("!违禁词 添加 <词>", "添加违禁词"),
                ("!违禁词 删除 <词>", "删除违禁词"),
                ("!违禁词 列表", "查看违禁词（前50个）"),
            ]),
            ("⚙️ 处罚参数", [
                ("!违禁词 阈值 <次数>", "第几次触发禁言（默认10，纯数字）"),
                ("!违禁词 时长 <秒>", "禁言时长秒数（默认600，纯数字）"),
                ("!违禁词 重置 <小时>", "多久不违规就重置（默认3，纯数字）"),
                ("!违禁词 撤回 开/关", "是否撤回违禁消息（默认开）"),
            ]),
            ("🚫 黑名单 · 开关", [
                ("!违禁词 黑名单启用", "本群黑名单开"),
                ("!违禁词 黑名单禁用", "本群黑名单关"),
                ("!违禁词 黑名单恢复", "本群恢复默认（启用）"),
                ("!违禁词 远程黑名单启用 <群号>", "远程开指定群黑名单"),
                ("!违禁词 远程黑名单禁用 <群号>", "远程关指定群黑名单"),
                ("!违禁词 远程黑名单恢复 <群号>", "远程恢复默认"),
                ("!违禁词 黑名单群状态", "查看哪些群单独设置过"),
            ]),
            ("🚫 黑名单 · 参数", [
                ("!违禁词 黑名单开关 开/关", "全局总开关（关掉=所有群失效）"),
                ("!违禁词 黑名单阈值 <次数>", "默认50，纯数字"),
                ("!违禁词 黑名单窗口 <小时>", "默认3，纯数字"),
                ("!违禁词 进群踢 开/关", "黑名单用户进群即踢"),
            ]),
            ("🚫 黑名单 · 本群加/删", [
                ("!违禁词 加入黑名单 <QQ> [原因]", "加本群黑名单并踢出"),
                ("!违禁词 移出黑名单 <QQ>", "解除本群黑名单"),
                ("!违禁词 清空黑名单", "清空本群黑名单"),
            ]),
            ("🌐 黑名单 · 全局", [
                ("!违禁词 加入全局黑名单 <QQ> [原因]", "所有启用群都踢"),
                ("!违禁词 移出全局黑名单 <QQ>", "解除全局黑名单"),
                ("!违禁词 清空全局黑名单", "清空全局黑名单"),
            ]),
            ("🌐 黑名单 · 远程操作指定群", [
                ("!违禁词 远程加黑 <群号> <QQ> [原因]", "远程加指定群黑名单"),
                ("!违禁词 远程移黑 <群号> <QQ>", "远程移出指定群黑名单"),
            ]),
            ("🔍 黑名单 · 查询", [
                ("!违禁词 黑名单", "查本群 + 全局黑名单"),
                ("!违禁词 全局黑名单", "只看全局黑名单"),
            ]),
            ("🗂 记录管理", [
                ("!违禁词 清除记录 <QQ>", "清除单个用户的违规记录"),
                ("!违禁词 清空本群", "清空本群所有记录"),
                ("!违禁词 状态", "查看当前运行状态"),
            ]),
        ]

        # ---------- 先算高度 ----------
        h = TITLE_H + PAD
        for _, items in sections:
            h += LINE_H + SECTION_GAP           # 分类标题
            h += LINE_H * len(items)            # 每条
            h += 10
        h += 160  # 底部提示区

        # ---------- 创建画布 ----------
        img = Image.new("RGB", (W, h), BG)
        draw = ImageDraw.Draw(img)

        # ---------- 标题栏 ----------
        draw.rectangle([0, 0, W, TITLE_H], fill=(45, 50, 60))
        draw.text((PAD, 22), "📝 违禁词检测 · 命令帮助", font=f_title, fill=TITLE_FG)
        draw.text((PAD, 60), "XP12 Bot · 违禁词 / 黑名单系统", font=f_sub, fill=SUB_FG)

        y = TITLE_H + PAD

        # ---------- 分类绘制 ----------
        for section_name, items in sections:
            # 分类标题
            draw.text((PAD, y), section_name, font=f_section, fill=SECTION_FG)
            y += LINE_H

            # 每条命令
            for cmd, desc in items:
                # 命令（左对齐，加粗）
                draw.text((PAD + 10, y), cmd, font=f_cmd, fill=CMD_FG)

                # 描述（右对齐不美观，直接缩进换行规则）
                # 用一个小箭头 + 描述
                desc_x = PAD + 10 + 320   # 命令区域大约宽度
                if desc_x > W - 200:
                    desc_x = PAD + 10
                # 换行处理：简单截断
                if len(desc) > 22:
                    desc = desc[:21] + "…"
                draw.text((desc_x, y), "→ " + desc, font=f_desc, fill=DESC_FG)
                y += LINE_H

            y += 10

        # ---------- 底部提示框 ----------
        y += 10
        box_h = 120
        draw.rounded_rectangle(
            [PAD, y, W - PAD, y + box_h],
            radius=10, fill=(50, 42, 42), outline=(120, 70, 70), width=2
        )
        draw.text((PAD + 16, y + 14), "💡 参数格式提示", font=f_warn, fill=(255, 180, 120))
        draw.text((PAD + 16, y + 44),
                  "⚠️ 带「纯数字」标记的参数，只写阿拉伯数字：",
                  font=f_desc, fill=DESC_FG)
        draw.text((PAD + 30, y + 68),
                  "✅ !违禁词 黑名单窗口 3          ❌ !违禁词 黑名单窗口 3小时",
                  font=f_desc, fill=DESC_FG)
        draw.text((PAD + 30, y + 90),
                  "✅ !违禁词 加入黑名单 123456789  ❌ !违禁词 加入黑名单 QQ123456789",
                  font=f_desc, fill=DESC_FG)

        return img

# ==================== 单例 ====================
_detector = None

def get_banned_word_detector() -> BannedWordDetector:
    global _detector
    if _detector is None:
        _detector = BannedWordDetector()
    return _detector
