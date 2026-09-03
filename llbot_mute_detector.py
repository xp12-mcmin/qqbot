# llbot_mute_detector.py
import json
from pathlib import Path
from datetime import datetime

class LLBotMuteDetector:
    """
    LLBot禁言检测与自动复仇系统
    核心功能：当机器人被禁言时，自动将操作者加入黑名单
    """
    
    def __init__(self, blacklist_system, config=None):
        """
        初始化禁言检测器
        
        Args:
            blacklist_system: SimpleBlacklist实例（你的黑名单系统）
            config: 配置字典，可选
        """
        self.blacklist = blacklist_system
        self.config = config or {}
        
        # 固定配置 - 基于你的测试结果
        self.BOT_FIXED_UID = "u_Adud_U_JQaQCiQ6UZkGq3g"  # 你的机器人UID
        self.BOT_NAME = "xp12"  # 你的机器人名称
        
        # 数据文件
        self.data_dir = Path("data")
        self.mute_log_file = self.data_dir / "mute_events.json"
        self.revenge_log_file = self.data_dir / "revenge_log.json"
        
        # 确保目录存在
        self.data_dir.mkdir(exist_ok=True)
        
        print(f"[禁言检测] 初始化完成")
        print(f"[禁言检测] 机器人UID: {self.BOT_FIXED_UID}")
        print(f"[禁言检测] 机器人名称: {self.BOT_NAME}")
    
    def is_bot_muted(self, event):
        """
        判断是否是机器人自己被禁言
        
        Args:
            event: LLBot的原始事件数据
            
        Returns:
            tuple: (是否机器人被禁言, 禁言详情字典)
        """
        try:
            # 1. 检查是否是禁言事件 (type=8)
            if event.get('type') != 8:
                return False, None
            
            # 2. 提取shutUp数据
            shutup = event.get('shutUp', {})
            if not shutup:
                return False, None
            
            # 3. 获取被禁言成员UID
            member = shutup.get('member', {})
            member_uid = member.get('uid', '')
            member_name = member.get('name', '')
            
            # 4. 获取禁言时长
            duration = int(shutup.get('duration', '0'))
            
            # 5. 判断是否是机器人被禁言
            is_muted = False
            reason = ""
            
            # 方案A：固定UID匹配（主逻辑）
            if member_uid == self.BOT_FIXED_UID and duration > 0:
                is_muted = True
                reason = "uid_match"
            
            # 方案B：名称匹配（保险逻辑）
            elif not is_muted and duration > 0:
                if self.BOT_NAME.lower() in member_name.lower():
                    is_muted = True
                    reason = "name_match"
            
            if is_muted:
                # 获取操作者信息
                admin = shutup.get('admin', {})
                
                mute_info = {
                    'timestamp': datetime.now().isoformat(),
                    'duration': duration,
                    'reason': reason,
                    'admin_uid': admin.get('uid'),
                    'admin_name': admin.get('name'),
                    'admin_role': admin.get('role'),
                    'member_uid': member_uid,
                    'member_name': member_name,
                    'raw_event': event  # 保存原始数据
                }
                
                return True, mute_info
            
            return False, None
            
        except Exception as e:
            print(f"[禁言检测] 判断失败: {e}")
            return False, None
    
    async def process_event(self, event):
        """
        处理事件，如果机器人被禁言则执行复仇
        
        Args:
            event: LLBot的原始事件数据
            
        Returns:
            bool: 是否执行了复仇
        """
        # 1. 检测是否是机器人被禁言
        is_muted, mute_info = self.is_bot_muted(event)
        
        if not is_muted:
            return False
        
        print(f"\n🚨 [禁言检测] 机器人被禁言！")
        print(f"   操作者: {mute_info['admin_name']} ({mute_info['admin_uid']})")
        print(f"   时长: {mute_info['duration']}秒")
        print(f"   识别依据: {mute_info['reason']}")
        
        # 2. 记录事件到日志
        self._log_mute_event(mute_info)
        
        # 3. 执行复仇：将操作者加入黑名单
        if mute_info['admin_uid']:
            revenge_success = await self._execute_revenge(mute_info)
            return revenge_success
        
        return False
    
    async def _execute_revenge(self, mute_info):
        """执行复仇：将操作者加入黑名单（智能适配QQ号和LLBot UID）"""
        try:
            admin_uid = mute_info['admin_uid']  # LLBot格式：u_xEJL4h2OpXSSwMVcd-JbuQ
            admin_name = mute_info['admin_name'] or "未知用户"
            duration = mute_info['duration']
            
            ban_reason = f"禁言机器人({duration}秒)"
            
            # 方案1：直接尝试加入（如果黑名单支持LLBot UID格式）
            result = self.blacklist.add_user(
                user_id=admin_uid,
                reason=ban_reason
            )
            
            if result:
                print(f"✅ [自动复仇] 已将 {admin_name} (UID: {admin_uid}) 加入黑名单")
                self._log_revenge_action(mute_info, "blacklist_uid")
                return True
            
            # 方案2：如果直接添加失败，尝试提取可能的QQ号
            # 从LLBot的UID中提取QQ号（如果有的话）
            qq_number = self._extract_qq_from_uid(admin_uid)
            
            if qq_number:
                result = self.blacklist.add_user(
                    user_id=qq_number,
                    reason=ban_reason
                )
                
                if result:
                    print(f"✅ [自动复仇] 已将 {admin_name} (QQ: {qq_number}) 加入黑名单")
                    self._log_revenge_action(mute_info, "blacklist_qq")
                    return True
                else:
                    print(f"⚠️ [自动复仇] QQ号 {qq_number} 添加失败（可能已在黑名单中）")
            else:
                print(f"⚠️ [自动复仇] 无法从UID {admin_uid} 中提取QQ号")
            
            print(f"❌ [自动复仇] 两种方案都失败")
            return False
            
        except Exception as e:
            print(f"❌ [自动复仇] 执行失败: {e}")
            return False

    def _extract_qq_from_uid(self, uid):
        """
        尝试从LLBot的UID中提取QQ号
        
        Args:
            uid: LLBot格式的UID，如 'u_xEJL4h2OpXSSwMVcd-JbuQ'
            
        Returns:
            str or None: 提取到的QQ号，或None
        """
        # 方法1：如果UID就是纯数字（可能是QQ号）
        if uid.isdigit():
            return uid
        
        # 方法2：尝试从特殊格式中提取
        # 例如：'u_1234567890' -> '1234567890'
        if uid.startswith('u_'):
            # 移除'u_'前缀，检查剩余部分
            remaining = uid[2:]
            # 如果剩余部分是数字，可能是QQ号
            if remaining.isdigit():
                return remaining
        
        # 方法3：更复杂的提取（根据你的实际UID格式调整）
        # 这里可以根据你的UID格式添加更多提取逻辑
        
        return None
    def _calculate_ban_duration(self, mute_duration):
        """根据禁言时长计算黑名单时长"""
        # 默认策略：禁言机器人多久，就封禁操作者多久（可按需调整）
        return mute_duration
    
    def _log_mute_event(self, mute_info):
        """记录禁言事件到文件"""
        try:
            events = []
            if self.mute_log_file.exists():
                with open(self.mute_log_file, 'r', encoding='utf-8') as f:
                    events = json.load(f)
            
            # 只保留必要信息，避免文件过大
            log_entry = {
                'timestamp': mute_info['timestamp'],
                'admin_uid': mute_info['admin_uid'],
                'admin_name': mute_info['admin_name'],
                'duration': mute_info['duration'],
                'reason': mute_info['reason']
            }
            
            events.append(log_entry)
            
            # 只保留最近100条记录
            if len(events) > 100:
                events = events[-100:]
            
            with open(self.mute_log_file, 'w', encoding='utf-8') as f:
                json.dump(events, f, ensure_ascii=False, indent=2)
                
            print(f"[事件记录] 已记录禁言事件到 {self.mute_log_file}")
            
        except Exception as e:
            print(f"[事件记录] 保存失败: {e}")
    
    def _log_revenge_action(self, mute_info, action_type):
        """记录复仇操作到文件"""
        try:
            actions = []
            if self.revenge_log_file.exists():
                with open(self.revenge_log_file, 'r', encoding='utf-8') as f:
                    actions = json.load(f)
            
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'action': action_type,
                'target_uid': mute_info['admin_uid'],
                'target_name': mute_info['admin_name'],
                'mute_duration': mute_info['duration'],
                'reason': f"禁言机器人({mute_info['duration']}秒)"
            }
            
            actions.append(log_entry)
            
            if len(actions) > 100:
                actions = actions[-100:]
            
            with open(self.revenge_log_file, 'w', encoding='utf-8') as f:
                json.dump(actions, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"[复仇记录] 保存失败: {e}")
    
    def get_stats(self):
        """获取统计数据"""
        try:
            mute_count = 0
            if self.mute_log_file.exists():
                with open(self.mute_log_file, 'r', encoding='utf-8') as f:
                    events = json.load(f)
                    mute_count = len(events)
            
            revenge_count = 0
            if self.revenge_log_file.exists():
                with open(self.revenge_log_file, 'r', encoding='utf-8') as f:
                    actions = json.load(f)
                    revenge_count = len(actions)
            
            return {
                'total_mute_events': mute_count,
                'total_revenge_actions': revenge_count,
                'bot_uid': self.BOT_FIXED_UID,
                'bot_name': self.BOT_NAME
            }
            
        except Exception as e:
            print(f"[统计数据] 获取失败: {e}")
            return {}
