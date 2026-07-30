"""
AI黑名单系统 - 完整版
功能：永久/临时屏蔽用户，批量封禁，查罪名，支持时长
管理员：控制台直接管理
"""

import json
import os
import time
import re
from typing import Optional, Tuple


class SimpleBlacklist:
    def __init__(self, file_path="data/blacklist.json"):
        self.file_path = file_path
        self.blacklist = set()
        self.reasons = {}
        self.times = {}
        self.expires = {}
        self.durations = {}
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
                    self.expires = data.get("expires", {})
                    self.durations = data.get("durations", {})
        except Exception as e:
            print(f"[黑名单] 加载失败: {e}")
            self.blacklist = set()
            self.reasons = {}
            self.times = {}
            self.expires = {}
            self.durations = {}
    
    def save(self):
        """保存黑名单到文件"""
        try:
            data = {
                "users": list(self.blacklist),
                "reasons": self.reasons,
                "times": self.times,
                "expires": self.expires,
                "durations": self.durations,
                "last_update": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[黑名单] 保存失败: {e}")
    
    def is_banned(self, user_id: str) -> bool:
        """检查用户是否被屏蔽（自动处理过期）"""
        user_id_str = str(user_id)
        
        if user_id_str not in self.blacklist:
            return False
        
        if user_id_str in self.expires:
            expire_time = self.expires[user_id_str]
            if time.time() >= expire_time:
                self.unban_user(user_id_str)
                print(f"[黑名单] 用户 {user_id_str} 已自动解封（封禁到期）")
                return False
        
        return True
    
    def ban_user(self, user_id: str, reason: str = "骚扰AI", duration: int = 0) -> bool:
        """
        屏蔽用户
        :param user_id: 用户QQ号
        :param reason: 封禁原因（罪名）
        :param duration: 封禁时长（秒），0表示永久
        """
        user_id_str = str(user_id)
        if not user_id_str.isdigit():
            print(f"[黑名单] 错误: 用户ID {user_id_str} 不是有效数字")
            return False
        
        if user_id_str in self.blacklist:
            print(f"[黑名单] 用户 {user_id_str} 已在黑名单中")
            return False
        
        self.blacklist.add(user_id_str)
        self.reasons[user_id_str] = reason
        self.times[user_id_str] = time.strftime("%Y-%m-%d %H:%M:%S")
        
        if duration > 0:
            self.expires[user_id_str] = time.time() + duration
            self.durations[user_id_str] = duration
            duration_desc = self._format_duration(duration)
            print(f"[黑名单] 已屏蔽用户 {user_id_str}，时长: {duration_desc}，原因: {reason}")
        else:
            self.expires.pop(user_id_str, None)
            self.durations.pop(user_id_str, None)
            print(f"[黑名单] 已永久屏蔽用户 {user_id_str}，原因: {reason}")
        
        self.save()
        return True
    
    def unban_user(self, user_id: str) -> bool:
        """解除屏蔽用户"""
        user_id_str = str(user_id)
        if user_id_str in self.blacklist:
            self.blacklist.remove(user_id_str)
            self.reasons.pop(user_id_str, None)
            self.times.pop(user_id_str, None)
            self.expires.pop(user_id_str, None)
            self.durations.pop(user_id_str, None)
            self.save()
            print(f"[黑名单] 已解除屏蔽用户 {user_id_str}")
            return True
        return False
    
    def get_ban_info(self, user_id: str) -> dict:
        """获取用户的封禁详细信息（查罪名用）"""
        user_id_str = str(user_id)
        if user_id_str in self.blacklist:
            info = {
                "user_id": user_id_str,
                "reason": self.reasons.get(user_id_str, "未知原因"),
                "ban_time": self.times.get(user_id_str, "未知时间"),
            }
            if user_id_str in self.expires:
                remain = self.expires[user_id_str] - time.time()
                if remain > 0:
                    info["duration"] = self.durations.get(user_id_str, 0)
                    info["remaining"] = self._format_duration(int(remain))
                    info["expires_at"] = time.strftime("%Y-%m-%d %H:%M:%S", 
                                                       time.localtime(self.expires[user_id_str]))
                    info["status"] = "临时封禁"
                else:
                    info["status"] = "已过期（待清理）"
            else:
                info["duration"] = "永久"
                info["status"] = "永久封禁"
            return info
        return {}

    def get_all_banned(self) -> list:
        """获取所有被屏蔽用户"""
        self.clean_expired()
        result = []
        for user_id in sorted(self.blacklist):
            info = {
                "user_id": user_id,
                "reason": self.reasons.get(user_id, "未知原因"),
                "ban_time": self.times.get(user_id, "未知时间"),
            }
            if user_id in self.expires:
                remain = self.expires[user_id] - time.time()
                if remain > 0:
                    info["remaining"] = self._format_duration(int(remain))
                else:
                    continue
            else:
                info["remaining"] = "永久"
            result.append(info)
        return result

    def get_count(self) -> int:
        """获取黑名单用户数量（自动清理过期）"""
        self.clean_expired()
        return len(self.blacklist)

    def clear_all(self) -> None:
        """清空所有黑名单"""
        self.blacklist.clear()
        self.reasons.clear()
        self.times.clear()
        self.expires.clear()
        self.durations.clear()
        self.save()
        print("[黑名单] 已清空所有屏蔽记录")
    
    def clean_expired(self) -> int:
        """清理所有已过期的封禁，返回清理数量"""
        expired_users = []
        for user_id in list(self.blacklist):
            if user_id in self.expires:
                if time.time() >= self.expires[user_id]:
                    expired_users.append(user_id)
        
        for user_id in expired_users:
            self.unban_user(user_id)
        
        if expired_users:
            print(f"[黑名单] 清理了 {len(expired_users)} 个已过期封禁")
        return len(expired_users)
    
    def _format_duration(self, seconds: int) -> str:
        """格式化时长显示"""
        if seconds <= 0:
            return "永久"
        
        units = [
            (31536000, "年"),
            (2592000, "个月"),
            (604800, "周"),
            (86400, "天"),
            (3600, "小时"),
            (60, "分钟"),
            (1, "秒")
        ]
        
        parts = []
        remaining = seconds
        for unit_sec, unit_name in units:
            if remaining >= unit_sec:
                count = remaining // unit_sec
                remaining %= unit_sec
                parts.append(f"{int(count)}{unit_name}")
        
        return "".join(parts) if parts else "0秒"
    
    def list_users(self, limit: int = 20) -> list:
        """获取用户列表（用于显示），自动过滤已过期的"""
        self.clean_expired()
        
        result = []
        for user_id in sorted(self.blacklist):
            reason = self.reasons.get(user_id, "未知原因")
            
            if user_id in self.expires:
                remain = self.expires[user_id] - time.time()
                if remain > 0:
                    remain_str = self._format_duration(int(remain))
                    result.append(f"{user_id} (剩余: {remain_str}) - {reason}")
                else:
                    continue
            else:
                result.append(f"{user_id} (永久) - {reason}")
            
            if len(result) >= limit:
                break
        
        return result

# ==================== 控制台管理功能 ====================

    def console_show_list(self):
        """在控制台显示黑名单列表"""
        if not self.blacklist:
            print("当前黑名单为空")
            return
        
        print(f"\n当前有 {len(self.blacklist)} 个被屏蔽用户:")
        print("-"*55)
        
        for i, user_id in enumerate(sorted(self.blacklist), 1):
            reason = self.reasons.get(user_id, "未知原因")
            ban_time = self.times.get(user_id, "未知时间")
            
            if user_id in self.expires:
                remain = self.expires[user_id] - time.time()
                if remain > 0:
                    remain_str = self._format_duration(int(remain))
                else:
                    remain_str = "即将过期"
            else:
                remain_str = "永久"
            
            print(f"{i:2d}. QQ: {user_id}")
            print(f"    罪名: {reason} | 剩余: {remain_str}")
            print(f"    封禁时间: {ban_time}")
        
        print("-"*55)

    def console_ban_user(self):
        """通过控制台屏蔽用户（单个）"""
        qq = input("请输入要屏蔽的QQ号: ").strip()
        
        if not qq.isdigit():
            print("错误: QQ号必须是数字")
            return
        
        if self.is_banned(qq):
            print(f"QQ {qq} 已经被屏蔽了")
            return
        
        reason = input("请输入屏蔽原因（罪名，直接回车使用默认）: ").strip()
        if not reason:
            reason = "违规行为"
        
        duration_input = input("请输入封禁时长（单位：秒，直接回车为永久）: ").strip()
        duration = 0
        if duration_input:
            try:
                duration = int(duration_input)
                if duration < 0:
                    duration = 0
                if duration > 0:
                    print(f"封禁时长: {self._format_duration(duration)}")
            except ValueError:
                print("输入无效，将使用永久封禁")
                duration = 0
        
        if self.ban_user(qq, reason, duration):
            print(f"✅ 已成功屏蔽用户 {qq}")
        else:
            print(f"❌ 屏蔽用户 {qq} 失败")
    
    def console_ban_multi(self):
        """批量封禁用户（支持批量粘贴和文件读取）"""
        print("\n🔨 批量封禁用户")
        print("━" * 50)
        print("📝 粘贴QQ号列表，用空格、逗号或换行分隔")
        print("💡 也可以输入文件路径（例如: qq_list.txt）")
        print("📋 从QQ群复制成员时，可以直接粘贴")
        print("━" * 50)
        
        qq_input = input("\n请粘贴QQ号列表（或输入文件路径）: ").strip()
        if not qq_input:
            print("❌ 未输入任何内容")
            return
        
        qq_list = []
        
        # 如果是文件路径
        if os.path.exists(qq_input):
            try:
                with open(qq_input, 'r', encoding='utf-8') as f:
                    content = f.read()
                    qq_list = re.findall(r'\b(\d{5,11})\b', content)
                print(f"📄 从文件读取到 {len(qq_list)} 个QQ号")
            except Exception as e:
                print(f"❌ 读取文件失败: {e}")
                return
        else:
            # 直接解析输入的文本
            qq_list = re.findall(r'\b(\d{5,11})\b', qq_input)
        
        if not qq_list:
            print("❌ 没有找到有效的QQ号（5-11位数字）")
            return
        
        # 去重
        qq_list = list(set(qq_list))
        print(f"\n📋 共 {len(qq_list)} 个QQ号")
        
        # 显示前20个
        show = qq_list[:20]
        print(f"📋 前20个: {', '.join(show)}")
        if len(qq_list) > 20:
            print(f"   ... 共 {len(qq_list)} 人")
        
        # 询问是否继续
        confirm = input(f"\n⚠️ 确认封禁这 {len(qq_list)} 人？(y/N): ").strip().lower()
        if confirm != 'y':
            print("❌ 已取消操作")
            return
        
        # 输入封禁参数
        print("\n📝 设置封禁参数:")
        reason = input("封禁原因（直接回车使用默认）: ").strip()
        if not reason:
            reason = "批量封禁"
        
        duration_input = input("封禁时长（秒，直接回车为永久）: ").strip()
        duration = 0
        if duration_input:
            try:
                duration = int(duration_input)
                if duration > 0:
                    print(f"  时长: {self._format_duration(duration)}")
            except ValueError:
                print("输入无效，使用永久封禁")
                duration = 0
        
        # 执行批量封禁
        print(f"\n🔨 开始批量封禁 {len(qq_list)} 人...")
        success_count = 0
        fail_count = 0
        already_banned = 0
        success_list = []
        
        for i, qq in enumerate(qq_list, 1):
            if self.is_banned(qq):
                already_banned += 1
                continue
            
            if self.ban_user(qq, reason, duration):
                success_count += 1
                success_list.append(qq)
            else:
                fail_count += 1
            
            if i % 20 == 0:
                print(f"  进度: {i}/{len(qq_list)} (已封禁: {success_count})")
        
        # 输出结果
        print("\n" + "━" * 50)
        print(f"✅ 批量封禁完成！")
        print(f"  总处理: {len(qq_list)} 人")
        print(f"  成功封禁: {success_count} 人")
        print(f"  已在黑名单: {already_banned} 人")
        print(f"  失败: {fail_count} 人")
        if duration > 0:
            print(f"  时长: {self._format_duration(duration)}")
        else:
            print(f"  时长: 永久")
        print(f"  原因: {reason}")
        print("━" * 50)
    
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

    def console_search_user(self):
        """通过控制台查询用户封禁详情（查罪名）"""
        while True:
            print("\n🔍 【查罪名功能】")
            print("━" * 40)
            print("1. 按QQ号查询")
            print("2. 按罪名关键词搜索")
            print("0. 返回上级菜单")
            print("━" * 40)
            
            try:
                choice = input("\n请选择 (0-2): ").strip()
                
                if choice == "0":
                    return
                elif choice == "1":
                    self._search_by_qq()
                elif choice == "2":
                    self._search_by_reason()
                else:
                    print("❌ 无效选择，请输入 0、1 或 2")
            except KeyboardInterrupt:
                print("\n\n已取消")
                return
            except Exception as e:
                print(f"操作出错: {e}")

    def _search_by_qq(self):
        """按QQ号查询"""
        qq = input("\n请输入要查询的QQ号: ").strip()
        
        if not qq:
            print("❌ QQ号不能为空")
            return
        
        if not qq.isdigit():
            print("❌ QQ号必须是数字")
            return
        
        info = self.get_ban_info(qq)
        
        if not info:
            print(f"\n✅ 用户 {qq} 不在黑名单中")
            return
        
        self._print_ban_info(info)

    def _search_by_reason(self):
        """按罪名关键词搜索"""
        keyword = input("\n请输入罪名关键词（支持模糊搜索）: ").strip()
        
        if not keyword:
            print("❌ 关键词不能为空")
            return
        
        results = []
        for user_id in sorted(self.blacklist):
            reason = self.reasons.get(user_id, "未知原因")
            if keyword.lower() in reason.lower():
                info = self.get_ban_info(user_id)
                if info:
                    results.append(info)
        
        if not results:
            print(f"\n🔍 未找到罪名包含「{keyword}」的封禁记录")
            return
        
        print(f"\n🔍 找到 {len(results)} 条匹配「{keyword}」的封禁记录:")
        print("━" * 50)
        
        for i, info in enumerate(results, 1):
            print(f"{i:2d}. QQ: {info['user_id']}")
            print(f"    罪名: {info['reason']}")
            print(f"    状态: {info['status']}")
            if info.get('remaining'):
                print(f"    剩余: {info['remaining']}")
            print("   " + "-" * 40)
        
        if len(results) > 1:
            try:
                choice = input("\n输入序号查看详情（直接回车返回）: ").strip()
                if choice and choice.isdigit():
                    idx = int(choice) - 1
                    if 0 <= idx < len(results):
                        self._print_ban_info(results[idx])
                    else:
                        print("❌ 序号无效")
            except:
                pass

    def _print_ban_info(self, info: dict):
        """打印封禁详情"""
        print(f"\n🔍 【用户封禁详情】")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"👤 QQ号: {info['user_id']}")
        print(f"📋 罪名: {info['reason']}")
        print(f"📅 封禁时间: {info['ban_time']}")
        print(f"⏰ 封禁状态: {info['status']}")
        
        if info.get('duration') and info['duration'] != "永久":
            print(f"⏱️ 封禁时长: {info['duration']}")
        
        if info.get('remaining'):
            print(f"⌛ 剩余时间: {info['remaining']}")
        
        if info.get('expires_at'):
            print(f"📆 到期时间: {info['expires_at']}")
        
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    def console_show_status(self):
        """显示系统状态"""
        self.clean_expired()
        total = len(self.blacklist)
        permanent = sum(1 for uid in self.blacklist if uid not in self.expires)
        temporary = total - permanent
        
        print(f"\n黑名单系统状态:")
        print(f"  屏蔽用户数: {total} 人")
        print(f"  永久封禁: {permanent} 人")
        print(f"  临时封禁: {temporary} 人")
        print(f"  数据文件: {os.path.abspath(self.file_path)}")
        print(f"  最后更新: {time.strftime('%Y-%m-%d %H:%M:%S')}")

