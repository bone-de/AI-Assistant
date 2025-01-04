# main.py
import asyncio
import customtkinter as ctk
from gui.app import App
import tkinter as tk
import queue


async def start_app():
    root = ctk.CTk()
    app = App(root)

    # 在这里调用 get_text_frame()
    text_frame = app.get_text_frame()

    if text_frame: # 检查是否成功获取到 text_frame
        log_queue = text_frame.log_queue
        log_text = text_frame.log_text
        await async_mainloop(root, log_queue, log_text)
    else:
        print("无法获取 TextProcessFrame 实例")  # 或其他错误处理
async def async_mainloop(root, log_queue, log_text):
    while True:
        try:
            # 处理日志队列
            while True:
                try:
                    message = log_queue.get_nowait()
                    log_text.insert("end", f"{message}\n")
                    log_text.see("end")
                except queue.Empty:
                    break

            root.update()
            await asyncio.sleep(0.01)
        except tk.TclError as e:
            if "application has been destroyed" not in e.args[0]:
                raise
            break

async def start_app():
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    app = App(root)
    log_queue = app.text_frame.log_queue
    log_text = app.text_frame.log_text

    await async_mainloop(root, log_queue, log_text)

if __name__ == "__main__":
    asyncio.run(start_app())
