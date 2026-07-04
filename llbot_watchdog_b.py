"""
看门狗B - 守护进程
监控看门狗A，发现A挂了就重启
"""
import psutil
import time
import os
import sys
import subprocess

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
        sys.stderr.reconfigure(encoding='utf-8', errors='ignore')
    except:
        pass

WATCHDOG_A_SCRIPT = "llbot_watchdog.py"

def get_watchdog_a_pid():
    try:
        with open("watchdog_a.pid", "r") as f:
            return int(f.read().strip())
    except:
        return None

def start_watchdog_a():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_dir, WATCHDOG_A_SCRIPT)
    if os.path.exists(script_path):
        subprocess.Popen(
            [sys.executable, script_path],
            cwd=script_dir,
            creationflags=subprocess.CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL
        )
        return True
    return False

def main():
    while True:
        try:
            pid = get_watchdog_a_pid()
            if pid is None or not psutil.pid_exists(pid):
                start_watchdog_a()
        except:
            pass
        time.sleep(5)

if __name__ == "__main__":
    main()
