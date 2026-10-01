# notify_manager.py
"""
被踢通知 / 退群群发 管理器（独立模块）

功能：
1. 机器人被踢 → 拉黑踢人者 + 私聊通知【订阅了被踢通知的管理员】
2. 别人退群/被踢 → 群发提示（按群独立开关，默认关）
3. 持久化配置到 data/kick_notify.json
"""
import os
import json
import time
from datetime import datetime


class KickNotifyManager:
    """被踢通知 / 退群群发 管理器"""

    def __init__(self, config_file="data/kick_notify.json"):
        self.config_file = config_file

        # ========== 被踢通知订阅者（管理员QQ列表，默认空）==========
        # 谁发 "被踢通知 开" 就加进来，谁发 "被踢通知 关" 就移除
        self.kick_notify_subscribers = set()

        # ========== 退群群发：按群，默认关（只存开启的群）==========
        self.leave_notify_groups = set()

        # ========== 冷却记录 ==========
        self._leave_cooldown = {}

        # 加载配置
        self._load()

    # ==================== 持久化 ====================

    def _load(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                self.kick_notify_subscribers = set(str(x) for x in cfg.get("kick_notify_subscribers", []))
                self.leave_notify_groups = set(str(x) for x in cfg.get("leave_notify_groups", []))
                print(f"[被踢通知] 配置加载成功")
                print(f"[被踢通知] 被踢通知订阅者 {len(self.kick_notify_subscribers)} 人: {self.kick_notify_subscribers}")
                print(f"[被踢通知] 退群群发已开启 {len(self.leave_notify_groups)} 个群: {self.leave_notify_groups}")
            else:
                print(f"[被踢通知] 配置文件不存在，使用默认值并创建")
                self._save()
        except Exception as e:
            print(f"[被踢通知] 配置加载失败: {e}")
            self.kick_notify_subscribers = set()
            self.leave_notify_groups = set()

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            cfg = {
                "kick_notify_subscribers": sorted(self.kick_notify_subscribers),
                "leave_notify_groups": sorted(self.leave_notify_groups),
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[被踢通知] 配置保存失败: {e}")

    # ==================== 判断 ====================

    def has_subscribers(self) -> bool:
        """是否有管理员订阅了被踢通知"""
        return len(self.kick_notify_subscribers) > 0

    def is_leave_notify_enabled(self, group_id) -> bool:
        """退群群发：按群，默认关"""
        return str(group_id) in self.leave_notify_groups

    # ==================== 核心处理 ====================

    async def handle_group_decrease(self, data, handler):
        """
        处理群成员减少事件
        需要 handler 提供：
          - handler.bot_self_id
          - handler.blacklist
          - handler.admin_manager
          - handler.disabled_groups
          - handler.websocket
        """
        try:
            sub_type = data.get("sub_type", "")
            group_id = str(data.get("group_id", ""))
            operator_id = str(data.get("operator_id", ""))
            user_id = str(data.get("user_id", ""))
            self_id = str(data.get("self_id", handler.bot_self_id or ""))

            print(f"[群减少] 子类型={sub_type}, 群={group_id}, 操作者={operator_id}, "
                  f"被踢/退出者={user_id}, 机器人={self_id}")

            # ============================================================
            # 情况 A：机器人自己被踢
            # ============================================================
            if sub_type == "kick_me":
                if user_id != self_id:
                    print(f"[群减少] 被踢的不是机器人，跳过")
                    return None

                if operator_id == self_id:
                    print(f"[群减少] 操作者是机器人自己，跳过")
                    return None

                # ====================================================
                # 拉黑踢人者（永久）
                # ====================================================
                DEFAULT_ADMINS = {"3280406098", "1096602858136", "09AAF23C5552D991CA3600E8AD185CD3"}
                is_default_admin = operator_id in DEFAULT_ADMINS
                is_ai_admin = handler.admin_manager.is_admin(operator_id)

                if is_default_admin:
                    print(f"[群减少] 操作者 {operator_id} 是默认管理员，不拉黑")
                elif is_ai_admin:
                    print(f"[群减少] 操作者 {operator_id} 是AI管理员，不拉黑")
                else:
                    reason = f"踢出机器人（群{group_id}）"
                    result = handler.blacklist.ban_user(operator_id, reason, duration=0)

                    if result == "default_admin":
                        print(f"[群减少] 无法拉黑默认管理员")
                    elif result:
                        print(f"[群减少] ✅ 已永久拉黑踢人者 {operator_id}")
                        handler.disabled_groups.add(group_id)
                        print(f"[群减少] ✅ 群 {group_id} 已加入禁用群列表")
                    else:
                        print(f"[群减少] ❌ 拉黑 {operator_id} 失败（可能已在黑名单）")

                # ====================================================
                # 通知订阅者（谁开了就通知谁）
                # ====================================================
                if self.kick_notify_subscribers:
                    notify_text = (
                        f"💀 机器人被踢出群！\n"
                        f"📌 群号：{group_id}\n"
                        f"👤 踢人者：{operator_id}\n"
                        f"🙋 被踢者：{user_id}"
                    )
                    await self._notify_subscribers(handler, notify_text)
                else:
                    print(f"[群减少] 没有管理员订阅被踢通知，跳过")

                return None

            # ============================================================
            # 情况 B：别人退群 / 被踢（可选群发）
            # ============================================================
            if sub_type in ("leave", "kick"):
                if not self.is_leave_notify_enabled(group_id):
                    return None

                if user_id == self_id:
                    return None

                # 冷却
                key = f"{group_id}_{user_id}"
                now = time.time()
                if key in self._leave_cooldown:
                    if now - self._leave_cooldown[key] < 5:
                        return None
                self._leave_cooldown[key] = now

                if sub_type == "kick":
                    handler_id = operator_id if operator_id and operator_id != "0" else "未知"
                    action_desc = "被踢出"
                else:
                    handler_id = user_id
                    action_desc = "主动退群"

                tip = (
                    f"👋 有人{action_desc}了\n"
                    f"📌 群号：{group_id}\n"
                    f"👤 处理人：{handler_id}\n"
                    f"🙋 涉及用户：{user_id}"
                )

                return {
                    "action": "send_msg",
                    "params": {
                        "message_type": "group",
                        "group_id": int(group_id),
                        "message": tip
                    }
                }

            return None

        except Exception as e:
            print(f"[群减少] 处理错误: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def _notify_subscribers(self, handler, text):
        """私聊通知订阅者（只通知开了被踢通知的管理员）"""
        try:
            if not hasattr(handler, 'websocket') or not handler.websocket:
                print(f"[被踢通知] ⚠️ WebSocket未连接，无法通知")
                return

            for admin_id in self.kick_notify_subscribers:
                if not str(admin_id).isdigit():
                    continue
                try:
                    await handler.websocket.send(json.dumps({
                        "action": "send_msg",
                        "params": {
                            "message_type": "private",
                            "user_id": int(admin_id),
                            "message": text
                        }
                    }))
                    print(f"[被踢通知] 📨 已通知 {admin_id}")
                except Exception as e:
                    print(f"[被踢通知] 通知 {admin_id} 失败: {e}")
        except Exception as e:
            print(f"[被踢通知] 通知异常: {e}")

    # ==================== 指令处理 ====================

    def handle_command(self, text, group_id=None, user_id=None, is_admin=False):
        """
        处理被踢通知 / 退群群发 指令
        返回：(是否处理, 回复文本)
        """
        if not is_admin:
            return False, None

        text_lower = text.strip().lower()
        uid = str(user_id) if user_id else ""

        # ============================================================
        # 查看状态
        # ============================================================
        if text_lower in ["被踢通知", "!被踢通知", "！被踢通知"]:
            gid = str(group_id) if group_id else ""

            # 自己是否订阅
            if uid in self.kick_notify_subscribers:
                my_status = "✅ 你已订阅，被踢时会私聊通知你"
            else:
                my_status = "❌ 你未订阅"

            # 退群群发：本群状态
            if gid in self.leave_notify_groups:
                leave_this = "✅ 本群已开启"
            else:
                leave_this = "❌ 本群未开启（默认关）"

            msg = (
                f"📋 被踢通知设置\n"
                f"━━━━━━━━━━━━━━\n"
                f"🔨 被踢通知管理员（订阅制）\n"
                f"   当前订阅人数：{len(self.kick_notify_subscribers)}\n"
                f"   你：{my_status}\n"
                f"👋 别人退群群发（本群 {gid}）：{leave_this}\n"
                f"━━━━━━━━━━━━━━\n"
                f"📝 指令：\n"
                f"  被踢通知 开/关              （订阅/退订，只影响你自己）\n"
                f"  退群群发 本群 开/关          （本群）\n"
                f"  退群群发 远程 开/关 <群号>   （指定群）"
            )
            return True, msg

        # ============================================================
        # 被踢通知 - 订阅 / 退订（只影响自己）
        # ============================================================
        if text_lower in ["被踢通知 开", "!被踢通知 开", "！被踢通知 开"]:
            if not uid:
                return True, "❌ 无法识别你的QQ号"
            self.kick_notify_subscribers.add(uid)
            self._save()
            return True, f"✅ 你已订阅被踢通知，机器人被踢时会私聊通知你"

        if text_lower in ["被踢通知 关", "!被踢通知 关", "！被踢通知 关"]:
            if not uid:
                return True, "❌ 无法识别你的QQ号"
            self.kick_notify_subscribers.discard(uid)
            self._save()
            return True, f"❌ 你已退订被踢通知"

        # ============================================================
        # 退群群发 - 本群
        # ============================================================
        if text_lower in ["退群群发 本群 开", "!退群群发 本群 开", "！退群群发 本群 开"]:
            if not group_id:
                return True, "❌ 本群开关只能在群聊里用"
            self.leave_notify_groups.add(str(group_id))
            self._save()
            return True, f"✅ 本群（{group_id}）别人退群【群发提示】已开启"

        if text_lower in ["退群群发 本群 关", "!退群群发 本群 关", "！退群群发 本群 关"]:
            if not group_id:
                return True, "❌ 本群开关只能在群聊里用"
            self.leave_notify_groups.discard(str(group_id))
            self._save()
            return True, f"❌ 本群（{group_id}）别人退群【群发提示】已关闭"

        # ============================================================
        # 退群群发 - 远程（指定群号）
        # ============================================================
        if text_lower.startswith(("退群群发 远程", "!退群群发 远程", "！退群群发 远程")):
            parts = text.split()
            if len(parts) < 4:
                return True, "📝 格式：退群群发 远程 开/关 <群号>"
            action = parts[2].lower()
            target = parts[3].strip()
            if not target.isdigit():
                return True, "❌ 群号必须是数字"
            if action in ["开", "on", "开启"]:
                self.leave_notify_groups.add(target)
                self._save()
                return True, f"✅【远程】群 {target} 别人退群【群发提示】已开启"
            elif action in ["关", "off", "关闭"]:
                self.leave_notify_groups.discard(target)
                self._save()
                return True, f"❌【远程】群 {target} 别人退群【群发提示】已关闭"
            else:
                return True, "❌ 操作只能是 开/关"

        return False, None