# ==================== 运行控制台管理界面 ====================

    def run_console_admin(self):
        """运行控制台管理界面"""
        while True:
            print("\n" + "="*50)
            print("AI黑名单管理系统 - 控制台模式")
            print("="*50)
            print("1. 查看黑名单列表")
            print("2. 屏蔽用户（单个）")
            print("3. 批量封禁用户")          # ← 支持批量粘贴和文件
            print("4. 解封用户")
            print("5. 查询用户封禁详情（查罪名）")
            print("6. 查看系统状态")
            print("7. 清空所有黑名单")
            print("8. 清理已过期封禁")
            print("0. 退出")
            print("="*50)
            
            try:
                choice = input("\n请选择操作 (0-8): ").strip()
                
                if choice == "0":
                    print("退出控制台管理")
                    break
                elif choice == "1":
                    self.console_show_list()
                elif choice == "2":
                    self.console_ban_user()
                elif choice == "3":
                    self.console_ban_multi()
                elif choice == "4":
                    self.console_unban_user()
                elif choice == "5":
                    self.console_search_user()
                elif choice == "6":
                    self.console_show_status()
                elif choice == "7":
                    if self.blacklist:
                        confirm = input(f"确认要清空 {len(self.blacklist)} 条黑名单吗？(y/N): ").strip().lower()
                        if confirm == 'y':
                            self.clear_all()
                            print("✅ 已清空所有黑名单")
                    else:
                        print("黑名单已经是空的")
                elif choice == "8":
                    count = self.clean_expired()
                    print(f"✅ 已清理 {count} 个已过期封禁")
                else:
                    print("无效选择，请重新输入")
            
            except KeyboardInterrupt:
                print("\n\n用户中断，退出控制台")
                break
            except Exception as e:
                print(f"操作出错: {e}")


# ==================== 使用示例 ====================
if __name__ == "__main__":
    blacklist = SimpleBlacklist()
    blacklist.run_console_admin()
