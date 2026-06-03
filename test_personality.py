import json
import os

print("=" * 50)
print("AI性格诊断")
print("=" * 50)

# 1. 检查配置文件
config_file = "data/ai_personality.json"
print(f"\n1. 配置文件: {config_file}")
print(f"   存在: {os.path.exists(config_file)}")

if os.path.exists(config_file):
    with open(config_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        print(f"   内容: {json.dumps(data, ensure_ascii=False, indent=2)}")

# 2. 测试导入
print("\n2. 测试导入 AIPersonality")
try:
    from ai_personality import AIPersonality
    print("   ✅ 导入成功")
    pm = AIPersonality()
    print(f"   全局默认: {pm.global_default}")
    print(f"   群独立配置: {pm.group_personalities}")
except Exception as e:
    print(f"   ❌ 导入失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 50)
input("按 Enter 退出...")
