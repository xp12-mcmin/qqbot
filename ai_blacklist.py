"""
AI黑名单系统 - 精简版
功能：永久屏蔽骚扰用户，数据持久化
管理员：控制台直接管理
"""

import json
import os
import time

class SimpleBlacklist:
    def __init__(self, file_path="blacklist.json"):
        self.file_path = file_path
        self.blacklist = set()      # 被屏蔽用户集合
        self.reasons = {}           # 屏蔽原因
        self.times = {}             # 屏蔽时间
        self.load()
        print(f"[黑名单] 已加载 {len(self.blacklist)} 个用户")
    
    def load(self):
        """从文件加载黑名单"""
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.blacklist = set(data.get("users", []))
                    self.reasons = data.get("reasons", {})
                    self.times = data.get("times", {})
        except Exception as e:
            print(f"[黑名单] 加载失败: {e}")
            self.blacklist = set()
    
    def save(self):
        """保存黑名单到文件"""
        try:
            data = {
                "users": list(self.blacklist),
                "reasons": self.reasons,
                "times": self.times,
                "last_update": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[黑名单] 保存失败: {e}")
    
    def is_banned(self, user_id: str) -> bool:
        """检查用户是否被屏蔽"""
        return str(user_id) in self.blacklist
    
    def ban_user(self, user_id: str, reason: str = "骚扰AI") -> bool:
        """屏蔽用户"""
        user_id_str = str(user_id)
        if not user_id_str.isdigit():
            print(f"[黑名单] 错误: 用户ID {user_id_str} 不是有效数字")
            return False
        
        self.blacklist.add(user_id_str)
        self.reasons[user_id_str] = reason
        self.times[user_id_str] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.save()
        
        print(f"[黑名单] 已屏蔽用户 {user_id_str}，原因: {reason}")
        return True
    
    def unban_user(self, user_id: str) -> bool:
        """解除屏蔽用户"""
        user_id_str = str(user_id)
        if user_id_str in self.blacklist:
            self.blacklist.remove(user_id_str)
            if user_id_str in self.reasons:
                del self.reasons[user_id_str]
            if user_id_str in self.times:
                del self.times[user_id_str]
            self.save()
            
            print(f"[黑名单] 已解除屏蔽用户 {user_id_str}")
            return True
        return False
    def get_ban_info(self, user_id: str) -> dict:
        """获取用户的封禁信息"""
        user_id_str = str(user_id)
        if user_id_str in self.blacklist:
            return {
                "user_id": user_id_str,
                "reason": self.reasons.get(user_id_str, "未知原因"),
                "ban_time": self.times.get(user_id_str, "未知时间")
            }
        return {}

    def get_all_banned(self) -> list:
        """获取所有被屏蔽用户"""
        result = []
        for user_id in sorted(self.blacklist):
            result.append({
                "user_id": user_id,
                "reason": self.reasons.get(user_id, "未知原因"),
                "ban_time": self.times.get(user_id, "未知时间")
            })
        return result

    def get_count(self) -> int:
        """获取黑名单用户数量"""
        return len(self.blacklist)

    def clear_all(self) -> None:
        """清空所有黑名单"""
        self.blacklist.clear()
        self.reasons.clear()
        self.times.clear()
        self.save()
        print("[黑名单] 已清空所有屏蔽记录")

# ==================== 控制台管理功能 ====================

    def console_show_list(self):
        """在控制台显示黑名单列表"""
        if not self.blacklist:
            print("当前黑名单为空")
            return
        
        print(f"\n当前有 {len(self.blacklist)} 个被屏蔽用户:")
        print("-"*50)
        
        for i, user_id in enumerate(sorted(self.blacklist), 1):
            reason = self.reasons.get(user_id, "未知原因")
            ban_time = self.times.get(user_id, "未知时间")
            
            print(f"{i:2d}. QQ: {user_id}")
            print(f"    原因: {reason}")
            print(f"    时间: {ban_time}")
        
        print("-"*50)

    def console_ban_user(self):
        """通过控制台屏蔽用户"""
        qq = input("请输入要屏蔽的QQ号: ").strip()
        
        if not qq.isdigit():
            print("错误: QQ号必须是数字")
            return
        
        if self.is_banned(qq):
            print(f"QQ {qq} 已经被屏蔽了")
            return
        
        reason = input("请输入屏蔽原因（直接回车使用默认）: ").strip()
        if not reason:
            reason = "违规行为"
        
        if self.ban_user(qq, reason):
            print(f"✅ 已成功屏蔽用户 {qq}")
        else:
            print(f"❌ 屏蔽用户 {qq} 失败")
    def console_unban_user(self):
        """通过控制台解封用户"""
        qq = input("请输入要解封的QQ号: ").strip()
        
        if not qq.isdigit():
            print("错误: QQ号必须是数字")
            return
        
        if not self.is_banned(qq):
            print(f"QQ {qq} 不在黑名单中")
            return
        
        if self.unban_user(qq):
            print(f"✅ 已成功解封用户 {qq}")
        else:
            print(f"❌ 解封用户 {qq} 失败")

    def console_show_status(self):
        """显示系统状态"""
        print(f"\n黑名单系统状态:")
        print(f"  屏蔽用户数: {len(self.blacklist)}")
        print(f"  数据文件: {os.path.abspath(self.file_path)}")
        print(f"  最后更新: {time.strftime('%Y-%m-%d %H:%M:%S')}")

# ==================== 运行控制台管理界面 ====================

    def run_console_admin(self):
        """运行控制台管理界面"""
        while True:
            print("\n" + "="*40)
            print("AI黑名单管理系统 - 控制台模式")
            print("="*40)
            print("1. 查看黑名单列表")
            print("2. 屏蔽用户")
            print("3. 解封用户")
            print("4. 查看系统状态")
            print("5. 清空所有黑名单")
            print("0. 退出")
            print("="*40)
            
            try:
                choice = input("\n请选择操作 (0-5): ").strip()
                
                if choice == "0":
                    print("退出控制台管理")
                    break
                elif choice == "1":
                    self.console_show_list()
                elif choice == "2":
                    self.console_ban_user()
                elif choice == "3":
                    self.console_unban_user()
                elif choice == "4":
                    self.console_show_status()
                elif choice == "5":
                    if self.blacklist:
                        confirm = input(f"确认要清空 {len(self.blacklist)} 条黑名单吗？(y/N): ").strip().lower()
                        if confirm == 'y':
                            self.clear_all()
                            print("✅ 已清空所有黑名单")
                    else:
                        print("黑名单已经是空的")
                else:
                    print("无效选择，请重新输入")
            
            except KeyboardInterrupt:
                print("\n\n用户中断，退出控制台")
                break
            except Exception as e:
                print(f"操作出错: {e}")

# ==================== QQ机器人集成接口 ====================

def process_qq_command(self, sender_id: str, message: str) -> str:
    """
    处理QQ消息中的简单命令
    注意：这个版本只支持查询，不支持QQ上修改（安全考虑）
    """
    # 解析命令
    parts = message.strip().split(maxsplit=1)
    if len(parts) < 1:
        return ""
    
    command = parts[0].lower()
    
    if command in ["检查", "check", "查询"]:
        if len(parts) < 2:
            return "❌ 使用方法: 检查 <QQ号>"
        
        target_id = parts[1]
        
        if self.is_banned(target_id):
            info = self.get_ban_info(target_id)
            return f"🚫 用户 {target_id} 已被屏蔽\n原因: {info.get('reason', '未知')}"
        else:
            return f"✅ 用户 {target_id} 未被屏蔽"
    
    elif command in ["黑名单状态", "status"]:
        return f"📊 黑名单状态\n已屏蔽用户: {len(self.blacklist)} 人"
    
    return ""
# ==================== 使用示例 ====================
if __name__ == "__main__":
    # 创建黑名单实例
    blacklist = SimpleBlacklist()
    
    # 运行控制台管理界面
    blacklist.run_console_admin()


# ==================== 集成到QQ机器人的方法 ====================
"""
在你的主程序中这样使用：

# 1. 导入黑名单类
from ai_blacklist import SimpleBlacklist

# 2. 在机器人初始化时创建实例
class YourAIBot:
    def __init__(self):
        self.blacklist = SimpleBlacklist()
        
    async def handle_message(self, data):
        # 提取用户ID
        user_id = str(data.get('user_id', ''))
        message = data.get('message', '').strip()
        
        # 3. 检查是否被屏蔽
        if self.blacklist.is_banned(user_id):
            return "您已被屏蔽，无法使用AI功能"
        
        # 4. 处理查询命令（可选）
        if message.startswith(("检查 ", "查询 ", "check ")):
            reply = self.blacklist.process_qq_command(user_id, message)
            if reply:
                return reply
        
        # ... 原有AI处理逻辑 ...
        
# 5. 需要管理黑名单时，直接运行这个文件：
# python ai_blacklist.py
"""
