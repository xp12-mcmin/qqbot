# admin_manager.py
import json
import os
import time
from datetime import datetime

class AdminManager:
    """管理员管理系统 - 统一版本"""
    
    def __init__(self, data_dir="data", always_reload=True):
        """
        初始化管理员管理系统
        
        Args:
            data_dir: 数据目录
            always_reload: 是否总是重新加载文件（实时模式）
        """
        self.data_dir = data_dir
        self.always_reload = always_reload
        
        # 文件路径
        self.admins_file = os.path.join(data_dir, "admins.json")
        self.requests_file = os.path.join(data_dir, "admin_requests.json")
        
        # 确保目录存在
        os.makedirs(data_dir, exist_ok=True)
        
        # 缓存
        self._admins_cache = None
        self._requests_cache = None
        self._last_reload_time = 0
        
        # 初始化时加载数据
        self._reload_cache()
        
        print(f"[AdminManager] 初始化完成 (实时模式: {always_reload})")
        print(f"[AdminManager] 管理员: {len(self._admins_cache)} 个")
    
    # ==================== 核心方法 ====================
    
    def is_admin(self, user_id):
        """检查是否是管理员"""
        user_id_str = str(user_id)
        
        # 获取当前管理员列表
        admins = self._get_current_admins()
        
        is_admin = user_id_str in admins
        
        # 调试日志
        if is_admin:
            print(f"[AdminManager] {user_id_str} ✅ 是管理员")
        else:
            print(f"[AdminManager] {user_id_str} ❌ 不是管理员")
            
        return is_admin
    
    def apply_for_admin(self, user_id, reason="无"):
        """申请成为管理员"""
        user_id_str = str(user_id)
        
        # 1. 检查是否已经是管理员
        if self.is_admin(user_id_str):
            return "✅ 您已经是管理员了"
        
        # 2. 检查是否有待处理的申请
        requests = self._get_current_requests()
        existing_request = requests.get(user_id_str)
        
        if existing_request and existing_request.get("status") == "pending":
            return "⏳ 您的申请正在审核中，请耐心等待"
        
        # 3. 创建申请记录
        new_request = {
            "user_id": user_id_str,
            "reason": reason,
            "status": "pending",
            "apply_time": self._current_time(),
            "process_time": None,
            "processed_by": None,
            "reject_reason": None
        }
        
        # 更新缓存和文件
        requests[user_id_str] = new_request
        self._save_requests(requests)
        
        # 控制台通知
        self._notify_new_application(user_id_str, reason)
        
        return "📝 管理员申请已提交，请等待控制台审核"
    
    def approve_request(self, applicant_id, approver_id="console"):
        """批准申请"""
        applicant_str = str(applicant_id)
        approver_str = str(approver_id)
        
        print(f"[AdminManager] 开始批准 {applicant_str}")
        
        # 1. 获取当前数据
        admins = self._get_current_admins()
        requests = self._get_current_requests()
        
        # 2. 检查是否已经是管理员
        if applicant_str in admins:
            return False, "用户已经是管理员了"
        
        # 3. 检查申请记录
        request = requests.get(applicant_str)
        if not request:
            return False, "没有找到申请记录"
        
        # 4. 添加到管理员列表
        admins.add(applicant_str)
        
        # 5. 更新申请状态
        request["status"] = "approved"
        request["process_time"] = self._current_time()
        request["processed_by"] = approver_str
        if "reject_reason" in request:
            del request["reject_reason"]
        
        # 6. 保存所有数据
        self._save_admins(admins)
        self._save_requests(requests)
        
        # 7. 更新缓存
        self._admins_cache = admins
        self._requests_cache = requests
        self._last_reload_time = time.time()
        
        print(f"[AdminManager] 已批准 {applicant_str} 成为管理员")
        return True, f"已批准 {applicant_str} 成为管理员"
    
    def reject_request(self, applicant_id, reject_reason="无具体原因", rejecter_id="console"):
        """拒绝申请"""
        applicant_str = str(applicant_id)
        rejecter_str = str(rejecter_id)
        
        # 获取当前数据
        requests = self._get_current_requests()
        request = requests.get(applicant_str)
        
        if not request:
            return False, "没有找到申请记录"
        
        # 更新申请状态
        request["status"] = "rejected"
        request["process_time"] = self._current_time()
        request["processed_by"] = rejecter_str
        request["reject_reason"] = reject_reason
        
        # 保存
        self._save_requests(requests)
        self._requests_cache = requests
        
        return True, f"已拒绝 {applicant_str} 的申请"
    
    def remove_admin(self, target_id, operator_id="console"):
        """移除管理员"""
        target_str = str(target_id)
        operator_str = str(operator_id)
        
        # 获取当前数据
        admins = self._get_current_admins()
        
        if target_str not in admins:
            return False, "用户不是管理员"
        
        # 从管理员列表移除
        admins.remove(target_str)
        
        # 保存
        self._save_admins(admins)
        self._admins_cache = admins
        
        return True, f"已移除管理员 {target_str}"
    
    # ==================== 查询方法 ====================
    
    def get_request_status(self, user_id):
        """获取申请状态"""
        user_id_str = str(user_id)
        requests = self._get_current_requests()
        request = requests.get(user_id_str)
        
        if not request:
            return "no_request"
        return request.get("status", "unknown")
    
    def has_pending_request(self, user_id):
        """检查是否有待处理的申请"""
        return self.get_request_status(user_id) == "pending"
    
    def has_approved_request(self, user_id):
        """检查是否有已批准的申请"""
        return self.get_request_status(user_id) == "approved"
    
    def has_rejected_request(self, user_id):
        """检查是否有被拒绝的申请"""
        return self.get_request_status(user_id) == "rejected"
    
    def get_request_details(self, user_id):
        """获取申请详情"""
        user_id_str = str(user_id)
        requests = self._get_current_requests()
        return requests.get(user_id_str, {})
    
    def get_reject_reason(self, user_id):
        """获取拒绝原因"""
        request = self.get_request_details(user_id)
        return request.get("reject_reason", "无具体原因")
    
    def get_admin_count(self):
        """获取管理员数量"""
        admins = self._get_current_admins()
        return len(admins)
    
    def get_pending_count(self):
        """获取待处理申请数量"""
        requests = self._get_current_requests()
        count = sum(1 for r in requests.values() if r.get("status") == "pending")
        return count
    
    def list_admins(self):
        """获取管理员列表"""
        admins = self._get_current_admins()
        return sorted(list(admins))
    
    def list_pending_requests(self):
        """获取待处理申请列表"""
        requests = self._get_current_requests()
        pending = []
        for user_id, request in requests.items():
            if request.get("status") == "pending":
                pending.append({
                    "user_id": user_id,
                    "reason": request.get("reason", ""),
                    "apply_time": request.get("apply_time", "")
                })
        return pending
    
    # ==================== 工具方法 ====================
    
    def refresh(self):
        """强制刷新数据"""
        print("[AdminManager] 强制刷新数据...")
        self._reload_cache()
        print(f"[AdminManager] 刷新完成: {len(self._admins_cache)} 管理员")
        return True
    
    def get_stats(self):
        """获取统计信息"""
        return {
            "admins_count": self.get_admin_count(),
            "pending_count": self.get_pending_count(),
            "total_requests": len(self._get_current_requests())
        }
    
    # ==================== 私有方法 ====================
    
    def _get_current_admins(self):
        """获取当前管理员列表"""
        if self.always_reload:
            return self._load_admins_from_file()
        else:
            if self._admins_cache is None:
                self._admins_cache = self._load_admins_from_file()
            return self._admins_cache
    
    def _get_current_requests(self):
        """获取当前申请记录"""
        if self.always_reload:
            return self._load_requests_from_file()
        else:
            if self._requests_cache is None:
                self._requests_cache = self._load_requests_from_file()
            return self._requests_cache
    
    def _reload_cache(self):
        """重新加载缓存"""
        self._admins_cache = self._load_admins_from_file()
        self._requests_cache = self._load_requests_from_file()
        self._last_reload_time = time.time()
    
    def _load_admins_from_file(self):
        """从文件加载管理员列表"""
        try:
            if os.path.exists(self.admins_file):
                with open(self.admins_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return set(data.get("admins", []))
            else:
                # 创建空文件
                with open(self.admins_file, 'w', encoding='utf-8') as f:
                    json.dump({"admins": []}, f, ensure_ascii=False, indent=2)
                return set()
        except Exception as e:
            print(f"[AdminManager] 加载管理员失败: {e}")
            return set()
    
    def _load_requests_from_file(self):
        """从文件加载申请记录"""
        try:
            if os.path.exists(self.requests_file):
                with open(self.requests_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # 创建空文件
                with open(self.requests_file, 'w', encoding='utf-8') as f:
                    json.dump({}, f, ensure_ascii=False, indent=2)
                return {}
        except Exception as e:
            print(f"[AdminManager] 加载申请失败: {e}")
            return {}
    
    def _save_admins(self, admins):
        """保存管理员列表"""
        try:
            with open(self.admins_file, 'w', encoding='utf-8') as f:
                json.dump({"admins": list(admins)}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[AdminManager] 保存管理员失败: {e}")
    
    def _save_requests(self, requests):
        """保存申请记录"""
        try:
            with open(self.requests_file, 'w', encoding='utf-8') as f:
                json.dump(requests, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[AdminManager] 保存申请失败: {e}")
    
    def _current_time(self):
        """获取当前时间字符串"""
        return time.strftime("%Y-%m-%d %H:%M:%S")
    
    def _notify_new_application(self, user_id, reason):
        """通知新申请"""
        print(f"\n{'='*60}")
        print(f"📢 [管理员申请通知]")
        print(f"👤 申请人: {user_id}")
        print(f"📝 申请理由: {reason}")
        print(f"⏰ 申请时间: {self._current_time()}")
        print(f"📊 待处理申请: {self.get_pending_count()} 个")
        print(f"{'='*60}")
        print(f"💻 请使用图形化管理控制台处理申请")
        print(f"{'='*60}")

# ==================== 测试代码 ====================
if __name__ == "__main__":
    print("=== AdminManager 测试 ===")
    
    # 创建实例
    manager = AdminManager(always_reload=True)
    
    # 测试基本功能
    print(f"1. 管理员数量: {manager.get_admin_count()}")
    print(f"2. 待处理申请: {manager.get_pending_count()}")
    
    # 测试属性
    print(f"\n3. 属性检查:")
    print(f"   has admins: {hasattr(manager, '_admins_cache')}")
    print(f"   has requests: {hasattr(manager, '_requests_cache')}")
    
    # 测试方法
    print(f"\n4. 方法检查:")
    methods = ['is_admin', 'apply_for_admin', 'approve_request', 
               'get_request_status', 'refresh', 'get_admin_count']
    for method in methods:
        exists = hasattr(manager, method)
        print(f"   {method}: {'✅' if exists else '❌'}")
    
    print("\n=== 测试完成 ===")
