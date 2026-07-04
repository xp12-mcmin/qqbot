"""
看门狗A - 有窗口，任务栏隐藏，监控 LLBot
检测到 LLBot → 干掉 LLBot + 所有 Python → 自爆
"""
import psutil
import time
import os
import sys
import subprocess
import ctypes
import tkinter as tk
from tkinter import messagebox

# ========== 强制 UTF-8 ==========
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
        sys.stderr.reconfigure(encoding='utf-8', errors='ignore')
    except:
        pass

# ========== 隐藏任务栏图标 ==========
def hide_taskbar():
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        ctypes.windll.user32.SetWindowLongW(
            hwnd,
            -20,
            ctypes.windll.user32.GetWindowLongW(hwnd, -20) | 0x80
        )
    except:
        pass

# ========== 检查 LLBot ==========
def check_llbot():
    for p in psutil.process_iter(['name', 'cmdline']):
        try:
            name = (p.info['name'] or '').lower()
            cmdline = ' '.join(p.info['cmdline'] or []).lower()
            if 'llbot' in name or 'lucky' in name or 'lilia' in name:
                return True
        except:
            pass
    return False

# ========== 干掉所有 Python + LLBot ==========
def kill_all():
    current_pid = os.getpid()
    killed = 0
    for p in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            pid = p.info['pid']
            if pid == current_pid:
                continue
            name = (p.info['name'] or '').lower()
            cmdline = ' '.join(p.info['cmdline'] or []).lower()
            if 'python' in name or 'llbot' in name or 'lucky' in name or 'lilia' in name:
                p.kill()
                killed += 1
        except:
            pass
    return killed

# ========== 启动守护进程B ==========
def start_watchdog_b():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_dir, "llbot_watchdog_b.py")
    if os.path.exists(script_path):
        subprocess.Popen(
            [sys.executable, script_path],
            cwd=script_dir,
            creationflags=subprocess.CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL
        )

# ========== 主窗口 ==========
def main():
    # 写入 PID
    with open("watchdog_a.pid", "w") as f:
        f.write(str(os.getpid()))
    
    # 启动守护进程B
    start_watchdog_b()
    
    # 创建窗口
    root = tk.Tk()
    root.title("安全组件")
    root.geometry("320x120")
    root.resizable(False, False)
    root.attributes('-topmost', True)
    #root.after(100, hide_taskbar)
    root.protocol("WM_DELETE_WINDOW", lambda: None)
    
    label = tk.Label(root, text="系统安全组件运行中...", font=("Microsoft YaHei", 12))
    label.pack(pady=20)
    
    status_label = tk.Label(root, text="监控中", font=("Microsoft YaHei", 10), fg="green")
    status_label.pack()
    
    def monitor():
        try:
            if check_llbot():
                status_label.config(text="检测到非法组件!", fg="red")
                root.update()
                time.sleep(0.5)
                killed = kill_all()
                messagebox.showwarning("警告", f"已清除 {killed} 个相关进程")
                os._exit(0)
        except:
            pass
        root.after(3000, monitor)
    
    monitor()
    root.mainloop()

if __name__ == "__main__":
    main()
