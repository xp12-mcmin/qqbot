"""
授权验证工具
"""
import os
import sys
import json

def verify_module(module_name: str) -> bool:
    """验证模块授权（从 builtins 读取密钥）"""
    try:
        import builtins
        license_key = getattr(builtins, 'XP12_LICENSE_KEY', '')
    except:
        license_key = ''
    
    expected_key = ''
    try:
        if os.path.exists("data/.module_license"):
            with open("data/.module_license", "r") as f:
                data = json.load(f)
                expected_key = data.get("license_key", '')
    except:
        pass
    
    if license_key != expected_key or not expected_key:
        print(f"❌ 模块 [{module_name}] 授权失败！")
        print(f"   请通过主程序调用本模块")
        sys.exit(1)
    
    print(f"✅ 模块 [{module_name}] 授权通过")
    return True
