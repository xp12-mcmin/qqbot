# 保存为 test_lottery_debug.py，放在和 qai主程序.py 同一目录
import os
import sys
from PIL import Image, ImageDraw, ImageFont

print("=" * 50)
print("抽签系统诊断")
print("=" * 50)

# 1. 检查当前目录
current_dir = os.getcwd()
print(f"\n1. 当前工作目录: {current_dir}")

# 2. 检查 fonts 文件夹
fonts_dir = "fonts"
print(f"\n2. 检查 fonts 文件夹:")
print(f"   路径: {os.path.abspath(fonts_dir)}")
print(f"   是否存在: {os.path.exists(fonts_dir)}")

if os.path.exists(fonts_dir):
    files = os.listdir(fonts_dir)
    print(f"   文件列表: {files}")
    
    # 查找字体文件
    font_files = [f for f in files if f.endswith(('.ttf', '.ttc', '.otf'))]
    if font_files:
        print(f"   找到字体: {font_files}")
    else:
        print(f"   ❌ 未找到字体文件！")
else:
    print(f"   ❌ fonts 文件夹不存在！")

# 3. 检查 data/temp_images 文件夹
temp_dir = "data/temp_images"
print(f"\n3. 检查临时图片文件夹:")
print(f"   路径: {os.path.abspath(temp_dir)}")
print(f"   是否存在: {os.path.exists(temp_dir)}")

if not os.path.exists(temp_dir):
    print(f"   ❌ 文件夹不存在，尝试创建...")
    os.makedirs(temp_dir, exist_ok=True)
    print(f"   ✅ 已创建")

# 4. 测试 PIL 和字体加载
print(f"\n4. 测试字体加载:")

# 尝试加载系统字体
test_fonts = [
    "fonts/simhei.ttf",
    "fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/msyh.ttc",
]

font_loaded = False
for font_path in test_fonts:
    if os.path.exists(font_path):
        try:
            font = ImageFont.truetype(font_path, 20)
            print(f"   ✅ 字体加载成功: {font_path}")
            font_loaded = True
            break
        except Exception as e:
            print(f"   ❌ 加载失败 {font_path}: {e}")

if not font_loaded:
    print(f"   ⚠️ 使用默认字体（中文会显示为方块）")

# 5. 测试生成图片
print(f"\n5. 测试生成图片:")

try:
    from lottery import get_lottery
    
    lottery = get_lottery()
    print(f"   ✅ lottery 实例创建成功")
    
    img_path, name, desc, score = lottery.draw_lottery_image("daily", "123456", "测试用户")
    print(f"   ✅ 图片生成成功")
    print(f"      路径: {img_path}")
    print(f"      结果: {name}")
    print(f"      描述: {desc}")
    print(f"      分数: {score}")
    
    # 检查图片文件是否存在
    if os.path.exists(img_path):
        file_size = os.path.getsize(img_path)
        print(f"      文件大小: {file_size} bytes")
        if file_size > 1000:
            print(f"      ✅ 图片文件正常")
        else:
            print(f"      ⚠️ 图片文件可能损坏")
    else:
        print(f"      ❌ 图片文件不存在！")
        
except Exception as e:
    print(f"   ❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 50)
print("诊断完成")
input("按 Enter 键退出...")
