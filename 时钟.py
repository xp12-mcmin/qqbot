"""
桌面时钟 + 多任务定时器 + 反破解保护（含反CE）
"""

import sys
import subprocess
import os
import json
import time
import hashlib
import secrets
import threading
import ctypes
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QMenu, QAction, QSystemTrayIcon,
    QGroupBox, QCheckBox, QDialog, QFormLayout,
    QLineEdit, QFileDialog, QComboBox, QListWidget, QListWidgetItem,
    QMessageBox
)
from PyQt5.QtCore import Qt, QTimer, QPoint, QTime, QPropertyAnimation
from PyQt5.QtGui import QPainter, QBrush, QPen, QColor

# 弹窗通知
try:
    from plyer import notification
    HAS_NOTIFY = True
except:
    HAS_NOTIFY = False

# 反破解依赖
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


# ==================== 反破解系统 ====================

# 进程黑名单（包含CE）
BLACKLIST_PROCESSES = [
    # 调试器
    "x64dbg.exe", "x32dbg.exe", "ollydbg.exe", "ida.exe", "ida64.exe",
    # Cheat Engine
    "cheatengine.exe", "cheatengine-i386.exe", "cheatengine-x86_64.exe",
    "cheatengine-x86_64-sse4-avx2.exe",
    # 进程工具
    "processhacker.exe", "processexplorer.exe", "procexp.exe",
    # 注入工具
    "apimonitor.exe", "injector.exe", "extremeinjector.exe",
]

# DLL黑名单
BLACKLIST_DLLS = [
    "injector.dll", "inject.dll", "hook.dll", "cheatengine.dll",
    "speedhack.dll", "bypass.dll",
]

# Cheat Engine 窗口标题关键词
CE_WINDOW_TITLES = [
    "Cheat Engine", "CheatEngine", "Memory Viewer",
    "Address list", "Speedhack", "Advanced Options",
    "Scan Settings", "Memory Scan"
]


