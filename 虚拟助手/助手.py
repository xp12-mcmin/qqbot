import tkinter as tk
from tkinter import scrolledtext, Menu
import requests
import threading
import random
import os
from PIL import Image, ImageTk
import glob

class DesktopAssistant:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("桌面助手")
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)
        self.window.attributes('-transparentcolor', '#abcdef')
        self.window.configure(bg='#abcdef')
        
        # Ollama配置
        self.ollama_url = "http://localhost:11434/api/generate"
        self.model = "gemma4:31b-cloud"
        
        # 图片配置
        self.image_path = "assistant_images"
        self.states = ['idle', 'happy', 'thinking', 'sleeping']
        self.current_state = 'idle'
        self.current_images = []
        self.animation_index = 0
        self.animation_delay = 200
        
        # 角色状态
        self.energy = 100
        self.chat_window = None
        
        # 加载图片
        self.load_images()
        
        # 界面
        self.pet_frame = tk.Frame(self.window, bg='#abcdef', cursor='hand2')
        self.pet_frame.pack()
        
        self.pet_label = tk.Label(self.pet_frame, bg='#abcdef', borderwidth=0, highlightthickness=0)
        self.pet_label.pack()
        
        self.status_label = tk.Label(
            self.pet_frame, text="✨ 来聊聊天吧",
            font=("Microsoft YaHei", 10), bg='#abcdef', fg='#666'
        )
        self.status_label.pack(pady=(5, 0))
        
        # 右键菜单
        self.menu = Menu(self.window, tearoff=0)
        self.menu.add_command(label="💬 打开聊天", command=self.open_chat)
        self.menu.add_command(label="🎨 换皮肤", command=self.change_skin)
        self.menu.add_separator()
        self.menu.add_command(label="❌ 退出", command=self.on_closing)
        
        # 绑定事件
        self.pet_frame.bind("<Button-1>", self.start_move)
        self.pet_frame.bind("<B1-Motion>", self.on_move)
        self.pet_frame.bind("<Button-3>", self.show_menu)
        self.pet_label.bind("<Button-1>", self.start_move)
        self.pet_label.bind("<B1-Motion>", self.on_move)
        self.pet_label.bind("<Button-3>", self.show_menu)
        
        # 窗口位置（右下角）
        self.window.update_idletasks()
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        self.window.geometry(f"150x180+{screen_width-200}+{screen_height-230}")
        
        self.drag_start_x = 0
        self.drag_start_y = 0
        
        # 启动动画和状态机
        self.update_image()
        self.state_timer = threading.Timer(3.0, self.update_state)
        self.state_timer.daemon = True
        self.state_timer.start()
    
    def load_images(self):
        """加载图片"""
        if not os.path.exists(self.image_path):
            os.makedirs(self.image_path)
            self.create_readme()
            return
        
        for state in self.states:
            state_folder = os.path.join(self.image_path, state)
            if os.path.exists(state_folder):
                images = []
                for img_file in glob.glob(os.path.join(state_folder, "*.png")) + \
                             glob.glob(os.path.join(state_folder, "*.jpg")):
                    try:
                        img = Image.open(img_file)
                        img = self.crop_and_resize(img)
                        images.append(ImageTk.PhotoImage(img))
                    except:
                        pass
                
                if images:
                    setattr(self, f"{state}_images", images)
                else:
                    setattr(self, f"{state}_images", [])
            else:
                os.makedirs(state_folder, exist_ok=True)
                setattr(self, f"{state}_images", [])
        
        self.current_images = getattr(self, "idle_images", [])
    
    def crop_and_resize(self, img):
        """裁剪白边并调整到1:1"""
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # 获取非透明区域边界
        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)
        
        # 调整为正方形
        size = max(img.size)
        new_img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        new_img.paste(img, ((size - img.width) // 2, (size - img.height) // 2))
        
        # 缩放到120x120
        new_img = new_img.resize((120, 120), Image.Resampling.LANCZOS)
        return new_img
    
    def create_readme(self):
        """创建说明文件"""
        readme = """请在 assistant_images 文件夹中创建以下子文件夹：
- idle/      空闲状态图片
- happy/     开心状态图片  
- thinking/  思考状态图片
- sleeping/  睡觉状态图片

支持的图片格式：PNG、JPG
推荐尺寸：正方形图片
        """
        with open(os.path.join(self.image_path, "README.txt"), 'w', encoding='utf-8') as f:
            f.write(readme)
    
    def set_state(self, new_state):
        """切换状态"""
        if new_state != self.current_state:
            self.current_state = new_state
            self.current_images = getattr(self, f"{new_state}_images", [])
            self.animation_index = 0
    
    def update_image(self):
        """更新动画"""
        if self.current_images:
            img = self.current_images[self.animation_index % len(self.current_images)]
            self.pet_label.config(image=img)
            self.animation_index += 1
        else:
            # 没有图片时显示emoji
            emojis = {'idle': '😊', 'happy': '😄', 'thinking': '🤔', 'sleeping': '😴'}
            self.pet_label.config(text=emojis.get(self.current_state, '😊'), font=("Segoe UI Emoji", 60))
        
        self.window.after(self.animation_delay, self.update_image)
    
    def update_state(self):
        """状态机"""
        if self.current_state == 'sleeping':
            self.energy = min(100, self.energy + 8)
        else:
            self.energy = max(0, self.energy - 1)
        
        if self.energy <= 20 and self.current_state != 'sleeping':
            self.set_state('sleeping')
            self.status_label.config(text="😴 有点困...")
        elif self.energy >= 80 and self.current_state == 'sleeping':
            self.set_state('idle')
            self.status_label.config(text="✨ 睡醒啦！")
        
        self.state_timer = threading.Timer(2.0, self.update_state)
        self.state_timer.daemon = True
        self.state_timer.start()
    
    def show_menu(self, event):
        self.menu.post(event.x_root, event.y_root)
    
    def change_skin(self):
        new_state = random.choice(self.states)
        self.set_state(new_state)
        self.status_label.config(text=f"🎨 切换到{new_state}模式")
        self.window.after(2000, lambda: self.status_label.config(text="✨ 来聊聊天吧"))
        self.window.after(3000, lambda: self.set_state('idle') if self.energy > 20 else None)
    
    def open_chat(self):
        if self.chat_window and self.chat_window.winfo_exists():
            self.chat_window.lift()
            return
        
        self.set_state('thinking')
        self.status_label.config(text="🤔 准备聊天...")
        
        self.chat_window = tk.Toplevel(self.window)
        self.chat_window.title("桌面助手")
        self.chat_window.geometry("450x550")
        self.chat_window.configure(bg='#f5f5f5')
        
        # 聊天区域
        self.chat_area = scrolledtext.ScrolledText(
            self.chat_window, wrap=tk.WORD, height=20,
            font=("Microsoft YaHei", 10), bg='white'
        )
        self.chat_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        self.chat_area.tag_config("user", foreground="#4a90e2", font=("Microsoft YaHei", 10, "bold"))
        self.chat_area.tag_config("assistant", foreground="#2c3e50")
        
        # 输入框
        input_frame = tk.Frame(self.chat_window, bg='#f5f5f5')
        input_frame.pack(padx=10, pady=(0, 10), fill=tk.X)
        
        self.chat_input = tk.Entry(input_frame, font=("Microsoft YaHei", 10), bg='white')
        self.chat_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.chat_input.bind("<Return>", self.send_chat)
        
        send_btn = tk.Button(input_frame, text="发送", command=self.send_chat,
                            bg='#4a90e2', fg='white', cursor='hand2', padx=15)
        send_btn.pack(side=tk.RIGHT)
        
        self.chat_window.protocol("WM_DELETE_WINDOW", self.on_chat_close)
        
        self.chat_area.insert(tk.END, "助手: ", "assistant")
        self.chat_area.insert(tk.END, "你好！我是你的桌面小助手～\n有什么可以帮你的吗？\n\n")
        
        self.window.after(500, lambda: self.set_state('happy'))
        self.window.after(500, lambda: self.status_label.config(text="💬 聊得很开心"))
    
    def on_chat_close(self):
        self.chat_window.destroy()
        self.chat_window = None
        self.set_state('idle')
        self.status_label.config(text="✨ 来聊聊天吧")
    
    def send_chat(self, event=None):
        user_msg = self.chat_input.get().strip()
        if not user_msg:
            return
        
        self.chat_area.insert(tk.END, f"\n你: ", "user")
        self.chat_area.insert(tk.END, f"{user_msg}\n")
        self.chat_input.delete(0, tk.END)
        self.chat_area.see(tk.END)
        
        self.set_state('thinking')
        self.status_label.config(text="🤔 思考中...")
        
        threading.Thread(target=self.call_ollama, args=(user_msg,), daemon=True).start()
    
    def call_ollama(self, user_msg):
        try:
            response = requests.post(
                self.ollama_url,
                json={"model": self.model, "prompt": user_msg, "stream": False,
                      "options": {"temperature": 0.7, "max_tokens": 2048}},
                timeout=60
            )
            reply = response.json().get("response", "无回复") if response.status_code == 200 else f"API错误: {response.status_code}"
        except Exception as e:
            reply = f"连接失败: {str(e)}"
        
        self.chat_window.after(0, self.show_reply, reply)
    
    def show_reply(self, reply):
        self.chat_area.insert(tk.END, f"\n助手: ", "assistant")
        self.chat_area.insert(tk.END, f"{reply}\n")
        self.chat_area.insert(tk.END, "-" * 40 + "\n")
        self.chat_area.see(tk.END)
        self.set_state('happy')
        self.status_label.config(text="✨ 来聊聊天吧")
    
    def start_move(self, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y
    
    def on_move(self, event):
        x = self.window.winfo_x() + event.x - self.drag_start_x
        y = self.window.winfo_y() + event.y - self.drag_start_y
        self.window.geometry(f"+{x}+{y}")
    
    def on_closing(self):
        if self.state_timer:
            self.state_timer.cancel()
        self.window.destroy()
    
    def run(self):
        self.window.mainloop()

if __name__ == "__main__":
    app = DesktopAssistant()
    app.run()
