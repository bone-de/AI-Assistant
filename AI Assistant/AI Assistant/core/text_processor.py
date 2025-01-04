# core/text_processor.py
from openai import AsyncOpenAI
import os
import time
import asyncio
import logging
from datetime import datetime
import re
import uuid
from typing import List, Dict, Optional
import aiohttp

class ProcessorBase:
    def __init__(self):
        self.log_callback = None
        self.progress_callback = None
        self.running = True
        self.model = "gpt-3.5-turbo"  # 默认模型

    def set_callbacks(self, log_callback=None, progress_callback=None):
        self.log_callback = log_callback
        self.progress_callback = progress_callback

    def log(self, message):
        if self.log_callback:
            self.log_callback(message)
        logging.info(message)  # 使用logging模块记录日志

    def update_progress(self, current, total):
        if self.progress_callback:
            self.progress_callback(current, total)


class NovelProcessor(ProcessorBase):
    def __init__(self, api_key, api_base, input_folder, output_folder, system_prompt, max_concurrent=3):
        super().__init__()
        self.client = AsyncOpenAI(api_key=api_key, base_url=api_base)
        self.input_folder = input_folder
        self.output_folder = output_folder
        self.system_prompt = system_prompt
        self.max_concurrent = max_concurrent
        self.split_mode = "auto"
        self.chunk_size = 2000
        self.keyword = ""

        self.create_directories()
        self.stats = {
            'total_chapters': 0,
            'successful_tasks': 0,
            'failed_tasks': 0,
            'start_time': None,
            'end_time': None,
            'processing_time': None
        }
        self.setup_logging()


    def set_split_mode(self, mode, chunk_size=2000, keyword=""):
        self.split_mode = mode
        self.chunk_size = chunk_size
        self.keyword = keyword

    def create_directories(self):
        os.makedirs(self.output_folder, exist_ok=True)
        os.makedirs('logs', exist_ok=True)

    def setup_logging(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f'logs/novel_processor_{timestamp}.log'
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def split_text(self, content):
        if self.split_mode == "auto":
            chunks = []
            current_chunk = ""
            paragraphs = content.split('\n')
            for para in paragraphs:
                if len(current_chunk) + len(para) <= self.chunk_size:
                    current_chunk += para + '\n'
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = para + '\n'
            if current_chunk:
                chunks.append(current_chunk.strip())
            return chunks
        elif self.split_mode == "keyword":
            if self.keyword:
                positions = [m.start() for m in re.finditer(self.keyword, content)]
            else:
                chapters = re.finditer(r'第[一二三四五六七八九十百千]+章|第\d+章', content)
                positions = [m.start() for m in chapters]

            if not positions:
                return [content]

            chunks = []
            start = 0
            for pos in positions:
                chunks.append(content[start:pos].strip())
                start = pos
            chunks.append(content[start:].strip())
            return chunks
        else:
            return [content]

    async def process_chunk(self, chunk: str, index: int) -> Dict:
        try:
            self.log(f"正在处理第 {index + 1} 段")
            start_time = time.time()

            response = await self.client.chat.completions.create(
                model=self.model,  # 使用 self.model
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": chunk}
                ]
            )

            processing_time = time.time() - start_time
            result = response.choices[0].message.content

            self.stats['successful_tasks'] += 1
            self.log(f"第 {index + 1} 段处理完成，用时 {processing_time:.2f} 秒")

            return {
                'chunk_index': index,
                'content': chunk,
                'result': result,
                'processing_time': processing_time
            }

        except Exception as e:
            self.stats['failed_tasks'] += 1
            self.log(f"处理第 {index + 1} 段时出错: {str(e)}")
            return {
                'chunk_index': index,
                'content': chunk,
                'result': f"Error: {str(e)}",
                'processing_time': 0
            }

    async def process_batch(self, chunks: List[str]) -> List[Dict]:
        tasks = []
        for i, chunk in enumerate(chunks):
            if not self.running:
                break
            tasks.append(self.process_chunk(chunk, i))
        return await asyncio.gather(*tasks)

    def write_results(self, results: List[Dict], output_file: str):
        try:
            with open(output_file, 'a', encoding='utf-8') as f:
                for result in results:
                    f.write(f"\n\n=== 第 {result['chunk_index'] + 1} 段 ===\n")
                    f.write("=" * 50 + "\n")
                    f.write(result['result'])
                    f.write("\n" + "=" * 50)
            self.log(f"结果已保存到: {output_file}")
        except Exception as e:
            self.log(f"写入结果时出错: {str(e)}")


    async def process_novel(self):
        self.stats['start_time'] = datetime.now()
        self.log(f"开始处理文件: {os.path.basename(self.input_file)}")

        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                content = f.read()

            chunks = self.split_text(content)

            if isinstance(chunks, int):
                chunks = [str(chunks)]

            self.stats['total_chapters'] = len(chunks)
            self.log(f"文本已分割为 {len(chunks)} 段")

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(
                self.output_folder,
                f"processed_{os.path.splitext(os.path.basename(self.input_file))[0]}_{timestamp}.txt"
            )

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("AI 处理结果\n")
                f.write(f"原文件: {os.path.basename(self.input_file)}\n")
                f.write(f"处理时间: {self.stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 50 + "\n")

            for i in range(0, len(chunks), self.max_concurrent):
                if not self.running:
                    self.log("处理已停止")
                    break

                batch = chunks[i:i + self.max_concurrent]
                results = await self.process_batch(batch)

                self.write_results(results, output_file)

                progress = min(i + self.max_concurrent, len(chunks))
                self.update_progress(progress, len(chunks))

                if i + self.max_concurrent < len(chunks):
                    await asyncio.sleep(1)

            self.stats['end_time'] = datetime.now()
            self.stats['processing_time'] = (self.stats['end_time'] - self.stats['start_time']).total_seconds()

            self.log_final_stats(output_file)

        except Exception as e:
            self.log(f"处理文件时出错: {str(e)}")
            raise

    async def process_all_novels(self):
        try:
            novel_files = [f for f in os.listdir(self.input_folder) if f.endswith('.txt')]
            self.log(f"找到 {len(novel_files)} 个文件待处理")

            for novel_file in novel_files:
                if not self.running:
                    self.log("处理已停止")
                    break

                try:
                    self.stats = {
                        'total_chapters': 0,
                        'successful_tasks': 0,
                        'failed_tasks': 0,
                        'start_time': None,
                        'end_time': None,
                        'processing_time': None
                    }

                    self.input_file = os.path.join(self.input_folder, novel_file)
                    self.log(f"开始处理: {novel_file}")
                    await self.process_novel()

                    await asyncio.sleep(5)

                except Exception as e:
                    self.log(f"处理文件 {novel_file} 时出错: {str(e)}")
                    continue

        except Exception as e:
            self.log(f"批量处理时出错: {str(e)}")
            raise


    def log_final_stats(self, output_file):
        stats_message = f"""
处理完成！
====================
文件: {os.path.basename(self.input_file)}
总段数: {self.stats['total_chapters']}
成功: {self.stats['successful_tasks']}
失败: {self.stats['failed_tasks']}
开始时间: {self.stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}
结束时间: {self.stats['end_time'].strftime('%Y-%m-%d %H:%M:%S')}
总处理时间: {self.stats['processing_time']:.2f} 秒
成功率: {(self.stats['successful_tasks']/self.stats['total_chapters']*100):.1f}%
平均每段处理时间: {(self.stats['processing_time']/self.stats['total_chapters']):.2f} 秒
====================
结果保存于: {output_file}
"""
        self.log(stats_message)

        with open(output_file, 'a', encoding='utf-8') as f:
            f.write("\n\n" + stats_message)



class QuestionProcessor(ProcessorBase):
    def __init__(self, api_key, api_base, input_file, output_prefix, max_concurrent=3):
        super().__init__()
        self.client = AsyncOpenAI(api_key=api_key, base_url=api_base)
        self.input_file = input_file
        self.output_prefix = output_prefix
        self.max_concurrent = max_concurrent
        self.output_format = "qa"  # 默认问答格式
        
        # 创建输出目录
        os.makedirs(os.path.dirname(output_prefix), exist_ok=True)
        
        self.setup_logging()

    def set_output_format(self, format_type):
        """设置输出格式"""
        self.output_format = format_type

    def setup_logging(self):
        """设置日志系统"""
        if not os.path.exists('logs'):
            os.makedirs('logs')
        log_filename = f'logs/question_processor_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
# core/text_processor.py (第四部分 - QuestionProcessor 继续)

    def read_questions(self):
        """读取问题文件"""
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip()]
        except Exception as e:
            self.log(f"读取问题文件时出错: {str(e)}")
            raise

    async def process_question(self, question: str, index: int) -> dict:
        """处理单个问题"""
        try:
            self.log(f"正在处理第 {index + 1} 个问题")
            start_time = time.time()
            
            response = await self.client.chat.completions.create(
                model=self.model,  # 使用 self.model
                messages=[
                    {"role": "user", "content": question}
                ]
            )
            
            processing_time = time.time() - start_time
            result = response.choices[0].message.content
            
            self.log(f"第 {index + 1} 个问题处理完成，用时 {processing_time:.2f} 秒")
            
            return {
                'question_index': index,
                'question': question,
                'answer': result,
                'processing_time': processing_time
            }
            
        except Exception as e:
            self.log(f"处理第 {index + 1} 个问题时出错: {str(e)}")
            return {
                'question_index': index,
                'question': question,
                'answer': f"Error: {str(e)}",
                'processing_time': 0
            }

    async def process_batch(self, questions_batch): # 不需要 model 参数
        tasks = []
        for i, question in questions_batch:
            if not self.running:
                break
            tasks.append(self.process_question(question, i))
        return await asyncio.gather(*tasks)

    def write_results(self, results: List[Dict], output_file: str):
        """写入处理结果"""
        try:
            with open(output_file, 'a', encoding='utf-8') as f:
                for result in results:
                    if self.output_format == "qa":
                        # 问答格式
                        f.write(f"\n问题 {result['question_index'] + 1}：{result['question']}\n")
                        f.write("-"*50 + "\n")
                        f.write(f"回答：{result['answer']}\n")
                        f.write("="*50 + "\n")
                    else:
                        # 仅答案格式
                        f.write(f"{result['answer']}\n")
                        f.write("-"*50 + "\n")
                        
        except Exception as e:
            self.log(f"写入结果时出错: {str(e)}")

    async def process_all_questions(self):
        """处理所有问题"""
        try:
            # 创建输出文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            output_file = f"{self.output_prefix}_{timestamp}_{unique_id}.txt"
            
            # 写入文件头部信息
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("批量问答处理结果\n")
                f.write(f"原文件: {os.path.basename(self.input_file)}\n")
                f.write(f"处理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("="*50 + "\n")

            # 读取所有问题
            questions = self.read_questions()
            total_questions = len(questions)
            self.log(f"共找到 {total_questions} 个问题")
            
            # 批量处理问题
            for i in range(0, total_questions, self.max_concurrent):
                if not self.running:
                    self.log("处理已停止")
                    break
                    
                batch = list(enumerate(questions[i:i + self.max_concurrent]))
                results = await self.process_batch(batch)
                
                # 写入结果
                self.write_results(results, output_file)
                
                # 更新进度
                progress = min(i + self.max_concurrent, total_questions)
                self.update_progress(progress, total_questions)
                
                # 批次间延迟
                if i + self.max_concurrent < total_questions:
                    await asyncio.sleep(1)
            
            self.log(f"处理完成！结果已保存至: {output_file}")
            
        except Exception as e:
            self.log(f"处理问题时出错: {str(e)}")
            raise

    def stop(self):
        """停止处理"""
        self.running = False
        self.log("正在停止处理...")
