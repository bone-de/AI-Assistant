# gui/frames/settings.py
import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
from config.settings import Settings
import json

class SettingsFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.settings = Settings()
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        # 创建主设置区域，使用滚动容器
        self.main_frame = ctk.CTkScrollableFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # ========== API 设置 ==========
        self.api_frame = ctk.CTkFrame(self.main_frame)
        self.api_frame.pack(fill="x", pady=(0, 20))

        self.api_label = ctk.CTkLabel(
            self.api_frame, 
            text="API 设置",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.api_label.pack(anchor="w", padx=10, pady=5)

        # API Key
        self.api_key_label = ctk.CTkLabel(self.api_frame, text="API Key:")
        self.api_key_label.pack(anchor="w", padx=10)
        
        self.api_key_entry = ctk.CTkEntry(self.api_frame, width=400, show="*")
        self.api_key_entry.pack(anchor="w", padx=10, pady=(0, 10))

        # API Base URL
        self.api_base_label = ctk.CTkLabel(self.api_frame, text="API Base URL:")
        self.api_base_label.pack(anchor="w", padx=10)
        
        self.api_base_entry = ctk.CTkEntry(self.api_frame, width=400)
        self.api_base_entry.pack(anchor="w", padx=10, pady=(0, 10))

        # 默认模型
        self.model_label = ctk.CTkLabel(self.api_frame, text="默认模型:")
        self.model_label.pack(anchor="w", padx=10)
        
        self.model_entry = ctk.CTkEntry(self.api_frame, width=200)
        self.model_entry.pack(anchor="w", padx=10, pady=(0, 10))

        # ========== 处理设置 ==========
        self.process_frame = ctk.CTkFrame(self.main_frame)
        self.process_frame.pack(fill="x", pady=(0, 20))

        self.process_label = ctk.CTkLabel(
            self.process_frame, 
            text="处理设置",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.process_label.pack(anchor="w", padx=10, pady=5)

        # 并发数
        self.concurrent_label = ctk.CTkLabel(self.process_frame, text="默认并发数:")
        self.concurrent_label.pack(anchor="w", padx=10)
        
        self.concurrent_entry = ctk.CTkEntry(self.process_frame, width=100)
        self.concurrent_entry.pack(anchor="w", padx=10, pady=(0, 10))

        # 图片大小限制
        self.image_size_label = ctk.CTkLabel(self.process_frame, text="图片大小限制(像素):")
        self.image_size_label.pack(anchor="w", padx=10)
        
        self.image_size_entry = ctk.CTkEntry(self.process_frame, width=100)
        self.image_size_entry.pack(anchor="w", padx=10, pady=(0, 10))

        # ========== 输出设置 ==========
        self.output_frame = ctk.CTkFrame(self.main_frame)
        self.output_frame.pack(fill="x", pady=(0, 20))

        self.output_label = ctk.CTkLabel(
            self.output_frame, 
            text="输出设置",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.output_label.pack(anchor="w", padx=10, pady=5)

        # 默认输出路径
        self.output_path_label = ctk.CTkLabel(self.output_frame, text="默认输出路径:")
        self.output_path_label.pack(anchor="w", padx=10)
        
        self.output_path_frame = ctk.CTkFrame(self.output_frame)
        self.output_path_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self.output_path_entry = ctk.CTkEntry(self.output_path_frame)
        self.output_path_entry.pack(side="left", fill="x", expand=True)
        
        self.output_path_btn = ctk.CTkButton(
            self.output_path_frame,
            text="浏览",
            width=60,
            command=self.select_output_path
        )
        self.output_path_btn.pack(side="right", padx=(5, 0))

        # ========== 界面设置 ==========
        self.ui_frame = ctk.CTkFrame(self.main_frame)
        self.ui_frame.pack(fill="x", pady=(0, 20))

        self.ui_label = ctk.CTkLabel(
            self.ui_frame, 
            text="界面设置",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.ui_label.pack(anchor="w", padx=10, pady=5)

        # 主题选择
        self.theme_label = ctk.CTkLabel(self.ui_frame, text="主题:")
        self.theme_label.pack(anchor="w", padx=10)
        
        self.theme_var = ctk.StringVar(value="System")
        self.theme_menu = ctk.CTkOptionMenu(
            self.ui_frame,
            values=["System", "Light", "Dark"],
            variable=self.theme_var,
            command=self.change_theme
        )
        self.theme_menu.pack(anchor="w", padx=10, pady=(0, 10))

        # 默认文本大小
        self.font_size_label = ctk.CTkLabel(self.ui_frame, text="默认文本大小:")
        self.font_size_label.pack(anchor="w", padx=10)
        
        self.font_size_entry = ctk.CTkEntry(self.ui_frame, width=100)
        self.font_size_entry.pack(anchor="w", padx=10, pady=(0, 10))

        # ========== 按钮区域 ==========
        self.button_frame = ctk.CTkFrame(self)
        self.button_frame.pack(fill="x", padx=20, pady=10)

        self.save_btn = ctk.CTkButton(
            self.button_frame,
            text="保存设置",
            command=self.save_settings
        )
        self.save_btn.pack(side="right", padx=5)

        self.reset_btn = ctk.CTkButton(
            self.button_frame,
            text="重置设置",
            command=self.reset_settings
        )
        self.reset_btn.pack(side="right", padx=5)

    def load_settings(self):
        """从配置文件加载设置"""
        # API 设置
        self.api_key_entry.insert(0, self.settings.get("api_key", ""))
        self.api_base_entry.insert(0, self.settings.get("api_base", ""))
        self.model_entry.insert(0, self.settings.get("model", "gpt-3.5-turbo"))

        # 处理设置
        self.concurrent_entry.insert(0, str(self.settings.get("max_concurrent", 3)))
        self.image_size_entry.insert(0, str(self.settings.get("max_image_size", 800)))

        # 输出设置
        self.output_path_entry.insert(0, self.settings.get("output_path", "output"))

        # 界面设置
        self.theme_var.set(self.settings.get("theme", "System"))
        self.font_size_entry.insert(0, str(self.settings.get("font_size", 13)))

    def save_settings(self):
        """保存设置到配置文件"""
        try:
            settings = {
                # API 设置
                "api_key": self.api_key_entry.get(),
                "api_base": self.api_base_entry.get(),
                "model": self.model_entry.get(),

                # 处理设置
                "max_concurrent": int(self.concurrent_entry.get()),
                "max_image_size": int(self.image_size_entry.get()),

                # 输出设置
                "output_path": self.output_path_entry.get(),

                # 界面设置
                "theme": self.theme_var.get(),
                "font_size": int(self.font_size_entry.get())
            }

            self.settings.update(settings)
            messagebox.showinfo("成功", "设置已保存")
            
        except ValueError as e:
            messagebox.showerror("错误", f"输入格式错误: {str(e)}")
        except Exception as e:
            messagebox.showerror("错误", f"保存设置时出错: {str(e)}")

    def reset_settings(self):
        """重置所有设置为默认值"""
        if messagebox.askyesno("确认", "确定要重置所有设置吗？"):
            # API 设置
            self.api_key_entry.delete(0, 'end')
            self.api_base_entry.delete(0, 'end')
            self.model_entry.delete(0, 'end')
            self.model_entry.insert(0, "gpt-3.5-turbo")

            # 处理设置
            self.concurrent_entry.delete(0, 'end')
            self.concurrent_entry.insert(0, "3")
            self.image_size_entry.delete(0, 'end')
            self.image_size_entry.insert(0, "800")

            # 输出设置
            self.output_path_entry.delete(0, 'end')
            self.output_path_entry.insert(0, "output")

            # 界面设置
            self.theme_var.set("System")
            self.font_size_entry.delete(0, 'end')
            self.font_size_entry.insert(0, "13")

            # 保存默认设置
            self.save_settings()

    def select_output_path(self):
        """选择输出路径"""
        path = filedialog.askdirectory()
        if path:
            self.output_path_entry.delete(0, 'end')
            self.output_path_entry.insert(0, path)

    def change_theme(self, new_theme):
        """更改界面主题"""
        ctk.set_appearance_mode(new_theme)
