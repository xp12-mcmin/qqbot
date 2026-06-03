"""
黑名单管理模块 - 独立文件
"""

import json
import os


class SimpleBlacklist:
    def __init__(self, file_path="data/blacklist.json"):
        self.file_path = file_path
        self.blacklist = set()
        self.reasons = {}
        self.load()
    
    def load(self):
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.blacklist = set(data.get("users", []))
                    self.reasons = data.get("reasons", {})
                    print(f"[调试] 黑名单加载成功 - 共{len(self.blacklist)}个用户")
            else:
                self.save()
                print("[调试] 黑名单文件不存在，已创建空文件")
        except Exception as e:
            print(f"[调试] 黑名单加载失败: {e}")
            self.blacklist = set()
            self.reasons = {}
    
    def save(self):
        try:
            data = {"users": list(self.blacklist), "reasons": self.reasons}
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[调试] 黑名单保存失败: {e}")
    
    def is_banned(self, user_id):
        user_id_str = str(user_id)
        return user_id_str in self.blacklist
    
    def add_user(self, user_id, reason="管理员封禁"):
        try:
            user_id_str = str(user_id)
            if user_id_str in self.blacklist:
                return False
            
            self.blacklist.add(user_id_str)
            self.reasons[user_id_str] = reason
            self.save()
            return True
        except Exception as e:
            print(f"[调试] 黑名单添加失败: {e}")
            return False
    
    def remove_user(self, user_id):
        try:
            user_id_str = str(user_id)
            if user_id_str not in self.blacklist:
                return False
            
            self.blacklist.remove(user_id_str)
            if user_id_str in self.reasons:
                del self.reasons[user_id_str]
            self.save()
            return True
        except Exception as e:
            print(f"[调试] 黑名单移除失败: {e}")
            return False
    
    def get_count(self):
        return len(self.blacklist)
    
    def get_reason(self, user_id):
        user_id_str = str(user_id)
        return self.reasons.get(user_id_str, "无")
    
    def list_users(self):
        result = []
        for user_id in self.blacklist:
            reason = self.reasons.get(user_id, "无")
            result.append(f"{user_id} (原因: {reason})")
        return result
