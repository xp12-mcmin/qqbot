# rebaseline.py
"""
一键开启"开发者后门"并重建防篡改基线
==========================================
本脚本做两件事：
  1) 在 qai 项目根目录创建 .devmode 标志文件 → 开启开发者后门
     （之后防篡改看门狗、进程查杀全部跳过，不会再回滚你改的代码）
  2) 把"当前文件"作为新的受保护基线写入 C:\\ProgramData\\qai_guard
     （因为 anti_tamper_guard.py 加了后门判断，基线也要更新成新版，
       否则旧版守护会把你改的文件再次回滚）

运行方式（以你的正常用户账号，必要时用管理员身份）：
  python rebaseline.py

说明：
  若提示 PermissionError: C:\\ProgramData\\qai_guard ... denied，
  请右键"以管理员身份运行"命令提示符后再次执行本脚本。

  · 临时关闭后门： 删除项目根目录的 .devmode 文件即可恢复防篡改能力。
  · 命令行开关：  python rebaseline.py off   → 只关闭后门不重建基线
"""
import os
import sys

DEV_FLAG = ".devmode"


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    mode = sys.argv[1] if len(sys.argv) > 1 else "on"

    sys.path.insert(0, here)

    # ---------- 1) 处理 .devmode 标志 ----------
    flag_path = os.path.join(here, DEV_FLAG)
    if mode == "off":
        try:
            if os.path.exists(flag_path):
                os.remove(flag_path)
                print("✅ 已删除 .devmode，开发者后门关闭（恢复防篡改）")
            else:
                print("ℹ️ .devmode 不存在，本来就没开")
        except Exception as e:
            print(f"❌ 删除 .devmode 失败: {e}")
            return 1
    else:
        try:
            with open(flag_path, "w", encoding="utf-8") as f:
                f.write("1")
            print("✅ 已创建 .devmode，开发者后门开启（跳过基线校验与进程查杀）")
        except Exception as e:
            print(f"❌ 创建 .devmode 失败: {e}")
            return 1

    # ---------- 2) 重建基线（含加了后门的 anti_tamper_guard / dev_mode） ----------
    guard_py = os.path.join(here, "anti_tamper_guard.py")
    if not os.path.exists(guard_py):
        print("❌ 未找到 anti_tamper_guard.py，请确认在 qai 项目根目录运行")
        return 1
    import anti_tamper_guard as atg
    atg.reinstall_baseline()
    print("✅ 防篡改基线已更新为当前文件版本（含开发者后门）")
    return 0


if __name__ == "__main__":
    sys.exit(main())