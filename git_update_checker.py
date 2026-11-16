# git_update_checker.py
"""
QAI 连上 Git 自动更新检测模块
==============================
功能：
  1. 启动时检查 git 远程仓库是否有新提交（更新）。
  2. 若有更新：
     - 自动 git fetch + git pull 拉取最新代码；
     - 拉取成功后调用 anti_tamper_guard.reinstall_baseline()
       重建防篡改基线（让新版本成为受保护基线，避免防篡改回滚更新）；
     - 写一个"更新标记" gie_update_needed.flag，
       主程序连上 GIE 后检测到该标记，会触发强制更新（重启），
       让新代码在全新进程里生效。
  3. 全程静默失败，不影响主程序正常运行。

远程地址：
  - 优先使用用户指定的 HTTPS 地址（无需 SSH 配置即可拉公共仓库）：
      https://github.com/xp12-mcmin/qqbot.git
  - 若失败，则回退使用仓库已配置的 remote（origin / public）。
"""
import os
import sys
import subprocess

# ==================== 配置 ====================
# 用户指定的远端地址（HTTPS，公共仓库，pull 无需认证）
TARGET_HTTPS_URL = "https://github.com/xp12-mcmin/qqbot.git"
# 可用环境变量 GIT_UPDATE_URL 覆盖远端地址（用于测试/自定义）
TARGET_HTTPS_URL = os.environ.get("GIT_UPDATE_URL", TARGET_HTTPS_URL)
# 拉取分支
TARGET_BRANCH = os.environ.get("GIT_UPDATE_BRANCH", "main")

# 更新标记（与主程序 GIE 强制更新共用同一个文件）
GIE_UPDATE_FLAG = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "gie_update_needed.flag"
)


# ==================== 工具 ====================
def _run_git(*args, timeout=60, cwd=None):
    """运行 git 命令，返回 (returncode, stdout, stderr)。失败静默返回 None。"""
    try:
        base = os.path.dirname(os.path.abspath(__file__))
        proc = subprocess.run(
            ["git", *args],
            cwd=cwd or base,
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except Exception:
        return None


def _git_remote_url(remote_name):
    """读取某个 remote 的 URL。"""
    r = _run_git("config", "--get", f"remote.{remote_name}.url")
    if r and r[0] == 0:
        return (r[1] or "").strip()
    return None


def _resolve_fetch_url():
    """
    决定用哪个地址去做 fetch / pull。
    优先 HTTPS（用户指定），因为拉公共仓库无需 SSH 密钥。
    若 HTTPS 不可用则回退到仓库已有 remote。
    """
    if _test_url(TARGET_HTTPS_URL):
        return TARGET_HTTPS_URL
    # 回退：优先 public，其次 origin
    for remote in ("public", "origin"):
        url = _git_remote_url(remote)
        if url:
            return url
    return TARGET_HTTPS_URL


def _test_url(url):
    """快速测试一个 URL 是否可达（用 git ls-remote）。"""
    r = _run_git("ls-remote", url, "HEAD", timeout=30)
    return bool(r and r[0] == 0 and r[1].strip())


def _get_local_head():
    """读取当前本地 HEAD 的 commit hash。"""
    r = _run_git("rev-parse", "HEAD")
    if r and r[0] == 0:
        return (r[1] or "").strip()
    return None


def _get_remote_head(url, branch=None):
    """读取远程分支的最新 commit hash。"""
    branch = branch or TARGET_BRANCH
    r = _run_git("ls-remote", url, f"refs/heads/{branch}", timeout=30)
    if r and r[0] == 0 and r[1].strip():
        return r[1].split()[0].strip()
    return None


def _set_update_flag():
    """写更新标记，主程序连上 GIE 后会触发强制更新。"""
    try:
        with open(GIE_UPDATE_FLAG, "w", encoding="utf-8") as f:
            f.write("git-update")
        print(f"[Git更新] 已写入更新标记: {GIE_UPDATE_FLAG}")
    except Exception as e:
        print(f"[Git更新] 写更新标记失败: {e}")


def _refresh_tamper_baseline():
    """
    git pull 成功后，重建防篡改基线。
    让新拉取下来的版本成为新的受保护基线，避免 anti_tamper_guard
    下次启动把更新后的文件"恢复"回旧版本。
    """
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import anti_tamper_guard

        if hasattr(anti_tamper_guard, "reinstall_baseline"):
            anti_tamper_guard.reinstall_baseline()
            print("[Git更新] 已重建防篡改基线（新版本成为受保护基线）")
        else:
            # 旧版没有 reinstall_baseline，直接调用 install_and_guard 重建
            anti_tamper_guard.install_and_guard()
    except Exception as e:
        print(f"[Git更新] 重建防篡改基线失败: {e}")


# ==================== 对外入口 ====================
def check_and_update():
    """
    检测并执行 git 自动更新。
    返回 True 表示"检测到更新并已拉取，需要强制更新重启"；
    返回 False 表示无需更新或更新失败（不影响主程序继续运行）。
    """
    try:
        base = os.path.dirname(os.path.abspath(__file__))
        # 不是 git 仓库则跳过
        r = _run_git("rev-parse", "--is-inside-work-tree")
        if not r or r[0] != 0:
            print("[Git更新] 当前目录不是 git 仓库，跳过自动更新")
            return False

        # 本地有未提交修改（可能是用户正在改代码），不强行更新，避免覆盖
        r = _run_git("status", "--porcelain")
        if r and r[0] == 0 and r[1].strip():
            print("[Git更新] 检测到本地有未提交修改，跳过自动更新（避免覆盖工作）")
            return False

        url = _resolve_fetch_url()
        local_head = _get_local_head()
        remote_head = _get_remote_head(url, TARGET_BRANCH)

        if not local_head:
            print("[Git更新] 无法读取本地 HEAD，跳过")
            return False
        if not remote_head:
            print("[Git更新] 无法读取远程仓库，跳过（可能是网络/认证问题）")
            return False

        if local_head == remote_head:
            print("[Git更新] 已是最新版本，无需更新")
            return False

        # ===== 有更新：拉取 =====
        print(f"[Git更新] 检测到新版本 {remote_head[:8]} (当前 {local_head[:8]})，开始拉取...")
        pull = _run_git("pull", url, TARGET_BRANCH, timeout=180)
        if not pull or pull[0] != 0:
            print(f"[Git更新] 拉取失败: {pull[2] if pull else 'git 不可用'}")
            return False

        # 重建防篡改基线，避免更新被回滚
        _refresh_tamper_baseline()

        # 写更新标记，主程序连上 GIE 后强制更新重启
        _set_update_flag()
        return True

    except Exception as e:
        print(f"[Git更新] 检测异常（不影响主程序）: {e}")
        return False


if __name__ == "__main__":
    updated = check_and_update()
    if updated:
        print("[Git更新] 检测到更新，等待主程序强制重启...")
    else:
        print("[Git更新] 无需更新或更新失败")