# gui/frames/image_process.py
import customtkinter as ctk
from tkinter import filedialog, messagebox
import asyncio
import os
import threading
import queue
from core.image_processor import ImageProcessor
from config.settings import Settings
import logging
from PIL import Image
import time
from datetime import datetime

class ImageProcessFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)

        self.settings = Settings()
        self.log_queue = queue.Queue()
        self.setup_logging()
        self.setup_ui()
        self.selected_folder = ""
        self.processing_task = None
        self.stats = {
            'start_time': None,
            'processed': 0,
            'success': 0,
            'failed': 0,
            'total': 0
        }

    def setup_ui(self):
        self.control_frame = ctk.CTkFrame(self)
        self.control_frame.pack(side="left", fill="y", padx=10, pady=10)

        self.select_folder_btn = ctk.CTkButton(self.control_frame, text="选择文件夹", command=self.select_folder)
        self.select_folder_btn.pack(pady=10)

        self.settings_frame = ctk.CTkFrame(self.control_frame)
        self.settings_frame.pack(fill="x", pady=10)

        # API Key 输入
        self.api_key_label = ctk.CTkLabel(self.settings_frame, text="API Key:")
        self.api_key_label.pack()
        self.api_key_entry = ctk.CTkEntry(self.settings_frame, show="*")
        self.api_key_entry.pack(pady=5)
        self.api_key_entry.insert(0, self.settings.get("api_key", ""))

        # API Base URL 输入
        self.api_base_label = ctk.CTkLabel(self.settings_frame, text="API Base URL:")
        self.api_base_label.pack()
        self.api_base_entry = ctk.CTkEntry(self.settings_frame)
        self.api_base_entry.pack(pady=5)
        self.api_base_entry.insert(0, self.settings.get("api_base", ""))

        # 模型名称输入
        self.model_label = ctk.CTkLabel(self.settings_frame, text="模型名称:")
        self.model_label.pack()
        self.model_entry = ctk.CTkEntry(self.settings_frame)
        self.model_entry.pack(pady=5)
        self.model_entry.insert(0, self.settings.get("model", "gpt-4v-0301"))

        # 并发数设置
        self.concurrent_label = ctk.CTkLabel(self.settings_frame, text="并发数:")
        self.concurrent_label.pack()
        self.concurrent_entry = ctk.CTkEntry(self.settings_frame)
        self.concurrent_entry.pack(pady=5)
        self.concurrent_entry.insert(0, str(self.settings.get("max_concurrent", 3)))

        # 添加提示词输入框
        self.prompt_label = ctk.CTkLabel(self.settings_frame, text="提示词:")
        self.prompt_label.pack()
        self.prompt_text = ctk.CTkTextbox(self.settings_frame, height=100)
        self.prompt_text.pack(pady=5, fill="x")
        default_prompt = "识别图片中的文字："
        self.prompt_text.insert("1.0", self.settings.get("image_prompt", default_prompt))

        # 修改右侧内容区布局
        self.content_frame = ctk.CTkFrame(self)
        self.content_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        # 状态显示区域
        self.status_frame = ctk.CTkFrame(self.content_frame)
        self.status_frame.pack(fill="x", padx=10, pady=5)

        # 总体进度
        self.progress_frame = ctk.CTkFrame(self.status_frame)
        self.progress_frame.pack(fill="x", pady=5)

        self.progress_label = ctk.CTkLabel(self.progress_frame, text="总体进度:")
        self.progress_label.pack(side="left", padx=5)

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=5)
        self.progress_bar.set(0)

        self.progress_text = ctk.CTkLabel(self.progress_frame, text="0/0")
        self.progress_text.pack(side="right", padx=5)

        # 详细状态信息
        self.stats_frame = ctk.CTkFrame(self.status_frame)
        self.stats_frame.pack(fill="x", pady=5)

        # 处理状态
        self.status_label = ctk.CTkLabel(self.stats_frame, text="状态: 就绪")
        self.status_label.pack(side="left", padx=5)

        # 成功/失败计数
        self.success_label = ctk.CTkLabel(self.stats_frame, text="成功: 0")
        self.success_label.pack(side="left", padx=5)

        self.failed_label = ctk.CTkLabel(self.stats_frame, text="失败: 0")
        self.failed_label.pack(side="left", padx=5)

        # 预计剩余时间
        self.time_label = ctk.CTkLabel(self.stats_frame, text="预计剩余时间: --:--")
        self.time_label.pack(side="right", padx=5)

        # 当前处理信息
        self.current_frame = ctk.CTkFrame(self.status_frame)
        self.current_frame.pack(fill="x", pady=5)

        self.current_label = ctk.CTkLabel(self.current_frame, text="当前处理: 无")
        self.current_label.pack(side="left", padx=5)

        self.speed_label = ctk.CTkLabel(self.current_frame, text="处理速度: --/s")
        self.speed_label.pack(side="right", padx=5)

        # 日志显示区域
        self.log_frame = ctk.CTkFrame(self.content_frame)
        self.log_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.log_label = ctk.CTkLabel(self.log_frame, text="处理日志:")
        self.log_label.pack(anchor="w", padx=5, pady=2)

        self.log_text = ctk.CTkTextbox(self.log_frame, height=400)
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

        # 控制按钮
        self.button_frame = ctk.CTkFrame(self.content_frame)
        self.button_frame.pack(fill="x", pady=10)

        self.start_btn = ctk.CTkButton(
            self.button_frame, 
            text="开始处理", 
            command=self.start_processing_wrapper
        )
        self.start_btn.pack(side="left", padx=5)

        self.stop_btn = ctk.CTkButton(
            self.button_frame,
            text="停止",
            command=self.stop_processing,
            state="disabled"
        )
        self.stop_btn.pack(side="left", padx=5)

        # 添加清空日志按钮
        self.clear_log_btn = ctk.CTkButton(
            self.button_frame,
            text="清空日志",
            command=self.clear_log
        )
        self.clear_log_btn.pack(side="right", padx=5)

    def clear_log(self):
        self.log_text.delete("1.0", "end")

    def select_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.selected_folder = folder_path
            self.log_message(f"已选择文件夹: {folder_path}")

    def setup_logging(self):
        log_handler = QueueHandler(self.log_queue)
        log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        log_handler.setFormatter(log_formatter)
        logging.getLogger().addHandler(log_handler)
        logging.getLogger().setLevel(logging.INFO)

    def update_status(self, status_text):
        self.status_label.configure(text=f"状态: {status_text}")

    def update_stats(self, success=None, failed=None):
        if success is not None:
            self.stats['success'] = success
            self.success_label.configure(text=f"成功: {success}")
        if failed is not None:
            self.stats['failed'] = failed
            self.failed_label.configure(text=f"失败: {failed}")

    def log_message(self, message):
        self.log_queue.put(message)
        self.after(0, self._update_log_display, message)

    def _update_log_display(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.see("end")

    def update_progress(self, current, total, success=None, failed=None):
        self.after(0, self._update_progress_display, current, total, success, failed)

    def _update_progress_display(self, current, total, success=None, failed=None):
        # 更新进度条和文本
        progress = current / total if total > 0 else 0
        self.progress_bar.set(progress)
        self.progress_text.configure(text=f"{current}/{total}")
        
        # 更新成功/失败计数
        if success is not None:
            self.success_label.configure(text=f"成功: {success}")
        if failed is not None:
            self.failed_label.configure(text=f"失败: {failed}")
        
        # 更新处理速度和预计剩余时间
        if self.stats['start_time'] and current > 0:
            elapsed_time = time.time() - self.stats['start_time']
            speed = current / elapsed_time
            self.speed_label.configure(text=f"处理速度: {speed:.2f}/s")
            
            remaining_items = total - current
            if speed > 0:
                remaining_time = remaining_items / speed
                minutes = int(remaining_time // 60)
                seconds = int(remaining_time % 60)
                self.time_label.configure(text=f"预计剩余时间: {minutes:02d}:{seconds:02d}")

        # 更新当前处理信息
        self.current_label.configure(text=f"当前处理: 第 {current} 张，共 {total} 张")

    def start_processing_wrapper(self):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.create_task(self.start_processing())

    async def start_processing(self):
        self.stats['start_time'] = time.time()
        self.processing_task = asyncio.create_task(self.run_processing())

    async def run_processing(self):
        try:
            # 保存设置
            self.settings.update({
                "api_key": self.api_key_entry.get(),
                "api_base": self.api_base_entry.get(),
                "model": self.model_entry.get(),
                "max_concurrent": int(self.concurrent_entry.get()),
                "image_prompt": self.prompt_text.get("1.0", "end-1c")
            })

            if not self.selected_folder:
                raise Exception("请先选择图片文件夹")

            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
            self.progress_bar.set(0)

            self.update_status("正在处理...")
            await self.process_images()
            self.update_status("处理完成")

        except Exception as e:
            messagebox.showerror("错误", str(e))
            self.log_message(f"错误: {str(e)}")
            self.update_status("处理出错")
        finally:
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")

    async def process_images(self):
        try:
            processor = ImageProcessor(
                image_dir=self.selected_folder,
                output_file="output/images/results.txt",
                api_key=self.api_key_entry.get(),
                base_url=self.api_base_entry.get(),
                max_workers=int(self.concurrent_entry.get()),
                model=self.model_entry.get(),
                prompt=self.prompt_text.get("1.0", "end-1c")
            )

            processor.set_callbacks(
                log_callback=self.log_message,
                progress_callback=self.update_progress
            )

            await processor.process_images()

        except Exception as e:
            raise Exception(f"处理图片时出错: {str(e)}")

    def stop_processing(self):
        if self.processing_task:
            self.processing_task.cancel()
            self.log_message("处理已停止")
            self.update_status("已停止")

class QueueHandler(logging.Handler):
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.put(self.format(record))
