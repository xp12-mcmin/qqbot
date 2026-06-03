"""
sign_module.py - 独立打卡模块
与主程序完全兼容的版本
"""

import asyncio
import json
import random
from datetime import datetime
from typing import Dict, List, Optional, Any
import time

class MultiGroupSignModule:
    """多群打卡模块 - 与主程序完全兼容"""
    
    def __init__(self):
        # 17个目标群 - 与主程序中的群列表完全一致
        self.target_groups = [
            "1009018182", "894506131", "597105096", "259099997", "2169057338",
            "1031919133", "1042681049", "197272874", "157509373", "435624010",
            "1006371944", "743645787", "1049056800", "924947078", "340841402",
            "437531257", "779699980"
        ]
        
        # 午夜打卡消息
        self.midnight_messages = [
            "?? 午夜打卡！新的一天开始啦~",
            "?? 零点签到！又是崭新的一天！",
            "?? 深夜打卡成功！大家早点休息~",
            "?? 准时打卡！开启新的一天！",
            "?? 午夜时分，打卡完成！",
            "?? 零时已到，准时签到！",
            "?? 深夜打卡，明日再会！",
            "?? 新的一天从打卡开始！",
            "?? 午夜钟声，打卡时刻！",
            "?? 零点整，打卡成功！"
        ]
        
        # 早晨打卡消息（可选）
        self.morning_messages = [
            "?? 早安打卡！新的一天加油！",
            "?? 早晨签到，元气满满！",
            "?? 清晨打卡，开启美好一天！",
            "?? 早安！今日也要努力哦~",
            "?? 早上好，打卡完成！"
        ]
        
        # 手动打卡回复
        self.manual_responses = [
            "?? 已为你签到！获得+1积分~",
            "?? 打卡成功！你是今天第一个！",
            "?? 签到完成！今日运势：大吉！",
            "?? 打卡get！保持活跃哦~",
            "?? 已记录签到！继续加油！",
            "?? 签到成功！今日幸运儿~",
            "?? 打卡完成！保持连签记录！",
            "?? 成功签到！获得每日奖励~"
        ]
        
        # 状态管理
        self.last_sent_date = None
        self.is_enabled = True
        self.daily_limit = 1
        self.sent_count_today = 0
        self.group_stats = {}
        
        print(f"[打卡模块] 初始化完成 - 目标群: {len(self.target_groups)}个")
        print(f"[打卡模块] 首3个群示例: {self.target_groups[:3]}")
    
    def should_send_today(self, hour: int = 0) -> bool:
        """检查今天是否需要发送"""
        if not self.is_enabled:
            return False
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 如果今天已经发送过指定次数，不再发送
        if self.sent_count_today >= self.daily_limit:
            return False
        
        # 如果今天已经发送过并且是同一时段
        if self.last_sent_date == today and hour == 0:
            return False
        
        return True
    
    async def send_daily_sign(self, websocket, hour: int = 0) -> Dict[str, Any]:
        """发送每日打卡消息 - 主程序调用的接口"""
        try:
            if not self.should_send_today(hour):
                return {"success": False, "message": "今天已发送或未到时间"}
            
            today = datetime.now().strftime("%Y-%m-%d")
            current_time = datetime.now().strftime("%H:%M:%S")
            
            print(f"[打卡模块] ?? 开始发送打卡 - 时间: {current_time}, 群数: {len(self.target_groups)}")
            
            # 选择消息
            if hour == 0:  # 午夜
                messages = self.midnight_messages
            elif 6 <= hour < 10:  # 早晨
                messages = self.morning_messages
            else:
                messages = self.midnight_messages
            
            sign_msg = random.choice(messages)
            
            success_groups = []
            failed_groups = []
            
            # 分批发送，避免同时发送太多
            for i, group_id in enumerate(self.target_groups):
                try:
                    # 发送消息到群
                    message_data = {
                        "action": "send_msg",
                        "params": {
                            "message_type": "group",
                            "group_id": int(group_id),
                            "message": sign_msg
                        }
                    }
                    
                    await websocket.send(json.dumps(message_data))
                    
                    success_groups.append(group_id)
                    
                    # 更新统计
                    if group_id not in self.group_stats:
                        self.group_stats[group_id] = {"success": 0, "fail": 0}
                    self.group_stats[group_id]["success"] += 1
                    
                    # 分批延迟：每5个群延迟一下
                    if (i + 1) % 5 == 0:
                        delay = random.uniform(2.0, 5.0)
                        await asyncio.sleep(delay)
                    else:
                        await asyncio.sleep(random.uniform(0.5, 1.5))
                    
                except Exception as e:
                    print(f"[打卡模块] ? 群{group_id}发送失败: {e}")
                    failed_groups.append(group_id)
                    
                    if group_id not in self.group_stats:
                        self.group_stats[group_id] = {"success": 0, "fail": 0}
                    self.group_stats[group_id]["fail"] += 1
            
            # 更新状态
            if success_groups:
                self.last_sent_date = today
                self.sent_count_today += 1
                
                result = {
                    "success": True,
                    "message": "发送完成",
                    "stats": {
                        "total": len(self.target_groups),
                        "success": len(success_groups),
                        "failed": len(failed_groups),
                        "success_rate": f"{(len(success_groups)/len(self.target_groups))*100:.1f}%",
                        "time": current_time
                    }
                }
                
                print(f"[打卡模块] ? 打卡完成: {len(success_groups)}成功/{len(failed_groups)}失败")
                print(f"[打卡模块] ? 成功率: {result['stats']['success_rate']}")
                
                if failed_groups:
                    print(f"[打卡模块] ? 失败群: {failed_groups[:5]}{'...' if len(failed_groups) > 5 else ''}")
                
                return result
            else:
                print(f"[打卡模块] ? 所有群发送失败")
                return {"success": False, "message": "所有群发送失败"}
            
        except Exception as e:
            print(f"[打卡模块] ? 发送失败: {e}")
            return {"success": False, "message": f"发送异常: {str(e)}"}
    
    async def send_manual_sign(self, websocket, group_id: str, user_id: str = None) -> Dict[str, Any]:
        """发送手动打卡消息 - 处理 !打卡 命令"""
        try:
            sign_msg = random.choice(self.manual_responses)
            
            if user_id:
                message = f"[CQ:at,qq={user_id}] {sign_msg}"
            else:
                message = sign_msg
            
            message_data = {
                "action": "send_msg",
                "params": {
                    "message_type": "group",
                    "group_id": int(group_id),
                    "message": message
                }
            }
            
            await websocket.send(json.dumps(message_data))
            
            print(f"[打卡模块] ? 手动打卡发送到群 {group_id}")
            return {"success": True, "message": "手动打卡成功"}
            
        except Exception as e:
            print(f"[打卡模块] ? 手动打卡失败: {e}")
            return {"success": False, "message": f"手动打卡失败: {str(e)}"}
    
    def reset_daily_counter(self):
        """重置每日计数器（在00:00调用）"""
        today = datetime.now().strftime("%Y-%m-%d")
        if self.last_sent_date != today:
            self.sent_count_today = 0
            print(f"[打卡模块] ? 每日计数器已重置")
    
    def get_status(self) -> str:
        """获取状态信息 - 用于 !打卡状态 命令"""
        today = datetime.now().strftime("%Y-%m-%d")
        total_success = sum(stat["success"] for stat in self.group_stats.values())
        total_fail = sum(stat["fail"] for stat in self.group_stats.values())
        total = total_success + total_fail
        
        status_lines = [
            "??【打卡模块状态】",
            f"? 启用状态: {'是' if self.is_enabled else '否'}",
            f"?? 目标群数: {len(self.target_groups)}个",
            f"?? 最后发送: {self.last_sent_date or '从未发送'}",
            f"?? 今日已发: {self.sent_count_today}/{self.daily_limit}次",
            f"?? 发送统计: 成功{total_success}次, 失败{total_fail}次"
        ]
        
        if total > 0:
            success_rate = (total_success / total * 100) if total > 0 else 0
            status_lines.append(f"?? 成功率: {success_rate:.1f}%")
        
        status_lines.append(f"? 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 添加最近活跃的群
        if self.group_stats:
            sorted_groups = sorted(
                self.group_stats.items(),
                key=lambda x: x[1]["success"],
                reverse=True
            )[:5]
            
            status_lines.append("\n??【活跃群TOP5】")
            for i, (group_id, stats) in enumerate(sorted_groups, 1):
                total_sends = stats["success"] + stats["fail"]
                success_rate = (stats["success"] / total_sends * 100) if total_sends > 0 else 0
                status_lines.append(f"  {i}. 群{group_id}: 成功{stats['success']}次 ({success_rate:.1f}%)")
        
        return "\n".join(status_lines)
    
    def add_group(self, group_id: str) -> bool:
        """添加目标群"""
        if group_id in self.target_groups:
            return False
        
        self.target_groups.append(group_id)
        print(f"[打卡模块] ? 添加群{group_id}成功，当前共{len(self.target_groups)}个群")
        return True
    
    def remove_group(self, group_id: str) -> bool:
        """移除目标群"""
        if group_id not in self.target_groups:
            return False
        
        self.target_groups.remove(group_id)
        print(f"[打卡模块] ? 移除群{group_id}成功，当前共{len(self.target_groups)}个群")
        return True
