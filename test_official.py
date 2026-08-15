"""
语音上传测试脚本 - 完全复用 official_bot_adapter
"""
import asyncio
import os
import sys

# ===== 直接导入适配器（它会自己读环境变量）=====
from official_bot_adapter import (
    ensure_token,
    upload_voice_official,
    send_message_official,
    BOT_QQ,
    APP_ID  # 打印确认用
)

USER_OPENID = "09AAF23C5552D991CA3600E8AD185CD3"
FILE_PATH = r"C:\Users\xp123\Desktop\qai\data\temp_music\反乌托邦.silk"

async def test_voice():
    print(f"📌 适配器使用的 APP_ID: {APP_ID[:6]}...")
    print(f"📌 机器人QQ: {BOT_QQ}")
    
    # 1. 确保 Token 有效
    token = ensure_token()
    if not token:
        print("❌ 获取 Token 失败")
        return
    
    print(f"✅ Token 已就绪: {token[:20]}...")
    
    # 2. 检查文件
    if not os.path.exists(FILE_PATH):
        print(f"❌ 文件不存在: {FILE_PATH}")
        return
    
    # 3. 读取文件
    with open(FILE_PATH, 'rb') as f:
        voice_data = f.read()
    
    print(f"✅ 文件大小: {len(voice_data)} 字节")
    
    # 4. 上传语音
    print("📤 开始上传语音...")
    file_info = await upload_voice_official(USER_OPENID, voice_data, "反乌托邦.silk")
    
    if not file_info:
        print("❌ 语音上传失败")
        return
    
    print(f"✅ file_info 获取成功，长度: {len(file_info)}")
    
    # 5. 发送语音消息
    print("📤 发送语音消息...")
    result = await send_message_official(
        f"[CQ:record,file=file:///{FILE_PATH}]",
        user_openid=USER_OPENID
    )
    
    if result:
        print("✅ 语音消息发送成功！")
    else:
        print("❌ 语音消息发送失败")

if __name__ == "__main__":
    # 注意：不要在这里设置环境变量，让适配器自己读
    asyncio.run(test_voice())
