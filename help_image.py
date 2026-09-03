

import random
import sys
from PIL import Image, ImageDraw, ImageFont
import os
import json
import time
import builtins
from datetime import datetime
from typing import Dict, Optional, List
import asyncio


# ==================== 授权验证 ====================
def _verify_module():
    """验证模块授权"""
    module_name = "help_image"
    
    try:
        license_key = getattr(builtins, 'XP12_LICENSE_KEY', '')
        print(f"[调试] 从 builtins 读取密钥: {license_key}")
    except Exception as e:
        print(f"[调试] 读取 builtins 异常: {e}")
        license_key = ''
    
    expected_key = ''
    try:
        if os.path.exists("data/.module_license"):
            with open("data/.module_license", "r") as f:
                data = json.load(f)
                expected_key = data.get("license_key", '')
                print(f"[调试] 从文件读取密钥: {expected_key}")
    except Exception as e:
        print(f"[调试] 读取文件异常: {e}")
        pass
    
    print(f"[调试] 对比: license_key={license_key}, expected_key={expected_key}")
    
    if license_key != expected_key or not expected_key:
        print(f"❌ 模块 [{module_name}] 授权失败！")
        print(f"   请通过主程序调用本模块")
        sys.exit(1)
    
    print(f"✅ 模块 [{module_name}] 授权通过")

_verify_module()

# ==================== 正常代码 ====================
"""
模块名：help_image
功能：待补充
"""

# ==================== 正常代码 ====================




