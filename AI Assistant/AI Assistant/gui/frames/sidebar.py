# gui/frames/sidebar.py
import customtkinter as ctk
from tkinter import messagebox
import webbrowser
from PIL import Image
import os

class SidebarFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.setup_ui()

    def setup_ui(self):
        # 创建导航按钮
        self.create_nav_buttons()
        
        # 创建分隔线
        self.separator = ctk.CTkFrame(self, height=2)
        self.separator.pack(fill="x", padx=20, pady=10)
        
        # 创建图标框架
        self.icon_frame = ctk.CTkFrame(self)
        self.icon_frame.pack(side="bottom", padx=10, pady=10)

        # 加载图标
        try:
            github_icon = self.load_icon("assets/icons/github.png", (30, 30))
            website_icon = self.load_icon("assets/icons/website.png", (30, 30))

            # GitHub 图标按钮
            self.github_btn = ctk.CTkButton(
                self.icon_frame,
                text="",
                image=github_icon,
                width=40,
                height=40,
                command=self.open_github,
                fg_color="transparent",
                hover_color=("gray70", "gray30")
            )
            self.github_btn.pack(side="left", padx=5)

            # 网站图标按钮
            self.website_btn = ctk.CTkButton(
                self.icon_frame,
                text="",
                image=website_icon,
                width=40,
                height=40,
                command=self.open_website,
                fg_color="transparent",
                hover_color=("gray70", "gray30")
            )
            self.website_btn.pack(side="left", padx=5)

        except Exception as e:
            self.show_error(f"加载图标出错: {str(e)}")

    def create_nav_buttons(self):
        buttons = [
            ("文本处理", "text"),
            ("图片处理", "image"),
            ("设置", "settings")
        ]
        
        for text, frame_name in buttons:
            btn = ctk.CTkButton(
                self,
                text=text,
                command=lambda x=frame_name: self.controller.show_frame(x)
            )
            btn.pack(pady=10, padx=20)

    def load_icon(self, path, size):
        """加载并调整图标大小"""
        try:
            # 获取绝对路径
            abs_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), path)
            return ctk.CTkImage(
                light_image=Image.open(abs_path),
                dark_image=Image.open(abs_path),
                size=size
            )
        except Exception as e:
            raise Exception(f"无法加载图标 {path}: {str(e)}")

    def open_github(self):
        """打开 GitHub 链接"""
        webbrowser.open("https://github.com/bone-de")

    def open_website(self):
        """打开网站链接"""
        webbrowser.open("https://open.api.gu28.top")

    def show_error(self, message):
        """显示错误消息"""
        messagebox.showerror("错误", message)
