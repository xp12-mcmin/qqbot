"""
管理员管理模块 - 独立文件
"""

import json
import os
from datetime import datetime


class AdminManager:
    def __init__(self):
        self.data_dir = "data"
        self.admins_file = os.path.join(self.data_dir, "admins.json")
        self.requests_file = os.path.join(self.data_dir, "admin_requests.json")
        os.makedirs(self.data_dir, exist_ok=True)
        self.admins = self._load_admins()
        self.requests = self._load_requests()
        print(f"[调试] 管理员模块初始化完成 - 现有管理员：{len(self.admins)}人")
    
    def _load_admins(self):
        if os.path.exists(self.admins_file):
            try:
                with open(self.admins_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return set(str(admin) for admin in data.get("admins", []))
            except:
                return set()
        return set()
    
    def _load_requests(self):
        if os.path.exists(self.requests_file):
            try:
                with open(self.requests_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_admins(self):
        with open(self.admins_file, 'w', encoding='utf-8') as f:
            json.dump({"admins": list(self.admins)}, f, ensure_ascii=False, indent=2)
    
    def _save_requests(self):
        with open(self.requests_file, 'w', encoding='utf-8') as f:
            json.dump(self.requests, f, ensure_ascii=False, indent=2)
    
    def submit_apply(self, user_id, reason):
        user_id_str = str(user_id).strip()
        if not user_id_str:
            return False, "QQ号不能为空"
        
        self.requests[user_id_str] = {
            "reason": reason.strip() if reason else "无",
            "status": "pending",
            "apply_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "process_time": "",
            "processed_by": "",
            "reject_reason": ""
        }
        self._save_requests()
        return True, f"申请提交成功（QQ：{user_id_str}）"
    
    def approve_request(self, user_id, operator):
        user_id_str = str(user_id).strip()
        operator_str = str(operator)
        if not user_id_str:
            return False, "QQ号不能为空"
        
        if user_id_str not in self.requests:
            return False, "该用户未提交申请"
        
        if self.requests[user_id_str]["status"] == "approved":
            return False, "该用户已是管理员"
        
        self.admins.add(user_id_str)
        self._save_admins()
        self.requests[user_id_str].update({
            "status": "approved",
            "process_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "processed_by": operator_str
        })
        self._save_requests()
        return True, f"已批准 {user_id_str} 成为管理员"
    
    def reject_request(self, user_id, operator, reject_reason):
        user_id_str = str(user_id).strip()
        operator_str = str(operator)
        if not user_id_str:
            return False, "QQ号不能为空"
        
        if user_id_str not in self.requests:
            return False, "该用户未提交申请"
        
        self.requests[user_id_str].update({
            "status": "rejected",
            "process_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "processed_by": operator_str,
            "reject_reason": reject_reason.strip() if reject_reason else "无"
        })
        self._save_requests()
        return True, f"已拒绝 {user_id_str} 的申请"
    
    def remove_admin(self, user_id, operator):
        user_id_str = str(user_id).strip()
        operator_str = str(operator)
        if not user_id_str:
            return False, "QQ号不能为空"
        
        if user_id_str not in self.admins:
            return False, "该用户不是管理员"
        
        self.admins.remove(user_id_str)
        self._save_admins()
        if user_id_str in self.requests:
            self.requests[user_id_str]["status"] = "removed"
            self.requests[user_id_str]["remove_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.requests[user_id_str]["removed_by"] = operator_str
            self._save_requests()
        
        return True, f"已移除 {user_id_str} 的管理员权限"
    
    def is_admin(self, user_id):
        return str(user_id).strip() in self.admins
