import win32gui
import win32con
import ctypes
import sys
import subprocess
import time
import os
import requests

# ===== 自动提权 =====
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if not is_admin():
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, " ".join(sys.argv), None, 1
    )
    sys.exit()

# ===== 配置 =====
QQ_PATH = r"F:\napcat\QQ.exe"
SNOWLUMA_DIR = r"E:\SnowLuma-v1.14.11-win-x64-lite"
BASE_URL = "http://127.0.0.1:5099"
PASSWORD = "9:fR8jpN7!QX7Yu"
QAI_MAIN = r"C:\Users\xp123\Desktop\qai\qai主程序.py"
BAT_FILE = r"F:\zhenxun_bot-2026\启动与管理.bat"

# ===== MC 服务器配置 (NeoForge) =====
MC_SERVER_DIR = r"E:\下载\122\Server5"

# ===== frpc 配置 =====
FRPC_DIR = r"E:\下载\frp_0.67.0-MSLFrp-20260223_windows_amd64\frp_0.67.0-MSLFrp-20260223_windows_amd64"
FRPC_EXE = os.path.join(FRPC_DIR, "frpc.exe")

FRPC_TUNNELS = [
    ["-u", "HtZYecobfrK6WtHrgIPWr56GPLq-20973", "-t", "53328"],
    ["-u", "HtZYecobfrK6WtHrgIPWr56GPLq-20973", "-t", "53468"],
]

# ===== 检查 QQ 是否在运行 =====
def is_qq_running():
    try:
        result = subprocess.run(["tasklist", "/FI", "IMAGENAME eq QQ.exe"], 
                               capture_output=True, text=True)
        return "QQ.exe" in result.stdout
    except:
        return False

# ===== 获取 QQ 进程 PID =====
def get_qq_pid():
    try:
        result = subprocess.run(["tasklist", "/FI", "IMAGENAME eq QQ.exe", "/FO", "CSV"], 
                               capture_output=True, text=True)
        lines = result.stdout.strip().split("\n")
        for line in lines:
            if "QQ.exe" in line:
                parts = line.split(",")
                if len(parts) >= 2:
                    return int(parts[1].strip('"'))
    except:
        pass
    return None

# ===== 启动 QQ =====
def start_qq():
    print("正在启动 QQ...")
    subprocess.Popen([QQ_PATH])
    print("等待 15 秒让 QQ 登录...")
    time.sleep(15)

# ===== 关闭 QQ 主窗口 =====
def close_qq_window():
    for i in range(5):
        hwnd = win32gui.FindWindow("Chrome_WidgetWin_1", "QQ")
        if not hwnd:
            hwnd = win32gui.FindWindow("Chrome_WidgetWin_1", None)
        if hwnd:
            win32gui.SendMessage(hwnd, win32con.WM_SYSCOMMAND, win32con.SC_CLOSE, 0)
            print(f"已发送关闭命令 (第 {i+1} 次)")
            time.sleep(0.5)
            hwnd_check = win32gui.FindWindow("Chrome_WidgetWin_1", "QQ")
            if not hwnd_check:
                print("✅ QQ 主窗口已关闭")
                return True
        time.sleep(1)
    print("❌ 尝试多次仍无法关闭")
    return False

# ===== 后台启动 SnowLuma =====
def start_snowluma():
    print("正在后台启动 SnowLuma...")
    subprocess.Popen(
        ["node", "./index.mjs"],
        cwd=SNOWLUMA_DIR,
        creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL
    )
    print("等待 SnowLuma 初始化...")
    time.sleep(8)

