"""
帮助菜单图片生成模块
"""

import os
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import base64
from io import BytesIO


class HelpImageGenerator:
    """帮助菜单图片生成器"""
    
    def __init__(self, font_dir: str = "fonts"):
        self.font_dir = font_dir
        os.makedirs(font_dir, exist_ok=True)
        
        # 尝试加载中文字体，如果失败则使用默认字体
        self.font_title = None
        self.font_normal = None
        self._load_fonts()
    
    def image_to_base64(self, img: Image.Image) -> str:
        """将图片转换为 base64 编码"""
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return f"base64://{img_base64}"
    
    def _load_fonts(self):
        """加载字体"""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            font_path = os.path.join(script_dir, "fonts", "simhei.ttf")
            
            if os.path.exists(font_path):
                self.font_title = ImageFont.truetype(font_path, 24)
                self.font_normal = ImageFont.truetype(font_path, 16)
                print(f"[帮助图片] 加载字体成功: {font_path}")
            else:
                print(f"[帮助图片] 字体文件不存在: {font_path}")
                self.font_title = ImageFont.load_default()
                self.font_normal = ImageFont.load_default()
        except Exception as e:
            print(f"[帮助图片] 字体加载失败: {e}")
            self.font_title = ImageFont.load_default()
            self.font_normal = ImageFont.load_default()
    
    def create_help_page(self, category: str, title: str, commands: list, is_admin: bool = False) -> Image.Image:
        """创建帮助页面"""
        line_height = 35
        base_height = 150
        content_height = len(commands) * line_height
        height = base_height + content_height
        width = 600
        
        img = Image.new('RGB', (width, height), color='#1a1a2e')
        draw = ImageDraw.Draw(img)
        
        # 标题
        draw.text((20, 20), title, fill='#00ff88', font=self.font_title)
        
        # 分类信息
        draw.text((20, 55), f"分类: {category}", fill='#ffaa00', font=self.font_normal)
        
        # 分割线
        draw.line((20, 80, width-20, 80), fill='#333333', width=1)
        
        # 命令列表
        y = 105
        for cmd, desc in commands:
            draw.text((20, y), cmd, fill='#00ccff', font=self.font_normal)
            draw.text((220, y), desc, fill='#ffffff', font=self.font_normal)
            y += line_height
        
        # 底部提示
        draw.line((20, y+10, width-20, y+10), fill='#333333', width=1)
        draw.text((20, y+30), "💡 输入「!帮助」返回主菜单", fill='#aaaaaa', font=self.font_normal)
        
        return img
    
    def create_search_help_page(self) -> Image.Image:
        """创建联网搜索帮助页面"""
        width = 500
        height = 350
        line_height = 35
        
        img = Image.new('RGB', (width, height), color='#1a1a2e')
        draw = ImageDraw.Draw(img)
        
        # 标题
        draw.text((20, 20), "【🌐 联网搜索】", fill='#00ff88', font=self.font_title)
        
        # 分割线
        draw.line((20, 60, width-20, 60), fill='#333333', width=1)
        
        # 命令列表
        y = 85
        commands = [
            ("!搜索 <内容>", "联网搜索信息"),
            ("!问问 <问题>", "AI联网问答"),
            ("", ""),
            ("📌 示例:", ""),
            ("  !搜索 今日新闻", "搜索新闻"),
            ("  !问问 今天天气", "AI问答"),
            ("", ""),
            ("⏱️ 说明:", ""),
            ("  可能需要5-10秒", "请耐心等待"),
        ]
        
        for cmd, desc in commands:
            if cmd.startswith("📌") or cmd.startswith("⏱️"):
                draw.text((20, y), cmd, fill='#ffaa00', font=self.font_normal)
            elif cmd.startswith("  !"):
                draw.text((20, y), cmd, fill='#00ccff', font=self.font_normal)
                draw.text((220, y), desc, fill='#888888', font=self.font_normal)
            elif cmd:
                draw.text((20, y), cmd, fill='#ffffff', font=self.font_normal)
                if desc:
                    draw.text((220, y), desc, fill='#aaaaaa', font=self.font_normal)
            y += line_height
        
        # 底部提示
        draw.line((20, y+10, width-20, y+10), fill='#333333', width=1)
        draw.text((20, y+30), "💡 输入「!帮助」返回主菜单", fill='#aaaaaa', font=self.font_normal)
        
        return img
    def create_draw_help_page(self, is_admin: bool = False) -> Image.Image:
        """创建AI绘画帮助页面"""
        width = 550
        height = 380
        line_height = 35
        
        img = Image.new('RGB', (width, height), color='#1a1a2e')
        draw = ImageDraw.Draw(img)
        
        # 标题
        draw.text((20, 20), "【🎨 AI绘画】", fill='#00ff88', font=self.font_title)
        draw.line((20, 55, width-20, 55), fill='#333333', width=1)
        
        y = 80
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
            ("💡 如果失败", "换个关键词试试"),
        ]
        
        for cmd, desc in commands:
            if cmd.startswith("---"):
                draw.text((20, y), cmd, fill='#ffaa44', font=self.font_normal)
            elif cmd == "":
                pass
            elif desc == "":
                draw.text((20, y), cmd, fill='#00ccff', font=self.font_normal)
            else:
                draw.text((20, y), cmd, fill='#00ccff', font=self.font_normal)
                draw.text((180, y), desc, fill='#ffffff', font=self.font_normal)
            y += line_height
        
        draw.line((20, y+10, width-20, y+10), fill='#333333', width=1)
        draw.text((20, y+30), "💡 输入「!帮助」返回主菜单", fill='#aaaaaa', font=self.font_normal)
        
        return img
    def create_music_help_page(self, is_admin: bool = False) -> Image.Image:
        """创建点歌帮助页面"""
        width = 550
        height = 400
        line_height = 35
        
        img = Image.new('RGB', (width, height), color='#1a1a2e')
        draw = ImageDraw.Draw(img)
        
        # 标题
        draw.text((20, 20), "【🎵 点歌功能】", fill='#00ff88', font=self.font_title)
        
        # 分割线
        draw.line((20, 55, width-20, 55), fill='#333333', width=1)
        
        y = 80
        commands = [
            ("--- 基本命令 ---", ""),
            ("点歌 <歌曲名>", "搜索并下载歌曲"),
            ("!点歌 <歌曲名>", "同上"),
            ("", ""),
            ("--- 使用示例 ---", ""),
            ("点歌 稻香", "搜索周杰伦的《稻香》"),
            ("点歌 海阔天空", "搜索Beyond的《海阔天空》"),
            ("点歌 起风了", "搜索《起风了》"),
            ("", ""),
            ("--- 功能说明 ---", ""),
            ("🎤 自动搜索", "从QQ音乐搜索歌曲"),
            ("📥 自动下载", "下载音频文件到本地"),
            ("📁 群文件上传", "上传到群文件供下载"),
            ("🔗 备用链接", "提供在线播放链接"),
            ("", ""),
            ("💡 提示:", ""),
            ("  如果文件被拦截，可以使用备用链接", "或手动复制链接到浏览器下载"),
        ]
        
        for cmd, desc in commands:
            if cmd.startswith("---"):
                draw.text((20, y), cmd, fill='#ffaa44', font=self.font_normal)
            elif cmd.startswith("💡"):
                draw.text((20, y), cmd, fill='#ffaa00', font=self.font_normal)
                if desc:
                    draw.text((250, y), desc, fill='#aaaaaa', font=self.font_normal)
            elif cmd.startswith("  "):
                draw.text((20, y), cmd, fill='#00ccff', font=self.font_normal)
                if desc:
                    draw.text((250, y), desc, fill='#ffffff', font=self.font_normal)
            elif cmd == "":
                pass
            elif desc == "" and cmd:
                draw.text((20, y), cmd, fill='#00ff88', font=self.font_normal)
            else:
                draw.text((20, y), cmd, fill='#00ccff', font=self.font_normal)
                draw.text((180, y), desc, fill='#ffffff', font=self.font_normal)
            y += line_height
        
        # 底部提示
        draw.line((20, y+10, width-20, y+10), fill='#333333', width=1)
        draw.text((20, y+30), "💡 输入「!帮助」返回主菜单", fill='#aaaaaa', font=self.font_normal)
        
        return img
    def create_marriage_help_page(self, is_admin: bool = False) -> Image.Image:
        """创建今日老婆/婚姻系统帮助页面"""
        width = 580
        line_height = 35
        height = 450 if is_admin else 400
        
        img = Image.new('RGB', (width, height), color='#1a1a2e')
        draw = ImageDraw.Draw(img)
        
        # 标题
        draw.text((20, 20), "【💑 今日老婆/婚姻系统】", fill='#ff69b4', font=self.font_title)
        
        # 分割线
        draw.line((20, 55, width-20, 55), fill='#333333', width=1)
        
        # 命令列表
        y = 80
        commands = [
            ("--- 基础命令 ---", ""),
            ("今日老婆 / 抽老婆", "随机抽取今日老婆（每天一次）"),
            ("结婚 @对方", "和对方结婚（双方需单身）"),
            ("离婚", "解除婚姻关系"),
            ("配偶 / 老婆 / 老公", "查询自己的配偶"),
            ("夫妻榜 / 婚姻榜", "查看本群夫妻排行榜"),
            ("", ""),
            ("✨ 特色功能:", ""),
            ("  • 每日老婆", "每天随机抽取，次日0点重置"),
            ("  • 结婚证图片", "结婚时自动生成结婚证"),
            ("  • 双向绑定", "离婚自动解除双方关系"),
            ("", ""),
        ]
        
        if is_admin:
            commands.extend([
                ("--- 管理员命令 ---", ""),
                ("!婚姻重置 <QQ>", "强制解除指定用户的婚姻"),
                ("!婚姻重置群", "清空本群所有婚姻数据"),
                ("", ""),
            ])
        
        for cmd, desc in commands:
            if cmd.startswith("---"):
                draw.text((20, y), cmd, fill='#ffaa44', font=self.font_normal)
            elif cmd.startswith("✨"):
                draw.text((20, y), cmd, fill='#ffaa00', font=self.font_normal)
                if desc:
                    draw.text((180, y), desc, fill='#aaaaaa', font=self.font_normal)
            elif cmd.startswith("  •"):
                draw.text((20, y), cmd, fill='#00ccff', font=self.font_normal)
                if desc:
                    draw.text((200, y), desc, fill='#ffffff', font=self.font_normal)
            elif cmd == "":
                pass
            elif desc == "" and cmd:
                draw.text((20, y), cmd, fill='#ff69b4', font=self.font_normal)
            else:
                draw.text((20, y), cmd, fill='#00ccff', font=self.font_normal)
                draw.text((180, y), desc, fill='#ffffff', font=self.font_normal)
            y += line_height
        
        # 底部提示
        draw.line((20, y+10, width-20, y+10), fill='#333333', width=1)
        draw.text((20, y+30), "💡 输入「!帮助」返回主菜单", fill='#aaaaaa', font=self.font_normal)
        
        return img    
    def create_lottery_help_page(self) -> Image.Image:
        """创建抽签系统帮助页面"""
        width = 550
        height = 420
        line_height = 35
        
        img = Image.new('RGB', (width, height), color='#1a1a2e')
        draw = ImageDraw.Draw(img)
        
        # 标题
        draw.text((20, 20), "【🎋 抽签系统】", fill='#00ff88', font=self.font_title)
        
        # 分割线
        draw.line((20, 55, width-20, 55), fill='#333333', width=1)
        
        # 命令列表
        y = 80
        commands = [
            ("!抽签", "随机抽取每日运势签"),
            ("!抽签 daily / 每日", "每日运势签"),
            ("!抽签 fortune / 财运", "财运签"),
            ("!抽签 love / 姻缘", "姻缘签"),
            ("!抽签 work / 事业", "事业签"),
            ("!抽签 study / 学业", "学业签"),
            ("!抽签帮助", "查看抽签帮助"),
            ("", ""),
            ("✨ 特色功能:", ""),
            ("  • 每天每种签结果固定", "同一天多次抽签结果相同"),
            ("  • 次日0点重置", "每天都有新运势"),
            ("  • 自动生成运势图片", "支持中文显示"),
        ]
        
        for cmd, desc in commands:
            if cmd.startswith("✨") or cmd.startswith("  •"):
                draw.text((20, y), cmd, fill='#ffaa00', font=self.font_normal)
                if desc:
                    draw.text((250, y), desc, fill='#aaaaaa', font=self.font_normal)
            elif cmd == "":
                pass
            elif desc == "" and cmd:
                draw.text((20, y), cmd, fill='#ffaa00', font=self.font_normal)
            else:
                draw.text((20, y), cmd, fill='#00ccff', font=self.font_normal)
                draw.text((220, y), desc, fill='#ffffff', font=self.font_normal)
            y += line_height
        
        # 底部提示
        draw.line((20, y+10, width-20, y+10), fill='#333333', width=1)
        draw.text((20, y+30), "💡 输入「!帮助」返回主菜单", fill='#aaaaaa', font=self.font_normal)
        
        return img
    
    def create_welcome_help_page(self) -> Image.Image:
        """创建入群欢迎帮助页面"""
        width = 580
        height = 480
        line_height = 35
        
        img = Image.new('RGB', (width, height), color='#1a1a2e')
        draw = ImageDraw.Draw(img)
        
        # 标题
        draw.text((20, 20), "【🎉 入群欢迎系统】", fill='#00ff88', font=self.font_title)
        
        # 分割线
        draw.line((20, 55, width-20, 55), fill='#333333', width=1)
        
        # 命令列表
        y = 80
        commands = [
            ("--- 用户命令 ---", ""),
            ("!欢迎配置", "查看欢迎配置"),
            ("", ""),
            ("--- 管理员命令 ---", ""),
            ("!欢迎开关 开/关", "全局开关（仅AI管理员）"),
            ("!开启欢迎", "开启本群欢迎"),
            ("!关闭欢迎", "关闭本群欢迎"),
            ("!设置欢迎 <消息>", "设置本群欢迎语"),
            ("", ""),
            ("📝 欢迎语变量:", ""),
            ("  {name}", "新人昵称"),
            ("  {user_id}", "新人QQ号"),
            ("  {group_id}", "本群群号"),
            ("", ""),
            ("💡 示例:", ""),
            ("  !设置欢迎 🎉 欢迎{name}加入本群！", ""),
            ("  !设置欢迎 欢迎{name}（{user_id}）入群~", ""),
        ]
        
        for cmd, desc in commands:
            if cmd.startswith("---"):
                draw.text((20, y), cmd, fill='#ffaa44', font=self.font_normal)
            elif cmd.startswith("📝") or cmd.startswith("💡"):
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
                draw.text((180, y), desc, fill='#ffffff', font=self.font_normal)
            y += line_height
        
        # 底部提示
        draw.line((20, y+10, width-20, y+10), fill='#333333', width=1)
        draw.text((20, y+30), "💡 输入「!帮助」返回主菜单", fill='#aaaaaa', font=self.font_normal)
        
        return img
    
    def create_personality_help_page(self, is_admin: bool = False) -> Image.Image:
        """创建AI性格帮助页面"""
        width = 600
        line_height = 35
        
        # 基础命令数量
        base_commands = 7  # 群聊命令(3) + 空行(1) + 私聊说明(2) + 空行(1) = 7行
        admin_commands = 6  # 管理员命令(4行) + 空行(1) + 示例(2行) = 7行
        
        total_lines = base_commands + (admin_commands if is_admin else 0)
        height = 150 + total_lines * line_height + 80
        
        img = Image.new('RGB', (width, height), color='#1a1a2e')
        draw = ImageDraw.Draw(img)
        
        # 标题
        draw.text((20, 20), "【🎭 AI性格系统】", fill='#00ff88', font=self.font_title)
        
        # 分割线
        draw.line((20, 55, width-20, 55), fill='#333333', width=1)
        
        # 命令列表
        y = 80
        commands = [
            ("--- 群聊命令（在目标群发送）---", ""),
            ("!本群性格", "查看本群当前性格"),
            ("!本群切换 猫娘/默认", "切换本群性格"),
            ("!本群恢复", "恢复跟随全局"),
            ("", ""),
            ("--- 私聊说明 ---", ""),
            ("私聊固定使用【默认助手】", "不受任何群性格影响"),
            ("", ""),
        ]
        
        if is_admin:
            commands.extend([
                ("--- 管理员命令 ---", ""),
                ("!全局切换 猫娘/默认", "设置全局默认性格"),
                ("!远程性格 <群号> <模式>", "远程修改任意群的性格"),
                ("", ""),
                ("📝 远程性格示例:", ""),
                ("  !远程性格 123456 猫娘", "将123456群改为猫娘"),
                ("  !远程性格 123456 默认", "将123456群改为默认"),
            ])
        
        for cmd, desc in commands:
            if cmd.startswith("---"):
                draw.text((20, y), cmd, fill='#ffaa44', font=self.font_normal)
            elif cmd.startswith("--- 私聊"):
                draw.text((20, y), cmd, fill='#00ff88', font=self.font_normal)
            elif cmd.startswith("📝"):
                draw.text((20, y), cmd, fill='#ffaa00', font=self.font_normal)
            elif cmd.startswith("  !"):
                draw.text((20, y), cmd, fill='#00ccff', font=self.font_normal)
                if desc:
                    draw.text((280, y), desc, fill='#aaaaaa', font=self.font_normal)
            elif cmd == "":
                pass
            elif desc == "" and cmd:
                draw.text((20, y), cmd, fill='#00ff88' if "私聊" in cmd else '#ffaa00', font=self.font_normal)
            else:
                draw.text((20, y), cmd, fill='#00ccff', font=self.font_normal)
                draw.text((220, y), desc, fill='#ffffff', font=self.font_normal)
            y += line_height
        
        # 底部提示
        draw.line((20, y+10, width-20, y+10), fill='#333333', width=1)
        draw.text((20, y+30), "💡 私聊默认使用默认助手，不受群性格影响", fill='#aaaaaa', font=self.font_normal)
        draw.text((20, y+55), "📝 输入「!帮助」返回主菜单", fill='#aaaaaa', font=self.font_normal)
        
        return img
    
    def create_main_menu(self, is_admin: bool = False) -> Image.Image:
        """创建主菜单图片"""
        width = 550
        height = 660 if is_admin else 630  # 增加高度
        
        img = Image.new('RGB', (width, height), color='#1a1a2e')
        draw = ImageDraw.Draw(img)
        
        # 标题
        draw.text((20, 20), "🤖 机器人主菜单", fill='#00ff88', font=self.font_title)
        draw.text((20, 55), "发送「!帮助 序号」查看详细命令", fill='#aaaaaa', font=self.font_normal)
        
        # 分割线
        draw.line((20, 80, width-20, 80), fill='#ffaa44', width=1)
        
        # 菜单项（所有项都包含）
        y = 105
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
            ("14", "AI绘画", "关键词生成图片"),  # 所有人可见
        ]

        if is_admin:
            items.append(("15", "管理员命令", "好感度设置、禁言、封禁"))
            items.append(("16", "其他功能", "刷屏、重进、解禁"))
        
        for num, name, desc in items:
            draw.text((20, y), f"{num}", fill='#ffaa00', font=self.font_normal)
            draw.text((60, y), f"{name}", fill='#ffffff', font=self.font_normal)
            draw.text((200, y), f"{desc}", fill='#888888', font=self.font_normal)
            y += 35
        
        # 底部提示
        draw.line((20, y+10, width-20, y+10), fill='#333333', width=1)
        draw.text((20, y+30), "💡 示例: !帮助 14   查看AI绘画", fill='#aaaaaa', font=self.font_normal)
        draw.text((20, y+55), "📝 发送「!帮助 全部」查看完整命令", fill='#aaaaaa', font=self.font_normal)
        
        return img
        
      
    def create_full_help(self, is_admin: bool = False) -> Image.Image:
        """创建完整帮助图片"""
        width = 600
        lines = [
            ("【🤖 完整功能帮助】", ""),
            ("", ""),
            ("📌 基础功能:", ""),
            ("  @机器人 + 消息", "AI聊天（自动记忆）"),
            ("  !记忆状态", "查看AI记忆状态"),
            ("  !清除我的记忆", "清除个人对话记忆"),
            ("  !上一句", "查看自己刚才说的话"),
            ("", ""),
            ("📅 打卡功能:", ""),
            ("  !打卡", "手动打卡"),
            ("  !打卡状态", "查看打卡状态"),
            ("", ""),
            ("🎋 抽签系统:", ""),
            ("  !抽签", "每日运势签"),
            ("  !抽签 财运/姻缘/事业/学业", "各类运势签"),
            ("  !抽签帮助", "查看抽签帮助"),
            ("  ✨ 每天结果固定", "同一天多次抽签结果相同"),
            ("", ""),
            ("🎉 入群欢迎:", ""),
            ("  !欢迎配置", "查看欢迎配置"),
            ("  !开启欢迎", "开启本群欢迎"),
            ("  !关闭欢迎", "关闭本群欢迎"),
            ("  !设置欢迎 <消息>", "设置欢迎语（支持变量）"),
            ("", ""),
            ("🎭 AI性格:", ""),
            ("  !本群性格", "查看本群性格"),
            ("  !本群切换 猫娘/默认", "切换本群性格"),
            ("  💡 私聊固定使用默认助手", "不受群性格影响"),
            ("", ""),
            ("❤️ 好感度系统:", ""),
            ("  !好感度 (@用户)", "查看好感度"),
            ("  !好感榜", "查看本群排行榜"),
            ("  !签到", "每日签到"),
            ("  !商店", "查看商店"),
            ("  !购买 <商品ID>", "购买商品"),
            ("  !设置称号 <称号>", "设置专属称号"),
            ("", ""),
            ("🌐 联网搜索:", ""),
            ("  !搜索 <内容>", "联网搜索信息"),
            ("  !问问 <问题>", "AI联网问答"),
            ("", ""),
        ]
        
        if is_admin:
            lines.extend([
                ("", ""),
                ("⚙️ 管理员命令:", ""),
                ("  !好感度设置 <QQ> <数值>", "设置好感度"),
                ("  !好感度增加 <QQ> <数值>", "增加好感度"),
                ("  !禁言 <QQ> [分钟]", "禁言成员"),
                ("  !解禁 <QQ>", "解除禁言"),
                ("  !ban <QQ> [原因]", "封禁用户"),
                ("  !unban <QQ>", "解封用户"),
                ("  !ban-g <群号>", "拉黑整个群（连坐）"),
                ("  !欢迎开关 开/关", "全局欢迎开关"),
                ("  !远程性格 <群号> <模式>", "远程修改群性格"),
                ("  !绿茶添加群 <群号>", "开启绿茶反击"),
                ("  !自动解禁 开关 开/关", "自动解禁开关"),
            ])
        
        line_height = 28
        height = len(lines) * line_height + 100
        
        img = Image.new('RGB', (width, height), color='#1a1a2e')
        draw = ImageDraw.Draw(img)
        
        y = 20
        for cmd, desc in lines:
            if cmd.startswith("【"):
                draw.text((20, y), cmd, fill='#00ff88', font=self.font_title)
            elif cmd and not cmd.startswith(" "):
                draw.text((20, y), cmd, fill='#ffaa00', font=self.font_normal)
            elif cmd:
                draw.text((20, y), cmd, fill='#00ccff', font=self.font_normal)
                if desc:
                    cmd_len = len(cmd) * 12
                    desc_x = 220 if cmd_len < 200 else 280
                    draw.text((desc_x, y), desc, fill='#ffffff', font=self.font_normal)
            y += line_height
        
        return img
    def create_rename_help_page(self, is_admin: bool = False) -> Image.Image:
        """创建改名帮助页面"""
        width = 550
        height = 420
        line_height = 35
        
        img = Image.new('RGB', (width, height), color='#1a1a2e')
        draw = ImageDraw.Draw(img)
        
        # 标题
        draw.text((20, 20), "【✏️ 改名功能】", fill='#00ff88', font=self.font_title)
        
        # 分割线
        draw.line((20, 55, width-20, 55), fill='#333333', width=1)
        
        y = 80
        commands = [
            ("--- 修改群成员名片 ---", ""),
            ("!改名 @对方 新名字", "修改指定群成员的名片"),
            ("", "需要群管理员或AI管理员权限"),
            ("", "示例: !改名 @张三 李四"),
            ("", ""),
            ("--- 修改机器人名字 ---", ""),
            ("改我名 新名字", "修改机器人自己的名片"),
            ("", "需要AI管理员权限"),
            ("", "示例: 改我名 小可爱"),
            ("", ""),
            ("--- 其他别名 ---", ""),
            ("!改群名片 @对方 新名字", "同上"),
            ("!设置群名片 @对方 新名字", "同上"),
        ]
        
        for cmd, desc in commands:
            if cmd.startswith("---"):
                draw.text((20, y), cmd, fill='#ffaa44', font=self.font_normal)
            elif cmd.startswith("示例"):
                draw.text((40, y), cmd, fill='#aaaaaa', font=self.font_normal)
            elif cmd == "":
                pass
            elif desc == "":
                draw.text((20, y), cmd, fill='#00ccff', font=self.font_normal)
            else:
                draw.text((20, y), cmd, fill='#00ccff', font=self.font_normal)
                draw.text((200, y), desc, fill='#ffffff', font=self.font_normal)
            y += line_height
        
        # 底部提示
        draw.line((20, y+10, width-20, y+10), fill='#333333', width=1)
        draw.text((20, y+30), "💡 输入「!帮助」返回主菜单", fill='#aaaaaa', font=self.font_normal)
        
        return img
    def save_to_temp(self, img: Image.Image) -> str:
        """保存图片到临时文件"""
        temp_dir = "data/temp_images"
        os.makedirs(temp_dir, exist_ok=True)
        
        filename = f"help_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = os.path.join(temp_dir, filename)
        img.save(filepath, "PNG")
        
        return filepath
