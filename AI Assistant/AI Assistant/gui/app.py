# gui/app.py
import customtkinter as ctk
from gui.frames import SidebarFrame, ImageProcessFrame, TextProcessFrame, SettingsFrame

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Assistant")
        self.root.geometry("1200x800")
        
        # 创建主布局
        self.setup_layout()
        
    def setup_layout(self):
        # 创建侧边栏
        self.sidebar = SidebarFrame(self.root, self)
        self.sidebar.pack(side="left", fill="y", padx=10, pady=10)
        
        # 创建主内容区
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        
        # 初始化各功能页面
        self.frames = {
            "image": ImageProcessFrame(self.main_frame),
            "text": TextProcessFrame(self.main_frame),
            "settings": SettingsFrame(self.main_frame)
        }
        # 获取 TextProcessFrame 实例
        self.text_frame = self.frames["text"] # 添加此行
        # 默认显示文本处理页面
        self.show_frame("text")
    
    def show_frame(self, frame_name):
        # 隐藏所有框架
        for frame in self.frames.values():
            frame.pack_forget()
        
        # 显示选中的框架
        self.frames[frame_name].pack(fill="both", expand=True)

    def get_text_frame(self):  # 新添加的方法
        if "text" in self.frames:
            return self.frames["text"]
        return None # or raise an exception, depending on your error handling
