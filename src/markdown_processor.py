#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown文档处理模块

支持基于Markdown语义结构的智能分块处理，特别优化表格处理。
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import chardet

# 导入日志
from .logger import logger

# Markdown处理库
try:
    import markdown
    from markdown.extensions import tables, toc
    logger.success("markdown 库加载成功")
except ImportError:
    markdown = None
    logger.warning("markdown 库未安装，Markdown 处理功能不可用")

try:
    from markdown_it import MarkdownIt
    from markdown_it.tree import SyntaxTreeNode
    logger.success("markdown-it-py 库加载成功")
except ImportError:
    MarkdownIt = None
    logger.warning("markdown-it-py 库未安装，高级 Markdown 解析功能不可用")


class MarkdownChunk:
    """Markdown分块数据结构"""
    
    def __init__(self, content: str, chunk_type: str, level: int = 0, 
                 metadata: Optional[Dict[str, Any]] = None):
        self.content = content.strip()
        self.chunk_type = chunk_type  # 'heading', 'paragraph', 'table', 'list', 'code', 'mixed'
        self.level = level  # 标题级别或嵌套级别
        self.metadata = metadata or {}
        self.char_count = len(self.content)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'content': self.content,
            'chunk_type': self.chunk_type,
            'level': self.level,
            'char_count': self.char_count,
            'metadata': self.metadata
        }


