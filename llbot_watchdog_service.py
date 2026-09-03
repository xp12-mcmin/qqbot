import win32serviceutil
import win32service
import win32event
import servicemanager
import psutil
import time
import os
import sys
import ctypes
import subprocess

# ========== 配置 ==========
SERVICE_NAME = "LLBotWatchdog"
SERVICE_DISPLAY_NAME = "LLBot Watchdog Service"
SERVICE_DESCRIPTION = "监控并阻止 LLBot 运行"

# ========== 窗口隐藏 ==========
def hide_console_window():
    """隐藏控制台窗口（任务栏也不显示）"""
    try:
        # 获取控制台窗口句柄
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            # 隐藏窗口（0 = 隐藏）
            ctypes.windll.user32.ShowWindow(hwnd, 0)
            # 从任务栏移除
            ctypes.windll.user32.SetWindowLongW(
                hwnd,
                -20,  # GWL_EXSTYLE
                ctypes.windll.user32.GetWindowLongW(hwnd, -20) | 0x80  # WS_EX_TOOLWINDOW
            )
    except:
        pass

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def elevate_and_restart():
    """提权重启"""
    try:
        script = os.path.abspath(sys.argv[0])
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, script, None, 0  # 0 = 隐藏窗口
        )
        sys.exit(0)
    except:
        sys.exit(1)

# ========== 服务类 ==========
class WatchdogService(win32serviceutil.ServiceFramework):
    _svc_name_ = SERVICE_NAME
    _svc_display_name_ = SERVICE_DISPLAY_NAME
    _svc_description_ = SERVICE_DESCRIPTION

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, ''))
        self.main()

    def main(self):
        while True:
            try:
                for p in psutil.process_iter(['name', 'cmdline']):
                    try:
                        name = (p.info['name'] or '').lower()
                        cmdline = ' '.join(p.info['cmdline'] or []).lower()
                        if 'llbot' in name or 'lucky' in name or 'lilia' in name:
                            for proc in psutil.process_iter(['name']):
                                try:
                                    if 'python' in (proc.info['name'] or '').lower():
                                        proc.kill()
                                except:
                                    pass
                            os._exit(0)
                    except:
                        pass
            except:
                pass
            time.sleep(3)

# ========== 服务管理 ==========
def is_service_installed():
    try:
        win32serviceutil.QueryServiceStatus(SERVICE_NAME)
        return True
    except:
        return False

def install_service():
    try:
        script_path = os.path.abspath(__file__)
        cmd = [sys.executable, script_path, "install"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False

def start_service():
    try:
        win32serviceutil.StartService(SERVICE_NAME)
        return True
    except:
        return False

def auto_register():
    if is_service_installed():
        try:
            status = win32serviceutil.QueryServiceStatus(SERVICE_NAME)
            if status[1] != win32service.SERVICE_RUNNING:
                start_service()
            return True
        except:
            return False
    if install_service():
        time.sleep(1)
        return start_service()
    return False

# ========== 入口 ==========
if __name__ == '__main__':
    # 有命令行参数 → 交给服务管理器
    if len(sys.argv) > 1 and sys.argv[1] in ["install", "start", "stop", "remove", "debug", "status"]:
        win32serviceutil.HandleCommandLine(WatchdogService)
        sys.exit(0)
    
    # 没有参数 → 自动提权 + 自动注册 + 隐藏窗口
    if not is_admin():
        elevate_and_restart()
    
    # 隐藏窗口和任务栏图标
    hide_console_window()
    
    print("[看门狗] 开始自动注册...")
    if auto_register():
        print("[看门狗] ✅ 服务已安装并启动")
        print("[看门狗] 卸载: python llbot_watchdog_service.py remove")
        # 保持窗口不关闭（但已经隐藏了）
        time.sleep(2)
    else:
        print("[看门狗] ❌ 自动注册失败")
        time.sleep(2)
        sys.exit(1)
