"""
抽签系统 - 图片版（每日固定结果 + 随机背景）
"""

import os
import random
import time
import json
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, List, Optional, Tuple


class LotterySystem:
    """抽签系统 - 每日结果固定"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.font_dir = "fonts"
        self.temp_dir = os.path.join(data_dir, "temp_images")
        self.bg_dir = os.path.join(data_dir, "lottery_bg")  # 抽签背景文件夹
        self.records_file = os.path.join(data_dir, "lottery_records.json")
        
        # 确保目录存在
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.bg_dir, exist_ok=True)
        
        # 加载每日记录
        self.daily_records = self._load_records()
        
        # 加载背景图片列表
        self.bg_images = self._load_bg_images()
        
        # 抽签类型配置
        self.lottery_types = {
            "daily": {
                "name": "每日运势",
                "items": [
                    {"name": "大吉", "color": "#ff4444", "desc": "万事如意，好运连连！", "score": 100},
                    {"name": "中吉", "color": "#ff8844", "desc": "心想事成，顺风顺水！", "score": 80},
                    {"name": "小吉", "color": "#ffaa44", "desc": "略有小成，继续努力！", "score": 60},
                    {"name": "半吉", "color": "#cccc44", "desc": "平平淡淡，稳中求进！", "score": 50},
                    {"name": "末吉", "color": "#88aa44", "desc": "稍有不顺，谨慎行事！", "score": 40},
                    {"name": "小凶", "color": "#44aa88", "desc": "注意小人，多加小心！", "score": 30},
                    {"name": "凶", "color": "#4488aa", "desc": "诸事不宜，静待时机！", "score": 20}
                ]
            },
            "fortune": {
                "name": "财运签",
                "items": [
                    {"name": "💰 暴富", "color": "#ffaa00", "desc": "财运亨通，财源滚滚！", "score": 100},
                    {"name": "💵 大财", "color": "#ffcc44", "desc": "收入可观，钱包鼓鼓！", "score": 80},
                    {"name": "💶 中财", "color": "#ddaa44", "desc": "小有收获，意外之财！", "score": 65},
                    {"name": "💷 小财", "color": "#aa8844", "desc": "略有盈余，积少成多！", "score": 50},
                    {"name": "💴 破财", "color": "#886644", "desc": "注意开销，避免损失！", "score": 30},
                    {"name": "💸 漏财", "color": "#664444", "desc": "谨慎投资，防止被骗！", "score": 15}
                ]
            },
            "love": {
                "name": "姻缘签",
                "items": [
                    {"name": "💕 天赐良缘", "color": "#ff6699", "desc": "真爱将至，把握机会！", "score": 100},
                    {"name": "💗 桃花运", "color": "#ff88aa", "desc": "魅力四射，人见人爱！", "score": 85},
                    {"name": "💖 有缘人", "color": "#ffaacc", "desc": "缘分将至，顺其自然！", "score": 70},
                    {"name": "💓 暗恋", "color": "#ddaacc", "desc": "默默喜欢，勇敢表白！", "score": 55},
                    {"name": "💔 无缘", "color": "#cc8899", "desc": "缘分未到，等待时机！", "score": 35},
                    {"name": "💢 情劫", "color": "#aa6677", "desc": "情路坎坷，多加沟通！", "score": 20}
                ]
            },
            "work": {
                "name": "事业签",
                "items": [
                    {"name": "🏆 飞黄腾达", "color": "#ff6644", "desc": "升职加薪，事业巅峰！", "score": 100},
                    {"name": "📈 步步高升", "color": "#ff8844", "desc": "稳步前进，前途光明！", "score": 85},
                    {"name": "💼 顺风顺水", "color": "#ffaa44", "desc": "工作顺利，得心应手！", "score": 70},
                    {"name": "📊 平平淡淡", "color": "#cccc44", "desc": "保持现状，稳中求进！", "score": 55},
                    {"name": "⚠️ 小人作祟", "color": "#88aa44", "desc": "注意同事，谨言慎行！", "score": 35},
                    {"name": "📉 事业低谷", "color": "#4488aa", "desc": "暂避锋芒，蓄势待发！", "score": 20}
                ]
            },
            "study": {
                "name": "学业签",
                "items": [
                    {"name": "🎓 金榜题名", "color": "#44ff44", "desc": "考试顺利，成绩优异！", "score": 100},
                    {"name": "📚 学有所成", "color": "#88ff44", "desc": "勤奋刻苦，收获满满！", "score": 85},
                    {"name": "✏️ 进步明显", "color": "#aaff44", "desc": "努力见效，继续加油！", "score": 70},
                    {"name": "📖 稳住心态", "color": "#cccc44", "desc": "保持状态，戒骄戒躁！", "score": 55},
                    {"name": "😴 注意力分散", "color": "#88aa44", "desc": "集中精力，提高效率！", "score": 35},
                    {"name": "💤 成绩下滑", "color": "#4488aa", "desc": "查漏补缺，迎头赶上！", "score": 20}
                ]
            }
        }
        
        self._load_font()
        print(f"[抽签系统] 初始化完成，类型: {list(self.lottery_types.keys())}")
        print(f"[抽签系统] 已加载 {len(self.daily_records)} 条抽签记录")
        print(f"[抽签系统] 已加载 {len(self.bg_images)} 张背景图片")
    
    def _load_bg_images(self) -> List[str]:
        """加载背景图片列表"""
        bg_images = []
        if os.path.exists(self.bg_dir):
            for file in os.listdir(self.bg_dir):
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                    bg_images.append(os.path.join(self.bg_dir, file))
        return bg_images
    
    def _get_random_bg(self) -> Optional[str]:
        """随机获取一张背景图片"""
        if self.bg_images:
            return random.choice(self.bg_images)
        return None
    
    def _load_records(self) -> Dict:
        """加载抽签记录"""
        if os.path.exists(self.records_file):
            try:
                with open(self.records_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[抽签系统] 加载记录失败: {e}")
                return {}
        return {}
    
    def _save_records(self):
        """保存抽签记录"""
        try:
            with open(self.records_file, 'w', encoding='utf-8') as f:
                json.dump(self.daily_records, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[抽签系统] 保存记录失败: {e}")
    
    def _clean_old_records(self):
        """清理7天前的记录"""
        today = datetime.now().strftime("%Y-%m-%d")
        to_delete = []
        for key, record in self.daily_records.items():
            if record.get("date") != today:
                to_delete.append(key)
        for key in to_delete:
            del self.daily_records[key]
        if to_delete:
            print(f"[抽签系统] 清理了 {len(to_delete)} 条过期记录")
    
    def _get_or_create_result(self, lottery_type: str, user_id: str) -> Tuple[str, str, int]:
        """获取或创建今日抽签结果"""
        today = datetime.now().strftime("%Y-%m-%d")
        key = f"{user_id}_{lottery_type}"
        
        # 检查今天是否已经抽过
        if key in self.daily_records:
            record = self.daily_records[key]
            if record.get("date") == today:
                print(f"[抽签系统] 用户{user_id}今日已抽过{lottery_type}，返回相同结果: {record['result_name']}")
                return record["result_name"], record["result_desc"], record["score"]
        
        # 新抽签：随机选择一个结果
        config = self.lottery_types.get(lottery_type, self.lottery_types["daily"])
        items = config["items"]
        result = random.choice(items)
        
        # 保存结果
        self.daily_records[key] = {
            "date": today,
            "lottery_type": lottery_type,
            "result_name": result["name"],
            "result_desc": result["desc"],
            "score": result["score"]
        }
        self._save_records()
        self._clean_old_records()
        
        print(f"[抽签系统] 用户{user_id}今日首次抽{lottery_type}，结果: {result['name']}")
        return result["name"], result["desc"], result["score"]
    
    def _load_font(self):
        """加载字体"""
        try:
            font_path = os.path.join(self.font_dir, "simhei.ttf")
            if os.path.exists(font_path):
                self.font_title = ImageFont.truetype(font_path, 36)
                self.font_big = ImageFont.truetype(font_path, 48)
                self.font_normal = ImageFont.truetype(font_path, 20)
                self.font_small = ImageFont.truetype(font_path, 16)
                print(f"[抽签系统] 字体加载成功: simhei.ttf")
                return
            
            font_path = os.path.join(self.font_dir, "msyh.ttc")
            if os.path.exists(font_path):
                self.font_title = ImageFont.truetype(font_path, 36)
                self.font_big = ImageFont.truetype(font_path, 48)
                self.font_normal = ImageFont.truetype(font_path, 20)
                self.font_small = ImageFont.truetype(font_path, 16)
                print(f"[抽签系统] 字体加载成功: msyh.ttc")
                return
            
            self.font_title = ImageFont.load_default()
            self.font_big = ImageFont.load_default()
            self.font_normal = ImageFont.load_default()
            self.font_small = ImageFont.load_default()
            print("[抽签系统] 警告：未找到中文字体")
        except Exception as e:
            print(f"[抽签系统] 字体加载失败: {e}")
            self.font_title = ImageFont.load_default()
            self.font_big = ImageFont.load_default()
            self.font_normal = ImageFont.load_default()
            self.font_small = ImageFont.load_default()
    
    def draw_lottery_image(self, lottery_type: str, user_id: str, user_name: str) -> Tuple[str, str, str, int]:
        """生成抽签图片 - 支持随机背景"""
        # 获取或创建今日结果
        result_name, result_desc, score = self._get_or_create_result(lottery_type, user_id)
        
        # 获取配置
        config = self.lottery_types.get(lottery_type, self.lottery_types["daily"])
        result_color = "#ffaa44"
        for item in config["items"]:
            if item["name"] == result_name:
                result_color = item["color"]
                break
        
        # 获取随机背景
        bg_path = self._get_random_bg()
        
        # 图片尺寸
        img_width = 600
        img_height = 500
        
        # 创建背景
        if bg_path and os.path.exists(bg_path):
            # 使用随机背景图片
            bg_img = Image.open(bg_path)
            bg_img = bg_img.resize((img_width, img_height), Image.Resampling.LANCZOS)
            img = bg_img.convert('RGB')
            # 添加半透明遮罩，让文字更清晰
            overlay = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 128))
            img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
        else:
            # 默认渐变背景
            img = Image.new('RGB', (img_width, img_height), color='#1a1a2e')
            # 添加简单渐变效果
            for i in range(img_height):
                r = 26 + int(i / img_height * 10)
                g = 26 + int(i / img_height * 20)
                b = 46 + int(i / img_height * 30)
                for x in range(img_width):
                    img.putpixel((x, i), (r, g, b))
        
        draw = ImageDraw.Draw(img)
        
        # 绘制边框（金色）
        draw.rectangle([8, 8, img_width-8, img_height-8], outline='#ffaa44', width=3)
        
        # 标题
        title = f"【{config['name']}】"
        draw.text((img_width//2, 50), title, fill='#ffaa44', font=self.font_title, anchor='mm')
        
        # 分割线
        draw.line((80, 90, img_width-80, 90), fill='#ffaa44', width=1)
        
        # 用户信息（半透明白色）
        draw.text((img_width//2, 125), f"抽签人: {user_name} ({user_id})", 
                 fill='#dddddd', font=self.font_small, anchor='mm')
        
        # 抽签结果（大号字体）
        draw.text((img_width//2, 200), result_name, fill=result_color, font=self.font_big, anchor='mm')
        
        # 签文解读
        draw.text((img_width//2, 275), result_desc, fill='#eeeeee', font=self.font_normal, anchor='mm')
        
        # 评分条背景
        bar_width = 400
        bar_height = 25
        bar_x = (img_width - bar_width) // 2
        bar_y = 330
        
        # 背景条
        draw.rectangle([bar_x, bar_y, bar_x+bar_width, bar_y+bar_height], fill='#333333')
        # 填充条
        fill_width = int(bar_width * score / 100)
        draw.rectangle([bar_x, bar_y, bar_x+fill_width, bar_y+bar_height], fill=result_color)
        
        # 分数
        draw.text((img_width//2, 375), f"运势值: {score}", fill='#ffaa44', font=self.font_small, anchor='mm')
        
        # 底部提示
        draw.text((img_width//2, 420), f"抽签时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                 fill='#aaaaaa', font=self.font_small, anchor='mm')
        draw.text((img_width//2, 455), "✨ 今日运势，次日重置 ✨",
                 fill='#888888', font=self.font_small, anchor='mm')
        
        # 保存图片
        filename = f"lottery_{lottery_type}_{user_id}_{int(time.time())}.png"
        filepath = os.path.join(self.temp_dir, filename)
        img.save(filepath, "PNG")
        
        return filepath, result_name, result_desc, score
    
    def get_lottery_types(self) -> str:
        """获取可用抽签类型"""
        lines = ["【🎋 抽签系统】", ""]
        for key, config in self.lottery_types.items():
            lines.append(f"  • {key}: {config['name']}")
        lines.append("")
        lines.append("📝 使用: !抽签 <类型>")
        lines.append("💡 示例: !抽签 daily")
        lines.append("")
        lines.append("✨ 每天每种签只能抽一次，结果当天固定")
        return "\n".join(lines)


# 全局实例
_lottery = None

def get_lottery():
    global _lottery
    if _lottery is None:
        _lottery = LotterySystem()
    return _lottery
