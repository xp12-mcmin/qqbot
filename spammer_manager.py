import re
from typing import Dict, Optional

class SpamCommandManager:
    """刷屏命令管理器"""
    
    def __init__(self, spammer, admin_manager):
        self.spammer = spammer
        self.admin_manager = admin_manager
    
    def check_permission(self, user_id: str) -> bool:
        """检查权限"""
        return self.admin_manager.is_admin(str(user_id))
    
    def extract_command_info(self, text: str) -> Optional[Dict]:
        """提取命令信息"""
        text = text.strip()
        
        # 模式1: @机器人 QQ号 [时长]
        if text.startswith("@机器人"):
            return self._parse_at_command(text)
        
        # 模式2: !刷屏 QQ号 [时长]
        elif text.lower().startswith("!刷屏"):
            return self._parse_spam_command(text)
        
        return None
    

    
    def _parse_at_command(self, text: str) -> Optional[Dict]:
        """解析@机器人命令 - 已禁用"""
        # 返回一个标准格式，让主程序知道这是已禁用的刷屏命令
        return {
            "type": "spam_command_disabled",
            "message": "⚠️ 刷屏功能因安全原因已被永久禁用。"
        }

    def _parse_spam_command(self, text: str) -> Optional[Dict]:
        """解析!刷屏命令 - 已禁用"""
        return {
            "type": "spam_command_disabled", 
            "message": "⚠️ 刷屏功能因安全原因已被永久禁用。"
        }
    def get_help_text(self) -> str:
        """获取帮助文本"""
        return """
你好，该功能被禁用
        """.strip()
