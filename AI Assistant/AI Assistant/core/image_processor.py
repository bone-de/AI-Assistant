# core/image_processor.py
import os
import base64
import time
import asyncio
import aiohttp
from datetime import datetime
from tqdm import tqdm
from openai import AsyncOpenAI
import logging
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
import io
from core.text_processor import ProcessorBase

class ImageProcessor(ProcessorBase):
    def __init__(self, image_dir, output_file, api_key, base_url, max_workers=10, model="gpt-4v-0301", prompt="识别图片中的文字："):
        super().__init__()
        self.image_dir = image_dir
        self.output_file = output_file
        self.api_key = api_key
        self.base_url = base_url
        self.max_workers = max_workers
        self.model = model
        self.prompt = prompt  # 添加提示词
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
        self.setup_logging()


    def setup_logging(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f'logs/image_processor_{timestamp}.log'

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)


    def optimize_image(self, image_path, max_size=800):
        """优化图片大小，减少传输数据量"""
        try:
            with Image.open(image_path) as img:
                # 转换为RGB模式
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # 调整图片大小
                if max(img.size) > max_size:
                    ratio = max_size / max(img.size)
                    new_size = tuple(int(dim * ratio) for dim in img.size)
                    img = img.resize(new_size, Image.Resampling.LANCZOS)

                # 保存到内存中
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=85, optimize=True)
                return base64.b64encode(buffer.getvalue()).decode('utf-8')
        except Exception as e:
            self.log(f"优化图片 {image_path} 时出错: {str(e)}")
            return None

    async def process_single_image(self, session, image_name):
        try:
            image_path = os.path.join(self.image_dir, image_name)

            with ThreadPoolExecutor() as executor:
                base64_image = await asyncio.get_event_loop().run_in_executor(
                    executor, self.optimize_image, image_path
                )

            if not base64_image:
                return None

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self.prompt},  # 使用自定义提示词
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                         },
                     ],
                 }
             ],
         )

            result = response.choices[0].message.content.replace("*", "").replace("#", "").replace(" ", "")
            return f"文件名: {image_name}\n处理结果: {result}\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{'=' * 80}\n"

        except Exception as e:
            self.log(f"处理图片 {image_name} 时出错: {str(e)}")
            return None

    async def process_batch(self, batch):
        async with aiohttp.ClientSession() as session:
            tasks = [self.process_single_image(session, img) for img in batch]
            return await asyncio.gather(*tasks)

    def chunk_list(self, lst, chunk_size):
        return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


    async def process_images(self):
        start_time = time.time()
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)

        try:
            images = [f for f in os.listdir(self.image_dir) 
                     if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
            
            if not images:
                self.log(f"在 {self.image_dir} 中未找到图片")
                return

            self.log(f"找到 {len(images)} 张图片待处理")
            total_images = len(images)
            processed_images = 0
            success_count = 0
            failed_count = 0

            with open(self.output_file, 'w', encoding='utf-8') as f:
                f.write(f"处理开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{'='*80}\n")

            batches = self.chunk_list(images, self.max_workers)

            for batch in batches:
                if not self.running:
                    self.log("处理已停止")
                    break

                results = await self.process_batch(batch)
                for result in results:
                    if result:
                        success_count += 1
                        with open(self.output_file, 'a', encoding='utf-8') as f:
                            f.write(result)
                    else:
                        failed_count += 1

                processed_images += len(batch)
                self.update_progress(processed_images, total_images)
                
                # 更新成功/失败计数
                if self.progress_callback:
                    self.progress_callback(processed_images, total_images, success_count, failed_count)

            elapsed_time = time.time() - start_time
            summary = (f"\n总处理时间: {elapsed_time:.2f}秒\n"
                      f"处理的图片数量: {total_images}\n"
                      f"成功: {success_count}\n"
                      f"失败: {failed_count}\n"
                      f"平均每张图片处理时间: {elapsed_time/total_images:.2f}秒\n")

            with open(self.output_file, 'a', encoding='utf-8') as f:
                f.write(summary)

            self.log(f"处理完成. 结果已保存到 {self.output_file}")

        except Exception as e:
            self.log(f"处理过程中发生错误: {str(e)}")

    def stop(self):
      self.running = False


