import aiohttp
import json
import os
import time
import base64
from typing import Optional, Dict, Any

class MediaDownloader:
    """媒体文件下载器 - 使用流式接口"""
    
    def __init__(self, cache_dir="data/media_cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.api_base = "http://127.0.0.1:3000"  # NapCat HTTP 端口
    
    async def download_image(self, file_id: str, chunk_size: int = 65536) -> Optional[str]:
        """
        下载图片到本地缓存
        :param file_id: 图片 file_id
        :return: 本地文件路径
        """
        return await self._download_media("download_file_stream", file_id, "image", chunk_size)
    
    async def download_voice(self, file_id: str, chunk_size: int = 65536) -> Optional[str]:
        """
        下载语音到本地缓存
        :param file_id: 语音 file_id
        :return: 本地文件路径
        """
        return await self._download_media("download_file_record_stream", file_id, "voice", chunk_size)
    
    async def _download_media(self, action: str, file_id: str, media_type: str, chunk_size: int) -> Optional[str]:
        """通用下载方法"""
        try:
            # 检查缓存
            cache_path = os.path.join(self.cache_dir, f"{file_id}.{media_type}")
            if os.path.exists(cache_path):
                print(f"[媒体缓存] ✅ 已存在: {cache_path}")
                return cache_path
            
            print(f"[媒体下载] 📥 开始下载 {media_type}: {file_id}")
            
            # 发送下载请求
            payload = {
                "action": action,
                "params": {
                    "file_id": file_id,
                    "chunk_size": chunk_size
                },
                "echo": f"download_{media_type}_{file_id}_{int(time.time()*1000)}"
            }
            
            # 这里需要通过 WebSocket 发送请求并接收流式响应
            # 简化版：用 HTTP 方式获取
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_base}/{action}",
                    json={"file_id": file_id, "chunk_size": chunk_size},
                    timeout=60
                ) as resp:
                    if resp.status != 200:
                        print(f"[媒体下载] ❌ HTTP {resp.status}")
                        return None
                    
                    # 接收流式数据
                    chunks = []
                    file_info = None
                    
                    async for line in resp.content:
                        if not line:
                            continue
                        try:
                            data = json.loads(line.decode('utf-8'))
                            msg_type = data.get("type")
                            
                            if msg_type == "file_info":
                                file_info = data.get("data", {})
                                print(f"[媒体下载] 📋 文件信息: {file_info}")
                            
                            elif msg_type == "file_chunk":
                                chunk_data = data.get("data", {}).get("chunk", "")
                                if chunk_data:
                                    chunks.append(base64.b64decode(chunk_data))
                            
                            elif msg_type == "file_complete":
                                print(f"[媒体下载] ✅ 下载完成，共 {len(chunks)} 个分片")
                                break
                                
                        except json.JSONDecodeError:
                            continue
                    
                    if not chunks:
                        print(f"[媒体下载] ❌ 没有接收到数据")
                        return None
                    
                    # 保存文件
                    ext = self._get_extension(file_info, media_type)
                    filename = f"{file_id}{ext}"
                    filepath = os.path.join(self.cache_dir, filename)
                    
                    with open(filepath, "wb") as f:
                        for chunk in chunks:
                            f.write(chunk)
                    
                    print(f"[媒体下载] ✅ 保存成功: {filepath} ({len(chunks)} 分片)")
                    return filepath
                    
        except Exception as e:
            print(f"[媒体下载] ❌ 异常: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _get_extension(self, file_info: Dict, media_type: str) -> str:
        """获取文件扩展名"""
        if file_info:
            filename = file_info.get("file_name", "")
            if filename and "." in filename:
                return os.path.splitext(filename)[1]
        
        # 默认扩展名
        return ".png" if media_type == "image" else ".m4a"
