"""
视频解析模块 - 使用 bilibili-api-python 库
支持 B站、抖音、YouTube、腾讯视频、爱奇艺等平台
默认关闭，需管理员开启
超过20分钟的视频只发送封面和基本信息
"""

import json
import os
import re
import asyncio
import random
from typing import Dict, Optional, Tuple

# B站专用库
try:
    from bilibili_api import video, sync
    BILIBILI_API_AVAILABLE = True
except ImportError:
    BILIBILI_API_AVAILABLE = False
    print("[视频解析] bilibili-api-python 未安装，B站解析将不可用")

# HTTP请求库
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    print("[视频解析] aiohttp 未安装")

class VideoParser:
    """视频解析器"""
    
    def __init__(self, data_dir: str = "data"):
        self.config_file = os.path.join(data_dir, "video_parser_config.json")
        
        # 默认配置
        self.config = {
            "enabled": False,  # 默认关闭
            "send_to_group": True,  # 是否发送到群里
            "max_duration": 1200,  # 最大时长（秒），20分钟=1200秒，不可更改
            "platforms": {
                "bilibili": {"enabled": True, "name": "B站"},
                "douyin": {"enabled": True, "name": "抖音"},
                "youtube": {"enabled": True, "name": "YouTube"},
                "tencent": {"enabled": True, "name": "腾讯视频"},
                "iqiyi": {"enabled": True, "name": "爱奇艺"}
            }
        }
        
        # 平台URL匹配规则
        self.platform_patterns = {
            "bilibili": [
                r'(?:https?://)?(?:www\.)?bilibili\.com/video/(?:BV\w+|av\d+)',
                r'(?:https?://)?(?:www\.)?b23\.tv/\w+'
            ],
            "douyin": [
                r'(?:https?://)?(?:www\.)?douyin\.com/video/\d+',
                r'(?:https?://)?v\.douyin\.com/\w+'
            ],
            "youtube": [
                r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+',
                r'(?:https?://)?youtu\.be/[\w-]+'
            ],
            "tencent": [
                r'(?:https?://)?v\.qq\.com/x/page/\w+',
                r'(?:https?://)?(?:www\.)?qq\.com/.*?vid=\w+'
            ],
            "iqiyi": [
                r'(?:https?://)?(?:www\.)?iqiyi\.com/v_\w+\.html'
            ]
        }
        
        os.makedirs(data_dir, exist_ok=True)
        self._load_config()
        
        print(f"[视频解析] 模块初始化完成")
        print(f"[视频解析] 状态: {'开启' if self.config['enabled'] else '关闭'}")
        print(f"[视频解析] 发送方式: {'群聊' if self.config['send_to_group'] else '私聊'}")
        print(f"[视频解析] B站API库: {'可用' if BILIBILI_API_AVAILABLE else '不可用'}")
        print(f"[视频解析] 时长限制: 20分钟（超过只发封面）")
    
    def _load_config(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                    self.config.update(saved)
                    self.config["max_duration"] = 1200  # 确保不可更改
            else:
                self._save_config()
        except Exception as e:
            print(f"[视频解析] 配置加载失败: {e}")
    
    def _save_config(self):
        try:
            self.config["max_duration"] = 1200
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[视频解析] 配置保存失败: {e}")
    
    def detect_platform(self, url: str) -> Optional[str]:
        """检测视频链接来自哪个平台"""
        for platform, patterns in self.platform_patterns.items():
            for pattern in patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    return platform
        return None
    
    def extract_bvid(self, url: str) -> Optional[str]:
        """提取B站BV号"""
        patterns = [
            r'BV\w+',
            r'av(\d+)',
            r'b23\.tv/(\w+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                return match.group(0)
        return None
    
    def _format_duration(self, seconds: int) -> str:
        """格式化时长"""
        minutes = seconds // 60
        secs = seconds % 60
        if minutes >= 60:
            hours = minutes // 60
            minutes = minutes % 60
            return f"{hours}小时{minutes}分钟"
        return f"{minutes}分{secs}秒"
    
    async def _parse_bilibili_with_api(self, url: str) -> Optional[Dict]:
        """使用 bilibili-api-python 库解析B站视频"""
        if not BILIBILI_API_AVAILABLE:
            return None
        
        try:
            bvid = self.extract_bvid(url)
            if not bvid:
                return None
            
            print(f"[B站解析] 使用API解析 BV号: {bvid}")
            
            # 创建视频对象
            v = video.Video(bvid=bvid)
            
            # 获取视频信息（异步）
            info = await v.get_info()
            
            duration = info.get("duration", 0)
            is_too_long = duration > self.config["max_duration"]
            
            # 获取统计数据
            stat = info.get("stat", {})
            
            result = {
                "title": info.get("title", "未知标题"),
                "duration": duration,
                "duration_str": self._format_duration(duration),
                "author": info.get("owner", {}).get("name", "未知UP主"),
                "cover": info.get("pic", ""),
                "play": stat.get("view", 0),
                "like": stat.get("like", 0),
                "coin": stat.get("coin", 0),
                "favorite": stat.get("favorite", 0),
                "share": stat.get("share", 0),
                "reply": stat.get("reply", 0),
                "platform": "B站",
                "url": url,
                "is_too_long": is_too_long
            }
            
            if is_too_long:
                result["note"] = f"⚠️ 视频时长 {result['duration_str']}，超过20分钟限制，仅展示封面"
            
            print(f"[B站解析] 成功: {result['title'][:30]}...")
            return result
            
        except Exception as e:
            print(f"[B站解析] API解析失败: {e}")
            return None
    
    async def _parse_bilibili_with_http(self, url: str) -> Optional[Dict]:
        """使用 HTTP 请求解析B站视频（备用方案）"""
        if not AIOHTTP_AVAILABLE:
            return None
        
        try:
            bvid = self.extract_bvid(url)
            if not bvid:
                return None
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://www.bilibili.com/',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            }
            
            api_url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, headers=headers, timeout=10) as resp:
                    if resp.status != 200:
                        return None
                    
                    data = await resp.json()
                    if data.get("code") != 0:
                        print(f"[B站解析] API返回错误: {data.get('message')}")
                        return None
                    
                    info = data["data"]
                    duration = info.get("duration", 0)
                    is_too_long = duration > self.config["max_duration"]
                    
                    return {
                        "title": info.get("title", "未知标题"),
                        "duration": duration,
                        "duration_str": self._format_duration(duration),
                        "author": info.get("owner", {}).get("name", "未知UP主"),
                        "cover": info.get("pic", ""),
                        "play": info.get("stat", {}).get("view", 0),
                        "like": info.get("stat", {}).get("like", 0),
                        "platform": "B站",
                        "url": url,
                        "is_too_long": is_too_long
                    }
        except Exception as e:
            print(f"[B站解析] HTTP解析失败: {e}")
            return None
    
    async def parse_video(self, url: str) -> Optional[Dict]:
        """解析视频链接"""
        platform = self.detect_platform(url)
        if not platform:
            return None
        
        # 检查平台是否启用
        if not self.config["platforms"].get(platform, {}).get("enabled", True):
            return None
        
        # B站解析
        if platform == "bilibili":
            # 优先使用官方API库
            result = await self._parse_bilibili_with_api(url)
            if result:
                return result
            
            # 备用HTTP方案
            result = await self._parse_bilibili_with_http(url)
            if result:
                return result
            
            # 都失败，返回基本信息
            return {
                "title": "B站视频",
                "duration": 0,
                "duration_str": "未知",
                "author": "未知",
                "platform": "B站",
                "url": url,
                "is_too_long": False,
                "note": "解析失败，可能是B站风控，请稍后再试"
            }
        
        # 其他平台暂不支持详细解析
        return {
            "title": f"{self.config['platforms'][platform]['name']}视频",
            "duration": 0,
            "duration_str": "未知",
            "author": "未知",
            "platform": self.config['platforms'][platform]['name'],
            "url": url,
            "is_too_long": False,
            "note": f"该平台暂不支持详细解析"
        }
    
    def format_message(self, info: Dict) -> str:
        """格式化输出消息"""
        # 超过20分钟的视频：只发送封面和基本信息
        if info.get("is_too_long"):
            msg = f"🎬 【{info['platform']}视频】\n"
            msg += f"📺 标题：{info['title']}\n"
            msg += f"⏱️ 时长：{info['duration_str']}\n"
            msg += f"👤 UP主：{info['author']}\n"
            msg += f"⚠️ 视频超过20分钟限制，仅展示封面\n"
            if info.get('cover'):
                msg += f"[CQ:image,file={info['cover']}]"
            return msg
        
        # 正常视频：发送完整信息
        msg = f"🎬 【{info['platform']}视频解析】\n"
        msg += f"📺 标题：{info['title']}\n"
        msg += f"⏱️ 时长：{info['duration_str']}\n"
        msg += f"👤 UP主：{info['author']}\n"
        if info.get('play'):
            msg += f"👀 播放量：{info['play']}\n"
        if info.get('like'):
            msg += f"❤️ 点赞数：{info['like']}\n"
        if info.get('coin'):
            msg += f"💰 硬币数：{info['coin']}\n"
        if info.get('favorite'):
            msg += f"⭐ 收藏数：{info['favorite']}\n"
        if info.get('cover'):
            msg += f"[CQ:image,file={info['cover']}]"
        if info.get('note'):
            msg += f"\n📝 备注：{info['note']}"
        msg += f"\n🔗 链接：{info['url']}"
        
        return msg
    
    # ==================== 管理方法 ====================
    def set_enabled(self, enabled: bool):
        self.config["enabled"] = enabled
        self._save_config()
    
    def set_send_to_group(self, send_to_group: bool):
        self.config["send_to_group"] = send_to_group
        self._save_config()
    
    def get_status(self) -> str:
        bili_status = "✅" if BILIBILI_API_AVAILABLE else "❌"
        return f"""【🎬 视频解析系统】
状态: {'✅ 开启' if self.config['enabled'] else '❌ 关闭'}
发送方式: {'📢 群聊' if self.config['send_to_group'] else '💬 私聊'}
B站API库: {bili_status}
时长限制: ⏰ 20分钟（超过只发封面）

📋 命令:
  !视频解析 开/关 - 开关视频解析
  !视频解析 群发/私聊 - 切换发送方式
  !视频解析 状态 - 查看当前状态

支持平台: B站、抖音、YouTube、腾讯视频、爱奇艺"""