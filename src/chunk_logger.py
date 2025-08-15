#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分块和LLM响应专用日志记录器
"""

import os
import logging
from datetime import datetime
from pathlib import Path

class ChunkLogger:
    """专门记录分块内容和LLM响应的日志器"""
    
    def __init__(self, log_dir: str = "chunk_logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # 创建日志文件名（按日期）
        today = datetime.now().strftime('%Y%m%d')
        self.log_file = self.log_dir / f"chunk_processing_{today}.log"
        
        # 配置日志器
        self.logger = logging.getLogger('chunk_processor')
        self.logger.setLevel(logging.INFO)
        
        # 避免重复添加handler
        if not self.logger.handlers:
            # 文件处理器
            file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            
            # 格式化器
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            
            self.logger.addHandler(file_handler)
    
    def log_chunk_start(self, filename: str, chunk_index: int, total_chunks: int):
        """记录分块处理开始"""
        separator = "=" * 80
        self.logger.info(f"\n{separator}")
        self.logger.info(f"开始处理分块 - 文件: {filename} | 分块: {chunk_index + 1}/{total_chunks}")
        self.logger.info(f"{separator}")
    
    def log_chunk_content(self, chunk_content: str, chunk_index: int):
        """记录分块内容"""
        self.logger.info(f"\n【分块 {chunk_index + 1} 内容】")
        self.logger.info(f"长度: {len(chunk_content)} 字符")
        self.logger.info(f"内容:\n{chunk_content}")
        self.logger.info(f"{'─' * 60}")
    
    def log_llm_response(self, llm_response: str, chunk_index: int):
        """记录LLM响应内容"""
        self.logger.info(f"\n【分块 {chunk_index + 1} LLM响应】")
        self.logger.info(f"长度: {len(llm_response)} 字符")
        self.logger.info(f"响应:\n{llm_response}")
        self.logger.info(f"{'─' * 60}")
    
    def log_chunk_complete(self, chunk_index: int, processing_time: float = None):
        """记录分块处理完成"""
        if processing_time:
            self.logger.info(f"分块 {chunk_index + 1} 处理完成 - 耗时: {processing_time:.2f}秒")
        else:
            self.logger.info(f"分块 {chunk_index + 1} 处理完成")
        self.logger.info(f"{'=' * 80}\n")
    
    def log_file_complete(self, filename: str, total_chunks: int, total_time: float = None):
        """记录文件处理完成"""
        separator = "*" * 100
        self.logger.info(f"\n{separator}")
        if total_time:
            self.logger.info(f"文件处理完成 - {filename} | 总分块数: {total_chunks} | 总耗时: {total_time:.2f}秒")
        else:
            self.logger.info(f"文件处理完成 - {filename} | 总分块数: {total_chunks}")
        self.logger.info(f"{separator}\n")
    
    def get_log_file_path(self) -> str:
        """获取日志文件路径"""
        return str(self.log_file)