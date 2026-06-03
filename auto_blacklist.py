# auto_blacklist.py
"""
自动黑名单模块 - 独立运行
功能：监听禁言事件，自动拉黑禁言者
"""

import json
import os
import time
from datetime import datetime
import threading

class AutoBlacklist:
    """自动黑名单处理模块"""
    
    def __init__(self, config_file="config/blacklist_config.json"):
        self.event_file = "data/mute_events.json"
        self.blacklist_file = "data/blacklist.json"
        self.processed_file = "data/processed_events.json"
        
        # 加载配置
        self.config = self._load_config(config_file)
        
        # 已处理的事件ID记录
        self.processed_events = set()
        self._load_processed_events()
        
        print("=" * 60)
        print("🤖 自动黑名单模块 v1.0")
        print("=" * 60)
        print(f"📁 监听文件: {self.event_file}")
        print(f"🔧 黑名单文件: {self.blacklist_file}")
        print(f"⚡ 触发时长: {self.config['min_duration']}秒")
        print(f"📊 已处理事件: {len(self.processed_events)} 个")
        print("=" * 60)
    
    def _load_config(self, config_file):
        """加载配置文件"""
        default_config = {
            "enabled": True,
            "min_duration": 60,           # 触发黑名单的最小禁言时长
            "exempt_users": [],           # 豁免用户列表
            "auto_revenge": True,         # 是否自动拉黑
            "check_interval": 5,          # 检查间隔(秒)
            "max_retry": 3,               # 最大重试次数
            "log_level": "INFO"           # 日志级别
        }
        
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
                print(f"[配置] 已加载用户配置")
        except Exception as e:
            print(f"[配置] 加载失败: {e}")
        
        return default_config
    
    def _load_processed_events(self):
        """加载已处理的事件"""
        try:
            if os.path.exists(self.processed_file):
                with open(self.processed_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.processed_events = set(data.get("processed", []))
                print(f"[处理记录] 已加载 {len(self.processed_events)} 个已处理事件")
        except Exception as e:
            print(f"[处理记录] 加载失败: {e}")
            self.processed_events = set()
    
    def _save_processed_events(self):
        """保存已处理的事件"""
        try:
            data = {
                "processed": list(self.processed_events),
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(self.processed_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[处理记录] 保存失败: {e}")
    
    def _generate_event_id(self, mute_event):
        """生成事件唯一ID"""
        operator_id = mute_event.get("operator_id", "unknown")
        timestamp = mute_event.get("timestamp", 0)
        duration = mute_event.get("duration", 0)
        
        return f"{operator_id}_{int(timestamp)}_{duration}"
    
    def _load_blacklist(self):
        """加载黑名单"""
        try:
            if os.path.exists(self.blacklist_file):
                with open(self.blacklist_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # 创建空的黑名单
                empty_data = {
                    "users": [],
                    "reasons": {},
                    "version": "1.0",
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                with open(self.blacklist_file, 'w', encoding='utf-8') as f:
                    json.dump(empty_data, f, ensure_ascii=False, indent=2)
                return empty_data
        except Exception as e:
            print(f"[黑名单] 加载失败: {e}")
            return {"users": [], "reasons": {}}
    
    def _save_blacklist(self, data):
        """保存黑名单"""
        try:
            with open(self.blacklist_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"[黑名单] 保存失败: {e}")
            return False
    
    def _add_to_blacklist(self, user_id, reason):
        """添加用户到黑名单"""
        try:
            user_id_str = str(user_id)
            
            # 检查豁免用户
            if user_id_str in self.config["exempt_users"]:
                print(f"[自动黑名单] ⚠️ 用户 {user_id_str} 是豁免用户，跳过")
                return {"status": "exempt"}
            
            # 加载黑名单
            blacklist_data = self._load_blacklist()
            users = blacklist_data.get("users", [])
            reasons = blacklist_data.get("reasons", {})
            
            # 检查是否已在黑名单
            if user_id_str in users:
                print(f"[自动黑名单] ⚠️ 用户 {user_id_str} 已在黑名单中")
                return {"status": "already_banned"}
            
            # 添加到黑名单
            users.append(user_id_str)
            reasons[user_id_str] = f"自动黑名单: {reason}"
            
            blacklist_data["users"] = users
            blacklist_data["reasons"] = reasons
            blacklist_data["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 保存
            if self._save_blacklist(blacklist_data):
                print(f"[自动黑名单] ✅ 已拉黑用户 {user_id_str}")
                print(f"[自动黑名单] 📝 原因: {reason}")
                return {"status": "success", "user_id": user_id_str}
            else:
                return {"status": "save_failed"}
                
        except Exception as e:
            print(f"[自动黑名单] ❌ 拉黑失败: {e}")
            return {"status": "error", "error": str(e)}
    
    def check_new_events(self):
        """检查新的事件并处理"""
        if not self.config["enabled"]:
            return
        
        try:
            # 读取事件文件
            if not os.path.exists(self.event_file):
                return
            
            with open(self.event_file, 'r', encoding='utf-8') as f:
                events = json.load(f)
            
            # 处理新事件
            new_count = 0
            for event in events:
                event_id = self._generate_event_id(event)
                
                # 检查是否已处理
                if event_id in self.processed_events:
                    continue
                
                # 标记为已处理
                self.processed_events.add(event_id)
                new_count += 1
                
                # 处理事件
                self._process_mute_event(event)
            
            # 如果有新事件，保存处理记录
            if new_count > 0:
                self._save_processed_events()
                print(f"[自动黑名单] 处理了 {new_count} 个新事件")
                
        except Exception as e:
            print(f"[自动黑名单] 检查事件失败: {e}")
    
    def _process_mute_event(self, event):
        """处理单个禁言事件"""
        operator_id = event.get("operator_id")
        duration = event.get("duration", 0)
        
        print(f"[自动黑名单] 🔍 处理事件: 用户 {operator_id}, 禁言 {duration}秒")
        
        # 检查是否达到触发条件
        if duration < self.config["min_duration"]:
            print(f"[自动黑名单] 禁言时长 {duration}秒 < {self.config['min_duration']}秒，忽略")
            return
        
        # 生成原因
        reason = self._generate_reason(duration)
        
        # 自动拉黑
        if self.config["auto_revenge"]:
            result = self._add_to_blacklist(operator_id, reason)
            
            # 记录日志
            self._log_action(event, result)
    
    def _generate_reason(self, duration):
        """生成黑名单原因"""
        if duration <= 60:
            return f"禁言机器人 {duration}秒"
        elif duration <= 300:
            return f"禁言机器人 {duration}秒 (警告)"
        elif duration <= 1800:
            return f"严重禁言机器人 {duration}秒"
        elif duration <= 3600:
            return f"禁言机器人1小时"
        else:
            return f"永久禁言机器人"
    
    def _log_action(self, event, result):
        """记录操作日志"""
        log_file = "data/blacklist_log.json"
        
        try:
            logs = []
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            
            log_entry = {
                "event": event,
                "result": result,
                "timestamp": time.time(),
                "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            logs.append(log_entry)
            
            # 只保留最近100条日志
            if len(logs) > 100:
                logs = logs[-100:]
            
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"[日志] 记录失败: {e}")
    
    def start_monitoring(self):
        """开始监控"""
        print("[自动黑名单] 🚀 开始监控...")
        print(f"[自动黑名单] 🔄 检查间隔: {self.config['check_interval']}秒")
        
        try:
            while True:
                self.check_new_events()
                time.sleep(self.config["check_interval"])
        except KeyboardInterrupt:
            print("\n[自动黑名单] 正在停止...")
            self._save_processed_events()
            print("[自动黑名单] 已保存处理记录")
        except Exception as e:
            print(f"[自动黑名单] 监控异常: {e}")

# ==================== 启动脚本 ====================
def main():
    """主函数"""
    print("=" * 60)
    print("🤖 自动黑名单模块启动")
    print("=" * 60)
    
    # 创建自动黑名单实例
    auto_blacklist = AutoBlacklist()
    
    # 开始监控
    auto_blacklist.start_monitoring()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n程序已停止")
    except Exception as e:
        print(f"程序异常: {e}")
        input("按Enter键退出...")
