# ==================== 新版GUI发送器 ====================
import tkinter as tk
from tkinter import ttk, messagebox
import json
import time
import os
import threading
from datetime import datetime

class QQMessageSenderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("QQ消息发送器 - 防撤回专用")
        self.root.geometry("500x400")
        
        # 设置图标（如果有）
        try:
            self.root.iconbitmap("icon.ico")
        except:
            pass
        
        # 不再需要队列目录
        # self.queue_dir = "data/queue"  # 删除这行
        # os.makedirs(self.queue_dir, exist_ok=True)  # 删除这行
        
        self.setup_ui()
        
    def setup_ui(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 群组选择
        ttk.Label(main_frame, text="目标群组:").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        self.group_var = tk.StringVar()
        self.group_combo = ttk.Combobox(main_frame, textvariable=self.group_var, width=40)
        self.group_combo.grid(row=0, column=1, columnspan=2, pady=5, sticky=(tk.W, tk.E))
        self.group_combo['values'] = [
            "1009018182", "894506131", "597105096", "259099997", 
            "2169057338", "1031919133", "1042681049", "197272874",
            "157509373", "435624010", "1006371944", "743645787",
            "1049056800", "924947078", "340841402", "437531257", "779699980", "1080663142"
        ]
        self.group_combo.set("1009018182")
        
        # 消息内容
        ttk.Label(main_frame, text="消息内容:").grid(row=1, column=0, sticky=tk.NW, pady=5)
        
        self.message_text = tk.Text(main_frame, width=40, height=8, wrap=tk.WORD)
        self.message_text.grid(row=1, column=1, columnspan=2, pady=5, sticky=(tk.W, tk.E))
        self.message_text.insert("1.0", "测试消息")
        
        # 发送选项（简化版）
        ttk.Label(main_frame, text="发送方式:").grid(row=2, column=0, sticky=tk.W, pady=5)
        
        self.send_type = tk.StringVar(value="direct")
        ttk.Radiobutton(main_frame, text="直接发送（自动缓存）", 
                       variable=self.send_type, value="direct").grid(row=2, column=1, sticky=tk.W, columnspan=2)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=3, pady=15)
        
        ttk.Button(button_frame, text="发送消息", command=self.send_message).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="清空内容", command=self.clear_message).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="查看状态", command=self.check_status).pack(side=tk.LEFT, padx=5)
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.columnconfigure(2, weight=1)
        
    def send_message(self):
        group_id = self.group_var.get().strip()
        message = self.message_text.get("1.0", tk.END).strip()
        
        if not group_id:
            messagebox.showerror("错误", "请选择目标群组")
            return
        
        if not message:
            messagebox.showerror("错误", "消息内容不能为空")
            return
        
        # 直接通过WebSocket发送，新的防撤回系统会自动缓存
        threading.Thread(target=self.send_via_websocket, args=(group_id, message), daemon=True).start()
        self.status_var.set(f"正在发送到群{group_id}...")
    
    def send_via_websocket(self, group_id, message):
        """通过WebSocket发送消息，并确保被防撤回系统缓存"""
        try:
            import websockets
            import asyncio
            
            async def send():
                uri = "ws://127.0.0.1:8765"
                try:
                    async with websockets.connect(uri) as websocket:
                        # ========== 关键步骤1：先发送一个特殊命令，让主程序记录缓存 ==========
                        print(f"[GUI调试] 步骤1：尝试让主程序记录缓存")
                        
                        # 发送一个"假的"撤回事件给主程序，让它记录消息
                        fake_recall_prep = {
                            "action": "fake_cache_request",
                            "params": {
                                "group_id": int(group_id),
                                "message": message,
                                "cache_only": True  # 只缓存，不发消息
                            }
                        }
                        
                        try:
                            await websocket.send(json.dumps(fake_recall_prep))
                            print(f"[GUI调试] 已发送缓存请求")
                        except:
                            print(f"[GUI调试] 缓存请求失败，继续发送消息")
                        
                        # 等待一下
                        await asyncio.sleep(0.5)
                        
                        # ========== 关键步骤2：发送真实消息 ==========
                        print(f"[GUI调试] 步骤2：发送真实消息")
                        
                        # 发送真实消息
                        real_message_data = {
                            "action": "send_msg",
                            "params": {
                                "message_type": "group",
                                "group_id": int(group_id),
                                "message": message
                            }
                        }
                        
                        await websocket.send(json.dumps(real_message_data))
                        print(f"[GUI调试] 真实消息已发送")
                        
                        # ========== 关键步骤3：发送后再次确保缓存 ==========
                        print(f"[GUI调试] 步骤3：发送缓存确认命令")
                        
                        # 发送一个强制缓存命令
                        force_cache_cmd = {
                            "action": "send_msg",
                            "params": {
                                "message_type": "group",
                                "group_id": int(group_id),

                            }
                        }
                        
                        await websocket.send(json.dumps(force_cache_cmd))
                        print(f"[GUI调试] 缓存确认命令已发送")
                        
                        # 等待缓存完成
                        await asyncio.sleep(1)
                        
                        # ========== 关键步骤4：查询缓存状态 ==========
                        print(f"[GUI调试] 步骤4：查询防撤回状态")
                        
                        status_cmd = {
                            "action": "send_msg",
                            "params": {
                                "message_type": "group",
                                "group_id": int(group_id),

                            }
                        }
                        
                        await websocket.send(json.dumps(status_cmd))
                        
                        self.root.after(0, lambda: self.status_var.set(f"消息已发送到群{group_id}"))
                        self.root.after(0, lambda: messagebox.showinfo("成功", 
                            f"GUI消息发送完成！\n"
                            f"群：{group_id}\n"
                            f"请让别人撤回这条消息测试防撤回\n"
                            f"然后查看防撤回状态确认缓存"))
                            
                except ConnectionRefusedError:
                    self.root.after(0, lambda: self.status_var.set("连接失败：机器人未运行"))
                    self.root.after(0, lambda: messagebox.showerror("错误", 
                        "无法连接到机器人！\n"
                        "请确保主程序正在运行"))
                except Exception as e:
                    self.root.after(0, lambda: self.status_var.set(f"发送失败: {e}"))
                    self.root.after(0, lambda: messagebox.showerror("错误", f"发送失败: {e}"))
            
            asyncio.run(send())
            
        except Exception as e:
            self.root.after(0, lambda: self.status_var.set(f"发送失败: {e}"))
            self.root.after(0, lambda: messagebox.showerror("错误", f"发送失败: {e}"))    
    def clear_message(self):
        self.message_text.delete("1.0", tk.END)
        self.status_var.set("内容已清空")
    
    def check_status(self):
        """查看防撤回系统状态"""
        try:
            import websockets
            import asyncio
            
            async def check():
                uri = "ws://127.0.0.1:8765"
                try:
                    async with websockets.connect(uri) as websocket:
                        # 发送状态查询命令
                        group_id = self.group_var.get().strip()
                        await websocket.send(json.dumps({
                            "action": "send_msg",
                            "params": {
                                "message_type": "group",
                                "group_id": int(group_id),

                            }
                        }))
                        
                        self.root.after(0, lambda: self.status_var.set(f"已发送状态查询到群{group_id}"))
                        
                except ConnectionRefusedError:
                    self.root.after(0, lambda: self.status_var.set("机器人未运行"))
                    self.root.after(0, lambda: messagebox.showerror("错误", "机器人未运行"))
                except Exception as e:
                    self.root.after(0, lambda: self.status_var.set(f"查询失败: {e}"))
            
            asyncio.run(check())
            
        except Exception as e:
            messagebox.showerror("错误", f"状态查询失败: {e}")

def main():
    root = tk.Tk()
    app = QQMessageSenderGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