class MarkdownProcessor:
    """Markdown文档处理器，支持语义分块和表格优化"""
    
    def __init__(self, chunk_size: int = 1500, chunk_overlap: int = 200, 
                 preserve_tables: bool = True):
        """
        初始化Markdown处理器
        
        Args:
            chunk_size: 目标分块大小
            chunk_overlap: 分块重叠大小
            preserve_tables: 是否保持表格完整性
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.preserve_tables = preserve_tables
        logger.info(f"Markdown处理器初始化完成 - 分块大小: {chunk_size}, 保持表格完整: {preserve_tables}")
    
    def process_markdown_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        处理Markdown文件，返回语义分块结果
        
        Args:
            file_path: Markdown文件路径
            
        Returns:
            List[Dict]: 分块结果列表
        """
        logger.info(f"开始处理Markdown文件: {file_path}")
        
        try:
            # 读取文件内容
            content = self._read_markdown_file(file_path)
            logger.success(f"文件读取完成，原始长度: {len(content)} 字符")
            
            # 解析Markdown结构
            chunks = self._parse_markdown_structure(content)
            logger.success(f"Markdown结构解析完成，识别到 {len(chunks)} 个语义块")
            
            # 优化分块大小
            optimized_chunks = self._optimize_chunk_sizes(chunks)
            logger.success(f"分块优化完成，最终生成 {len(optimized_chunks)} 个分块")
            
            # 转换为标准格式
            results = []
            for i, chunk in enumerate(optimized_chunks):
                result = chunk.to_dict()
                result.update({
                    'chunk_id': i,
                    'source_file': Path(file_path).name,
                    'file_type': 'markdown'
                })
                results.append(result)
                logger.debug(f"分块 {i+1} ({chunk.chunk_type}): {chunk.char_count} 字符")
            
            # 统计信息
            self._log_chunk_statistics(optimized_chunks)
            
            return results
            
        except Exception as e:
            logger.error(f"处理Markdown文件时发生错误: {str(e)}")
            raise
    
    def _read_markdown_file(self, file_path: str) -> str:
        """读取Markdown文件内容"""
        try:
            # 检测文件编码
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                encoding_result = chardet.detect(raw_data)
                encoding = encoding_result.get('encoding', 'utf-8')
            
            logger.debug(f"检测到文件编码: {encoding}")
            
            # 读取文件内容
            with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                content = f.read()
            
            return content
            
        except Exception as e:
            logger.error(f"读取Markdown文件失败: {str(e)}")
            raise
    
    def _parse_markdown_structure(self, content: str) -> List[MarkdownChunk]:
        """解析Markdown结构，识别不同类型的内容块"""
        logger.debug("开始解析Markdown结构")
        
        chunks = []
        lines = content.split('\n')
        current_block = []
        current_type = None
        current_level = 0
        in_table = False
        in_code_block = False
        code_fence = None
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped_line = line.strip()
            
            # 处理代码块
            if stripped_line.startswith('```') or stripped_line.startswith('~~~'):
                if not in_code_block:
                    # 开始代码块
                    if current_block:
                        chunks.append(self._create_chunk(current_block, current_type, current_level))
                        current_block = []
                    
                    in_code_block = True
                    code_fence = stripped_line[:3]
                    current_type = 'code'
                    current_block = [line]
                else:
                    # 结束代码块
                    if stripped_line.startswith(code_fence):
                        current_block.append(line)
                        chunks.append(self._create_chunk(current_block, current_type, current_level))
                        current_block = []
                        in_code_block = False
                        code_fence = None
                        current_type = None
                    else:
                        current_block.append(line)
                i += 1
                continue
            
            # 在代码块内部，直接添加行
            if in_code_block:
                current_block.append(line)
                i += 1
                continue
            
            # 检测表格
            if self._is_table_row(line) or (stripped_line and '|' in stripped_line):
                if not in_table:
                    # 开始表格
                    if current_block:
                        chunks.append(self._create_chunk(current_block, current_type, current_level))
                        current_block = []
                    
                    in_table = True
                    current_type = 'table'
                    
                    # 检查是否有表格标题（前一行）
                    if i > 0 and lines[i-1].strip() and not self._is_table_row(lines[i-1]):
                        # 可能的表格标题
                        table_title = lines[i-1].strip()
                        if not table_title.startswith('#'):
                            current_block = [lines[i-1], line]
                        else:
                            current_block = [line]
                    else:
                        current_block = [line]
                else:
                    current_block.append(line)
                i += 1
                continue
            
            # 表格结束检测
            if in_table and (not stripped_line or not ('|' in stripped_line)):
                # 表格结束
                if current_block:
                    chunks.append(self._create_chunk(current_block, current_type, current_level))
                    current_block = []
                in_table = False
                current_type = None
                
                # 处理当前行（如果不是空行）
                if stripped_line:
                    i -= 1  # 回退一行，重新处理
                i += 1
                continue
            
            # 检测标题
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', stripped_line)
            if heading_match:
                # 保存之前的块
                if current_block:
                    chunks.append(self._create_chunk(current_block, current_type, current_level))
                    current_block = []
                
                # 创建标题块
                level = len(heading_match.group(1))
                chunks.append(MarkdownChunk(
                    content=line,
                    chunk_type='heading',
                    level=level,
                    metadata={'title': heading_match.group(2)}
                ))
                current_type = 'paragraph'  # 标题后通常是段落
                current_level = 0
                i += 1
                continue
            
            # 检测列表
            if re.match(r'^\s*[-*+]\s+', line) or re.match(r'^\s*\d+\.\s+', line):
                if current_type != 'list':
                    if current_block:
                        chunks.append(self._create_chunk(current_block, current_type, current_level))
                        current_block = []
                    current_type = 'list'
                current_block.append(line)
                i += 1
                continue
            
            # 空行处理
            if not stripped_line:
                if current_block and current_type:
                    # 空行可能表示块的结束
                    if current_type in ['paragraph', 'list']:
                        # 检查下一个非空行
                        next_non_empty = self._find_next_non_empty_line(lines, i + 1)
                        if next_non_empty and (self._is_new_block_start(lines[next_non_empty])):
                            # 结束当前块
                            chunks.append(self._create_chunk(current_block, current_type, current_level))
                            current_block = []
                            current_type = None
                        else:
                            # 保留空行
                            current_block.append(line)
                    else:
                        current_block.append(line)
                i += 1
                continue
            
            # 普通文本行
            if current_type is None:
                current_type = 'paragraph'
            current_block.append(line)
            i += 1
        
        # 处理最后的块
        if current_block:
            chunks.append(self._create_chunk(current_block, current_type, current_level))
        
        logger.debug(f"解析完成，识别到 {len(chunks)} 个语义块")
        return chunks
    
    def _is_table_row(self, line: str) -> bool:
        """检测是否为表格行"""
        stripped = line.strip()
        if not stripped:
            return False
        
        # 检测表格分隔符行 (如: |---|---|---| 或 |:---|:---:|---:|)
        if re.match(r'^\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?$', stripped):
            return True
        
        # 检测普通表格行（包含管道符）
        if '|' in stripped and stripped.count('|') >= 2:
            return True
        
        return False
    
    def _find_next_non_empty_line(self, lines: List[str], start_index: int) -> Optional[int]:
        """查找下一个非空行的索引"""
        for i in range(start_index, len(lines)):
            if lines[i].strip():
                return i
        return None
    
    def _is_new_block_start(self, line: str) -> bool:
        """检测是否为新块的开始"""
        stripped = line.strip()
        
        # 标题
        if re.match(r'^#{1,6}\s+', stripped):
            return True
        
        # 列表
        if re.match(r'^\s*[-*+]\s+', line) or re.match(r'^\s*\d+\.\s+', line):
            return True
        
        # 代码块
        if stripped.startswith('```') or stripped.startswith('~~~'):
            return True
        
        # 表格
        if self._is_table_row(line):
            return True
        
        return False
    
    def _create_chunk(self, lines: List[str], chunk_type: str, level: int) -> MarkdownChunk:
        """创建分块对象"""
        content = '\n'.join(lines)
        metadata = {}
        
        if chunk_type == 'table':
            metadata['table_info'] = self._analyze_table(lines)
        elif chunk_type == 'list':
            metadata['list_info'] = self._analyze_list(lines)
        
        return MarkdownChunk(
            content=content,
            chunk_type=chunk_type or 'paragraph',
            level=level,
            metadata=metadata
        )
    
    def _analyze_table(self, lines: List[str]) -> Dict[str, Any]:
        """分析表格结构"""
        table_lines = [line for line in lines if line.strip()]
        if not table_lines:
            return {}
        
        # 查找表头和分隔符
        header_row = None
        separator_row = None
        data_rows = []
        
        for i, line in enumerate(table_lines):
            if self._is_table_row(line):
                if re.match(r'^\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?$', line.strip()):
                    separator_row = i
                    if i > 0:
                        header_row = i - 1
                else:
                    if separator_row is not None and i > separator_row:
                        data_rows.append(i)
                    elif separator_row is None:
                        data_rows.append(i)
        
        # 计算列数
        column_count = 0
        if header_row is not None:
            column_count = table_lines[header_row].count('|') - 1
            if not table_lines[header_row].strip().startswith('|'):
                column_count += 1
        
        return {
            'row_count': len(data_rows) + (1 if header_row is not None else 0),
            'column_count': column_count,
            'has_header': header_row is not None,
            'data_row_count': len(data_rows)
        }
    
    def _analyze_list(self, lines: List[str]) -> Dict[str, Any]:
        """分析列表结构"""
        list_items = []
        for line in lines:
            if re.match(r'^\s*[-*+]\s+', line) or re.match(r'^\s*\d+\.\s+', line):
                list_items.append(line.strip())
        
        return {
            'item_count': len(list_items),
            'is_ordered': any(re.match(r'^\s*\d+\.\s+', line) for line in lines)
        }
    
    def _optimize_chunk_sizes(self, chunks: List[MarkdownChunk]) -> List[MarkdownChunk]:
        """优化分块大小，实现智能拆分和合并"""
        logger.debug("开始优化分块大小")
        
        optimized_chunks = []
        current_group = []
        current_size = 0
        
        for chunk in chunks:
            # 表格特殊处理：如果启用了表格保护，表格不拆分
            if chunk.chunk_type == 'table' and self.preserve_tables:
                # 先处理当前组
                if current_group:
                    optimized_chunks.extend(self._finalize_chunk_group(current_group))
                    current_group = []
                    current_size = 0
                
                # 表格单独处理
                if chunk.char_count > self.chunk_size:
                    logger.info(f"表格大小 {chunk.char_count} 超过限制 {self.chunk_size}，但保持完整")
                
                optimized_chunks.append(chunk)
                continue
            
            # 检查是否可以添加到当前组
            if current_size + chunk.char_count <= self.chunk_size:
                current_group.append(chunk)
                current_size += chunk.char_count
            else:
                # 当前组已满，处理并开始新组
                if current_group:
                    optimized_chunks.extend(self._finalize_chunk_group(current_group))
                
                # 检查当前块是否需要拆分
                if chunk.char_count > self.chunk_size:
                    optimized_chunks.extend(self._split_large_chunk(chunk))
                    current_group = []
                    current_size = 0
                else:
                    current_group = [chunk]
                    current_size = chunk.char_count
        
        # 处理最后的组
        if current_group:
            optimized_chunks.extend(self._finalize_chunk_group(current_group))
        
        logger.debug(f"分块优化完成，从 {len(chunks)} 个块优化为 {len(optimized_chunks)} 个块")
        return optimized_chunks
    
    def _finalize_chunk_group(self, group: List[MarkdownChunk]) -> List[MarkdownChunk]:
        """完成分块组的处理"""
        if len(group) == 1:
            return group
        
        # 合并多个小块
        combined_content = '\n\n'.join(chunk.content for chunk in group)
        combined_metadata = {
            'combined_chunks': len(group),
            'original_types': [chunk.chunk_type for chunk in group]
        }
        
        return [MarkdownChunk(
            content=combined_content,
            chunk_type='mixed',
            level=0,
            metadata=combined_metadata
        )]
    
    def _split_large_chunk(self, chunk: MarkdownChunk) -> List[MarkdownChunk]:
        """拆分过大的块，使用平均分割策略"""
        logger.debug(f"拆分大块: {chunk.char_count} 字符 ({chunk.chunk_type})")
        
        # 计算需要拆分的数量
        split_count = (chunk.char_count + self.chunk_size - 1) // self.chunk_size
        target_size = chunk.char_count // split_count
        
        logger.debug(f"目标拆分为 {split_count} 个块，每块约 {target_size} 字符")
        
        # 按行拆分
        lines = chunk.content.split('\n')
        sub_chunks = []
        current_lines = []
        current_size = 0
        
        for line in lines:
            line_size = len(line) + 1  # +1 for newline
            
            if current_size + line_size > target_size and current_lines:
                # 创建子块
                sub_content = '\n'.join(current_lines)
                sub_chunks.append(MarkdownChunk(
                    content=sub_content,
                    chunk_type=chunk.chunk_type,
                    level=chunk.level,
                    metadata={**chunk.metadata, 'split_part': len(sub_chunks) + 1}
                ))
                current_lines = [line]
                current_size = line_size
            else:
                current_lines.append(line)
                current_size += line_size
        
        # 处理最后的行
        if current_lines:
            sub_content = '\n'.join(current_lines)
            sub_chunks.append(MarkdownChunk(
                content=sub_content,
                chunk_type=chunk.chunk_type,
                level=chunk.level,
                metadata={**chunk.metadata, 'split_part': len(sub_chunks) + 1}
            ))
        
        logger.debug(f"大块拆分完成，生成 {len(sub_chunks)} 个子块")
        return sub_chunks
    
    def _log_chunk_statistics(self, chunks: List[MarkdownChunk]):
        """记录分块统计信息"""
        if not chunks:
            return
        
        # 按类型统计
        type_counts = {}
        type_sizes = {}
        
        for chunk in chunks:
            chunk_type = chunk.chunk_type
            type_counts[chunk_type] = type_counts.get(chunk_type, 0) + 1
            if chunk_type not in type_sizes:
                type_sizes[chunk_type] = []
            type_sizes[chunk_type].append(chunk.char_count)
        
        # 总体统计
        total_chars = sum(chunk.char_count for chunk in chunks)
        avg_size = total_chars / len(chunks)
        min_size = min(chunk.char_count for chunk in chunks)
        max_size = max(chunk.char_count for chunk in chunks)
        
        logger.info(f"分块统计 - 总数: {len(chunks)}, 平均: {avg_size:.0f}, 最小: {min_size}, 最大: {max_size} 字符")
        
        # 按类型统计
        for chunk_type, count in type_counts.items():
            sizes = type_sizes[chunk_type]
            avg_type_size = sum(sizes) / len(sizes)
            logger.info(f"  {chunk_type}: {count} 个, 平均 {avg_type_size:.0f} 字符")
    
    def get_supported_extensions(self) -> List[str]:
        """获取支持的文件扩展名"""
        return ['.md', '.markdown', '.mdown', '.mkd']
    
    def is_markdown_file(self, file_path: str) -> bool:
        """检查是否为Markdown文件"""
        ext = Path(file_path).suffix.lower()
        return ext in self.get_supported_extensions()