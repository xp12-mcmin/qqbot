import subprocess
import logging
import os
import time

LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "watchdog.log")
if os.path.exists(LOG_PATH):
    try:
        os.remove(LOG_PATH)
    except Exception:
        pass

logging.basicConfig(
    filename=LOG_PATH, level=logging.INFO,
    format="%(asctime)s %(message)s", encoding="utf-8"
)

PROCESS_NAME = "GameViewer.exe"
EXE_PATH = r"D:\新建文件夹 (10)\GameViewer\bin\GameViewer.exe"
CHECK_INTERVAL = 600

def is_running():
    r = subprocess.run(
        f'tasklist /FI "IMAGENAME eq {PROCESS_NAME}"',
        shell=True, capture_output=True,
        text=True, encoding="gbk", errors="ignore"
    )
    return PROCESS_NAME.lower() in r.stdout.lower()

while True:
    try:
        if not is_running():
            logging.info(f"{PROCESS_NAME} 不在运行，尝试拉起...")
            subprocess.Popen(f'"{EXE_PATH}"', shell=True)
        else:
            logging.info(f"{PROCESS_NAME} 正常运行")
    except Exception as e:
            logging.error(f"检查异常: {e}")
    time.sleep(CHECK_INTERVAL)
