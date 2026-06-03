# test_web_search.py
import aiohttp
import asyncio

async def test_web_search():
    """测试联网搜索功能"""
    print("🌐 测试Ollama联网搜索功能...")
    
    try:
        async with aiohttp.ClientSession() as session:
            # 创建一个需要实时信息的查询
            payload = {
                "model": "deepseek-v3.1:671b-cloud",
                "messages": [{
                    "role": "user", 
                    "content": "请使用联网搜索告诉我今天的重要新闻头条"
                }],
                "stream": False
            }
            
            print("发送联网搜索请求...")
            async with session.post(
                "http://127.0.0.1:11434/api/chat",
                json=payload,
                timeout=20  # 给联网搜索足够的时间
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    reply = data.get('message', {}).get('content', '')
                    
                    print("✅ 请求成功！")
                    print(f"回复长度: {len(reply)} 字符")
                    print(f"回复内容: {reply}")
                    
                    # 检查是否包含网络内容指示器
                    web_indicators = ["根据网络", "搜索显示", "最新消息", "新闻报道", "http", "www."]
                    has_web_content = any(indicator in reply for indicator in web_indicators)
                    
                    if has_web_content:
                        print("🎉 联网功能正常工作！")
                    else:
                        print("⚠️ 回复中未检测到明显的网络内容")
                    
                    return True
                else:
                    print(f"❌ 请求失败，状态码: {response.status}")
                    return False
                    
    except asyncio.TimeoutError:
        print("⏰ 请求超时 - 联网搜索可能需要更长时间")
        return False
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        return False

async def main():
    """主测试函数"""
    print("=" * 50)
    print("Ollama联网功能测试")
    print("=" * 50)
    
    success = await test_web_search()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ 测试完成: Ollama联网功能可能已启用")
        print("💡 提示: 有些回复可能不会明确显示'根据网络搜索'等字样")
    else:
        print("❌ 测试完成: 联网功能可能仍有问题")
        print("💡 建议: 尝试不同的查询或检查Ollama配置")

if __name__ == "__main__":
    asyncio.run(main())
