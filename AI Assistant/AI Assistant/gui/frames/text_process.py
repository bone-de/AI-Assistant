# gui/frames/text_process.py
import customtkinter as ctk
from tkinter import filedialog, messagebox
import asyncio
import os
import threading
import queue
import logging
from core.text_processor import NovelProcessor, QuestionProcessor
from config.settings import Settings
import customtkinter as ctk

class TextProcessFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.settings = Settings()
        self.log_queue = queue.Queue()
        self.setup_logging() # 初始化日志
        self.setup_ui()
        self.log_queue = queue.Queue()  # 用于线程间通信
        self.setup_logging()  # 在初始化时设置日志

    def setup_ui(self):
        # 创建左侧控制面板
        self.control_frame = ctk.CTkFrame(self)
        self.control_frame.pack(side="left", fill="y", padx=10, pady=10)

        # 模式选择
        self.mode_label = ctk.CTkLabel(self.control_frame, text="处理模式:")
        self.mode_label.pack(pady=5)
        self.mode_var = ctk.StringVar(value="book")

        self.mode_book = ctk.CTkRadioButton(
            self.control_frame,
            text="书籍/大段落处理",
            variable=self.mode_var,
            value="book",
            command=self.update_ui_for_mode
        )
        self.mode_book.pack(pady=2)

        self.mode_batch = ctk.CTkRadioButton(
            self.control_frame,
            text="批量问答处理",
            variable=self.mode_var,
            value="batch",
            command=self.update_ui_for_mode
        )
        self.mode_batch.pack(pady=2)

        # 分段方式（仅用于书籍模式）
        self.split_frame = ctk.CTkFrame(self.control_frame)
        self.split_frame.pack(fill="x", pady=5)
        self.split_var = ctk.StringVar(value="auto")
        self.split_label = ctk.CTkLabel(self.split_frame, text="分段方式:")
        self.split_label.pack()

        self.split_auto = ctk.CTkRadioButton(
            self.split_frame,
            text="自动分段",
            variable=self.split_var,
            value="auto"
        )
        self.split_auto.pack()

        self.split_keyword = ctk.CTkRadioButton(
            self.split_frame,
            text="关键词分段",
            variable=self.split_var,
            value="keyword"
        )
        self.split_keyword.pack()

        # 关键词输入（用于关键词分段）
        self.keyword_frame = ctk.CTkFrame(self.split_frame)
        self.keyword_frame.pack(fill="x", pady=5)
        self.keyword_label = ctk.CTkLabel(self.keyword_frame, text="关键词:")
        self.keyword_label.pack(side="left")
        self.keyword_entry = ctk.CTkEntry(self.keyword_frame)
        self.keyword_entry.pack(side="left", fill="x", expand=True)

        # 分段长度设置（用于自动分段）
        self.chunk_size_frame = ctk.CTkFrame(self.split_frame)
        self.chunk_size_frame.pack(fill="x", pady=5)
        self.chunk_size_label = ctk.CTkLabel(self.chunk_size_frame, text="分段长度:")
        self.chunk_size_label.pack(side="left")
        self.chunk_size_entry = ctk.CTkEntry(self.chunk_size_frame)
        self.chunk_size_entry.pack(side="left", fill="x", expand=True)
        self.chunk_size_entry.insert(0, str(self.settings.get("chunk_size", 2000)))

        # 输出格式（批量模式）
        self.output_format_frame = ctk.CTkFrame(self.control_frame)
        self.output_format_frame.pack(fill="x", pady=5)
        self.format_var = ctk.StringVar(value="qa")
        self.format_label = ctk.CTkLabel(self.output_format_frame, text="输出格式:")
        self.format_label.pack()

        self.format_qa = ctk.CTkRadioButton(
            self.output_format_frame,
            text="问答格式",
            variable=self.format_var,
            value="qa"
        )
        self.format_qa.pack()

        self.format_answer = ctk.CTkRadioButton(
            self.output_format_frame,
            text="仅答案",
            variable=self.format_var,
            value="answer"
        )
        self.format_answer.pack()
        
        # 文件选择
        self.file_frame = ctk.CTkFrame(self.control_frame)
        self.file_frame.pack(fill="x", pady=10)
        self.select_file_btn = ctk.CTkButton(
            self.file_frame,
            text="选择文件",
            command=self.select_file
        )
        self.select_file_btn.pack(pady=5)
        
        # API设置
        self.settings_frame = ctk.CTkFrame(self.control_frame)
        self.settings_frame.pack(fill="x", pady=10)
        
        # API Key
        self.api_key_label = ctk.CTkLabel(self.settings_frame, text="API Key:")
        self.api_key_label.pack()
        self.api_key_entry = ctk.CTkEntry(self.settings_frame, show="*")
        self.api_key_entry.pack(pady=5)
        self.api_key_entry.insert(0, self.settings.get("api_key", ""))
        
        # API Base URL
        self.api_base_label = ctk.CTkLabel(self.settings_frame, text="API Base URL:")
        self.api_base_label.pack()
        self.api_base_entry = ctk.CTkEntry(self.settings_frame)
        self.api_base_entry.pack(pady=5)
        self.api_base_entry.insert(0, self.settings.get("api_base", ""))
        
        # 模型名称
        self.model_label = ctk.CTkLabel(self.settings_frame, text="模型名称:")
        self.model_label.pack()
        self.model_entry = ctk.CTkEntry(self.settings_frame)
        self.model_entry.pack(pady=5)
        self.model_entry.insert(0, self.settings.get("model", "gpt-3.5-turbo"))
        
        # 并发设置
        self.concurrent_label = ctk.CTkLabel(self.settings_frame, text="并发数:")
        self.concurrent_label.pack()
        self.concurrent_entry = ctk.CTkEntry(self.settings_frame)
        self.concurrent_entry.pack(pady=5)
        self.concurrent_entry.insert(0, str(self.settings.get("max_concurrent", 3)))
        
        # 提示词设置
        self.prompt_label = ctk.CTkLabel(self.settings_frame, text="系统提示词:")
        self.prompt_label.pack()
        self.prompt_text = ctk.CTkTextbox(self.settings_frame, height=100)
        self.prompt_text.pack(pady=5, fill="x")
        self.prompt_text.insert("1.0", self.settings.get("system_prompt", ""))
        
        # 创建右侧内容区
        self.content_frame = ctk.CTkFrame(self)
        self.content_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        
        # 状态和进度显示
        self.status_label = ctk.CTkLabel(self.content_frame, text="就绪")
        self.status_label.pack(pady=5)
        self.progress_bar = ctk.CTkProgressBar(self.content_frame)
        self.progress_bar.pack(fill="x", padx=10, pady=5)
        self.progress_bar.set(0)
        
        # 日志显示区域
        self.log_text = ctk.CTkTextbox(self.content_frame, height=400)
        self.log_text.pack(fill="both", expand=True, padx=10, pady=5)
        
        # 控制按钮
        self.button_frame = ctk.CTkFrame(self.content_frame)
        self.button_frame.pack(fill="x", pady=10)
        
        self.start_btn = ctk.CTkButton(
            self.button_frame,
            text="开始处理",
            command=self.start_processing_wrapper # 使用包装函数
        )
        self.start_btn.pack(side="left", padx=5)
        
        self.stop_btn = ctk.CTkButton(
            self.button_frame,
            text="停止",
            command=self.stop_processing,
            state="disabled"
        )
        self.stop_btn.pack(side="left", padx=5)

    def start_processing_wrapper(self):
        # 获取当前正在运行的事件循环
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:  # 如果没有正在运行的循环，则获取主线程的循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        loop.create_task(self.start_processing())

    def update_ui_for_mode(self):
        mode = self.mode_var.get()
        # 更新UI显示
        if mode == "book":
            self.split_frame.pack(fill="x", pady=5)
            self.output_format_frame.pack_forget()
            self.select_file_btn.configure(text="选择文件/文件夹")
        else:
            self.split_frame.pack_forget()
            self.output_format_frame.pack(fill="x", pady=5)
            self.select_file_btn.configure(text="选择问题文件/文件夹")