class HelpImageGenerator:
    """帮助菜单图片生成器"""
    
    def __init__(self, font_dir: str = "fonts"):
        self.font_dir = font_dir
        os.makedirs(font_dir, exist_ok=True)
        
        self.font_title = None
        self.font_normal = None
        self._load_fonts()
    
    def _load_fonts(self):
        """加载字体"""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            
            font_paths = [
                os.path.join(script_dir, "fonts", "simhei.ttf"),
                os.path.join(script_dir, "fonts", "msyh.ttf"),
                "C:/Windows/Fonts/simhei.ttf",
                "C:/Windows/Fonts/msyh.ttc",
                "C:/Windows/Fonts/STHUPO.TTF",
                "C:/Windows/Fonts/STKAITI.TTF",
            ]
            
            font_loaded = False
            for font_path in font_paths:
                if os.path.exists(font_path):
                    self.font_title = ImageFont.truetype(font_path, 24)
                    self.font_normal = ImageFont.truetype(font_path, 16)
                    print(f"[帮助图片] 加载字体成功: {font_path}")
                    font_loaded = True
                    break
            
            if not font_loaded:
                print(f"[帮助图片] 未找到字体文件，使用默认字体")
                self.font_title = ImageFont.load_default()
                self.font_normal = ImageFont.load_default()
                
        except Exception as e:
            print(f"[帮助图片] 字体加载失败: {e}")
            self.font_title = ImageFont.load_default()
            self.font_normal = ImageFont.load_default()
    
    def image_to_base64(self, img: Image.Image) -> str:
        """统一返回文件路径（兼容 NapCat 和官方适配器）"""
        return self.save_to_temp(img)
    
    def save_to_temp(self, img: Image.Image) -> str:
        """保存图片到临时文件"""
        try:
            temp_dir = "data/temp_images"
            os.makedirs(temp_dir, exist_ok=True)
            
            filename = f"help_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}.png"
            filepath = os.path.join(temp_dir, filename)
            img.save(filepath, "PNG")
            print(f"[帮助图片] 保存到文件: {filepath}")
            return filepath
        except Exception as e:
            print(f"[帮助图片] 保存文件失败: {e}")
            return None
    
    def create_help_page(self, category: str, title: str, commands: list, is_admin: bool = False) -> Image.Image:
        """创建帮助页面"""
        line_height = 35
        base_height = 150
        content_height = len(commands) * line_height
        height = max(base_height + content_height, 300)
        width = 600
        
        img = Image.new('RGB', (width, height), color='#1a1a2e')
        draw = ImageDraw.Draw(img)
        
        draw.text((20, 20), title, fill='#00ff88', font=self.font_title)
        draw.text((20, 55), f"分类: {category}", fill='#ffaa00', font=self.font_normal)
        draw.line((20, 80, width-20, 80), fill='#333333', width=1)
        
        y = 105
        for cmd, desc in commands:
            if cmd.startswith("---"):
                draw.text((20, y), cmd, fill='#ffaa44', font=self.font_normal)
            elif cmd.startswith("📌") or cmd.startswith("💡") or cmd.startswith("✨"):
                draw.text((20, y), cmd, fill='#ffaa00', font=self.font_normal)
                if desc:
                    draw.text((200, y), desc, fill='#aaaaaa', font=self.font_normal)
            elif cmd.startswith("  "):
                draw.text((20, y), cmd, fill='#00ccff', font=self.font_normal)
                if desc:
                    draw.text((200, y), desc, fill='#ffffff', font=self.font_normal)
            elif cmd == "":
                pass
            elif desc == "" and cmd:
                draw.text((20, y), cmd, fill='#ffaa00', font=self.font_normal)
            else:
                draw.text((20, y), cmd, fill='#00ccff', font=self.font_normal)
                draw.text((220, y), desc, fill='#ffffff', font=self.font_normal)
            y += line_height
        
        draw.line((20, y+10, width-20, y+10), fill='#333333', width=1)
        draw.text((20, y+30), "💡 输入「!帮助」返回主菜单", fill='#aaaaaa', font=self.font_normal)
        
        return img
    
    def create_main_menu(self, is_admin: bool = False) -> Image.Image:
        """创建主菜单图片"""
        width = 550
        
        items = [
            ("1", "基础功能", "AI聊天、记忆"),
            ("2", "打卡", "签到、打卡状态"),
            ("3", "防撤回", "撤回保护、账号保护"),
            ("4", "好感度", "好感度查看、商店"),
            ("5", "性格", "AI性格切换"),
            ("6", "阴阳库", "阴阳库管理"),
            ("7", "黑名单", "拉黑、解禁、连坐"),
            ("8", "联网搜索", "搜索、AI问答"),
            ("9", "抽签系统", "每日运势、财运、姻缘"),
            ("10", "入群欢迎", "欢迎语设置、开关"),
            ("11", "婚姻系统", "今日老婆、结婚、离婚"),
            ("12", "改名功能", "修改群名片"),
            ("13", "点歌功能", "搜索、下载歌曲"),
            ("14", "AI绘画", "关键词生成图片"),
        ]

        if is_admin:
            items.append(("15", "管理员命令", "好感度设置、禁言、封禁"))
            items.append(("16", "其他功能", "刷屏、重进、解禁"))
        
        height = 150 + len(items) * 35 + 80
        height = max(height, 400)
        
        img = Image.new('RGB', (width, height), color='#1a1a2e')
        draw = ImageDraw.Draw(img)
        
        draw.text((20, 20), "🤖 机器人主菜单", fill='#00ff88', font=self.font_title)
        draw.text((20, 55), "发送「!帮助 序号」查看详细命令", fill='#aaaaaa', font=self.font_normal)
        draw.line((20, 80, width-20, 80), fill='#ffaa44', width=1)
        
        y = 105
        for num, name, desc in items:
            draw.text((20, y), f"{num}", fill='#ffaa00', font=self.font_normal)
            draw.text((60, y), f"{name}", fill='#ffffff', font=self.font_normal)
            draw.text((200, y), f"{desc}", fill='#888888', font=self.font_normal)
            y += 35
        
        draw.line((20, y+10, width-20, y+10), fill='#333333', width=1)
        draw.text((20, y+30), "💡 示例: !帮助 14   查看AI绘画", fill='#aaaaaa', font=self.font_normal)
        draw.text((20, y+55), "📝 发送「!帮助 全部」查看完整命令", fill='#aaaaaa', font=self.font_normal)
        
        return img
    
    def create_draw_help_page(self, is_admin: bool = False) -> Image.Image:
        commands = [
            ("画图 <关键词>", "AI生成图片"),
            ("!画图 <关键词>", "同上"),
            ("", ""),
            ("--- 示例 ---", ""),
            ("画图 猫娘", "生成猫娘图片"),
            ("画图 赛博朋克", "生成赛博朋克风格"),
            ("画图 星空", "生成星空夜景"),
            ("", ""),
            ("--- 说明 ---", ""),
            ("🎨 基于百度文心AI", "自动优化关键词"),
            ("⏱️ 生成约10-30秒", "请耐心等待"),
        ]
        return self.create_help_page("AI绘画", "【🎨 AI绘画】", commands, is_admin)
    
    def create_music_help_page(self, is_admin: bool = False) -> Image.Image:
        commands = [
            ("点歌 <歌曲名>", "搜索并下载歌曲"),
            ("!点歌 <歌曲名>", "同上"),
            ("", ""),
            ("--- 使用示例 ---", ""),
            ("点歌 稻香", "搜索周杰伦的《稻香》"),
            ("点歌 海阔天空", "搜索Beyond的《海阔天空》"),
            ("", ""),
            ("--- 功能说明 ---", ""),
            ("🎤 自动搜索", "从QQ音乐搜索歌曲"),
            ("📥 自动下载", "下载音频文件到本地"),
        ]
        return self.create_help_page("点歌功能", "【🎵 点歌功能】", commands, is_admin)
    
    def create_marriage_help_page(self, is_admin: bool = False) -> Image.Image:
        commands = [
            ("今日老婆", "随机抽取今日老婆（每天一次）"),
            ("结婚 @对方", "和对方结婚（需双方单身）"),
            ("离婚", "解除婚姻关系"),
            ("配偶", "查询自己的配偶"),
            ("夫妻榜", "查看夫妻排行榜"),
            ("", ""),
            ("✨ 每日老婆", "每天随机抽取，次日0点重置"),
        ]
        if is_admin:
            commands.extend([
                ("", ""),
                ("--- 管理员命令 ---", ""),
                ("!婚姻重置 <QQ>", "强制解除指定用户的婚姻"),
            ])
        return self.create_help_page("婚姻系统", "【💑 婚姻系统】", commands, is_admin)
    
    def create_personality_help_page(self, is_admin: bool = False) -> Image.Image:
        commands = [
            ("--- 群聊命令 ---", ""),
            ("!本群性格", "查看本群当前性格"),
            ("!本群切换 猫娘/默认", "切换本群性格"),
            ("!本群恢复", "恢复跟随全局"),
            ("", ""),
            ("--- 私聊说明 ---", ""),
            ("私聊固定使用【默认助手】", "不受任何群性格影响"),
        ]
        if is_admin:
            commands.extend([
                ("", ""),
                ("--- 管理员命令 ---", ""),
                ("!全局切换 猫娘/默认", "设置全局默认性格"),
                ("!远程性格 <群号> <模式>", "远程修改任意群的性格"),
            ])
        return self.create_help_page("AI性格", "【🎭 AI性格系统】", commands, is_admin)
    
    def create_lottery_help_page(self) -> Image.Image:
        commands = [
            ("!抽签", "随机抽取每日运势签"),
            ("!抽签 daily", "每日运势签"),
            ("!抽签 fortune", "财运签"),
            ("!抽签 love", "姻缘签"),
            ("!抽签 work", "事业签"),
            ("!抽签 study", "学业签"),
            ("", ""),
            ("✨ 每天结果固定", "同一天多次抽签结果相同"),
            ("✨ 次日0点重置", "每天都有新运势"),
        ]
        return self.create_help_page("抽签系统", "【🎋 抽签系统】", commands, False)
    
    def create_welcome_help_page(self) -> Image.Image:
        commands = [
            ("!欢迎配置", "查看欢迎配置"),
            ("", ""),
            ("--- 管理员命令 ---", ""),
            ("!欢迎开关 开/关", "全局开关（仅AI管理员）"),
            ("!开启欢迎", "开启本群欢迎"),
            ("!关闭欢迎", "关闭本群欢迎"),
            ("!设置欢迎 <消息>", "设置本群欢迎语"),
            ("", ""),
            ("📝 变量:", "{name} 新人昵称, {user_id} 新人QQ号"),
        ]
        return self.create_help_page("入群欢迎", "【🎉 入群欢迎系统】", commands, False)
    
    def create_rename_help_page(self, is_admin: bool = False) -> Image.Image:
        commands = [
            ("--- 修改群成员名片 ---", ""),
            ("!改名 @对方 新名字", "修改指定群成员的名片"),
            ("", "需要群管理员或AI管理员权限"),
            ("", "示例: !改名 @张三 李四"),
            ("", ""),
            ("--- 修改机器人名字 ---", ""),
            ("改我名 新名字", "修改机器人自己的名片"),
            ("", "需要AI管理员权限"),
        ]
        return self.create_help_page("改名功能", "【✏️ 改名功能】", commands, is_admin)
    
    def create_full_help(self, is_admin: bool = False) -> Image.Image:
        commands = [
            ("--- 基础功能 ---", ""),
            ("@机器人 + 消息", "AI聊天（自动记忆）"),
            ("!记忆状态", "查看AI记忆状态"),
            ("!清除我的记忆", "清除个人对话记忆"),
            ("", ""),
            ("--- 打卡功能 ---", ""),
            ("!打卡", "手动打卡"),
            ("!打卡状态", "查看打卡状态"),
            ("", ""),
            ("--- 好感度系统 ---", ""),
            ("!好感度 (@用户)", "查看好感度"),
            ("!好感榜", "查看排行榜"),
            ("!签到", "每日签到"),
            ("!商店", "查看商店"),
            ("!购买 <ID>", "购买商品"),
            ("!设置称号 <称号>", "设置称号"),
            ("", ""),
            ("--- 抽签系统 ---", ""),
            ("!抽签", "每日运势签"),
            ("!抽签 财运/姻缘/事业/学业", "各类运势签"),
            ("", ""),
            ("--- 婚姻系统 ---", ""),
            ("今日老婆", "随机抽取今日老婆"),
            ("结婚 @对方", "和对方结婚"),
            ("离婚", "解除婚姻关系"),
            ("配偶", "查询配偶"),
        ]
        
        if is_admin:
            commands.extend([
                ("", ""),
                ("--- 管理员命令 ---", ""),
                ("!好感度设置 <QQ> <数值>", "设置好感度"),
                ("!好感度增加 <QQ> <数值>", "增加好感度"),
                ("!禁言 <QQ> [分钟]", "禁言成员"),
                ("!ban <QQ> [原因]", "封禁用户"),
                ("!ban-g <群号>", "拉黑整个群（连坐）"),
                ("!欢迎开关 开/关", "全局欢迎开关"),
            ])
        
        return self.create_help_page("全部命令", "【📖 完整帮助】", commands, is_admin)
