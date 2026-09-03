import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os
import time
import threading
from datetime import datetime
from admin_manager import AdminManager
class AdminConsoleGUI:
    """独立的图形化管理控制台"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.setup_data()
        self.setup_gui()
        self.load_data()
        # 创建AdminManager实例
        self.admin_manager = AdminManager()  # 添加这行
    def force_refresh_ui(self):
        """强制刷新所有UI"""
        try:
            # 重新加载所有数据
            self.load_data()
            
            # 刷新所有Treeview
            self.load_requests()
            self.load_admins()
            self.load_blacklist()
            
            # 更新状态栏
            self.update_status()
            
            self.log("🔄 UI已强制刷新")
            
        except Exception as e:
            self.log(f"❌ 刷新UI失败: {e}")
            import traceback
            traceback.print_exc()
    def setup_data(self):
        """设置数据文件路径"""
        self.data_dir = "data"
        self.blacklist_file = os.path.join(self.data_dir, "blacklist.json")
        self.admins_file = os.path.join(self.data_dir, "admins.json")
        self.requests_file = os.path.join(self.data_dir, "admin_requests.json")
        
        # 确保目录存在
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 初始化数据
        self.blacklist = set()
        self.admins = set()
        self.requests = {}
        
    def setup_gui(self):
        """设置GUI界面"""
        self.root.title("🤖 QQ机器人管理控制台")
        self.root.geometry("1000x700")
        
        # 设置窗口图标（如果有的话）
        try:
            self.root.iconbitmap('icon.ico')
        except:
            pass
        
        # 创建主框架
        self.create_main_frame()
        
        # 创建菜单栏
        self.create_menu()
        
        # 设置自动刷新
        self.auto_refresh()
        
    def create_main_frame(self):
        """创建主界面"""
        # 顶部状态栏
        self.status_frame = ttk.Frame(self.root)
        self.status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.status_label = ttk.Label(self.status_frame, text="正在加载...")
        self.status_label.pack(side=tk.LEFT)
        
        self.refresh_btn = ttk.Button(self.status_frame, text="🔄 刷新", 
                                     command=self.load_data, width=10)
        self.refresh_btn.pack(side=tk.RIGHT)
        
        # 创建笔记本（标签页）
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 申请管理标签页
        self.create_requests_tab()
        
        # 管理员管理标签页
        self.create_admins_tab()
        
        # 黑名单管理标签页
        self.create_blacklist_tab()
        
        # 系统日志标签页
        self.create_logs_tab()
        
    def create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="导出数据", command=self.export_data)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        
        # 工具菜单
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="工具", menu=tools_menu)
        tools_menu.add_command(label="批量导入", command=self.batch_import)
        tools_menu.add_command(label="备份数据", command=self.backup_data)
        
        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="使用说明", command=self.show_help)
        help_menu.add_command(label="关于", command=self.show_about)
    # admin_console_gui.py - 第2部分
    def create_requests_tab(self):
        """创建申请管理标签页"""
        self.requests_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.requests_frame, text="📨 申请管理")
        
        # 控制面板
        control_frame = ttk.LabelFrame(self.requests_frame, text="操作")
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(control_frame, text="✅ 批准选中", 
                  command=self.approve_selected, width=15).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(control_frame, text="❌ 拒绝选中", 
                  command=self.reject_selected, width=15).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(control_frame, text="📋 刷新列表", 
                  command=self.load_requests, width=15).pack(side=tk.LEFT, padx=5, pady=5)
        
        # 申请列表
        list_frame = ttk.LabelFrame(self.requests_frame, text="待处理申请")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 创建Treeview
        columns = ("序号", "QQ号", "申请理由", "申请时间")
        self.requests_tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        
        for col in columns:
            self.requests_tree.heading(col, text=col)
            self.requests_tree.column(col, width=100)
        
        self.requests_tree.column("申请理由", width=200)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.requests_tree.yview)
        self.requests_tree.configure(yscrollcommand=scrollbar.set)
        
        self.requests_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_admins_tab(self):
        """创建管理员管理标签页"""
        self.admins_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.admins_frame, text="👥 管理员")
        
        # 控制面板
        control_frame = ttk.LabelFrame(self.admins_frame, text="操作")
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(control_frame, text="➕ 添加管理员", 
                  command=self.add_admin, width=15).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(control_frame, text="➖ 移除选中", 
                  command=self.remove_selected_admin, width=15).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(control_frame, text="📋 刷新列表", 
                  command=self.load_admins, width=15).pack(side=tk.LEFT, padx=5, pady=5)
        
        # 管理员列表
        list_frame = ttk.LabelFrame(self.admins_frame, text="管理员列表")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        columns = ("QQ号", "状态", "申请时间", "处理时间")
        self.admins_tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        
        for col in columns:
            self.admins_tree.heading(col, text=col)
            self.admins_tree.column(col, width=120)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.admins_tree.yview)
        self.admins_tree.configure(yscrollcommand=scrollbar.set)
        
        self.admins_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    # admin_console_gui.py - 第3部分
    def create_blacklist_tab(self):
        """创建黑名单管理标签页"""
        self.blacklist_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.blacklist_frame, text="🚫 黑名单")
        
        # 控制面板
        control_frame = ttk.LabelFrame(self.blacklist_frame, text="操作")
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(control_frame, text="➕ 添加用户", 
                  command=self.add_to_blacklist, width=15).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(control_frame, text="➖ 移除选中", 
                  command=self.remove_from_blacklist, width=15).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(control_frame, text="📋 刷新列表", 
                  command=self.load_blacklist, width=15).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(control_frame, text="🔍 搜索用户", 
                  command=self.search_blacklist, width=15).pack(side=tk.LEFT, padx=5, pady=5)
        
        # 搜索框
        search_frame = ttk.Frame(control_frame)
        search_frame.pack(side=tk.RIGHT, padx=5)
        
        ttk.Label(search_frame, text="搜索:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=20)
        self.search_entry.pack(side=tk.LEFT, padx=5)
        self.search_entry.bind('<Return>', lambda e: self.search_blacklist())
        
        # 黑名单列表
        list_frame = ttk.LabelFrame(self.blacklist_frame, text="黑名单用户")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        columns = ("QQ号", "添加时间", "封禁原因")
        self.blacklist_tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        
        for col in columns:
            self.blacklist_tree.heading(col, text=col)
            self.blacklist_tree.column(col, width=150)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.blacklist_tree.yview)
        self.blacklist_tree.configure(yscrollcommand=scrollbar.set)
        
        self.blacklist_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_logs_tab(self):
        """创建系统日志标签页"""
        self.logs_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.logs_frame, text="📋 系统日志")
        
        # 日志文本框
        self.log_text = tk.Text(self.logs_frame, wrap=tk.WORD, font=("Consolas", 10))
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 控制按钮
        btn_frame = ttk.Frame(self.logs_frame)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(btn_frame, text="清空日志", 
                  command=self.clear_logs).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="保存日志", 
                  command=self.save_logs).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="复制日志", 
                  command=self.copy_logs).pack(side=tk.LEFT, padx=5)
    # admin_console_gui.py - 第4部分
    # ========== 数据操作 ==========
    
    def load_data(self):
        """加载所有数据"""
        try:
            # 加载黑名单
            self.load_blacklist_data()
            
            # 加载管理员
            self.load_admins_data()
            
            # 加载申请
            self.load_requests_data()
            
            # 更新UI
            self.load_blacklist()
            self.load_admins()
            self.load_requests()
            
            # 更新状态
            self.update_status()
            self.log("✅ 数据加载完成")
            
        except Exception as e:
            self.log(f"❌ 数据加载失败: {e}")
    
    def load_blacklist_data(self):
        """加载黑名单数据"""
        if os.path.exists(self.blacklist_file):
            with open(self.blacklist_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.blacklist = set(data.get("users", []))
        else:
            self.blacklist = set()
            self.save_blacklist()
    
    def load_admins_data(self):
        """加载管理员数据"""
        if os.path.exists(self.admins_file):
            with open(self.admins_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.admins = set(data.get("admins", []))
        else:
            self.admins = set()
            self.save_admins()
    
    def load_requests_data(self):
        """加载申请数据"""
        if os.path.exists(self.requests_file):
            with open(self.requests_file, 'r', encoding='utf-8') as f:
                self.requests = json.load(f)
        else:
            self.requests = {}
            self.save_requests()
    
    def save_blacklist(self):
        """保存黑名单"""
        with open(self.blacklist_file, 'w', encoding='utf-8') as f:
            json.dump({"users": list(self.blacklist)}, f, ensure_ascii=False, indent=2)
    
    def save_admins(self):
        """保存管理员"""
        with open(self.admins_file, 'w', encoding='utf-8') as f:
            json.dump({"admins": list(self.admins)}, f, ensure_ascii=False, indent=2)
    
    def save_requests(self):
        """保存申请"""
        with open(self.requests_file, 'w', encoding='utf-8') as f:
            json.dump(self.requests, f, ensure_ascii=False, indent=2)
    # admin_console_gui.py - 第5部分
    # ========== UI更新 ==========
    
    def update_status(self):
        """更新状态栏"""
        status_text = f"🚫 黑名单: {len(self.blacklist)} | 👥 管理员: {len(self.admins)} | 📨 待处理申请: {len([r for r in self.requests.values() if r.get('status') == 'pending'])}"
        self.status_label.config(text=status_text)
    
    def load_requests(self):
        """加载申请列表到UI"""
        # 清空现有数据
        for item in self.requests_tree.get_children():
            self.requests_tree.delete(item)
        
        # 添加数据
        pending_requests = [r for r in self.requests.values() if r.get('status') == 'pending']
        for i, request in enumerate(pending_requests, 1):
            self.requests_tree.insert("", tk.END, values=(
                i,
                request.get('user_id', ''),
                request.get('reason', '无'),
                request.get('apply_time', '')
            ))
    
    def load_admins(self):
        """加载管理员列表到UI"""
        # 清空现有数据
        for item in self.admins_tree.get_children():
            self.admins_tree.delete(item)
        
        # 添加数据
        for admin in self.admins:
            request = self.requests.get(admin, {})
            status = request.get('status', 'unknown')
            status_text = {
                'pending': '⏳ 待处理',
                'approved': '✅ 已批准',
                'rejected': '❌ 已拒绝'
            }.get(status, '❓ 未知')
            
            self.admins_tree.insert("", tk.END, values=(
                admin,
                status_text,
                request.get('apply_time', '未知'),
                request.get('process_time', '')
            ))
    
    def load_blacklist(self):
        """加载黑名单列表到UI"""
        # 清空现有数据
        for item in self.blacklist_tree.get_children():
            self.blacklist_tree.delete(item)
        
        # 简单显示QQ号（实际中可以存储更多信息）
        for i, user in enumerate(self.blacklist, 1):
            self.blacklist_tree.insert("", tk.END, values=(
                user,
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                "控制台添加"
            ))
    # admin_console_gui.py - 第6部分
    # ========== 操作功能 ==========
    
    def approve_selected(self):
        """批准选中的申请 - 完整修复版"""
        selection = self.requests_tree.selection()
        if not selection:
            messagebox.showwarning("提示", "请先选择一个申请")
            return
        
        print(f"[DEBUG] 开始批准 {len(selection)} 个申请")
        
        for item in selection:
            values = self.requests_tree.item(item)['values']
            qq = values[1]  # QQ号在第二列
            
            if qq:
                print(f"\n[DEBUG] === 处理QQ: {qq} ===")
                
                # 1. 检查当前状态
                is_admin = self.admin_manager.is_admin(qq)
                print(f"[DEBUG] 批准前 - 是否为管理员: {is_admin}")
                print(f"[DEBUG] 批准前 - 申请状态: {self.requests.get(qq, {}).get('status', '无记录')}")
                
                # 2. 如果已经是管理员，只更新状态
                if is_admin:
                    print(f"[DEBUG] 用户已经是管理员，只需更新申请状态")
                    
                    # 更新申请状态为已批准
                    if qq in self.requests:
                        self.requests[qq]["status"] = "approved"
                        self.requests[qq]["process_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
                        self.requests[qq]["processed_by"] = "console_gui"
                        self.save_requests()  # 保存更新
                        print(f"[DEBUG] 已更新申请状态为 'approved'")
                    
                    # 从Treeview中删除
                    self.requests_tree.delete(item)
                    continue
                
                # 3. 使用AdminManager批准
                print(f"[DEBUG] 调用 admin_manager.approve_request()")
                success, message = self.admin_manager.approve_request(qq, "console_gui")
                print(f"[DEBUG] 批准结果: {success}, {message}")
                
                # 4. 强制重新加载数据
                if success:
                    print(f"[DEBUG] 强制重新加载数据...")
                    
                    # 重新加载AdminManager的数据
                    self.admin_manager.admins = self.admin_manager._load_admins()
                    self.admin_manager.requests = self.admin_manager._load_requests()
                    
                    # 同步控制台的数据
                    self.admins = self.admin_manager.admins.copy()
                    self.requests = self.admin_manager.requests.copy()
                    
                    print(f"[DEBUG] 同步后 - 是否为管理员: {self.admin_manager.is_admin(qq)}")
                    print(f"[DEBUG] 同步后 - 申请状态: {self.requests.get(qq, {}).get('status', '无记录')}")
                    
                    # 从Treeview中删除
                    self.requests_tree.delete(item)
                    
                    self.log(f"? {message}")
                else:
                    self.log(f"? {message}")
        
        # 5. 刷新所有UI
        print(f"[DEBUG] 刷新UI...")
        self.load_requests()  # 重新加载申请列表
        self.load_admins()    # 重新加载管理员列表
        self.update_status()  # 更新状态栏
        print(f"[DEBUG] UI刷新完成")
    def reject_selected(self):
        """拒绝选中的申请"""
        selection = self.requests_tree.selection()
        if not selection:
            messagebox.showwarning("提示", "请先选择一个申请")
            return
        
        reason = simpledialog.askstring("拒绝原因", "请输入拒绝原因:")
        if reason is None:  # 用户取消了
            return
        
        for item in selection:
            values = self.requests_tree.item(item)['values']
            qq = values[1]  # QQ号在第二列
            
            if qq and qq in self.requests:
                self.requests[qq]['status'] = 'rejected'
                self.requests[qq]['process_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.requests[qq]['processed_by'] = 'console_gui'
                self.requests[qq]['reject_reason'] = reason
                
                self.log(f"❌ 已拒绝 {qq} 的申请，原因: {reason}")
        
        # 保存数据并刷新UI
        self.save_requests()
        self.load_requests()
        self.load_admins()
        self.update_status()
    # admin_console_gui.py - 第7部分
    def add_admin(self):
        """添加管理员"""
        qq = simpledialog.askstring("添加管理员", "请输入QQ号:")
        if qq and qq.strip():
            qq = qq.strip()
            if qq not in self.admins:
                self.admins.add(qq)
                self.save_admins()
                self.load_admins()
                self.update_status()
                self.log(f"✅ 已添加管理员: {qq}")
            else:
                messagebox.showinfo("提示", "该用户已经是管理员")
    
    def remove_selected_admin(self):
        """移除选中的管理员"""
        selection = self.admins_tree.selection()
        if not selection:
            messagebox.showwarning("提示", "请先选择一个管理员")
            return
        
        if messagebox.askyesno("确认", "确定要移除选中的管理员吗？"):
            removed_count = 0
            
            for item in selection:
                values = self.admins_tree.item(item)['values']
                qq = values[0]  # QQ号在第一列
                
                if qq:
                    # 使用AdminManager的方法移除
                    success, message = self.admin_manager.remove_admin(qq, "console_gui")
                    if success:
                        self.log(f"➖ {message}")
                        removed_count += 1
                    else:
                        self.log(f"❌ {message}")
            
            if removed_count > 0:
                # 强制刷新UI
                self.force_refresh_ui()
                self.log(f"📊 已移除 {removed_count} 个管理员")
    def add_to_blacklist(self):
        """添加用户到黑名单"""
        qq = simpledialog.askstring("添加黑名单", "请输入要封禁的QQ号:")
        if qq and qq.strip():
            qq = qq.strip()
            reason = simpledialog.askstring("封禁原因", "请输入封禁原因:")
            
            if qq not in self.blacklist:
                self.blacklist.add(qq)
                self.save_blacklist()
                self.load_blacklist()
                self.update_status()
                
                reason_text = f"，原因: {reason}" if reason else ""
                self.log(f"🚫 已添加黑名单: {qq}{reason_text}")
            else:
                messagebox.showinfo("提示", "该用户已在黑名单中")
    
    def remove_from_blacklist(self):
        """从黑名单移除用户"""
        selection = self.blacklist_tree.selection()
        if not selection:
            messagebox.showwarning("提示", "请先选择一个用户")
            return
        
        if messagebox.askyesno("确认", "确定要从黑名单移除选中的用户吗？"):
            for item in selection:
                values = self.blacklist_tree.item(item)['values']
                qq = values[0]  # QQ号在第一列
                
                if qq in self.blacklist:
                    self.blacklist.remove(qq)
                    self.log(f"✅ 已从黑名单移除: {qq}")
        
        self.save_blacklist()
        self.load_blacklist()
        self.update_status()
    # admin_console_gui.py - 第8部分
    def search_blacklist(self):
        """搜索黑名单用户"""
        keyword = self.search_var.get().strip()
        if not keyword:
            self.load_blacklist()  # 清空搜索，显示全部
            return
        
        # 清空现有数据
        for item in self.blacklist_tree.get_children():
            self.blacklist_tree.delete(item)
        
        # 搜索匹配的用户
        for user in self.blacklist:
            if keyword in user:
                self.blacklist_tree.insert("", tk.END, values=(
                    user,
                    datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "控制台添加"
                ))
    
    def auto_refresh(self):
        """自动刷新数据"""
        self.load_data()
        self.root.after(30000, self.auto_refresh)  # 每30秒刷新一次
    
    # ========== 日志功能 ==========
    
    def log(self, message):
        """记录日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        # 添加到日志文本框
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)  # 滚动到最后
        
        # 同时在控制台输出（可选）
        print(log_message, end='')
    
    def clear_logs(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)
    
    def save_logs(self):
        """保存日志到文件"""
        os.makedirs("logs", exist_ok=True)
        filename = f"logs/system_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(self.log_text.get(1.0, tk.END))
        self.log(f"📄 日志已保存到: {filename}")
    # admin_console_gui.py - 第9部分
    def copy_logs(self):
        """复制日志到剪贴板"""
        self.root.clipboard_clear()
        self.root.clipboard_append(self.log_text.get(1.0, tk.END))
        self.log("📋 日志已复制到剪贴板")
    
    # ========== 工具功能 ==========
    
    def export_data(self):
        """导出数据"""
        export_dir = "exports"
        os.makedirs(export_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 导出黑名单
        with open(os.path.join(export_dir, f"blacklist_{timestamp}.json"), 'w', encoding='utf-8') as f:
            json.dump({"users": list(self.blacklist)}, f, indent=2, ensure_ascii=False)
        
        # 导出管理员
        with open(os.path.join(export_dir, f"admins_{timestamp}.json"), 'w', encoding='utf-8') as f:
            json.dump({"admins": list(self.admins)}, f, indent=2, ensure_ascii=False)
        
        # 导出申请
        with open(os.path.join(export_dir, f"requests_{timestamp}.json"), 'w', encoding='utf-8') as f:
            json.dump(self.requests, f, indent=2, ensure_ascii=False)
        
        self.log(f"📤 数据已导出到 {export_dir} 目录")
    
    def batch_import(self):
        """批量导入"""
        # 这里可以实现从文件批量导入功能
        messagebox.showinfo("提示", "批量导入功能开发中...")
    
    def backup_data(self):
        """备份数据"""
        backup_dir = "backups"
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"backup_{timestamp}")
        os.makedirs(backup_path)
        
        # 备份所有数据文件
        import shutil
        for file in [self.blacklist_file, self.admins_file, self.requests_file]:
            if os.path.exists(file):
                shutil.copy2(file, backup_path)
        
        self.log(f"💾 数据已备份到: {backup_path}")
    # admin_console_gui.py - 第10部分（最后部分）
    def show_help(self):
        """显示帮助"""
        help_text = """📖 使用说明：

1. 申请管理
   - 查看待处理的申请
   - 选中申请后可以批准或拒绝
   - 拒绝时需要输入原因

2. 管理员管理
   - 查看所有管理员
   - 可以添加新的管理员
   - 可以移除现有的管理员

3. 黑名单管理
   - 查看所有黑名单用户
   - 可以添加用户到黑名单
   - 可以从黑名单移除用户
   - 支持搜索功能

4. 系统日志
   - 查看所有操作记录
   - 可以清空、保存、复制日志

💡 提示：
- 数据每30秒自动刷新
- 所有更改会立即生效
- 建议定期备份数据"""
        
        messagebox.showinfo("使用说明", help_text)
    
    def show_about(self):
        """显示关于"""
        about_text = """🤖 QQ机器人管理控制台
版本: 1.0
作者: DeepSeek
功能: 管理QQ机器人的管理员和黑名单系统
        
📧 反馈: 请联系开发者
📅 更新: 2026/1/7年"""
        
        messagebox.showinfo("关于", about_text)
    
    def run(self):
        """运行GUI"""
        self.log("🚀 管理控制台启动")
        self.root.mainloop()

# ========== 启动程序 ==========
if __name__ == "__main__":
    try:
        console = AdminConsoleGUI()
        console.run()
    except Exception as e:
        print(f"程序启动失败: {e}")
        input("按Enter键退出...")
