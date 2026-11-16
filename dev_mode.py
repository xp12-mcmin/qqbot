# dev_mode.py
"""
开发者环境判断（防篡改看门狗后门）
===================================
QAI 自带防篡改看门狗 + 进程查杀组件，会在启动时把"被修改的文件"
还原成基线版本（导致你自己改的 config.json 读取逻辑被回滚），
并会在检测到可疑进程时杀掉所有 Python。

本模块提供"开发者后门"：当满足以下任一条件时，判定为本地开发环境，
看门狗/防篡改 全部跳过，不再还原代码、不再杀进程：
  1. qai 项目根目录下存在 .devmode 标志文件（推荐，最直观）
  2. 本机主机名命中 DEV_HOSTNAMES 里的关键字（备用）

对外只暴露 is_dev_environment()：
  返回 True  → 开发环境，跳过基线校验与进程查杀
  返回 False → 正常环境，保留完整防篡改能力
"""
import os
import socket

# ========== 配置 ==========
# 标志文件名（放在 qai 项目根目录）
DEV_FLAG_FILE = ".devmode"
# 主机名关键字（命中即视为开发环境）
DEV_HOSTNAMES = ["dev", "develop", "workstation", "thinkpad", "surface", "test"]


def _project_root():
    """返回 dev_mode.py 所在目录（qai 项目根目录）"""
    return os.path.dirname(os.path.abspath(__file__))


def is_dev_environment():
    """
    判断是否为本地开发环境。
    返回 True → 开发者后门开启，跳过防篡改校验与进程查杀。
    """
    # 1) 优先：项目根目录下存在 .devmode 标志文件
    try:
        if os.path.exists(os.path.join(_project_root(), DEV_FLAG_FILE)):
            return True
    except Exception:
        pass

    # 2) 备用：主机名命中关键字
    try:
        hostname = socket.gethostname().lower()
        for kw in DEV_HOSTNAMES:
            if kw in hostname:
                return True
    except Exception:
        pass

    return False


def set_dev_mode(on=True):
    """
    便捷地创建/删除 .devmode 标志文件。
      开启后门：  set_dev_mode(True)
      关闭后门：  set_dev_mode(False)
    """
    flag = os.path.join(_project_root(), DEV_FLAG_FILE)
    try:
        if on:
            with open(flag, "w", encoding="utf-8") as f:
                f.write("1")
            return True
        else:
            if os.path.exists(flag):
                os.remove(flag)
            return True
    except Exception:
        return False


if __name__ == "__main__":
    print(f"当前是否为开发者环境: {is_dev_environment()}")