class AntiCrack:
    """反破解系统 - 含反CE"""
    
    def __init__(self):
        self.is_cracked = False
        self.crack_count = 0
        self.max_crack_count = 3
        self.protection_enabled = True
        self.self_destruct_activated = False
        
    def start_protection(self):
        """启动所有防护"""
        if sys.platform != "win32":
            print("[反破解] 非Windows系统，跳过防护")
            return
        
        print("[反破解] 启动防护系统...")
        
        # 启动进程监控（含CE检测）
        self._start_process_monitor()
        
        # 启动调试器检测
        self._start_debugger_detector()
        
        # 启动DLL监控
        self._start_dll_monitor()
        
        # 启动CE窗口检测
        self._start_ce_window_monitor()
        
        print("[反破解] 防护系统已启动（含反CE）")
    
    def _start_process_monitor(self):
        """启动进程监控"""
        def monitor():
            while self.protection_enabled and not self.is_cracked:
                try:
                    self._scan_processes()
                    time.sleep(2)
                except:
                    time.sleep(5)
        
        threading.Thread(target=monitor, daemon=True).start()
    
    def _scan_processes(self):
        """扫描可疑进程（含CE）"""
        if not HAS_PSUTIL:
            return
        
        for proc in psutil.process_iter(['name']):
            try:
                name = proc.info['name'].lower() if proc.info['name'] else ''
                for black in BLACKLIST_PROCESSES:
                    if black in name:
                        self._on_threat(f"可疑进程: {name}")
                        return
            except:
                pass
    
    def _start_debugger_detector(self):
        """启动调试器检测"""
        def detect():
            while self.protection_enabled and not self.is_cracked:
                try:
                    if self._is_debugger_present():
                        self._on_threat("调试器检测")
                        return
                    time.sleep(1)
                except:
                    time.sleep(5)
        
        threading.Thread(target=detect, daemon=True).start()
    
    def _is_debugger_present(self):
        """检测调试器"""
        try:
            return ctypes.windll.kernel32.IsDebuggerPresent() != 0
        except:
            return False
    
    def _start_dll_monitor(self):
        """启动DLL监控"""
        def monitor():
            while self.protection_enabled and not self.is_cracked:
                try:
                    self._scan_dlls()
                    time.sleep(3)
                except:
                    time.sleep(5)
        
        threading.Thread(target=monitor, daemon=True).start()
    
    def _scan_dlls(self):
        """扫描可疑DLL"""
        if not HAS_PSUTIL:
            return
        
        try:
            current = psutil.Process()
            for module in current.memory_maps(grouped=False):
                if '.dll' in module.path.lower():
                    dll_name = os.path.basename(module.path).lower()
                    for black in BLACKLIST_DLLS:
                        if black in dll_name:
                            self._on_threat(f"可疑DLL: {dll_name}")
                            return
        except:
            pass
    
    def _start_ce_window_monitor(self):
        """启动 Cheat Engine 窗口检测"""
        def monitor():
            while self.protection_enabled and not self.is_cracked:
                try:
                    if self._check_ce_windows():
                        self._on_threat("Cheat Engine窗口检测")
                        return
                    time.sleep(2)
                except:
                    time.sleep(5)
        
        threading.Thread(target=monitor, daemon=True).start()
    
    def _check_ce_windows(self):
        """检测 Cheat Engine 窗口"""
        try:
            import win32gui
            
            def enum_callback(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    for ce_title in CE_WINDOW_TITLES:
                        if ce_title.lower() in title.lower():
                            windows.append(hwnd)
                return True
            
            windows = []
            win32gui.EnumWindows(enum_callback, windows)
            return len(windows) > 0
        except ImportError:
            # 没有 win32gui，跳过窗口检测
            return False
        except:
            return False
    
    def _on_threat(self, reason):
        """威胁处理"""
        self.crack_count += 1
        print(f"[反破解] 威胁检测 [{self.crack_count}]: {reason}")
        
        if self.crack_count >= self.max_crack_count:
            self.is_cracked = True
            self._self_destruct()
    
    def _self_destruct(self):
        """自毁"""
        if self.self_destruct_activated:
            return
        
        self.self_destruct_activated = True
        print("[反破解] 触发自毁保护")
        
        if getattr(sys, 'frozen', False):
            try:
                exe_path = sys.executable
                if os.path.exists(exe_path):
                    bat_path = os.path.join(os.environ['TEMP'], 'self_destruct.bat')
                    with open(bat_path, 'w') as f:
                        f.write(f'''@echo off
timeout /t 2 /nobreak > nul
del /f /q "{exe_path}"
del /f /q "{bat_path}"
''')
                    os.startfile(bat_path)
            except:
                pass
        
        sys.exit(888)
    
    def security_check(self):
        """安全检查（供主程序调用）"""
        if self.is_cracked:
            return False
        
        if self._is_debugger_present():
            self._on_threat("运行时调试检测")
            return False
        
        return True


_anti_crack = None
def get_anti_crack():
    global _anti_crack
    if _anti_crack is None:
        _anti_crack = AntiCrack()
    return _anti_crack


# ==================== 带动画按钮 ====================

class AnimatedButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(80)
        self.original_geometry = None
        
    def animate_click(self):
        if self.original_geometry is None:
            self.original_geometry = self.geometry()
        self.animation.stop()
        geo = self.geometry()
        new_geo = geo.adjusted(2, 2, -2, -2)
        self.animation.setEndValue(new_geo)
        self.animation.start()
        QTimer.singleShot(80, self.restore_size)
    
    def restore_size(self):
        if self.original_geometry:
            self.animation.setEndValue(self.original_geometry)
            self.animation.start()


class TaskItem:
    def __init__(self, task_id, name, task_time, task_type, task_content, enabled=True):
        self.id = task_id
        self.name = name
        self.task_time = task_time
        self.task_type = task_type
        self.task_content = task_content
        self.enabled = enabled
        self.last_run = None


# ==================== 主窗口 ====================

class FloatingClock(QWidget):
    def __init__(self):
        super().__init__()
        self.tasks = []
        self.next_id = 1
    
        self.init_ui()
        self.init_tray()
        self.init_timer()  # 确保这行存在
        self.load_config()
        self.update_task_display()
        self.check_autostart_status()
        
    def init_ui(self):
        self.setWindowTitle("桌面时钟")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setFixedSize(320, 420)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)
        
        # 时间显示
        self.time_label = QLabel()
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 52px;
                font-weight: bold;
                background: rgba(0,0,0,0.6);
                border-radius: 15px;
                padding: 8px;
            }
        """)
        layout.addWidget(self.time_label)
        
        # 日期显示
        self.date_label = QLabel()
        self.date_label.setAlignment(Qt.AlignCenter)
        self.date_label.setStyleSheet("""
            QLabel {
                color: #cccccc;
                font-size: 12px;
                background: rgba(0,0,0,0.6);
                border-radius: 10px;
                padding: 6px;
            }
        """)
        layout.addWidget(self.date_label)
        
        # 任务列表
        self.task_list = QListWidget()
        self.task_list.setStyleSheet("""
            QListWidget {
                background: rgba(0,0,0,0.5);
                border-radius: 8px;
                color: #ffffff;
                font-size: 11px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #333333;
            }
        """)
        self.task_list.setMaximumHeight(150)
        layout.addWidget(self.task_list)
        
        # 按钮布局
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        self.add_btn = AnimatedButton("➕ 添加任务")
        self.add_btn.setFixedHeight(32)
        self.add_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; border-radius: 6px; font-size: 11px; }")
        self.add_btn.clicked.connect(lambda: self.animated_click(self.add_btn, self.add_task))
        btn_layout.addWidget(self.add_btn)
        
        self.edit_btn = AnimatedButton("✏️ 编辑")
        self.edit_btn.setFixedHeight(32)
        self.edit_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; border-radius: 6px; font-size: 11px; }")
        self.edit_btn.clicked.connect(lambda: self.animated_click(self.edit_btn, self.edit_task))
        btn_layout.addWidget(self.edit_btn)
        
        self.del_btn = AnimatedButton("🗑️ 删除")
        self.del_btn.setFixedHeight(32)
        self.del_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; border-radius: 6px; font-size: 11px; }")
        self.del_btn.clicked.connect(lambda: self.animated_click(self.del_btn, self.delete_task))
        btn_layout.addWidget(self.del_btn)
        
        layout.addLayout(btn_layout)
        
        # 开机自启动开关
        autostart_layout = QHBoxLayout()
        autostart_layout.addWidget(QLabel("🔄 开机自启动:"))
        self.autostart_check = QCheckBox()
        self.autostart_check.toggled.connect(self.toggle_autostart)
        autostart_layout.addWidget(self.autostart_check)
        autostart_layout.addStretch()
        layout.addLayout(autostart_layout)
        
        # 测试按钮
        self.test_btn = AnimatedButton("🔔 弹窗测试")
        self.test_btn.setFixedHeight(32)
        self.test_btn.setStyleSheet("QPushButton { background-color: #555555; color: white; border-radius: 6px; font-size: 11px; }")
        self.test_btn.clicked.connect(lambda: self.animated_click(self.test_btn, self.test_notification))
        layout.addWidget(self.test_btn)
        
        self.setLayout(layout)
        
        # 关闭按钮
        self.close_btn = QPushButton("✕", self)
        self.close_btn.setFixedSize(28, 28)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff4444;
                color: white;
                border-radius: 14px;
                font-size: 14px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background-color: #cc0000;
            }
        """)
        self.close_btn.clicked.connect(self.quit_app)
        self.close_btn.move(self.width() - 35, 8)
        
        self.drag_pos = None
        
    def animated_click(self, button, callback):
        button.animate_click()
        callback()
    
    def resizeEvent(self, event):
        if hasattr(self, 'close_btn'):
            self.close_btn.move(self.width() - 35, 8)
        super().resizeEvent(event)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(QColor(0, 0, 0, 200)))
        painter.setPen(QPen(QColor(255, 255, 255, 80), 2))
        painter.drawRoundedRect(self.rect(), 15, 15)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
    
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_pos:
            self.move(event.globalPos() - self.drag_pos)
    
    def mouseReleaseEvent(self, event):
        self.drag_pos = None
    
    def update_time(self):
        now = datetime.now()
        self.time_label.setText(now.strftime("%H:%M:%S"))
        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        self.date_label.setText(now.strftime(f"%Y年%m月%d日 {weekdays[now.weekday()]}"))
    
    def init_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(5))
        menu = QMenu()
        menu.addAction("显示窗口", self.show)
        menu.addAction("退出", self.quit_app)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()
    
    def init_timer(self):
        """初始化定时器"""
        # 任务检查定时器（每秒检查）
        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self.check_tasks)
        self.check_timer.start(1000)

        # 反破解检查定时器（每5秒检查一次）
        self.crack_check_timer = QTimer()
        self.crack_check_timer.timeout.connect(self.check_crack)
        self.crack_check_timer.start(5000)

        # 时间更新定时器（每秒更新）
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_time)
        self.update_timer.start(1000)
        
        # 反破解检查定时器
        self.crack_check_timer = QTimer()
        self.crack_check_timer.timeout.connect(self.check_crack)
        self.crack_check_timer.start(5000)
    
    def check_crack(self):
        """反破解检查"""
        try:
            anti = get_anti_crack()
            if not anti.security_check():
                print("[反破解] 检测到破解行为，程序退出")
                self.quit_app()
        except Exception as e:
            print(f"[反破解] 检查失败: {e}")
    
    def check_tasks(self):
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        today = now.strftime("%Y-%m-%d")
        
        for task in self.tasks:
            if not task.enabled:
                continue
            if task.task_time == current_time and task.last_run != today:
                self.execute_task(task)
                task.last_run = today
                self.save_config()
    
    def execute_task(self, task):
        print(f"[任务] 执行: {task.name} ({task.task_time})")
        
        try:
            if task.task_type == "program":
                if task.task_content.endswith('.py'):
                    subprocess.Popen(
                        [sys.executable, task.task_content],
                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                    )
                else:
                    subprocess.Popen(
                        [task.task_content],
                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                    )
            
            elif task.task_type == "cmd":
                subprocess.Popen(
                    task.task_content,
                    shell=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                )
            
            elif task.task_type == "shutdown":
                subprocess.Popen("shutdown /s /t 60", shell=True)
                self.show_notification("系统关机", "60秒后自动关机")
            
            elif task.task_type == "restart":
                subprocess.Popen("shutdown /r /t 60", shell=True)
                self.show_notification("系统重启", "60秒后自动重启")
            
            elif task.task_type == "lock":
                if sys.platform == "win32":
                    subprocess.Popen("rundll32.exe user32.dll,LockWorkStation", shell=True)
                self.show_notification("锁屏", "已锁定计算机")
            
            self.show_notification("定时任务", f"已执行: {task.name}")
            
        except Exception as e:
            print(f"[任务] 执行失败: {e}")
    
    def show_notification(self, title, message):
        if HAS_NOTIFY:
            try:
                notification.notify(title=title, message=message, timeout=3)
            except:
                pass
        else:
            print(f"[通知] {title}: {message}")
    
    def test_notification(self):
        self.show_notification("测试", "弹窗测试成功！")
    
    # ========== 开机自启动功能 ==========
    
    def get_autostart_path(self):
        return os.path.join(os.getenv('APPDATA'), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
    
    def get_shortcut_path(self):
        return os.path.join(self.get_autostart_path(), "桌面时钟.lnk")
    
    def is_autostart_enabled(self):
        return os.path.exists(self.get_shortcut_path())
    
    def check_autostart_status(self):
        self.autostart_check.setChecked(self.is_autostart_enabled())
    
    def create_shortcut(self):
        script_path = os.path.abspath(sys.argv[0])
        shortcut_path = self.get_shortcut_path()
        
        ps_script = f'''
        $WScriptShell = New-Object -ComObject WScript.Shell
        $Shortcut = $WScriptShell.CreateShortcut("{shortcut_path}")
        $Shortcut.TargetPath = "{sys.executable}"
        $Shortcut.Arguments = "{script_path}"
        $Shortcut.WorkingDirectory = "{os.path.dirname(script_path)}"
        $Shortcut.Save()
        '''
        
        try:
            subprocess.run(["powershell", "-Command", ps_script], capture_output=True, check=True)
            return True
        except Exception as e:
            print(f"创建快捷方式失败: {e}")
            return False
    
    def delete_shortcut(self):
        shortcut_path = self.get_shortcut_path()
        try:
            if os.path.exists(shortcut_path):
                os.remove(shortcut_path)
            return True
        except Exception as e:
            print(f"删除快捷方式失败: {e}")
            return False
    
    def toggle_autostart(self, checked):
        if checked:
            if self.create_shortcut():
                self.show_notification("开机自启动", "已添加开机自启动")
            else:
                self.autostart_check.setChecked(False)
                QMessageBox.warning(self, "错误", "设置开机自启动失败，请以管理员权限运行？")
        else:
            if self.delete_shortcut():
                self.show_notification("开机自启动", "已取消开机自启动")
    
    # ========== 任务管理 ==========
    
    def add_task(self):
        self.show_task_dialog()
    
    def edit_task(self):
        current = self.task_list.currentRow()
        if current >= 0 and current < len(self.tasks):
            self.show_task_dialog(self.tasks[current])
    
    def delete_task(self):
        current = self.task_list.currentRow()
        if current >= 0 and current < len(self.tasks):
            reply = QMessageBox.question(self, "确认", f"删除任务「{self.tasks[current].name}」？")
            if reply == QMessageBox.Yes:
                self.tasks.pop(current)
                self.update_task_display()
                self.save_config()
    
    def show_task_dialog(self, task=None):
        dialog = QDialog()
        dialog.setWindowTitle("添加任务" if not task else "编辑任务")
        dialog.setFixedSize(420, 380)
        dialog.setWindowFlags(Qt.WindowStaysOnTopHint)
        dialog.setModal(True)
        
        layout = QVBoxLayout(dialog)
        
        # 任务名称
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("任务名称:"))
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("例如: 备份文件")
        if task:
            name_edit.setText(task.name)
        name_layout.addWidget(name_edit)
        layout.addLayout(name_layout)
        
        # 执行时间
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("执行时间:"))
        time_edit = QLineEdit()
        time_edit.setPlaceholderText("例如: 1:43 或 14:30")
        if task:
            time_edit.setText(task.task_time)
        else:
            time_edit.setText("12:00")
        time_layout.addWidget(time_edit)
        layout.addLayout(time_layout)
        
        # 任务类型
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("任务类型:"))
        type_combo = QComboBox()
        type_combo.addItems(["运行程序", "执行CMD命令", "关机", "重启", "锁屏"])
        if task:
            type_map = {"program": 0, "cmd": 1, "shutdown": 2, "restart": 3, "lock": 4}
            type_combo.setCurrentIndex(type_map.get(task.task_type, 0))
        type_layout.addWidget(type_combo)
        layout.addLayout(type_layout)
        
        # 任务内容
        content_group = QGroupBox("任务内容")
        content_layout = QVBoxLayout(content_group)
        
        self.content_edit = QLineEdit()
        self.content_edit.setPlaceholderText("选择程序或输入CMD命令")
        if task and task.task_type in ["program", "cmd"]:
            self.content_edit.setText(task.task_content)
        content_layout.addWidget(self.content_edit)
        
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(lambda: self.browse_file(self.content_edit))
        content_layout.addWidget(browse_btn)
        
        layout.addWidget(content_group)
        
        # 启用开关
        enable_layout = QHBoxLayout()
        enable_layout.addWidget(QLabel("启用任务:"))
        enable_check = QCheckBox()
        enable_check.setChecked(True if not task else task.enabled)
        enable_layout.addWidget(enable_check)
        layout.addLayout(enable_layout)
        
        # 按钮
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("保存")
        cancel_btn = QPushButton("取消")
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        def update_content_visibility():
            task_type = type_combo.currentIndex()
            if task_type in [0, 1]:
                self.content_edit.setVisible(True)
                browse_btn.setVisible(task_type == 0)
                if task_type == 0:
                    self.content_edit.setPlaceholderText("选择要运行的程序")
                else:
                    self.content_edit.setPlaceholderText("输入CMD命令，例如: ping 127.0.0.1")
            else:
                self.content_edit.setVisible(False)
                browse_btn.setVisible(False)
        
        type_combo.currentIndexChanged.connect(lambda: update_content_visibility())
        update_content_visibility()
        
        def save():
            name = name_edit.text().strip()
            if not name:
                QMessageBox.warning(dialog, "提示", "请输入任务名称")
                return
            
            import re
            task_time_raw = time_edit.text().strip()
            match = re.match(r'^(\d{1,2}):(\d{1,2})$', task_time_raw)
            if not match:
                QMessageBox.warning(dialog, "提示", "时间格式错误，请使用 HH:MM 格式，例如: 1:43 或 14:30")
                return
            h = int(match.group(1))
            m = int(match.group(2))
            if h < 0 or h > 23 or m < 0 or m > 59:
                QMessageBox.warning(dialog, "提示", "时间无效，小时应在 0-23，分钟应在 0-59")
                return
            task_time = f"{h:02d}:{m:02d}"
            
            task_type_idx = type_combo.currentIndex()
            task_type_map = ["program", "cmd", "shutdown", "restart", "lock"]
            task_type = task_type_map[task_type_idx]
            
            if task_type in ["program", "cmd"]:
                content = self.content_edit.text().strip()
                if not content:
                    QMessageBox.warning(dialog, "提示", "请输入程序路径或CMD命令")
                    return
            else:
                content = ""
            
            enabled = enable_check.isChecked()
            
            if task:
                task.name = name
                task.task_time = task_time
                task.task_type = task_type
                task.task_content = content
                task.enabled = enabled
            else:
                new_task = TaskItem(
                    task_id=self.next_id,
                    name=name,
                    task_time=task_time,
                    task_type=task_type,
                    task_content=content,
                    enabled=enabled
                )
                self.tasks.append(new_task)
                self.next_id += 1
            
            self.update_task_display()
            self.save_config()
            dialog.accept()
        
        save_btn.clicked.connect(save)
        cancel_btn.clicked.connect(dialog.reject)
        
        dialog.exec_()
    
    def browse_file(self, line_edit):
        file_path, _ = QFileDialog.getOpenFileName(
            None, "选择程序", "", 
            "可执行文件 (*.exe);;Python脚本 (*.py);;批处理文件 (*.bat);;所有文件 (*.*)"
        )
        if file_path:
            line_edit.setText(file_path)
    
    def update_task_display(self):
        self.task_list.clear()
        for task in self.tasks:
            status = "✅" if task.enabled else "⏸️"
            type_icon = {
                "program": "📁",
                "cmd": "💻",
                "shutdown": "🔌",
                "restart": "🔄",
                "lock": "🔒"
            }.get(task.task_type, "📌")
            item_text = f"{status} {type_icon} {task.name}  [{task.task_time}]"
            item = QListWidgetItem(item_text)
            self.task_list.addItem(item)
    
    def save_config(self):
        config = {
            "tasks": [
                {
                    "id": t.id,
                    "name": t.name,
                    "task_time": t.task_time,
                    "task_type": t.task_type,
                    "task_content": t.task_content,
                    "enabled": t.enabled,
                    "last_run": t.last_run
                }
                for t in self.tasks
            ],
            "next_id": self.next_id
        }
        try:
            with open("clock_config.json", "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    def load_config(self):
        try:
            if os.path.exists("clock_config.json"):
                with open("clock_config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.next_id = config.get("next_id", 1)
                    for t in config.get("tasks", []):
                        task = TaskItem(
                            task_id=t.get("id", self.next_id),
                            name=t.get("name", "未命名"),
                            task_time=t.get("task_time", "12:00"),
                            task_type=t.get("task_type", "program"),
                            task_content=t.get("task_content", ""),
                            enabled=t.get("enabled", True)
                        )
                        task.last_run = t.get("last_run")
                        self.tasks.append(task)
                        if task.id >= self.next_id:
                            self.next_id = task.id + 1
                    self.update_task_display()
        except:
            pass
    
    def quit_app(self):
        self.tray_icon.hide()
        QApplication.quit()


if __name__ == "__main__":
    # 启动反破解
    anti = get_anti_crack()
    anti.start_protection()
    
    # 正常启动程序
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    window = FloatingClock()
    window.show()
    sys.exit(app.exec_())