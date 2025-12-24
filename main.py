"""
文件树生成器主程序入口
"""
import tkinter as tk
from config import Config
from gui import FileTreeApp


def main():
    """主函数"""
    # 创建根窗口
    root = tk.Tk()
    
    # 加载配置
    config = Config()
    config.load_config()
    
    # 创建应用程序
    app = FileTreeApp(root, config)
    
    # 设置窗口关闭事件，保存配置
    def on_closing():
        app.save_ui_to_config()
        config.save_config()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # 运行主循环
    root.mainloop()


if __name__ == "__main__":
    main()

