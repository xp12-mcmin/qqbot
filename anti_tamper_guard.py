# anti_tamper_guard.py
"""
QAI 防篡改守护（首次启动安装版）
==================================
功能：
  1. qai 首次启动时，在"别的目录"（C:\\ProgramData\\qai_guard）放入
     隐藏文件 qai_integrity.dat，里面记录 qai 主程序 + 所有附属模块
     的 SHA256 基线指纹。
  2. 之后每次主程序启动（import 本模块时），自动校验：
     - 任何受保护文件 被修改 / 被删除 / 被替换 → 从基线目录
       C:\\ProgramData\\qai_guard\\baseline\\ 恢复原文件
     - 隐藏文件本身被删除 → 尝试重建
  3. 隐藏方式：Windows 文件隐藏属性 (FILE_ATTRIBUTE_HIDDEN)。

设计原则：
  - 指纹只算一次（首启），之后复用，避免"自己改自己导致指纹失效"。
  - 恢复用 baseline 里的原件，不重新算哈希。
  - 全程静默失败，不影响主程序正常运行。
"""
import os
import sys
import json
import time
import hashlib
import shutil
import ctypes

# ========== 开发者环境后门 ==========
try:
    from dev_mode import is_dev_environment
except Exception:
    def is_dev_environment():
        return False

# ==================== 路径配置 ====================
# "别的目录"：放隐藏文件和基线备份（主程序目录之外）
GUARD_DIR = r"C:\ProgramData\qai_guard"
HIDDEN_FILE = os.path.join(GUARD_DIR, "qai_integrity.dat")
BASELINE_DIR = os.path.join(GUARD_DIR, "baseline")

# 主程序 + 附属模块（要保护的文件列表）
# 主程序
PROTECTED_MAIN = "qai主程序彩色日志版.py"
# 附属模块（import 进来的那些）
PROTECTED_MODULES = [
    "music.py",
    "ai_draw.py",
    "web_search.py",
    "lottery.py",
    "anti_recall.py",
    "image_cache.py",
    "auto_unmute.py",
    "auto_rejoin.py",
    "sign_module.py",
    "ai_memory.py",
    "help_image.py",
    "video_parser.py",
    "spammer.py",
    "spammer_manager.py",
    "spam_detector.py",
    "llbot_watchdog.py",
    "llbot_watchdog_b.py",
    "llbot_watchdog_service.py",
    "notify_manager.py",
    "official_bot_adapter.py",
    "rename_manager.py",
    "auto_blacklist.py",
    "ai_blacklist.py",
    "blacklist_checker.py",
    "group_audit.py",
    "favorability.py",
    "ai_personality.py",
    "server.py",
    "Newqai.py",
    "auto_unmute_all.py",
    "banned_word_detector.py",
    "git_update_checker.py",
    "anti_tamper_guard.py",
]
# 附属脚本
PROTECTED_SCRIPTS = [
    "111.py",
    "一键启动.bat",
]

ALL_PROTECTED = [PROTECTED_MAIN] + PROTECTED_MODULES + PROTECTED_SCRIPTS


def _script_dir():
    """主程序所在目录（qai 项目根目录）"""
    if "__main__" in sys.modules:
        main_mod = sys.modules["__main__"]
        if hasattr(main_mod, "__file__") and main_mod.__file__:
            return os.path.dirname(os.path.abspath(main_mod.__file__))
    # fallback: 用当前文件位置（主程序 import 本模块时）
    return os.path.dirname(os.path.abspath(__file__))


# ==================== 哈希工具 ====================
def _sha256_file(path):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


# ==================== Windows 隐藏属性 ====================
def _set_hidden(path, hidden=True):
    try:
        kernel32 = ctypes.windll.kernel32
        FILE_ATTRIBUTE_HIDDEN = 0x2
        if not os.path.exists(path):
            return False
        attrs = kernel32.GetFileAttributesW(path)
        if attrs == 0xFFFFFFFF:
            return False
        if hidden:
            attrs |= FILE_ATTRIBUTE_HIDDEN
        else:
            attrs &= ~FILE_ATTRIBUTE_HIDDEN
        return kernel32.SetFileAttributesW(path, attrs) == 0
    except Exception:
        return False


def _ensure_guard_dir():
    try:
        os.makedirs(GUARD_DIR, exist_ok=True)
        os.makedirs(BASELINE_DIR, exist_ok=True)
    except Exception:
        pass


# ==================== 安装（首次启动） ====================
def _compute_fingerprints():
    sdir = _script_dir()
    fps = {}
    for name in ALL_PROTECTED:
        p = os.path.join(sdir, name)
        if os.path.exists(p):
            h = _sha256_file(p)
            if h:
                fps[name] = h
    return fps


def _install_baseline():
    _ensure_guard_dir()
    sdir = _script_dir()
    fps = {}
    for name in ALL_PROTECTED:
        src = os.path.join(sdir, name)
        if not os.path.exists(src):
            continue
        dst = os.path.join(BASELINE_DIR, name)
        try:
            shutil.copy2(src, dst)
            h = _sha256_file(src)
            if h:
                fps[name] = h
        except Exception:
            continue

    payload = {
        "version": 1,
        "installed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "fingerprints": fps,
    }
    with open(HIDDEN_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    _set_hidden(HIDDEN_FILE, True)
    return fps


def _load_guard():
    try:
        with open(HIDDEN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


# ==================== 校验 & 恢复 ====================
def _verify_and_restore():
    guard = _load_guard()
    if guard is None:
        return _install_baseline()

    sdir = _script_dir()
    fps = guard.get("fingerprints", {})
    changed = []

    for name, expect_hash in fps.items():
        cur = os.path.join(sdir, name)
        base = os.path.join(BASELINE_DIR, name)

        cur_hash = _sha256_file(cur) if os.path.exists(cur) else None

        if cur_hash == expect_hash:
            continue

        if os.path.exists(base):
            try:
                shutil.copy2(base, cur)
                changed.append(name)
            except Exception:
                pass
        else:
            if cur_hash:
                fps[name] = cur_hash

    guard["fingerprints"] = fps
    guard["last_check"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(HIDDEN_FILE, "w", encoding="utf-8") as f:
        json.dump(guard, f, ensure_ascii=False, indent=2)
    _set_hidden(HIDDEN_FILE, True)

    if changed:
        print(f"[防篡改] 已恢复 {len(changed)} 个被篡改文件: {', '.join(changed)}")
    return changed


# ==================== 对外入口 ====================
def install_and_guard():
    # 开发者后门：本地开发环境跳过基线校验与文件还原
    if is_dev_environment():
        print("[防篡改] 🔓 检测到开发者环境，跳过基线校验与文件还原（开发者后门）")
        return True

    if not os.path.exists(HIDDEN_FILE):
        print("[防篡改] 首次启动，正在安装基线...")
        _install_baseline()
        print(f"[防篡改] 基线已写入 {HIDDEN_FILE}")
    else:
        _verify_and_restore()
        _set_hidden(HIDDEN_FILE, True)
    return True


def reinstall_baseline():
    """
    重建防篡改基线（供 git 自动更新成功之后调用）。
    重新把当前主程序 + 所有附属模块复制到 baseline，并重算指纹，
    让"新拉取的版本"成为新的受保护基线，避免防篡改把更新回滚。
    """
    print("[防篡改] 正在重建基线（新版本作为受保护基线）...")
    _install_baseline()
    print(f"[防篡改] 基线已更新: {HIDDEN_FILE}")
    return True


if __name__ == "__main__":
    install_and_guard()
