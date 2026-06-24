# create_folders.py
import os

# 定义所有需要的状态文件夹
states = [
    'idle',          # 空闲待机
    'happy',         # 开心欢迎
    'thinking',      # 思考加载
    'sleeping',      # 睡觉休息
    'greeting',      # 打招呼
    'sad',           # 难过
    'surprised',     # 惊讶
    'love',          # 喜欢
    'angry',         # 生气
    'celebrate',     # 庆祝
    'remind',        # 提醒
    'confused'       # 疑惑
]

# 创建主文件夹
main_folder = "assistant_images"
if not os.path.exists(main_folder):
    os.makedirs(main_folder)
    print(f"✅ 创建主文件夹: {main_folder}")

# 创建所有状态子文件夹
for state in states:
    state_path = os.path.join(main_folder, state)
    if not os.path.exists(state_path):
        os.makedirs(state_path)
        print(f"✅ 创建: {state_path}")

# 创建说明文件
readme_content = """虚拟助手图片文件夹结构

将您的图片放入对应文件夹：

📁 idle/        - 空闲状态（眨眼、微笑、左右看）
📁 happy/       - 开心状态（大笑、蹦跳）
📁 thinking/    - 思考状态（托腮、转圈）
📁 sleeping/    - 睡觉状态（闭眼、流口水）
📁 greeting/    - 打招呼（挥手、鞠躬）
📁 sad/         - 难过（流泪、低头）
📁 surprised/   - 惊讶（瞪眼、后退）
📁 love/        - 喜欢（比心、飞吻）
📁 angry/       - 生气（叉腰、跺脚）
📁 celebrate/   - 庆祝（撒花、转圈）
📁 remind/      - 提醒（敲黑板、指方向）
📁 confused/    - 疑惑（歪头、挠头）

图片要求：
- 格式：PNG（推荐透明背景）、JPG、GIF
- 尺寸：建议 120x120 像素
- 命名：可以按顺序命名，如 01.png、02.png
- 多张图片会自动循环播放，实现动画效果
"""

readme_path = os.path.join(main_folder, "README.txt")
with open(readme_path, 'w', encoding='utf-8') as f:
    f.write(readme_content)
    print(f"✅ 创建说明文件: {readme_path}")

print(f"\n🎉 完成！共创建 {len(states)} 个文件夹")
print(f"请在 '{main_folder}' 文件夹中添加图片后运行主程序")
