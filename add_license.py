import os
import re

old_key = "7ebbd6192b241b7c"

for root, dirs, files in os.walk("."):
    for f in files:
        if f.endswith(".py"):
            filepath = os.path.join(root, f)
            try:
                with open(filepath, 'r', encoding='utf-8') as file:
                    content = file.read()
                    if old_key in content:
                        print(f"🔍 找到: {filepath}")
                        # 显示包含的行
                        for i, line in enumerate(content.split('\n')):
                            if old_key in line:
                                print(f"  第{i+1}行: {line.strip()}")
            except:
                pass
