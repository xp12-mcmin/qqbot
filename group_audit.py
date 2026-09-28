# group_audit.py
"""
进群审核模块 - 独立、每群白名单、黑名单+违禁词+AI审批
只在进群那一刻检查，进群后不再管
默认关闭
"""
import os
import json
import time
import asyncio
from typing import Optional, Dict, List, Tuple


class GroupAudit:
    def __init__(self, data_dir="data", blacklist=None, banned_word_detector=None, ai=None):
        self.data_dir = data_dir
        self.config_file = os.path.join(data_dir, "group_audit_config.json")
        self.records_file = os.path.join(data_dir, "group_audit_records.json")
        os.makedirs(data_dir, exist_ok=True)
        
        # 外部依赖（注入）
        self.blacklist = blacklist
        self.banned_word_detector = banned_word_detector
        self.ai = ai
        
        # 配置
        self.config = {
            "enabled": False,              # 全局总开关，默认关
            "enabled_groups": [],          # 白名单群号列表
            "group_prompts": {},           # {group_id: "本群只收玩MC的"}
            "extra_keywords": [
                "骚扰", "广告", "代练", "外挂", "开挂", "卖号",
                "破防", "懦夫", "废物群", "垃圾群"
            ],
            "reject_message": "抱歉，你的加群申请未通过审核。",
            "blacklist_message": "你已被本机器人拉黑，无法加群。",
        }
        self.records: List[Dict] = []
        
        self._load_config()
        self._load_records()
        
        print(f"[进群审核] 初始化完成")
        print(f"[进群审核] 全局状态: {'开启' if self.config['enabled'] else '关闭'}")
        print(f"[进群审核] 白名单群数: {len(self.config['enabled_groups'])}")
    
    # ==================== 配置读写 ====================
    def _load_config(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                for k, v in saved.items():
                    self.config[k] = v
        except Exception as e:
            print(f"[进群审核] 配置加载失败: {e}")
    
    def _save_config(self):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[进群审核] 配置保存失败: {e}")
    
    def _load_records(self):
        try:
            if os.path.exists(self.records_file):
                with open(self.records_file, "r", encoding="utf-8") as f:
                    self.records = json.load(f)
                if len(self.records) > 200:
                    self.records = self.records[-200:]
        except Exception as e:
            print(f"[进群审核] 记录加载失败: {e}")
            self.records = []
    
    def _save_records(self):
        try:
            if len(self.records) > 200:
                self.records = self.records[-200:]
            with open(self.records_file, "w", encoding="utf-8") as f:
                json.dump(self.records, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[进群审核] 记录保存失败: {e}")
    
    def _add_record(self, group_id, user_id, nickname, comment, result, reason):
        self.records.append({
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "group_id": str(group_id),
            "user_id": str(user_id),
            "nickname": nickname,
            "comment": comment,
            "result": result,
            "reason": reason,
        })
        self._save_records()
    
    # ==================== 开关 ====================
    def set_global_enabled(self, enabled: bool) -> str:
        self.config["enabled"] = enabled
        self._save_config()
        return f"✅ 进群审核【全局】已{'开启' if enabled else '关闭'}"
    
    def is_global_enabled(self) -> bool:
        return self.config.get("enabled", False)
    
    def enable_group(self, group_id: str) -> bool:
        gid = str(group_id)
        if gid not in self.config["enabled_groups"]:
            self.config["enabled_groups"].append(gid)
            self._save_config()
            return True
        return False
    
    def disable_group(self, group_id: str) -> bool:
        gid = str(group_id)
        if gid in self.config["enabled_groups"]:
            self.config["enabled_groups"].remove(gid)
            self._save_config()
            return True
        return False
    
    def is_group_enabled(self, group_id: str) -> bool:
        if not self.config.get("enabled", False):
            return False
        return str(group_id) in self.config.get("enabled_groups", [])
    
    # ==================== 诉求 ====================
    def set_group_prompt(self, group_id: str, prompt: str) -> str:
        self.config["group_prompts"][str(group_id)] = prompt
        self._save_config()
        return f"✅ 已设置本群审核诉求"
    
    def get_group_prompt(self, group_id: str) -> str:
        return self.config["group_prompts"].get(str(group_id), "")
    
    def remove_group_prompt(self, group_id: str) -> bool:
        gid = str(group_id)
        if gid in self.config["group_prompts"]:
            del self.config["group_prompts"][gid]
            self._save_config()
            return True
        return False
    
    # ==================== 关键词 ====================
    def add_keyword(self, word: str) -> bool:
        word = word.strip()
        if not word or word in self.config["extra_keywords"]:
            return False
        self.config["extra_keywords"].append(word)
        self._save_config()
        return True
    
    def remove_keyword(self, word: str) -> bool:
        word = word.strip()
        if word in self.config["extra_keywords"]:
            self.config["extra_keywords"].remove(word)
            self._save_config()
            return True
        return False
    
    # ==================== 核心审核 ====================
    def _check_keywords(self, comment: str) -> Optional[str]:
        if not comment:
            return None
        comment_lower = comment.lower()
        
        for w in self.config.get("extra_keywords", []):
            if w.lower() in comment_lower:
                return w
        
        if self.banned_word_detector:
            for w in self.banned_word_detector.list_words():
                if w.lower() in comment_lower:
                    return w
        
        return None
    
    async def _ai_judge(self, group_id: str, user_id: str,
                        nickname: str, comment: str) -> str:
        """返回 同意 / 拒绝 / 不确定"""
        if not self.ai:
            return "拒绝"
        
        group_prompt = self.get_group_prompt(group_id)
        
        user_prompt = f"""请判断以下用户是否应该被允许加入QQ群。

群规/诉求：{group_prompt if group_prompt else '无特殊要求，正常交流即可'}

申请人信息：
- QQ号：{user_id}
- 昵称：{nickname}
- 加群留言：{comment if comment else '（无留言）'}

请只回复「同意」或「拒绝」两个字，不要解释。"""
        
        try:
            reply = await self.ai.chat(
                user_prompt,
                use_personality=False,
                group_id=None,
                user_id=None,
                favor=None
            )
            reply = (reply or "").strip()
            print(f"[进群审核] AI 原始回复: {reply[:50]}")
            
            # 严格判断
            has_agree = "同意" in reply
            has_reject = "拒绝" in reply
            
            if has_agree and not has_reject:
                return "同意"
            if has_reject and not has_agree:
                return "拒绝"
            return "不确定"
        except Exception as e:
            print(f"[进群审核] AI 异常: {e}")
            return "不确定"
    
    async def audit_request(self, group_id: str, user_id: str,
                            nickname: str, comment: str) -> Tuple[str, str]:
        """返回 (flag, reason)，flag: approve / reject"""
        gid = str(group_id)
        uid = str(user_id)
        
        # 1. 全局关 → 放行
        if not self.is_global_enabled():
            return "approve", "全局关闭，直接放行"
        
        # 2. 群不在白名单 → 放行
        if not self.is_group_enabled(gid):
            return "approve", "群未启用审核，直接放行"
        
        # 3. 黑名单
        if self.blacklist and self.blacklist.is_banned(uid):
            self._add_record(gid, uid, nickname, comment, "拒绝", "黑名单用户")
            return "reject", self.config["blacklist_message"]
        
        # 4. 违禁词
        hit_word = self._check_keywords(comment)
        if hit_word:
            self._add_record(gid, uid, nickname, comment, "拒绝", f"留言含违禁词: {hit_word}")
            return "reject", self.config["reject_message"]
        
        # 5. AI 审批
        ai_result = await self._ai_judge(gid, uid, nickname, comment)
        if ai_result == "同意":
            self._add_record(gid, uid, nickname, comment, "同意", "AI通过")
            return "approve", ""
        elif ai_result == "拒绝":
            self._add_record(gid, uid, nickname, comment, "拒绝", "AI拒绝")
            return "reject", self.config["reject_message"]
        else:
            self._add_record(gid, uid, nickname, comment, "拒绝", "AI不确定，默认拒绝")
            return "reject", self.config["reject_message"]
    
    # ==================== 状态 ====================
    def get_status(self, group_id: str = None) -> str:
        lines = [
            "【🚪 进群审核】",
            f"全局开关: {'开启' if self.config['enabled'] else '关闭'}",
            f"白名单群数: {len(self.config['enabled_groups'])}",
            f"审核关键词: {len(self.config['extra_keywords'])} 个",
            f"已配置诉求群: {len(self.config['group_prompts'])} 个",
        ]
        if group_id:
            gid = str(group_id)
            enabled = gid in self.config["enabled_groups"]
            lines.append(f"本群状态: {'✅ 已启用' if enabled else '❌ 未启用'}")
            prompt = self.get_group_prompt(gid)
            lines.append(f"本群诉求: {prompt if prompt else '（未设置，AI按默认标准）'}")
        return "\n".join(lines)
    
    def get_recent_records(self, limit=10) -> str:
        if not self.records:
            return "📭 暂无审核记录"
        lines = [f"📋 最近 {min(limit, len(self.records))} 条审核记录:"]
        for r in self.records[-limit:][::-1]:
            lines.append(
                f"  [{r['time']}] 群{r['group_id']} {r['nickname']}({r['user_id']}) → {r['result']} | {r['reason']}"
            )
        return "\n".join(lines)


_audit = None

def get_group_audit(blacklist=None, banned_word_detector=None, ai=None):
    global _audit
    if _audit is None:
        _audit = GroupAudit(
            blacklist=blacklist,
            banned_word_detector=banned_word_detector,
            ai=ai
        )
    return _audit
