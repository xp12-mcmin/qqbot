import pyautogui
import requests
import json
import base64
import time
import tkinter as tk
from tkinter import messagebox
from PIL import ImageGrab, Image
import io
import numpy as np
import sys
import os
import threading
from datetime import datetime
import queue
import re

# 检查 pynput 是否安装
try:
    from pynput import mouse
except ImportError:
    print("❌ 缺少 pynput 库，正在安装...")
    os.system(f"{sys.executable} -m pip install pynput")
    print("请重新运行程序")
    input("按 Enter 退出...")
    sys.exit(0)

class LogWindow:
    """悬浮日志窗口"""
    def __init__(self):
        self.root = None
        self.text_widget = None
        self.is_running = False
        self.log_queue = queue.Queue()
        
    def create(self):
        self.root = tk.Tk()
        self.root.title("🤖 AI 日志")
        self.root.geometry("550x400")
        self.root.resizable(True, True)
        self.root.attributes('-topmost', True)
        self.root.geometry('+0+0')
        self.root.configure(bg='#1a1a2e')
        
        title_frame = tk.Frame(self.root, bg='#16213e', height=30)
        title_frame.pack(fill='x')
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(title_frame, text="🎯 AI 五子棋日志", 
                               font=('Microsoft YaHei', 11, 'bold'),
                               fg='#00d4ff', bg='#16213e')
        title_label.pack(side='left', padx=10, pady=5)
        
        clear_btn = tk.Button(title_frame, text="清空", 
                             command=self.clear_log,
                             font=('Microsoft YaHei', 9),
                             bg='#e94560', fg='white',
                             cursor='hand2')
        clear_btn.pack(side='right', padx=10, pady=3)
        
        region_frame = tk.Frame(self.root, bg='#0f0f23', height=25)
        region_frame.pack(fill='x', padx=5, pady=2)
        region_frame.pack_propagate(False)
        
        self.region_label = tk.Label(region_frame, 
                                     text="📍 区域: 未校准", 
                                     font=('Consolas', 10),
                                     fg='#ffd93d', bg='#0f0f23')
        self.region_label.pack(side='left', padx=10)
        
        self.size_label = tk.Label(region_frame, 
                                   text="📐 大小: -", 
                                   font=('Consolas', 10),
                                   fg='#00d4ff', bg='#0f0f23')
        self.size_label.pack(side='left', padx=10)
        
        self.cell_label = tk.Label(region_frame, 
                                   text="📏 格子: -", 
                                   font=('Consolas', 10),
                                   fg='#00ff88', bg='#0f0f23')
        self.cell_label.pack(side='left', padx=10)
        
        self.status_label = tk.Label(region_frame, 
                                     text="⏳ 等待操作", 
                                     font=('Consolas', 10, 'bold'),
                                     fg='#ff6bff', bg='#0f0f23')
        self.status_label.pack(side='right', padx=10)
        
        sep = tk.Frame(self.root, bg='#16213e', height=1)
        sep.pack(fill='x', padx=5, pady=2)
        
        text_frame = tk.Frame(self.root, bg='#1a1a2e')
        text_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.text_widget = tk.Text(text_frame, 
                                   bg='#0f0f23', 
                                   fg='#00ff88',
                                   font=('Consolas', 10),
                                   wrap='word',
                                   relief='flat',
                                   insertbackground='#00ff88')
        self.text_widget.pack(side='left', fill='both', expand=True)
        
        scrollbar = tk.Scrollbar(text_frame, command=self.text_widget.yview)
        scrollbar.pack(side='right', fill='y')
        self.text_widget.config(yscrollcommand=scrollbar.set)
        
        self.text_widget.tag_config('info', foreground='#00d4ff')
        self.text_widget.tag_config('success', foreground='#00ff88')
        self.text_widget.tag_config('error', foreground='#ff6b6b')
        self.text_widget.tag_config('warning', foreground='#ffd93d')
        self.text_widget.tag_config('move', foreground='#ff6bff')
        self.text_widget.tag_config('time', foreground='#8888ff')
        
        self.is_running = True
        self.log("🚀 AI 日志启动", 'info')
        self.log("📌 等待操作...", 'info')
        self.text_widget.see('end')
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.process_queue()
        
    def update_region_info(self, region, cell_size):
        if not self.is_running:
            return
        try:
            if region:
                left, top, right, bottom = region
                width = right - left
                height = bottom - top
                self.region_label.config(text=f"📍 区域: ({left}, {top}) → ({right}, {bottom})")
                self.size_label.config(text=f"📐 大小: {width}x{height}px")
                self.cell_label.config(text=f"📏 格子: {cell_size}px")
            else:
                self.region_label.config(text="📍 区域: 未校准")
                self.size_label.config(text="📐 大小: -")
                self.cell_label.config(text="📏 格子: -")
        except:
            pass
    
    def update_status(self, status):
        if not self.is_running:
            return
        try:
            self.status_label.config(text=status)
        except:
            pass
        
    def process_queue(self):
        if not self.is_running:
            return
        try:
            while not self.log_queue.empty():
                msg, tag = self.log_queue.get_nowait()
                self._add_log(msg, tag)
        except:
            pass
        if self.root and self.is_running:
            try:
                self.root.after(50, self.process_queue)
            except:
                pass
    
    def log(self, message, tag='info'):
        if not self.is_running:
            return
        self.log_queue.put((message, tag))
    
    def _add_log(self, message, tag='info'):
        if not self.is_running or not self.text_widget:
            return
        try:
            timestamp = datetime.now().strftime('%H:%M:%S')
            self.text_widget.insert('end', f'[{timestamp}] ', 'time')
            self.text_widget.insert('end', f'{message}\n', tag)
            self.text_widget.see('end')
        except:
            pass
    
    def clear_log(self):
        if self.text_widget:
            self.text_widget.delete('1.0', 'end')
            self.log("🗑️ 日志已清空", 'warning')
    
    def on_close(self):
        self.is_running = False
        if self.root:
            try:
                self.root.destroy()
            except:
                pass
            self.root = None
    
    def update(self):
        if self.root and self.is_running:
            try:
                self.root.update()
            except:
                pass

