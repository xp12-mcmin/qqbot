# blacklist_checker.py
import json
import os

class BlacklistChecker:
    """极简黑名单检查器"""
    
    def __init__(self, blacklist_file="data/blacklist.json"):
        self.blacklist_file = blacklist_file
        self.blacklist = set()
        self._load_blacklist()
    
    def _load_blacklist(self):
        """加载黑名单"""
        try:
            if os.path.exists(self.blacklist_file):
                with open(self.blacklist_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 假设黑名单文件格式: {"users": ["123456", "789012"]}
                    users = data.get("users", [])
                    self.blacklist = set(str(uid) for uid in users)
                    print(f"[黑名单] 已加载 {len(self.blacklist)} 个用户")
            else:
                print(f"[黑名单] 文件不存在: {self.blacklist_file}")
                self.blacklist = set()
        except Exception as e:
            print(f"[黑名单] 加载失败: {e}")
            self.blacklist = set()
    
    def is_banned(self, user_id):
        """检查用户是否在黑名单中"""
        return str(user_id) in self.blacklist
    
    def check_and_get_response(self, data):
        """
        检查消息是否需要拦截
        返回: 如果需要拦截返回消息，否则返回None
        """
        try:
            # 1. 提取用户ID（最简方式）
            user_id = ""
            if isinstance(data, dict):
                user_id = data.get("user_id")
            
            if not user_id:
                return None
            
            user_id_str = str(user_id)
            
            # 2. 检查黑名单
            if self.is_banned(user_id_str):
                # 3. 生成拦截消息
                message_type = data.get("message_type", "")
                
                if message_type == "private":
                    return "🚫 您已被加入黑名单，无法使用AI功能"
                elif message_type == "group":
                    return f"[CQ:at,qq={user_id_str}] 🚫 您已被加入黑名单"
                else:
                    return "🚫 您已被加入黑名单"
            
            return None
            
        except Exception as e:
            print(f"[黑名单检查] 出错: {e}")
            return None  # 即使出错也不影响正常功能