# ===== 登录 SnowLuma =====
def snowluma_login():
    try:
        resp = requests.post(f"{BASE_URL}/api/login", json={"password": PASSWORD}, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            token = data.get("token")
            if token:
                print("✅ SnowLuma 登录成功")
                return token
        print(f"❌ 登录失败: {resp.status_code}")
        return None
    except Exception as e:
        print(f"❌ 登录请求失败: {e}")
        return None

# ===== API 注入 =====
def inject_qq(pid, token):
    url = f"{BASE_URL}/api/processes/{pid}/load"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = requests.post(url, headers=headers, timeout=5)
        data = resp.json()
        if resp.status_code == 200 and data.get("success") == True:
            print(f"✅ 注入成功！PID={pid}")
            return True
        else:
            print(f"❌ 注入失败: {data}")
            return False
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False

# ===== 等待 QQ 进程 =====
def wait_for_qq_process(timeout=30):
    print(f"等待 QQ 进程出现（最多 {timeout} 秒）...")
    for i in range(timeout * 2):
        pid = get_qq_pid()
        if pid:
            print(f"✅ QQ 进程已出现: PID={pid}")
            return pid
        time.sleep(0.5)
    print("❌ 超时，未找到 QQ 进程")
    return None

# ===== 后台启动程序 =====
def start_background(program_path):
    print(f"正在后台启动: {os.path.basename(program_path)}...")
    
    ext = os.path.splitext(program_path)[1].lower()
    program_dir = os.path.dirname(program_path)
    
    if not os.path.exists(program_dir):
        print(f"⚠️ 目录不存在: {program_dir}")
        return
    
    if ext == ".py":
        subprocess.Popen(
            ["pythonw", program_path],
            cwd=program_dir,
            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL
        )
    elif ext == ".bat" or ext == ".cmd":
        subprocess.Popen(
            ["cmd", "/c", "start", "/b", "", f'"{program_path}"'],
            cwd=program_dir,
            shell=True,
            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL
        )
    else:
        subprocess.Popen(
            [program_path],
            cwd=program_dir,
            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL
        )

# ===== 后台启动 MC 服务器 (NeoForge + javaw.exe) =====
def start_mc_server():
    print("正在后台启动 NeoForge 服务器 (无窗口)...")
    if not os.path.exists(MC_SERVER_DIR):
        print(f"⚠️ MC 服务器目录不存在: {MC_SERVER_DIR}")
        return
    
    # 检查必要的文件是否存在
    jvm_args = os.path.join(MC_SERVER_DIR, "user_jvm_args.txt")
    win_args = os.path.join(MC_SERVER_DIR, "libraries/net/neoforged/neoforge/21.1.248/win_args.txt")
    
    if not os.path.exists(jvm_args):
        print(f"⚠️ 找不到 user_jvm_args.txt")
        return
    if not os.path.exists(win_args):
        print(f"⚠️ 找不到 win_args.txt")
        return
    
    # 用 javaw.exe 替代 java，无窗口运行
    subprocess.Popen(
        ["javaw.exe", f"@{jvm_args}", f"@{win_args}", "nogui"],
        cwd=MC_SERVER_DIR,
        creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL
    )
    print("✅ NeoForge 服务器已启动（无窗口）")

# ===== 后台启动 frpc（两个隧道）=====
def start_frpc():
    print("正在后台启动 frpc 隧道...")
    if not os.path.exists(FRPC_EXE):
        print(f"⚠️ frpc.exe 不存在: {FRPC_EXE}")
        return
    
    for i, tunnel_args in enumerate(FRPC_TUNNELS, 1):
        print(f"  启动隧道 {i}: {' '.join(tunnel_args)}")
        subprocess.Popen(
            [FRPC_EXE] + tunnel_args,
            cwd=FRPC_DIR,
            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL
        )
        time.sleep(0.3)
    print("✅ frpc 隧道已启动")

# ===== 主逻辑 =====
print("=" * 50)
print("   QQ Bot 自动化启动器")
print("=" * 50)

# 1. 启动 QQ
if not is_qq_running():
    start_qq()
else:
    print("QQ 已在运行")

# 2. 关闭 QQ 主窗口
close_qq_window()

# 3. 获取 QQ PID
pid = wait_for_qq_process(timeout=30)
if not pid:
    print("❌ 无法获取 QQ PID")
    sys.exit()

# 4. 启动 SnowLuma
start_snowluma()

# 5. 登录获取 token
token = snowluma_login()
if not token:
    print("❌ 无法获取 token")
    sys.exit()

# 6. API 注入
inject_qq(pid, token)

# 7. 后台启动其他程序
print("\n启动附属程序...")
start_background(QAI_MAIN)
start_background(BAT_FILE)
start_mc_server()
start_frpc()
time.sleep(1)

print("=" * 50)
print("✅ 全部完成！")
print("   - QQ 后台运行 ✅")
print("   - SnowLuma 已注入 ✅")
print("   - qai主程序 ✅")
print("   - 真寻 Bot ✅")
print("   - NeoForge 服务器 (无窗口) ✅")
print("   - frpc 两个隧道 ✅")
print("=" * 50)
