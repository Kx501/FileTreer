"""
图形界面模块
使用 tkinter 创建文件树生成器的用户界面
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
import threading
from config import Config
from filetree_generator import FileTreeGenerator


class FileTreeApp:
    """文件树生成器主窗口"""
    
    def __init__(self, root: tk.Tk, config: Config):
        """
        初始化应用程序
        
        Args:
            root: tkinter 根窗口
            config: 配置对象
        """
        self.root = root
        self.config = config
        self.selected_path: Path = None
        self.generated_result: dict = {}
        
        # 设置窗口
        self.root.title("文件树生成器 - FileTreer")
        self.root.geometry("465x665")
        
        # 创建界面
        self.create_widgets()
        
        # 加载配置
        self.load_config_to_ui()
    
    def create_widgets(self):
        """创建所有界面组件"""
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # 创建标签页
        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        # 标签页1：配置和生成
        self.config_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.config_frame, text="配置")
        
        # 标签页2：预览和结果
        self.preview_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.preview_frame, text="预览")
        
        # 创建配置标签页内容
        self.create_config_tab()
        
        # 创建预览标签页内容
        self.create_preview_tab()
    
    def create_config_tab(self):
        """创建配置标签页"""
        config_frame = self.config_frame
        config_frame.columnconfigure(1, weight=1)
        
        # 1. 文件夹选择区域
        folder_frame = ttk.LabelFrame(config_frame, text="选择文件夹", padding="5")
        folder_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        folder_frame.columnconfigure(1, weight=1)
        
        ttk.Button(folder_frame, text="选择文件夹", command=self.select_folder).grid(
            row=0, column=0, padx=5
        )
        self.path_var = tk.StringVar(value="未选择文件夹")
        ttk.Label(folder_frame, textvariable=self.path_var).grid(
            row=0, column=1, sticky=(tk.W, tk.E), padx=5
        )
        
        # 2. 格式选择区域
        format_frame = ttk.LabelFrame(config_frame, text="输出格式", padding="5")
        format_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.format_var = tk.StringVar(value='ascii')
        
        ttk.Radiobutton(format_frame, text="ASCII 艺术树", variable=self.format_var, value='ascii').grid(
            row=0, column=0, padx=5
        )
        ttk.Radiobutton(format_frame, text="Markdown 格式", variable=self.format_var, value='markdown').grid(
            row=0, column=1, padx=5
        )
        
        # 3. 设置面板
        settings_frame = ttk.LabelFrame(config_frame, text="设置", padding="5")
        settings_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        settings_frame.columnconfigure(1, weight=1)
        settings_frame.rowconfigure(2, weight=1)
        config_frame.rowconfigure(2, weight=1)
        
        # 忽略隐藏文件
        self.ignore_hidden_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            settings_frame, 
            text="忽略隐藏文件/文件夹", 
            variable=self.ignore_hidden_var
        ).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        # 忽略清单（使用Text widget，换行分隔）
        ttk.Label(settings_frame, text="忽略清单（每行一个，类似.gitignore）:").grid(
            row=1, column=0, columnspan=2, sticky=tk.W, pady=2
        )
        ignore_text_frame = ttk.Frame(settings_frame)
        ignore_text_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=2)
        ignore_text_frame.columnconfigure(0, weight=1)
        ignore_text_frame.rowconfigure(0, weight=1)
        
        self.ignore_patterns_text = scrolledtext.ScrolledText(
            ignore_text_frame,
            wrap=tk.NONE,
            font=('Consolas', 9),
            height=12
        )
        self.ignore_patterns_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 最大深度
        ttk.Label(settings_frame, text="最大深度（留空为无限）:").grid(
            row=3, column=0, sticky=tk.W, pady=2
        )
        self.max_depth_var = tk.StringVar()
        depth_entry = ttk.Entry(settings_frame, textvariable=self.max_depth_var, width=10)
        depth_entry.grid(row=3, column=1, sticky=tk.W, padx=5, pady=2)
        
        # 每层最大文件数
        ttk.Label(settings_frame, text="每层最大文件数（留空为无限）:").grid(
            row=4, column=0, sticky=tk.W, pady=2
        )
        self.max_items_var = tk.StringVar()
        items_entry = ttk.Entry(settings_frame, textvariable=self.max_items_var, width=10)
        items_entry.grid(row=4, column=1, sticky=tk.W, padx=5, pady=2)
        
        # 根目录文件数不限制
        self.unlimit_root_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            settings_frame, 
            text="根目录文件数不限制", 
            variable=self.unlimit_root_var
        ).grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        # 4. 生成按钮
        button_frame = ttk.Frame(config_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        self.generate_button = ttk.Button(
            button_frame, 
            text="生成文件树", 
            command=self.generate_tree,
            state=tk.DISABLED
        )
        self.generate_button.pack(side=tk.LEFT, padx=5)
    
    def create_preview_tab(self):
        """创建预览标签页"""
        preview_frame = self.preview_frame
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)
        
        # 预览区域
        preview_label_frame = ttk.LabelFrame(preview_frame, text="预览", padding="5")
        preview_label_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        preview_label_frame.columnconfigure(0, weight=1)
        preview_label_frame.rowconfigure(0, weight=1)
        
        self.preview_text = scrolledtext.ScrolledText(
            preview_label_frame, 
            wrap=tk.NONE,
            font=('Consolas', 10),
            width=100,
            height=35
        )
        self.preview_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 操作按钮区域
        action_frame = ttk.Frame(preview_frame)
        action_frame.grid(row=1, column=0, pady=5)
        
        self.copy_button = ttk.Button(
            action_frame,
            text="复制到剪贴板",
            command=self.copy_to_clipboard,
            state=tk.DISABLED
        )
        self.copy_button.pack(side=tk.LEFT, padx=5)
        
        self.save_button = ttk.Button(
            action_frame,
            text="保存到文件",
            command=self.save_to_file,
            state=tk.DISABLED
        )
        self.save_button.pack(side=tk.LEFT, padx=5)
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(preview_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)
    
    def load_config_to_ui(self):
        """将配置加载到UI"""
        self.ignore_hidden_var.set(self.config.ignore_hidden)
        
        # 显示所有忽略清单（包括默认清单），每行一个
        ignore_patterns_str = self.config.get_ignore_patterns_string()
        self.ignore_patterns_text.delete(1.0, tk.END)
        self.ignore_patterns_text.insert(1.0, ignore_patterns_str)
        
        if self.config.max_depth is not None:
            self.max_depth_var.set(str(self.config.max_depth))
        else:
            self.max_depth_var.set('')
        
        # 每层最大文件数
        if self.config.max_items_per_level is not None:
            self.max_items_var.set(str(self.config.max_items_per_level))
        else:
            self.max_items_var.set('')
        
        # 根目录文件数不限制
        self.unlimit_root_var.set(self.config.unlimit_root_items)
        
        # 格式选择
        self.format_var.set(self.config.output_format)
    
    def save_ui_to_config(self):
        """将UI设置保存到配置"""
        self.config.ignore_hidden = self.ignore_hidden_var.get()
        
        # 处理忽略清单（从Text widget读取，换行分隔）
        patterns_str = self.ignore_patterns_text.get(1.0, tk.END)
        self.config.set_ignore_patterns_from_string(patterns_str)
        
        # 处理最大深度
        depth_str = self.max_depth_var.get().strip()
        if depth_str:
            try:
                self.config.max_depth = int(depth_str)
            except ValueError:
                self.config.max_depth = 4  # 默认值
        else:
            self.config.max_depth = None  # 无限
        
        # 处理每层最大文件数
        items_str = self.max_items_var.get().strip()
        if items_str:
            try:
                items = int(items_str)
                self.config.max_items_per_level = max(1, items)  # 至少为1
            except ValueError:
                self.config.max_items_per_level = None  # 无限
        else:
            self.config.max_items_per_level = None  # 无限
        
        # 根目录文件数不限制
        self.config.unlimit_root_items = self.unlimit_root_var.get()
        
        # 处理输出格式
        self.config.output_format = self.format_var.get()
    
    def check_unlimited_settings(self):
        """
        检查是否有无限设置
        
        Returns:
            (has_unlimited, message): 是否有无限设置，以及提示消息
        """
        has_unlimited = False
        messages = []
        
        if self.config.max_depth is None:
            has_unlimited = True
            messages.append("最大深度：无限")
        
        if self.config.max_items_per_level is None:
            has_unlimited = True
            messages.append("每层最大文件数：无限")
        
        if self.config.unlimit_root_items:
            has_unlimited = True
            messages.append("根目录文件数：无限")
        
        if has_unlimited:
            msg = "检测到以下设置为无限，扫描可能需要较长时间：\n\n" + "\n".join(messages)
            msg += "\n\n是否继续？"
            return True, msg
        
        return False, ""
    
    def select_folder(self):
        """选择文件夹"""
        folder = filedialog.askdirectory(title="选择要扫描的文件夹")
        if folder:
            self.selected_path = Path(folder)
            self.path_var.set(str(self.selected_path))
            self.generate_button.config(state=tk.NORMAL)
            self.status_var.set(f"已选择: {self.selected_path.name}")
    
    def generate_tree(self):
        """生成文件树（在后台线程中执行）"""
        if not self.selected_path or not self.selected_path.exists():
            messagebox.showerror("错误", "请先选择一个有效的文件夹")
            return
        
        # 保存UI设置到配置
        self.save_ui_to_config()
        
        # 检查是否有无限设置，如果有则确认
        has_unlimited, msg = self.check_unlimited_settings()
        if has_unlimited:
            result = messagebox.askyesno("确认", msg, icon='warning')
            if not result:
                return
        
        # 禁用按钮，显示状态
        self.generate_button.config(state=tk.DISABLED)
        self.copy_button.config(state=tk.DISABLED)
        self.save_button.config(state=tk.DISABLED)
        self.status_var.set("正在扫描文件夹...")
        self.preview_text.delete(1.0, tk.END)
        self.preview_text.insert(tk.END, "正在扫描，请稍候...")
        
        # 切换到预览标签页
        self.notebook.select(1)
        
        # 在后台线程中执行扫描
        thread = threading.Thread(target=self._generate_tree_thread, daemon=True)
        thread.start()
    
    def _generate_tree_thread(self):
        """在后台线程中生成文件树"""
        try:
            generator = FileTreeGenerator(self.config)
            result = generator.generate(self.selected_path)
            self.generated_result = result
            
            # 在主线程中更新UI
            self.root.after(0, self._update_preview, result)
        
        except Exception as e:
            error_msg = f"生成文件树时出错: {str(e)}"
            self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
            self.root.after(0, lambda: self.status_var.set("生成失败"))
            self.root.after(0, lambda: self.generate_button.config(state=tk.NORMAL))
    
    def _update_preview(self, result: dict):
        """更新预览区域"""
        self.preview_text.delete(1.0, tk.END)
        
        # 显示生成的内容
        content = result.get('content', '未生成任何内容')
        self.preview_text.insert(tk.END, content)
        
        # 更新状态和按钮
        stats = result.get('stats', {'files': 0, 'dirs': 0})
        file_count = stats['files']
        dir_count = stats['dirs']
        self.status_var.set(f"生成完成 - 文件: {file_count}, 目录: {dir_count}")
        self.generate_button.config(state=tk.NORMAL)
        self.copy_button.config(state=tk.NORMAL)
        self.save_button.config(state=tk.NORMAL)
    
    def copy_to_clipboard(self):
        """复制到剪贴板"""
        content = self.preview_text.get(1.0, tk.END)
        if content.strip():
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            self.status_var.set("已复制到剪贴板")
        else:
            messagebox.showwarning("警告", "没有可复制的内容")
    
    def save_to_file(self):
        """保存到文件"""
        if not self.generated_result:
            messagebox.showwarning("警告", "请先生成文件树")
            return
        
        # 默认保存到扫描目录
        default_filename = self.selected_path / "filetree.txt" if self.selected_path else None
        
        if default_filename and self.selected_path.exists():
            # 尝试保存到默认位置
            try:
                self._save_content_to_file(default_filename)
                self.status_var.set(f"已保存到: {default_filename}")
                messagebox.showinfo("成功", f"文件树已保存到:\n{default_filename}")
                return
            except Exception as e:
                # 如果默认位置保存失败，让用户选择
                pass
        
        # 让用户选择保存位置
        filename = filedialog.asksaveasfilename(
            title="保存文件树",
            defaultextension=".txt",
            filetypes=[
                ("文本文件", "*.txt"),
                ("Markdown文件", "*.md"),
                ("所有文件", "*.*")
            ]
        )
        
        if filename:
            try:
                self._save_content_to_file(Path(filename))
                self.status_var.set(f"已保存到: {filename}")
                messagebox.showinfo("成功", f"文件树已保存到:\n{filename}")
            except Exception as e:
                messagebox.showerror("错误", f"保存文件失败: {str(e)}")
    
    def _save_content_to_file(self, filepath: Path):
        """将内容保存到文件"""
        content = self.preview_text.get(1.0, tk.END)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

