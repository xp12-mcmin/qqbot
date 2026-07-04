"""
看门狗A - 独立进程版（带 tkinter 窗口）
检测到 LLBot → 杀 LLBot + 杀主程序 + 杀所有 Python → 自爆
"""
import psutil
import time
import os
import sys
import subprocess
import ctypes
import tkinter as tk
from tkinter import messagebox

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
        sys.stderr.reconfigure(encoding='utf-8', errors='ignore')
    except:
        pass

# ========== 配置 ==========
CHECK_INTERVAL = 5
LLBOT_KEYWORDS = ['llbot', 'lucky', 'lilia']
MAIN_SCRIPT = "qai主程序.py"  # 主程序文件名

# ========== 隐藏任务栏 ==========
def hide_taskbar():
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        ctypes.windll.user32.SetWindowLongW(
            hwnd, -20,
            ctypes.windll.user32.GetWindowLongW(hwnd, -20) | 0x80
        )
    except:
        pass

# ========== 检查 LLBot（只检查新增进程）==========
class ProcessMonitor:
    def __init__(self):
        self.existing_pids = set()
        self._init_existing_pids()
    
    def _init_existing_pids(self):
        try:
            for p in psutil.process_iter(['pid']):
                try:
                    self.existing_pids.add(p.info['pid'])
                except:
                    pass
        except:
            pass
    
    def check_new_processes(self):
        new_processes = []
        try:
            for p in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    pid = p.info['pid']
                    if pid not in self.existing_pids:
                        new_processes.append(p)
                        self.existing_pids.add(pid)
                except:
                    pass
        except:
            pass
        return new_processes
    
    def is_llbot(self, process):
        try:
            name = (process.info.get('name') or '').lower()
            cmdline = ' '.join(process.info.get('cmdline') or []).lower()
            # 跳过看门狗自己
            if 'llbot_watchdog' in name or 'llbot_watchdog' in cmdline:
                return False
            for keyword in LLBOT_KEYWORDS:
                if keyword in name or keyword in cmdline:
                    return True
        except:
            pass
        return False

# ========== 干掉所有 Python + LLBot + 主程序 ==========
def kill_all():
    current_pid = os.getpid()
    killed = 0
    
    # 🔥 先杀占用 8080 的进程（释放端口）
    try:
        result = subprocess.run(
            ['netstat', '-ano', '|', 'findstr', '8080'],
            capture_output=True, text=True, shell=True
        )
        for line in result.stdout.splitlines():
            if 'LISTENING' in line or 'ESTABLISHED' in line:
                parts = line.split()
                pid = parts[-1]
                if pid.isdigit():
                    try:
                        p = psutil.Process(int(pid))
                        p.kill()
                        killed += 1
                        print(f"[看门狗] 干掉占用8080的进程: {pid}")
                    except:
                        pass
    except:
        pass
    
    # 🔥 干掉所有 Python + LLBot（包括主程序）
    for p in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            pid = p.info['pid']
            if pid == current_pid:
                continue
            name = (p.info['name'] or '').lower()
            cmdline = ' '.join(p.info['cmdline'] or []).lower()
            
            # 杀所有 Python 进程（包括主程序）
            if 'python' in name or 'python' in cmdline:
                p.kill()
                killed += 1
                print(f"[看门狗] 干掉 Python 进程: {pid}")
            # 杀 LLBot
            for keyword in LLBOT_KEYWORDS:
                if keyword in name or keyword in cmdline:
                    p.kill()
                    killed += 1
                    print(f"[看门狗] 干掉 LLBot 进程: {pid}")
                    break
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
    with open("watchdog_a.pid", "w") as f:
        f.write(str(os.getpid()))
    
    # 启动守护进程B
    start_watchdog_b()
    
    monitor = ProcessMonitor()
    
    root = tk.Tk()
    root.title("安全组件")
    root.geometry("320x140")
    root.resizable(False, False)
    root.attributes('-topmost', True)
    root.protocol("WM_DELETE_WINDOW", lambda: None)
    
    label = tk.Label(root, text="系统安全组件运行中...", font=("Microsoft YaHei", 12))
    label.pack(pady=10)
    
    status_label = tk.Label(root, text="✅ 监控中", font=("Microsoft YaHei", 10), fg="green")
    status_label.pack()
    
    detail_label = tk.Label(root, text="检测到 LLBot 自动清除", font=("Microsoft YaHei", 9), fg="gray")
    detail_label.pack(pady=5)
    
    def monitor_loop():
        try:
            new_processes = monitor.check_new_processes()
            for p in new_processes:
                if monitor.is_llbot(p):
                    status_label.config(text="⚠️ 检测到非法组件!", fg="red")
                    root.update()
                    time.sleep(0.5)
                    killed = kill_all()
                    messagebox.showwarning("警告", f"已清除 {killed} 个相关进程\n所有 Python 进程已终止")
                    os._exit(0)
                    return
        except:
            pass
        root.after(CHECK_INTERVAL * 1000, monitor_loop)
    
    root.after(1000, monitor_loop)
    root.mainloop()

if __name__ == "__main__":
    main()
