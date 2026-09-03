


import sys
import os
import json
import time
import builtins
from datetime import datetime
from typing import Dict, Optional, List
import asyncio
from typing import Optional


# ==================== 授权验证 ====================
def _verify_module():
    """验证模块授权"""
    module_name = "image_cache"
    
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
模块名：image_cache
功能：待补充
"""

# ==================== 正常代码 ====================




class ImageCache:
    def __init__(self, data_dir: str = "data"):
        self.cache_dir = os.path.join(data_dir, "image_cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        print(f"[图片缓存] 目录: {self.cache_dir}")
    
    def is_image(self, content) -> bool:
        """判断是否是图片消息"""
        if isinstance(content, str):
            return '[CQ:image' in content
        return False
    
    def extract_msg_id(self, content: str) -> Optional[str]:
        """提取消息ID"""
        match = re.search(r'pre_(\d+_\d+)', content)
        if match:
            return match.group(0)
        return None
    
    async def download(self, url: str, msg_id: str) -> Optional[str]:
        """下载图片"""
        try:
            url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
            filename = f"{msg_id}_{url_hash}.jpg"
            filepath = os.path.join(self.cache_dir, filename)
            
            if os.path.exists(filepath):
                return filepath
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        with open(filepath, 'wb') as f:
                            f.write(await resp.read())
                        print(f"[图片缓存] 下载成功: {filename}")
                        return filepath
        except Exception as e:
            print(f"[图片缓存] 下载失败: {e}")
        return None
    
    def get_cq_image(self, msg_id: str) -> Optional[str]:
        """获取图片CQ码"""
        for f in os.listdir(self.cache_dir):
            if f.startswith(msg_id):
                path = os.path.join(self.cache_dir, f)
                return f"[CQ:image,file=file:///{path}]"
        return None


# 全局实例
_image_cache = None

def get_image_cache():
    global _image_cache
    if _image_cache is None:
        _image_cache = ImageCache()
    return _image_cache