# gui/frames/text_process.py (继续)

    def select_file(self):
        mode = self.mode_var.get()
        if mode == "book":
            # 书籍模式可以选择单个文件或文件夹
            file_path = filedialog.askopenfilename(
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            if file_path:
                self.selected_path = file_path
                self.log_message(f"已选择文件: {file_path}")
        else:
            # 批量问答模式
            folder_path = filedialog.askdirectory()
            if folder_path:
                self.selected_path = folder_path
                self.log_message(f"已选择文件夹: {folder_path}")
    def setup_logging(self):
        # 创建日志处理器，将日志输出到队列
        log_handler = QueueHandler(self.log_queue)
        log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        log_handler.setFormatter(log_formatter)
        logging.getLogger().addHandler(log_handler)
        logging.getLogger().setLevel(logging.INFO)

        # 创建线程，用于从队列中获取日志消息并更新GUI
        self.log_thread = threading.Thread(target=self.update_log, daemon=True)
        self.log_thread.start()

    def log_message(self, message):
        # 将日志消息添加到队列
        self.log_queue.put(message)

    def update_log(self):
        while True:
            try:
                message = self.log_queue.get(block=True, timeout=0.1)

                # 使用 customtkinter 的 after 方法（如果可用）
                def update_log_text():  # 包装函数，这很重要
                    self.log_text.insert("end", f"{message}\n")
                    self.log_text.see("end")
                    
                self.log_text.after(0, update_log_text)  # 在此处调用 after

            except queue.Empty:
                pass


    def update_progress(self, current, total):
        """更新进度条"""
        progress = current / total if total > 0 else 0
        self.progress_bar.set(progress)
        self.status_label.configure(text=f"进度: {current}/{total}")

    async def start_processing(self):
        """开始处理文本"""
        self.processing_task = asyncio.create_task(self.run_processing())

    async def run_processing(self):
        try:
            # 保存设置
            self.settings.update({
                "api_key": self.api_key_entry.get(),
                "api_base": self.api_base_entry.get(),
                "model": self.model_entry.get(),
                "max_concurrent": int(self.concurrent_entry.get()),
                "system_prompt": self.prompt_text.get("1.0", "end-1c"),
                "chunk_size": int(self.chunk_size_entry.get())
            })

            # 更新UI状态
            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
            self.progress_bar.set(0)

            if self.mode_var.get() == "book":
                await self.process_book()
            else:
                await self.process_batch()

        except Exception as e:
            messagebox.showerror("错误", str(e))
            self.log_message(f"错误: {str(e)}")
        finally:
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")

    async def process_book(self):
        """处理书籍/大段落文本"""
        try:
            model = self.model_entry.get()  # 获取用户输入的模型名称

            processor = NovelProcessor(
                api_key=self.api_key_entry.get(),
                api_base=self.api_base_entry.get(),
                input_folder=os.path.dirname(self.selected_path),
                output_folder="output/books",
                system_prompt=self.prompt_text.get("1.0", "end-1c"),
                max_concurrent=int(self.concurrent_entry.get())
            )
            processor.model = model  # 设置模型名称

            # 设置回调函数
            processor.set_callbacks(
                log_callback=self.log_message,
                progress_callback=self.update_progress
            )

            # 根据分段方式设置处理参数
            split_mode = self.split_var.get()
            chunk_size = int(self.chunk_size_entry.get())
            keyword = self.keyword_entry.get()
            processor.set_split_mode(split_mode, chunk_size, keyword)

            if os.path.isfile(self.selected_path):
                # 处理单个文件
                processor.input_file = self.selected_path
                await processor.process_novel()
            else:
                # 处理文件夹
                await processor.process_all_novels()

        except Exception as e:
            raise Exception(f"处理书籍时出错: {str(e)}")


    async def process_batch(self):
        """处理批量问答"""
        try:
            # 确定输出格式
            output_format = self.format_var.get()
            
            if os.path.isfile(self.selected_path):
                # 处理单个问题文件
                await self.process_single_question_file(self.selected_path, output_format)
            else:
                # 处理文件夹中的所有问题文件
                for file in os.listdir(self.selected_path):
                    if file.endswith('.txt'):
                        file_path = os.path.join(self.selected_path, file)
                        await self.process_single_question_file(file_path, output_format)

        except Exception as e:
             raise Exception(f"处理批量问答时出错: {str(e)}")


    async def process_single_question_file(self, file_path, output_format):
        """处理单个问题文件"""
        try:
            model = self.model_entry.get()  # 获取用户输入的模型名称

            processor = QuestionProcessor(
                api_key=self.api_key_entry.get(),
                api_base=self.api_base_entry.get(),
                input_file=file_path,
                output_prefix="output/qa/answers",
                max_concurrent=int(self.concurrent_entry.get())
            )
            processor.model = model #  新的代码：设置模型名称

            # 设置输出格式
            processor.set_output_format(output_format)
            
            # 设置回调函数
            processor.set_callbacks(
                log_callback=self.log_message,
                progress_callback=self.update_progress
            )

            await processor.process_all_questions()

        except Exception as e:
            raise Exception(f"处理问题文件 {file_path} 时出错: {str(e)}")


    def stop_processing(self):
        if hasattr(self, 'processing_task') and self.processing_task:
            self.processing_task.cancel()
            self.log_message("处理已停止")
        # 实现停止逻辑
# 自定义队列处理器
class QueueHandler(logging.Handler):
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.put(self.format(record))