class GobanVisionAI:
    def __init__(self):
        self.my_color = None
        self.running = False
        self.ollama_url = "http://localhost:11434"
        self.model = "gemma4:31b-cloud"  # Gemma4云端模型
        self.region = None
        self.cell_size = None
        self.is_admin = False
        self.listener = None
        self.points = []
        self.calibrating = False
        self.calib_window = None
        self.log_window = None
        self.update_queue = queue.Queue()
        self._last_click_time = 0
        self.control_window = None
        self.wait_window = None
        self.move_count = 0
        self.root_ref = None
        self.border_window = None
        self.border_canvas = None
        self.board_state = np.zeros((15, 15), dtype=int)
        self.last_move = None
        self.state_file = "board_state.json"
        self.ai_call_count = 0  # 统计AI调用次数
        
    def init_log_window(self):
        self.log_window = LogWindow()
        self.log_window.create()
        self.log_window.root.update()
        self.root_ref = self.log_window.root
    
    def log(self, message, tag='info'):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        if self.log_window:
            try:
                self.log_window.log(message, tag)
            except:
                pass
    
    def update_region_info(self):
        if self.log_window:
            try:
                self.log_window.update_region_info(self.region, self.cell_size)
            except:
                pass
    
    def update_status(self, status):
        if self.log_window:
            try:
                self.log_window.update_status(status)
            except:
                pass
    
    def set_window_topmost(self, window):
        try:
            window.attributes('-topmost', True)
            window.after(100, lambda: window.attributes('-topmost', True))
        except:
            pass
    
    def check_admin(self):
        try:
            if os.name == 'nt':
                import ctypes
                self.is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
            else:
                self.is_admin = os.geteuid() == 0
            if not self.is_admin:
                self.log("⚠️ 未以管理员权限运行！", 'warning')
                return False
            return True
        except:
            self.is_admin = True
            return True
    
    def reset_board(self):
        self.board_state = np.zeros((15, 15), dtype=int)
        self.move_count = 0
        self.last_move = None
        self.ai_call_count = 0
        self.log("🔄 棋盘已重置", 'info')
        if os.path.exists(self.state_file):
            os.remove(self.state_file)
    
    def save_board_state(self):
        try:
            data = {
                'board_state': self.board_state.tolist(),
                'move_count': int(self.move_count),
                'my_color': int(self.my_color) if self.my_color is not None else None,
                'last_move': [int(x) for x in self.last_move] if self.last_move else None,
                'region': [int(x) for x in self.region] if self.region else None,
                'cell_size': int(self.cell_size) if self.cell_size else None,
                'ai_call_count': int(self.ai_call_count)
            }
            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.log(f"保存失败: {e}", 'error')
    
    def load_board_state(self):
        if not os.path.exists(self.state_file):
            return False
        
        try:
            with open(self.state_file, 'r') as f:
                content = f.read()
                if not content or content.strip() == '':
                    os.remove(self.state_file)
                    return False
                data = json.loads(content)
            
            self.board_state = np.array(data['board_state'])
            self.move_count = int(data['move_count'])
            self.my_color = int(data['my_color']) if data['my_color'] is not None else None
            self.last_move = tuple(data['last_move']) if data.get('last_move') else None
            self.region = tuple(data['region']) if data.get('region') else None
            self.cell_size = int(data['cell_size']) if data.get('cell_size') else None
            self.ai_call_count = int(data.get('ai_call_count', 0))
            
            self.log(f"📂 加载棋盘: {self.move_count} 步, AI调用: {self.ai_call_count}次", 'success')
            return True
        except json.JSONDecodeError:
            self.log("⚠️ 存档损坏，删除重建", 'warning')
            try:
                os.remove(self.state_file)
            except:
                pass
            return False
        except Exception as e:
            self.log(f"加载失败: {e}", 'error')
            return False
    def one_click_restart(self):
        """一键重开：完全重置，回到选颜色界面"""
        if messagebox.askyesno("🔄 一键重开", 
                               "确定要重新开始吗？\n\n"
                               "• 当前棋局将被清空\n"
                               "• 存档将被删除\n"
                               "• 返回颜色选择界面\n\n"
                               "确定继续？"):
            
            self.log("🔄 一键重开...", 'warning')
            
            # 1. 删除存档
            if os.path.exists(self.state_file):
                os.remove(self.state_file)
                self.log("🗑️ 已删除存档", 'info')
            
            # 2. 重置棋盘
            self.board_state = np.zeros((15, 15), dtype=int)
            self.move_count = 0
            self.last_move = None
            self.ai_call_count = 0
            
            # 3. 关闭等待窗口
            if self.wait_window:
                self.wait_window.destroy()
                self.wait_window = None
            
            # 4. 关闭边框（如果有）
            if hasattr(self, 'border_window') and self.border_window:
                try:
                    self.border_window.destroy()
                    self.border_window = None
                except:
                    pass
            
            # 5. 回到颜色选择界面
            self.create_start_window()
            
            self.log("✅ 已重置，返回选择界面", 'success')    
    def board_to_string(self):
        symbols = {0: '·', 1: '●', 2: '○'}
        lines = []
        for i in range(15):
            row = ''.join(symbols[self.board_state[i][j]] for j in range(15))
            lines.append(row)
        return '\n'.join(lines)
    
    def create_start_window(self):
        self.control_window = tk.Toplevel()
        self.control_window.title("🎯 五子棋 AI")
        self.control_window.geometry("350x250")
        self.control_window.resizable(False, False)
        self.set_window_topmost(self.control_window)
        
        self.control_window.update_idletasks()
        width = self.control_window.winfo_width()
        height = self.control_window.winfo_height()
        x = (self.control_window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.control_window.winfo_screenheight() // 2) - (height // 2)
        self.control_window.geometry(f'+{x}+{y}')
        
        tk.Label(self.control_window, text="🎯 五子棋 AI", 
                font=('Arial', 20, 'bold'), fg='#2196F3').pack(pady=20)
        
        tk.Label(self.control_window, text="选择执子颜色：", 
                font=('Arial', 13)).pack(pady=10)
        
        color_frame = tk.Frame(self.control_window)
        color_frame.pack(pady=15)
        
        btn_black = tk.Button(color_frame, text="● 黑子 (先手)", 
                             command=lambda: self.select_color(1),
                             font=('Arial', 13, 'bold'),
                             bg='#333', fg='white', width=14, height=2)
        btn_black.pack(side=tk.LEFT, padx=10)
        
        btn_white = tk.Button(color_frame, text="○ 白子 (后手)", 
                             command=lambda: self.select_color(2),
                             font=('Arial', 13, 'bold'),
                             bg='#ddd', fg='black', width=14, height=2)
        btn_white.pack(side=tk.LEFT, padx=10)
        
        tk.Label(self.control_window, text="💡 选择后自动进入校准", 
                font=('Arial', 10), fg='gray').pack(pady=15)
        
        self.control_window.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def select_color(self, color):
        self.my_color = color
        color_name = "黑子●" if color == 1 else "白子○"
        self.log(f"🎯 选择执{color_name}", 'info')
        
        if self.load_board_state():
            self.log("📂 恢复上一局", 'success')
            if self.control_window:
                self.control_window.destroy()
                self.control_window = None
            self.update_region_info()
            if self.region:
                self.show_wait_window()
                return
        
        self.reset_board()
        if self.control_window:
            self.control_window.destroy()
            self.control_window = None
        if self.root_ref:
            self.root_ref.after(300, self.calibrate_region_dialog)
    
    def calibrate_region_dialog(self):
        try:
            self.points = []
            self.calibrating = True
            
            root = tk.Toplevel()
            root.title("棋盘校准")
            root.geometry("450x350")
            root.resizable(False, False)
            self.set_window_topmost(root)
            
            root.update_idletasks()
            width = root.winfo_width()
            height = root.winfo_height()
            x = (root.winfo_screenwidth() // 2) - (width // 2)
            y = (root.winfo_screenheight() // 2) - (height // 2)
            root.geometry(f'+{x}+{y}')
            
            self.calib_window = root
            
            tk.Label(root, text="📐 棋盘校准", font=('Arial', 18, 'bold'), fg='#2196F3').pack(pady=15)
            
            self.step_var = tk.StringVar()
            self.step_var.set("👆 请将鼠标移到棋盘左上角，然后点击左键")
            self.step_label = tk.Label(root, textvariable=self.step_var, 
                                      font=('Arial', 16, 'bold'), fg='#FF9800', pady=15)
            self.step_label.pack()
            
            self.coord_var = tk.StringVar()
            self.coord_var.set("等待点击...")
            coord_label = tk.Label(root, textvariable=self.coord_var, 
                                   font=('Arial', 13), fg='green', pady=5)
            coord_label.pack()
            
            self.status_var = tk.StringVar()
            self.status_var.set("📍 点击棋盘左上角记录位置")
            status_label = tk.Label(root, textvariable=self.status_var, 
                                    font=('Arial', 11), fg='#666', pady=5)
            status_label.pack()
            
            self.confirm_frame = tk.Frame(root)
            
            self.btn_confirm = tk.Button(self.confirm_frame, text="✅ 确认校准", 
                                        command=self.confirm_calib,
                                        font=('Arial', 13, 'bold'),
                                        bg='#4CAF50', fg='white',
                                        width=14, height=2)
            self.btn_confirm.pack(side=tk.LEFT, padx=10)
            
            self.btn_redo = tk.Button(self.confirm_frame, text="🔄 重新校准", 
                                     command=self.redo_calib,
                                     font=('Arial', 13),
                                     bg='#FF5722', fg='white',
                                     width=12, height=2)
            self.btn_redo.pack(side=tk.LEFT, padx=10)
            
            btn_cancel = tk.Button(root, text="❌ 取消", 
                                  command=self.cancel_calib,
                                  font=('Arial', 11),
                                  bg='#f44336', fg='white',
                                  width=8, height=1)
            btn_cancel.pack(side=tk.BOTTOM, pady=15)
            
            tip = tk.Label(root, text="💡 点击左上角→右下角，红色边框会显示在棋盘上", 
                          font=('Arial', 10), fg='gray')
            tip.pack(side=tk.BOTTOM, pady=5)
            
            def start_listener():
                try:
                    with mouse.Listener(on_click=self.on_mouse_click_auto) as listener:
                        self.listener = listener
                        listener.join()
                except Exception as e:
                    self.log(f"监听器错误: {e}", 'error')
            
            threading.Thread(target=start_listener, daemon=True).start()
            self.wait_for_window(root)
            
            self.calibrating = False
            if self.listener:
                try:
                    self.listener.stop()
                except:
                    pass
            
            return self.region is not None
        except Exception as e:
            self.log(f"校准对话框错误: {e}", 'error')
            import traceback
            traceback.print_exc()
            return False
    
    def update_border(self, x1, y1, x2, y2):
        try:
            left = min(x1, x2)
            right = max(x1, x2)
            top = min(y1, y2)
            bottom = max(y1, y2)
            width = right - left
            height = bottom - top
            
            if width < 10 or height < 10:
                return
            
            if hasattr(self, 'border_window') and self.border_window:
                try:
                    self.border_window.destroy()
                except:
                    pass
                self.border_window = None
            
            self.border_window = tk.Toplevel()
            self.border_window.title("")
            self.border_window.geometry(f"{width}x{height}+{left}+{top}")
            self.border_window.attributes('-topmost', True)
            self.border_window.overrideredirect(True)
            self.border_window.configure(bg='white')
            self.border_window.attributes('-transparentcolor', 'white')
            
            self.border_canvas = tk.Canvas(self.border_window, 
                                          bg='white', 
                                          highlightthickness=0,
                                          width=width, 
                                          height=height)
            self.border_canvas.pack(fill='both', expand=True)
            
            self.border_canvas.create_rectangle(0, 0, width, height, 
                                               outline='red', width=3)
            
            c = 20
            self.border_canvas.create_line(0, c, 0, 0, fill='red', width=4)
            self.border_canvas.create_line(0, 0, c, 0, fill='red', width=4)
            self.border_canvas.create_line(width, c, width, 0, fill='red', width=4)
            self.border_canvas.create_line(width, 0, width-c, 0, fill='red', width=4)
            self.border_canvas.create_line(0, height-c, 0, height, fill='red', width=4)
            self.border_canvas.create_line(0, height, c, height, fill='red', width=4)
            self.border_canvas.create_line(width, height-c, width, height, fill='red', width=4)
            self.border_canvas.create_line(width, height, width-c, height, fill='red', width=4)
            
            self.border_canvas.create_text(width//2, height-20, 
                                          text=f"{width}x{height}px", 
                                          fill='red', font=('Arial', 12, 'bold'))
            
            self.border_window.lift()
            self.log(f"📐 边框: ({left},{top}) {width}x{height}px", 'info')
            
        except Exception as e:
            self.log(f"边框错误: {e}", 'error')
    
    def on_mouse_click_auto(self, x, y, button, pressed):
        try:
            if not pressed:
                return
            if time.time() - self._last_click_time < 0.3:
                return
            self._last_click_time = time.time()
            
            if not self.calibrating:
                return
            if len(self.points) >= 2:
                return
            
            try:
                if self.calib_window:
                    win_x = self.calib_window.winfo_x()
                    win_y = self.calib_window.winfo_y()
                    win_w = self.calib_window.winfo_width()
                    win_h = self.calib_window.winfo_height()
                    if win_x <= x <= win_x + win_w and win_y <= y <= win_y + win_h:
                        return
            except:
                pass
            
            self.points.append((x, y))
            
            if len(self.points) == 1:
                self.safe_ui_update(self.coord_var.set, f"✅ 左上角: ({x}, {y})")
                self.safe_ui_update(self.step_var.set, "👆 请将鼠标移到棋盘右下角，然后点击左键")
                self.safe_ui_update(self.step_label.config, fg='#FF9800')
                self.safe_ui_update(self.status_var.set, "📍 点击棋盘右下角记录位置")
                self.log(f"📍 记录左上角: ({x}, {y})", 'info')
                
            elif len(self.points) == 2:
                x1, y1 = self.points[0]
                x2, y2 = self.points[1]
                left = min(x1, x2)
                right = max(x1, x2)
                top = min(y1, y2)
                bottom = max(y1, y2)
                width = right - left
                height = bottom - top
                
                if width < 50 or height < 50:
                    self.log("⚠️ 区域太小，请重新点击", 'warning')
                    self.safe_ui_update(self.status_var.set, "⚠️ 区域太小，请重新点击")
                    self.points.clear()
                    self.safe_ui_update(self.coord_var.set, "等待点击...")
                    self.safe_ui_update(self.step_var.set, "👆 请将鼠标移到棋盘左上角，然后点击左键")
                    self.safe_ui_update(self.step_label.config, fg='#FF9800')
                    if hasattr(self, 'border_window') and self.border_window:
                        try:
                            self.border_window.destroy()
                            self.border_window = None
                        except:
                            pass
                    return
                
                self.region = (left, top, right, bottom)
                self.cell_size = width // 15
                
                self.log(f"📍 记录右下角: ({x2}, {y2})", 'info')
                self.log(f"📐 棋盘区域: {width}x{height}px, 格子: {self.cell_size}px", 'info')
                
                self.safe_ui_update(self.update_border, x1, y1, x2, y2)
                
                self.safe_ui_update(self.coord_var.set, f"✅ 左上角: ({left}, {top})\n✅ 右下角: ({right}, {bottom})")
                self.safe_ui_update(self.step_var.set, "✅ 校准完成！点击确认继续")
                self.safe_ui_update(self.step_label.config, fg='green')
                self.safe_ui_update(self.status_var.set, f"📐 棋盘: {width}x{height}px  格子: {self.cell_size}px")
                self.safe_ui_update(self.confirm_frame.pack, pady=10)
        except Exception as e:
            self.log(f"鼠标回调错误: {e}", 'error')
    
    def confirm_calib(self):
        if self.region is None:
            return
        
        result = messagebox.askyesno(
            "确认校准",
            f"棋盘区域:\n"
            f"左上角: ({self.region[0]}, {self.region[1]})\n"
            f"右下角: ({self.region[2]}, {self.region[3]})\n"
            f"大小: {self.region[2]-self.region[0]} x {self.region[3]-self.region[1]}px\n"
            f"格子大小: {self.cell_size}px\n\n"
            f"确认这个位置吗？"
        )
        if result:
            self.log("✅ 校准已确认", 'success')
            self.calibrating = False
            if self.listener:
                try:
                    self.listener.stop()
                except:
                    pass
            self.update_region_info()
            self.calib_window.destroy()
            self.save_board_state()
            self.show_wait_window()
        else:
            self.redo_calib()
    
    def redo_calib(self):
        self.points.clear()
        self.coord_var.set("等待点击...")
        self.step_var.set("👆 请将鼠标移到棋盘左上角，然后点击左键")
        self.step_label.config(fg='#FF9800')
        self.status_var.set("📍 重新校准")
        self.confirm_frame.pack_forget()
        if hasattr(self, 'border_window') and self.border_window:
            try:
                self.border_window.destroy()
                self.border_window = None
            except:
                pass
    
    def cancel_calib(self):
        self.log("❌ 校准取消", 'error')
        self.calibrating = False
        if self.listener:
            try:
                self.listener.stop()
            except:
                pass
        if hasattr(self, 'border_window') and self.border_window:
            try:
                self.border_window.destroy()
                self.border_window = None
            except:
                pass
        self.calib_window.destroy()
        self.region = None
        self.create_start_window()
    
    def show_wait_window(self):
        self.wait_window = tk.Toplevel()
        self.wait_window.title("⏳ 等待中...")
        self.wait_window.geometry("420x380")
        self.wait_window.resizable(False, False)
        self.set_window_topmost(self.wait_window)
        
        self.wait_window.update_idletasks()
        width = self.wait_window.winfo_width()
        height = self.wait_window.winfo_height()
        x = (self.wait_window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.wait_window.winfo_screenheight() // 2) - (height // 2)
        self.wait_window.geometry(f'+{x}+{y}')
        
        tk.Label(self.wait_window, text="🎯 五子棋 AI", 
                font=('Arial', 18, 'bold'), fg='#2196F3').pack(pady=15)
        
        self.wait_status_var = tk.StringVar()
        self.wait_status_var.set("⏳ 等待对手下棋...")
        status_label = tk.Label(self.wait_window, textvariable=self.wait_status_var, 
                               font=('Arial', 14, 'bold'), fg='#FF9800', pady=10)
        status_label.pack()
        
        color_name = "黑子●" if self.my_color == 1 else "白子○"
        tk.Label(self.wait_window, text=f"你执 {color_name}", 
                font=('Arial', 12), fg='#666').pack()
        
        self.wait_move_var = tk.StringVar()
        self.wait_move_var.set(f"📊 步数: {self.move_count}  |  AI调用: {self.ai_call_count}次")
        tk.Label(self.wait_window, textvariable=self.wait_move_var, 
                font=('Arial', 12), fg='#666').pack(pady=5)
        
        self.btn_wait_ai = tk.Button(self.wait_window, text="🤖 AI 下棋", 
                                    command=self.ai_move,
                                    font=('Arial', 14, 'bold'),
                                    bg='#4CAF50', fg='white',
                                    width=16, height=2)
        self.btn_wait_ai.pack(pady=15)
        
        btn_frame = tk.Frame(self.wait_window)
        btn_frame.pack(pady=5)
        # 在 btn_frame 里加这个按钮
        btn_restart = tk.Button(btn_frame, text="🔄 一键重开", 
                               command=self.one_click_restart,
                               font=('Arial', 11, 'bold'),
                               bg='#e94560', fg='white',
                               width=12)
        btn_restart.pack(side=tk.LEFT, padx=5)
        btn_reset = tk.Button(btn_frame, text="🔄 重置棋盘", 
                             command=self.reset_and_restart,
                             font=('Arial', 11),
                             bg='#FF9800', fg='white',
                             width=12)
        btn_reset.pack(side=tk.LEFT, padx=5)
        
        btn_new = tk.Button(btn_frame, text="🆕 新游戏", 
                           command=self.new_game,
                           font=('Arial', 11),
                           bg='#2196F3', fg='white',
                           width=12)
        btn_new.pack(side=tk.LEFT, padx=5)
        
        tk.Label(self.wait_window, text="💡 对手下完后，点击「AI下棋」", 
                font=('Arial', 10), fg='gray').pack(pady=5)
        
        btn_exit = tk.Button(self.wait_window, text="退出", 
                            command=self.on_close,
                            font=('Arial', 10),
                            bg='#f44336', fg='white',
                            width=10)
        btn_exit.pack(pady=10)
        
        self.wait_window.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def new_game(self):
        """开始新游戏（重置全部）"""
        if messagebox.askyesno("新游戏", "确定要开始新游戏吗？\n当前棋局将被清空。"):
            if os.path.exists(self.state_file):
                os.remove(self.state_file)
            self.board_state = np.zeros((15, 15), dtype=int)
            self.move_count = 0
            self.last_move = None
            self.ai_call_count = 0
            if self.wait_window:
                self.wait_move_var.set("📊 步数: 0  |  AI调用: 0次")
                self.wait_status_var.set("🔄 已重置，等待对手下棋")
            self.log("🔄 已开始新游戏", 'success')
    
    def reset_and_restart(self):
        if messagebox.askyesno("重置", "确定要重置棋盘吗？\n（保留颜色和校准，只清空棋子）"):
            self.board_state = np.zeros((15, 15), dtype=int)
            self.move_count = 0
            self.last_move = None
            self.ai_call_count = 0
            if os.path.exists(self.state_file):
                os.remove(self.state_file)
            if self.wait_window:
                self.wait_move_var.set("📊 步数: 0  |  AI调用: 0次")
                self.wait_status_var.set("🔄 棋盘已重置，等待对手下棋")
            self.log("🔄 棋盘已重置", 'warning')
    
    def safe_ui_update(self, func, *args, **kwargs):
        self.update_queue.put((func, args, kwargs))
    
    def wait_for_window(self, window):
        while True:
            try:
                if not window.winfo_exists():
                    break
                window.update()
                if self.log_window and self.log_window.root:
                    self.log_window.root.update()
                self.process_ui_queue()
                time.sleep(0.05)
            except:
                break
    
    def process_ui_queue(self):
        try:
            while not self.update_queue.empty():
                func, args, kwargs = self.update_queue.get_nowait()
                func(*args, **kwargs)
        except:
            pass
    
    def encode_image(self, image_np):
        try:
            if isinstance(image_np, Image.Image):
                buffered = io.BytesIO()
                image_np.save(buffered, format="PNG")
                return base64.b64encode(buffered.getvalue()).decode('utf-8')
            img = Image.fromarray(image_np)
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            return base64.b64encode(buffered.getvalue()).decode('utf-8')
        except Exception as e:
            self.log(f"编码错误: {e}", 'error')
            return None
    
    # ============ 核心：算法主 + Gemma4兜底 ============
    
    def get_ai_move(self, image_np):
        """混合决策：算法主 + Gemma4兜底"""
        try:
            if np.count_nonzero(self.board_state == 0) == 0:
                return None, None, "棋盘已满"
            
            # 1. 算法算最佳位置
            algo_result = self.algorithm_best_move()
            
            if algo_result:
                row, col, score, move_type = algo_result
                self.log(f"📊 算法评分: ({row},{col}) = {score} ({move_type})", 'info')
                
                # 分数高（>=30）：直接用算法
                if score >= 30:
                    self.log(f"✅ 算法决策 [{move_type}] ({row},{col})", 'success')
                    return row, col, f"{move_type} (分数:{score})"
                
                # 分数中等（10-30）：让Gemma4验证
                if score >= 10:
                    self.log(f"🤔 算法拿不准 (分数:{score})，咨询Gemma4...", 'info')
                    ai_ok, ai_reason = self.gemma4_verify(row, col, image_np)
                    if ai_ok:
                        self.log(f"✅ Gemma4同意: {ai_reason}", 'success')
                        self.ai_call_count += 1
                        return row, col, f"Gemma4验证通过 (算法分数:{score})"
                    else:
                        # AI不认可也强制用算法（避免AI乱下）
                        self.log(f"⚠️ Gemma4不同意 ({ai_reason})，强制使用算法", 'warning')
                        return row, col, f"强制算法 (Gemma4拒绝)"
            
            # 2. 算法完全无解，让Gemma4做主
            self.log("🧠 算法无解，Gemma4决策中...", 'info')
            ai_result = self.gemma4_decide(image_np)
            
            if ai_result:
                row, col, reason = ai_result
                if row is not None and col is not None:
                    row = max(0, min(14, row))
                    col = max(0, min(14, col))
                    if self.board_state[row][col] == 0:
                        self.log(f"✅ Gemma4决策: ({row},{col}) {reason}", 'success')
                        self.ai_call_count += 1
                        return row, col, f"Gemma4: {reason}"
            
            # 3. 保底：算法硬找
            self.log("⚠️ 所有方法失败，算法保底", 'warning')
            return self.find_first_empty_with_reason()
            
        except Exception as e:
            self.log(f"决策错误: {e}", 'error')
            import traceback
            traceback.print_exc()
            return self.find_first_empty_with_reason()
    
    def algorithm_best_move(self):
        """五子棋算法：返回 (row, col, score, type)"""
        best_score = -999
        best_move = None
        best_type = "普通"
        
        my_color = self.my_color
        opp_color = 1 if my_color == 2 else 2
        
        for i in range(15):
            for j in range(15):
                if self.board_state[i][j] != 0:
                    continue
                
                if not self.is_near_piece(i, j, 3) and self.move_count > 5:
                    continue
                
                score = 0
                move_type = "普通"
                
                # 1. 进攻
                win_score = self.check_win_opportunity(i, j, my_color)
                if win_score >= 2:
                    score += win_score * 1000
                    move_type = "必赢"
                elif win_score >= 1:
                    score += win_score * 500
                    move_type = "进攻"
                
                # 2. 防守
                defend_score = self.check_win_opportunity(i, j, opp_color)
                if defend_score >= 2:
                    score += defend_score * 800
                    move_type = "必防"
                elif defend_score >= 1:
                    score += defend_score * 400
                    if move_type == "普通":
                        move_type = "防守"
                
                # 3. 四个方向评估
                directions = [(1,0), (0,1), (1,1), (1,-1)]
                for dr, dc in directions:
                    attack = self.evaluate_direction(i, j, dr, dc, my_color)
                    defend = self.evaluate_direction(i, j, dr, dc, opp_color)
                    
                    score += attack * 10
                    score += defend * 8
                    
                    if attack >= 3:
                        score += 30
                    if defend >= 3:
                        score += 25
                
                # 4. 中心加成
                center_dist = abs(i-7) + abs(j-7)
                score += (14 - center_dist) * 2
                
                # 5. 附近棋子加成
                near_pieces = self.count_near_pieces(i, j, 2)
                score += near_pieces * 3
                
                if score > best_score:
                    best_score = score
                    best_move = (i, j)
                    best_type = move_type
        
        if best_move:
            return (best_move[0], best_move[1], best_score, best_type)
        return None
    
    def check_win_opportunity(self, row, col, color):
        """检查下在这里能不能赢/防住"""
        max_count = 0
        directions = [(1,0), (0,1), (1,1), (1,-1)]
        
        for dr, dc in directions:
            count = 1
            open_ends = 0
            
            for step in range(1, 5):
                nr, nc = row + dr*step, col + dc*step
                if 0 <= nr < 15 and 0 <= nc < 15:
                    if self.board_state[nr][nc] == color:
                        count += 1
                    elif self.board_state[nr][nc] == 0:
                        open_ends += 1
                        break
                    else:
                        break
                else:
                    break
            
            for step in range(1, 5):
                nr, nc = row - dr*step, col - dc*step
                if 0 <= nr < 15 and 0 <= nc < 15:
                    if self.board_state[nr][nc] == color:
                        count += 1
                    elif self.board_state[nr][nc] == 0:
                        open_ends += 1
                        break
                    else:
                        break
                else:
                    break
            
            max_count = max(max_count, count)
            
            if count >= 4 and open_ends >= 1:
                return 2
            if count >= 3 and open_ends >= 2:
                return 1
        
        return 0
    
    def evaluate_direction(self, row, col, dr, dc, color):
        count = 0
        for step in range(1, 6):
            nr, nc = row + dr*step, col + dc*step
            if 0 <= nr < 15 and 0 <= nc < 15:
                if self.board_state[nr][nc] == color:
                    count += 1
                else:
                    break
            else:
                break
        
        for step in range(1, 6):
            nr, nc = row - dr*step, col - dc*step
            if 0 <= nr < 15 and 0 <= nc < 15:
                if self.board_state[nr][nc] == color:
                    count += 1
                else:
                    break
            else:
                break
        
        return count
    
    def is_near_piece(self, row, col, radius=2):
        for i in range(max(0, row-radius), min(15, row+radius+1)):
            for j in range(max(0, col-radius), min(15, col+radius+1)):
                if self.board_state[i][j] != 0:
                    return True
        return False
    
    def count_near_pieces(self, row, col, radius=2):
        count = 0
        for i in range(max(0, row-radius), min(15, row+radius+1)):
            for j in range(max(0, col-radius), min(15, col+radius+1)):
                if self.board_state[i][j] != 0:
                    count += 1
        return count
    
    def find_first_empty_with_reason(self):
        for i in range(15):
            for j in range(15):
                if self.board_state[i][j] == 0:
                    return i, j, "保底空位"
        return None, None, "棋盘已满"
    
    def gemma4_verify(self, row, col, image_np):
        """让Gemma4验证算法推荐的位置"""
        try:
            img_base64 = self.encode_image(image_np)
            if not img_base64:
                return True, "图片编码失败，信任算法"
            
            board_text = self.board_to_string()
            
            prompt = f"""你是五子棋专家。算法推荐在位置 ({row}, {col}) 落子。

当前棋盘：
{board_text}

你执 {'黑●' if self.my_color == 1 else '白○'}。

请判断这个位置是否合理（只看这个位置行不行，不要给新位置）：
- 检查是否在空位
- 检查是否有进攻或防守价值
- 检查是否会造成对方反杀

回复格式（只回复JSON）：
{{"valid": true/false, "reason": "简短理由"}}"""
            
            data = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": prompt, "images": [img_base64]}
                ],
                "stream": False,
                "temperature": 0.1
            }
            
            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result["message"]["content"]
                
                try:
                    json_match = re.search(r'\{[^{}]*\}', content)
                    if json_match:
                        data = json.loads(json_match.group())
                        valid = data.get("valid", True)
                        reason = data.get("reason", "")
                        return valid, reason
                except:
                    pass
            
            return True, "验证超时，信任算法"
            
        except Exception as e:
            self.log(f"Gemma4验证失败: {e}", 'warning')
            return True, f"异常: {e}"
    
    def gemma4_decide(self, image_np):
        """Gemma4做主决策（算法完全无解时）"""
        try:
            img_base64 = self.encode_image(image_np)
            if not img_base64:
                return None, None, "图片编码失败"
            
            board_text = self.board_to_string()
            
            prompt = f"""你是五子棋专家。算法无法决策，请你给出最佳落子位置。

当前棋盘（15x15，●=黑子，○=白子，·=空位）：
{board_text}

你执 {'黑●' if self.my_color == 1 else '白○'}。

请分析局势，给出最佳落子位置。
要求：
1. 只能下在空位（·的位置）
2. 优先进攻（形成四子、活三）和防守（堵对方四子）

输出JSON格式：
{{"row": 数字0-14, "col": 数字0-14, "reason": "理由"}}

只输出JSON，不要其他内容。"""
            
            data = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": prompt, "images": [img_base64]}
                ],
                "stream": False,
                "temperature": 0.3
            }
            
            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json=data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result["message"]["content"]
                
                try:
                    json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group())
                        row = data.get("row")
                        col = data.get("col")
                        reason = data.get("reason", "Gemma4决策")
                        return row, col, reason
                except:
                    pass
            
            return None, None, "Gemma4决策失败"
            
        except Exception as e:
            self.log(f"Gemma4决策失败: {e}", 'error')
            return None, None, f"异常: {e}"
    
    # ============ 检测棋盘 ============
    
    def detect_board_simple(self, image_np):
        try:
            if self.region is None:
                return False
            
            left, top, right, bottom = self.region
            width = right - left
            cell_size = width // 15
            
            detected_count = 0
            
            for i in range(15):
                for j in range(15):
                    x = j * cell_size + cell_size // 2
                    y = i * cell_size + cell_size // 2
                    
                    half = max(1, cell_size // 5)
                    roi_y = max(0, y - half)
                    roi_y_end = min(image_np.shape[0], y + half)
                    roi_x = max(0, x - half)
                    roi_x_end = min(image_np.shape[1], x + half)
                    
                    if roi_y >= roi_y_end or roi_x >= roi_x_end:
                        continue
                    
                    roi = image_np[roi_y:roi_y_end, roi_x:roi_x_end]
                    avg_color = np.mean(roi, axis=(0, 1))
                    avg_brightness = np.mean(avg_color)
                    
                    if avg_brightness < 80:
                        if self.board_state[i][j] != 1:
                            self.board_state[i][j] = 1
                            detected_count += 1
                    elif avg_brightness > 200:
                        if self.board_state[i][j] != 2:
                            self.board_state[i][j] = 2
                            detected_count += 1
                    elif avg_brightness > 100 and avg_brightness < 200:
                        if self.board_state[i][j] != 0:
                            self.board_state[i][j] = 0
                            detected_count += 1
            
            if detected_count > 0:
                self.log(f"🔍 检测到 {detected_count} 个棋子变化", 'info')
                self.move_count = np.count_nonzero(self.board_state)
                if self.wait_window and hasattr(self, 'wait_move_var'):
                    self.wait_move_var.set(f"📊 步数: {self.move_count}  |  AI调用: {self.ai_call_count}次")
                self.save_board_state()
            
            return True
        except Exception as e:
            self.log(f"检测错误: {e}", 'error')
            return False
    
    # ============ 落子 ============
    
    def click_position(self, row, col):
        try:
            if self.region is None:
                self.log("❌ 未校准棋盘！", 'error')
                return False
            
            if self.board_state[row][col] != 0:
                self.log(f"⚠️ 位置 ({row},{col}) 已有棋子！", 'warning')
                return False
            
            left, top, right, bottom = self.region
            width = right - left
            cell_size = width // 15
            
            x = left + col * cell_size + cell_size // 2
            y = top + row * cell_size + cell_size // 2
            
            self.log(f"🖱️ 双击落子: ({row}, {col}) -> ({x}, {y})", 'info')
            
            pyautogui.click(x, y)
            time.sleep(0.12)
            pyautogui.click(x, y)
            
            self.board_state[row][col] = self.my_color
            self.last_move = (row, col)
            self.move_count = np.count_nonzero(self.board_state)
            
            if self.wait_window and hasattr(self, 'wait_move_var'):
                self.wait_move_var.set(f"📊 步数: {self.move_count}  |  AI调用: {self.ai_call_count}次")
            
            self.log(f"✅ 第 {self.move_count} 步落子完成", 'success')
            if self.wait_window:
                self.wait_status_var.set(f"✅ 已落子 ({row}, {col}) - 等待对手下棋")
            
            self.save_board_state()
            return True
        except Exception as e:
            self.log(f"点击错误: {e}", 'error')
            return False
    
    def ai_move(self):
        if self.my_color is None:
            messagebox.showwarning("提示", "请先选择执子颜色！")
            return
        if self.region is None:
            messagebox.showwarning("提示", "请先校准棋盘！")
            return
        
        if self.wait_window:
            self.btn_wait_ai.config(state=tk.DISABLED)
            self.wait_status_var.set("⏳ AI 思考中...")
        
        def do_ai():
            try:
                screenshot = ImageGrab.grab(bbox=self.region)
                img_np = np.array(screenshot)
                
                self.log("🔍 正在检测棋盘...", 'info')
                self.detect_board_simple(img_np)
                
                row, col, reason = self.get_ai_move(img_np)
                if row is not None and col is not None:
                    self.click_position(row, col)
                else:
                    self.log(f"❌ 决策失败: {reason}", 'error')
                    if self.wait_window:
                        self.wait_status_var.set(f"❌ {reason}")
            except Exception as e:
                self.log(f"❌ 错误: {e}", 'error')
                if self.wait_window:
                    self.wait_status_var.set("❌ 发生错误")
            finally:
                if self.wait_window:
                    self.btn_wait_ai.config(state=tk.NORMAL)
                    self.wait_window.update()
        
        threading.Thread(target=do_ai, daemon=True).start()
    
    def check_ollama(self):
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json()
                model_names = [m['name'] for m in models.get('models', [])]
                if self.model in model_names:
                    self.log(f"✅ Ollama 运行正常，模型 {self.model} 已加载", 'success')
                    return True
                else:
                    self.log(f"⚠️ 未找到模型 {self.model}", 'warning')
                    self.log(f"可用模型: {model_names}", 'info')
                    self.log(f"💡 运行: ollama pull {self.model}", 'info')
                    return False
            return False
        except:
            self.log("❌ 无法连接 Ollama，Gemma4兜底模式不可用", 'error')
            self.log("💡 将使用纯算法模式", 'warning')
            return False
    
    def on_close(self):
        self.running = False
        self.save_board_state()
        if hasattr(self, 'border_window') and self.border_window:
            try:
                self.border_window.destroy()
                self.border_window = None
            except:
                pass
        if self.log_window:
            self.log_window.on_close()
        if self.control_window:
            try:
                self.control_window.destroy()
            except:
                pass
        if self.wait_window:
            try:
                self.wait_window.destroy()
            except:
                pass
        sys.exit(0)
    
    def run(self):
        try:
            print("=" * 55)
            print("🎯 五子棋 AI 视觉助手 (算法主 + Gemma4兜底)")
            print("=" * 55)
            
            print("📋 启动日志窗口...")
            self.init_log_window()
            self.log("🚀 程序启动", 'info')
            self.log("📌 模式: 算法决策 95% + Gemma4兜底 5%", 'info')
            
            # 检查存档，询问是否继续
            if os.path.exists(self.state_file):
                try:
                    with open(self.state_file, 'r') as f:
                        old_data = json.load(f)
                        old_count = old_data.get('move_count', 0)
                except:
                    old_count = 0
                
                if messagebox.askyesno(
                    "🔄 加载存档？",
                    f"📂 发现未完成棋局 (步数: {old_count})\n\n是否继续？\n点击「是」继续，点击「否」开始新局"
                ):
                    self.log("📂 继续上一局", 'info')
                else:
                    if os.path.exists(self.state_file):
                        os.remove(self.state_file)
                    self.log("🗑️ 已删除旧存档，全新开局", 'info')
                    self.board_state = np.zeros((15, 15), dtype=int)
                    self.move_count = 0
                    self.ai_call_count = 0
            
            self.log("🔒 检查管理员权限...", 'info')
            if not self.check_admin():
                self.log("❌ 需要管理员权限！", 'error')
                try:
                    if os.name == 'nt':
                        import ctypes
                        ctypes.windll.shell32.ShellExecuteW(
                            None, "runas", sys.executable, " ".join(sys.argv), None, 1
                        )
                        sys.exit(0)
                except:
                    self.log("请右键以管理员身份运行", 'error')
                    input("按 Enter 退出...")
                    return
            self.log("✅ 已获取管理员权限", 'success')
            
            self.log("🔌 检查 Ollama 服务...", 'info')
            self.log("💡 Gemma4兜底模式需要 Ollama", 'info')
            if not self.check_ollama():
                self.log("⚠️ Gemma4 未就绪，将使用纯算法模式", 'warning')
            
            self.log("📌 启动选择窗口...", 'info')
            self.create_start_window()
            self.log("✅ 程序启动完成", 'success')
            
            self.control_window.mainloop()
            
        except KeyboardInterrupt:
            self.log("👋 已停止运行", 'warning')
        except Exception as e:
            self.log(f"❌ 运行错误: {e}", 'error')
            import traceback
            traceback.print_exc()
            input("按 Enter 退出...")

def create_bat_file():
    try:
        bat_content = f'''@echo off
title 五子棋 AI 助手
echo 正在以管理员权限启动...
echo.
python "{sys.argv[0]}"
pause
'''
        bat_path = os.path.join(os.path.dirname(sys.argv[0]), "启动五子棋AI.bat")
        with open(bat_path, 'w', encoding='gbk') as f:
            f.write(bat_content)
        print(f"✅ 已创建快捷启动: {bat_path}")
    except:
        pass

if __name__ == "__main__":
    try:
        import pynput
    except:
        print("❌ 正在安装 pynput...")
        os.system(f"{sys.executable} -m pip install pynput")
        print("请重新运行程序")
        input("按 Enter 退出...")
        sys.exit(0)
    
    if not os.path.exists("启动五子棋AI.bat"):
        create_bat_file()
    
    ai = GobanVisionAI()
    ai.run()
