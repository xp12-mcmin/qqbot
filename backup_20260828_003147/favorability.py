"""
好感度系统 - 全局版（所有群通用）
"""

import json
import os
import time
import re
import random
from typing import Dict, List, Optional, Tuple

class FavorabilityManager:
    """好感度管理器 - 全局版"""
    
    def __init__(self, data_dir: str = "data", ai_instance=None):
        self.config_file = os.path.join(data_dir, "favorability_config.json")
        self.data_file = os.path.join(data_dir, "favorability_data.json")
        self.shop_file = os.path.join(data_dir, "favorability_shop.json")
        
        self.ai = ai_instance
        
        # 好感度等级配置
        self.levels = [
            {"min": -9999, "max": -500, "name": "💀 仇敌", "color": "🖤", "badge": "仇敌"},
            {"min": -499, "max": -100, "name": "😠 厌恶", "color": "💜", "badge": "厌恶"},
            {"min": -99, "max": -1, "name": "😒 冷淡", "color": "💙", "badge": "冷淡"},
            {"min": 0, "max": 49, "name": "😐 普通", "color": "💚", "badge": "普通"},
            {"min": 50, "max": 199, "name": "😊 友善", "color": "💛", "badge": "友善"},
            {"min": 200, "max": 499, "name": "❤️ 亲密", "color": "❤️", "badge": "亲密"},
            {"min": 500, "max": 999, "name": "💕 挚友", "color": "💕", "badge": "挚友"},
            {"min": 1000, "max": 9999, "name": "💞 生死之交", "color": "💞", "badge": "生死之交"}
        ]
        
        # 默认商店商品
        self.default_shop = [
            {"id": "greeting", "name": "专属早安", "cost": 50, "type": "action", 
             "description": "让机器人每天早上单独对你说早安", "cooldown": 86400},
            {"id": "pet", "name": "摸头杀", "cost": 20, "type": "action",
             "description": "让机器人摸你的头", "cooldown": 3600},
            {"id": "hug", "name": "抱抱", "cost": 30, "type": "action",
             "description": "让机器人给你一个拥抱", "cooldown": 3600},
            {"id": "song", "name": "点歌", "cost": 100, "type": "action",
             "description": "让机器人推荐一首歌", "cooldown": 7200},
            {"id": "title", "name": "自定义称号", "cost": 200, "type": "permanent",
             "description": "给自己设置一个专属称号", "cooldown": 0}
        ]
        
        # 默认配置
        self.config = {
            "enabled": True,
            "notify_enabled": False,
            "default_favor": 0,
            "max_favor": 9999,
            "min_favor": -9999,
            "cooldown": 10,
            "ai_enabled": True,
            "ai_min_score": -10,
            "ai_max_score": 10,
            "daily_bonus": 5,
            "keywords": {
                "increase": [{"word": "谢谢", "value": 1}, {"word": "爱你", "value": 2}],
                "decrease": [{"word": "垃圾", "value": -2}, {"word": "SB", "value": -2}]
            }
        }
        
        # 好感度数据 {用户QQ: {"favor": 值, "last_daily": 时间戳, "title": 称号, "purchased": []}}
        self.data: Dict[str, Dict] = {}
        self.cooldowns: Dict[str, float] = {}
        self.action_cooldowns: Dict[str, float] = {}
        
        # 商店配置
        self.shop = self.default_shop.copy()
        
        os.makedirs(data_dir, exist_ok=True)
        self._load_config()
        self._load_data()
        self._load_shop()
        
        print(f"[好感度] 全局版初始化完成")
        print(f"[好感度] 记录开关: {'开启' if self.config['enabled'] else '关闭'}")
        print(f"[好感度] 商店商品: {len(self.shop)}个")
    
    def _load_config(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                    self.config.update(saved)
            else:
                self._save_config()
        except Exception as e:
            print(f"[好感度] 配置加载失败: {e}")
    
    def _save_config(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[好感度] 配置保存失败: {e}")
    
    def _load_data(self):
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
        except Exception as e:
            print(f"[好感度] 数据加载失败: {e}")
    
    def _save_data(self):
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[好感度] 数据保存失败: {e}")
    
    def _load_shop(self):
        try:
            if os.path.exists(self.shop_file):
                with open(self.shop_file, 'r', encoding='utf-8') as f:
                    self.shop = json.load(f)
        except Exception as e:
            print(f"[好感度] 商店加载失败: {e}")
    
    def _save_shop(self):
        try:
            with open(self.shop_file, 'w', encoding='utf-8') as f:
                json.dump(self.shop, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[好感度] 商店保存失败: {e}")
    
    def _get_user_data(self, user_id: str) -> Dict:
        """获取用户好感度数据（全局）"""
        user_id = str(user_id)
        
        if user_id not in self.data:
            self.data[user_id] = {
                "favor": self.config["default_favor"],
                "last_update": time.time(),
                "last_daily": 0,
                "title": "",
                "purchased": []
            }
        
        return self.data[user_id]
    
    def _check_cooldown(self, user_id: str) -> bool:
        key = f"msg_{user_id}"
        now = time.time()
        if key in self.cooldowns:
            if now - self.cooldowns[key] < self.config["cooldown"]:
                return False
        self.cooldowns[key] = now
        return True
    
    def _clamp_favor(self, value: int) -> int:
        return max(self.config["min_favor"], min(self.config["max_favor"], value))
    
    def get_level(self, favor: int) -> Dict:
        for level in self.levels:
            if level["min"] <= favor <= level["max"]:
                return level
        return self.levels[4]
    
    def get_privilege_level(self, favor: int) -> str:
        if favor >= 1000:
            return "super"
        elif favor >= 500:
            return "vip"
        elif favor >= 200:
            return "high"
        else:
            return "normal"
    
    async def _analyze_with_ai(self, message: str, user_id: str) -> Optional[int]:
        if not self.ai or not self.config["ai_enabled"]:
            return None
        
        prompt = f"""分析以下用户发言对机器人好感度的影响。只返回一个数字，范围-10到10。
正面（表扬、感谢、友善）返回正数，负面（辱骂、攻击）返回负数，中性返回0。

用户发言：{message}

只返回数字。"""
        
        try:
            response = await self.ai.chat(prompt, use_personality=False)
            numbers = re.findall(r'-?\d+', response)
            if numbers:
                score = int(numbers[0])
                score = max(self.config["ai_min_score"], min(self.config["ai_max_score"], score))
                return score
        except Exception as e:
            print(f"[好感度] AI分析失败: {e}")
        return None
    
    def _analyze_with_keywords(self, message: str) -> int:
        message_lower = message.lower()
        total = 0
        for kw in self.config["keywords"]["increase"]:
            if kw["word"].lower() in message_lower:
                total += kw["value"]
        for kw in self.config["keywords"]["decrease"]:
            if kw["word"].lower() in message_lower:
                total += kw["value"]
        return total
    
    async def process_message(self, user_id: str, message: str) -> Optional[Tuple[int, str, bool, str, str]]:
        if not self.config["enabled"]:
            return None
        
        if not self._check_cooldown(user_id):
            return None
        
        change = None
        if self.config["ai_enabled"]:
            change = await self._analyze_with_ai(message, user_id)
        
        if change is None:
            change = self._analyze_with_keywords(message)
        
        if change == 0:
            return None
        
        user_data = self._get_user_data(user_id)
        old_favor = user_data["favor"]
        new_favor = self._clamp_favor(old_favor + change)
        user_data["favor"] = new_favor
        user_data["last_update"] = time.time()
        self._save_data()
        
        old_level = self.get_level(old_favor)["name"]
        new_level = self.get_level(new_favor)["name"]
        level_up = old_level != new_level
        
        print(f"[好感度] 用户 {user_id} {change:+d}，当前: {new_favor}")
        
        return change, f"{change:+d}", level_up, old_level, new_level
    
    # ==================== 每日签到 ====================
    async def daily_sign(self, user_id: str) -> Tuple[bool, str, int]:
        """每日签到"""
        from datetime import datetime
    
        user_data = self._get_user_data(user_id)
    
        # 使用日期字符串，避免类型问题
        today = datetime.now().strftime("%Y-%m-%d")
        last_daily = user_data.get("last_daily", "")
    
        if last_daily == today:
            return False, "今天已经签过到了哦~", 0
    
        bonus = self.config["daily_bonus"]
        user_data["favor"] = self._clamp_favor(user_data["favor"] + bonus)
        user_data["last_daily"] = today  # 存储格式: "2026-04-20"
        self._save_data()
    
        return True, f"签到成功！获得 {bonus} 好感度", bonus
    
    # ==================== 好感度查询 ====================
    def get_favor_info(self, user_id: str) -> Dict:
        user_data = self._get_user_data(user_id)
        favor = user_data["favor"]
        level = self.get_level(favor)
        
        return {
            "favor": favor,
            "level_name": level["name"],
            "level_color": level["color"],
            "level_badge": level["badge"],
            "title": user_data.get("title", ""),
            "purchased": user_data.get("purchased", [])
        }
    
    def get_favor(self, user_id: str) -> int:
        """获取用户好感度数值"""
        user_data = self._get_user_data(user_id)
        return user_data["favor"]
    
    def get_rank(self, limit: int = 10) -> List[Dict]:
        """获取全局好感度排行榜"""
        users = []
        for user_id, data in self.data.items():
            level = self.get_level(data["favor"])
            users.append({
                "user_id": user_id,
                "favor": data["favor"],
                "level_badge": level["badge"],
                "level_color": level["color"],
                "title": data.get("title", "")
            })
        users.sort(key=lambda x: x["favor"], reverse=True)
        return users[:limit]
    
    # ==================== 商店系统 ====================
    def get_shop_items(self) -> List[Dict]:
        return self.shop
    
    async def buy_item(self, user_id: str, item_id: str, websocket) -> Tuple[bool, str]:
        item = None
        for i in self.shop:
            if i["id"] == item_id:
                item = i
                break
        
        if not item:
            return False, f"商品 {item_id} 不存在"
        
        user_data = self._get_user_data(user_id)
        favor = user_data["favor"]
        
        if favor < item["cost"]:
            return False, f"好感度不足！需要 {item['cost']}，当前 {favor}"
        
        if item["type"] == "permanent" and item_id in user_data.get("purchased", []):
            return False, "你已经购买过这个商品了"
        
        if item["cooldown"] > 0:
            cooldown_key = f"action_{user_id}_{item_id}"
            if cooldown_key in self.action_cooldowns:
                remaining = item["cooldown"] - (time.time() - self.action_cooldowns[cooldown_key])
                if remaining > 0:
                    return False, f"操作冷却中，剩余 {int(remaining)} 秒"
        
        user_data["favor"] = self._clamp_favor(favor - item["cost"])
        
        if "purchased" not in user_data:
            user_data["purchased"] = []
        if item["type"] == "permanent" and item_id not in user_data["purchased"]:
            user_data["purchased"].append(item_id)
        
        if item["cooldown"] > 0:
            self.action_cooldowns[f"action_{user_id}_{item_id}"] = time.time()
        
        self._save_data()
        
        result_msg = await self._execute_action(user_id, item, websocket)
        
        return True, f"购买成功！消耗 {item['cost']} 好感度\n{result_msg}"
    
    async def _execute_action(self, user_id: str, item: Dict, websocket) -> str:
        if item["type"] != "action":
            return f"已购买 {item['name']}，可在个人信息中查看"
        
        if item["id"] == "greeting":
            return f"早安设置成功！明天早上我会单独对你说早安~"
        elif item["id"] == "pet":
            return f"（轻轻摸了摸 {user_id} 的头）要乖乖的哦~"
        elif item["id"] == "hug":
            return f"（给了 {user_id} 一个大大的拥抱）🤗"
        elif item["id"] == "song":
            songs = ["《孤勇者》", "《起风了》", "《稻香》", "《夜曲》", "《平凡之路》"]
            return f"推荐歌曲：{random.choice(songs)}，希望你喜欢~"
        elif item["id"] == "title":
            return f"已解锁自定义称号功能！使用 !设置称号 <称号> 来设置你的专属称号"
        
        return f"已使用 {item['name']}"
    
    async def set_title(self, user_id: str, title: str) -> Tuple[bool, str]:
        user_data = self._get_user_data(user_id)
        
        if "title" not in user_data.get("purchased", []):
            if user_data["favor"] < 200:
                return False, "好感度不足200，无法设置称号。可在商店购买【自定义称号】权限"
        
        if len(title) > 20:
            return False, "称号太长了，限制20字以内"
        
        user_data["title"] = title
        self._save_data()
        return True, f"称号已设置为：{title}"
    
    # ==================== 管理方法 ====================
    def set_favor(self, user_id: str, value: int, operator_id: str) -> Tuple[bool, str]:
        value = self._clamp_favor(value)
        user_data = self._get_user_data(user_id)
        old = user_data["favor"]
        user_data["favor"] = value
        user_data["last_update"] = time.time()
        self._save_data()
        return True, f"已将 {user_id} 的好感度从 {old} 设置为 {value}"
    
    def add_favor(self, user_id: str, delta: int, operator_id: str) -> Tuple[bool, str]:
        user_data = self._get_user_data(user_id)
        old = user_data["favor"]
        new = self._clamp_favor(old + delta)
        user_data["favor"] = new
        user_data["last_update"] = time.time()
        self._save_data()
        return True, f"已为 {user_id} {'增加' if delta > 0 else '减少'} {abs(delta)} 好感度（{old} → {new}）"
    
    def reset_all(self, operator_id: str) -> Tuple[bool, str]:
        self.data = {}
        self._save_data()
        return True, "已重置所有用户的好感度"
    
    def set_enabled(self, enabled: bool):
        self.config["enabled"] = enabled
        self._save_config()
    
    def set_notify_enabled(self, enabled: bool):
        self.config["notify_enabled"] = enabled
        self._save_config()
    
    def set_ai_enabled(self, enabled: bool):
        self.config["ai_enabled"] = enabled
        self._save_config()
    
    def get_status(self) -> str:
        total_users = len(self.data)
        return f"""【❤️ 好感度系统状态】
记录开关: {'✅ 开启' if self.config['enabled'] else '❌ 关闭'}
通知开关: {'✅ 开启' if self.config['notify_enabled'] else '🔇 关闭'}
AI分析: {'✅ 开启' if self.config['ai_enabled'] else '❌ 关闭'}
记录用户: {total_users} 人
每日签到奖励: {self.config['daily_bonus']} 好感度
商店商品: {len(self.shop)} 个

📋 用户命令:
  !好感度 (@用户) - 查看好感度
  !好感榜 - 查看全局排行榜
  !签到 - 每日签到
  !商店 - 查看可兑换商品
  !购买 <商品ID> - 购买商品
  !设置称号 <称号> - 设置专属称号

🔧 管理员命令:
  !好感度开关 开/关 - 记录开关
  !好感度通知 开/关 - 通知开关
  !好感度AI 开/关 - AI分析开关
  !好感度设置 <QQ> <数值> - 设置好感度
  !好感度增加 <QQ> <数值> - 增加好感度
  !好感度减少 <QQ> <数值> - 减少好感度
  !好感度重置全群 - 重置所有数据"""
