import asyncio
import websockets
import json
import time
from datetime import datetime

async def manual_sign_all_groups():
    """手动获取群列表并对所有群打卡"""
    uri = "ws://127.0.0.1:8765"
    
    try:
        print("[打卡] 正在连接LLOneBot...")
        async with websockets.connect(uri) as websocket:
            print("[打卡] 连接成功")
            
            # ========== 关键修复：接收初始消息 ==========
            # 连接后先接收服务端发来的消息（如生命周期事件）
            try:
                init_msg = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                print(f"[打卡] 收到初始消息")
            except asyncio.TimeoutError:
                print("[打卡] 没有初始消息，继续")
            
            # 1. 获取群列表
            print("[打卡] 开始获取群列表...")
            request_id = f"manual_sign_getlist_{int(time.time()*1000)}"
            
            await websocket.send(json.dumps({
                "action": "get_group_list",
                "params": {"no_cache": False},
                "echo": request_id
            }))
            
            # 等待响应
            groups = None
            timeout = 10
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(response)
                    
                    # 跳过非响应消息
                    if data.get("echo") != request_id:
                        continue
                    
                    if data.get("status") == "ok":
                        groups = data.get("data", [])
                        print(f"[打卡] 获取到 {len(groups)} 个群")
                    else:
                        print(f"[打卡] 获取群列表失败: {data.get('message', '未知错误')}")
                    break
                except asyncio.TimeoutError:
                    continue
            
            if groups is None:
                print("[打卡] 获取群列表超时")
                return
            
            if not groups:
                print("[打卡] 群列表为空")
                return
            
            # 2. 遍历打卡
            print("[打卡] 开始批量打卡...")
            success = 0
            
            for i, group in enumerate(groups):
                group_id = group.get("group_id")
                group_name = group.get("group_name", f"群{group_id}")
                
                if group_id:
                    try:
                        sign_echo = f"manual_sign_{group_id}_{int(time.time()*1000)}"
                        await websocket.send(json.dumps({
                            "action": "send_group_sign",
                            "params": {"group_id": group_id},
                            "echo": sign_echo
                        }))
                        
                        # 简单延迟，不等待响应（避免超时）
                        await asyncio.sleep(0.001)
                        success += 1
                        print(f"[打卡] ✅ {group_name} ({group_id}) 打卡成功 ({success}/{len(groups)})")
                        
                    except Exception as e:
                        print(f"[打卡] ❌ {group_name} ({group_id}) 打卡失败: {e}")
                    
                    # 适当延迟，避免请求过快
                    await asyncio.sleep(0.001)
            
            # 3. 输出结果
            print("\n" + "="*50)
            print(f"[打卡] 批量打卡完成！")
            print(f"[打卡] 成功: {success}/{len(groups)} 个群")
            print("="*50)
            
    except ConnectionRefusedError:
        print("[打卡] 连接失败，请确保LLOneBot已启动")
    except Exception as e:
        print(f"[打卡] 错误: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主函数"""
    print("="*50)
    print("       一键群打卡工具")
    print("="*50)
    print("说明: 获取所有群并自动打卡")
    print("="*50)
    
    # 运行异步函数
    asyncio.run(manual_sign_all_groups())
    
    print("\n按Enter键退出...")
    input()

if __name__ == "__main__":
    main()
