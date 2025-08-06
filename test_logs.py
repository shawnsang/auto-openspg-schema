#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试日志功能的示例脚本
"""

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.logger import logger
from src.document_processor import DocumentProcessor
from src.llm_client import LLMClient
from src.schema_generator import SchemaGenerator

def test_document_processing():
    """测试文档处理的日志功能"""
    logger.info("=== 开始测试文档处理日志功能 ===")
    
    # 测试文档处理器
    logger.info("初始化文档处理器")
    doc_processor = DocumentProcessor(chunk_size=1000, chunk_overlap=200)
    
    # 测试处理示例文档
    test_file = "example_document.txt"
    if os.path.exists(test_file):
        logger.info(f"处理测试文档: {test_file}")
        try:
            chunks = doc_processor.process_document(test_file)
            logger.success(f"文档处理成功，生成 {len(chunks)} 个分块")
        except Exception as e:
            logger.error(f"文档处理失败: {e}")
    else:
        logger.warning(f"测试文档 {test_file} 不存在")

def test_llm_client_logs():
    """测试LLM客户端日志功能（仅模拟，不实际调用）"""
    logger.info("=== 开始测试LLM客户端日志功能 ===")
    
    # 模拟创建LLM客户端
    logger.info("模拟创建Ollama客户端")
    try:
        # 这里只是演示日志，不实际创建客户端
        logger.debug("配置参数: provider=ollama, model=qwen:7b")
        logger.info("LLM客户端配置完成")
        
        # 模拟提示词日志
        test_prompt = "请从以下文本中提取实体信息：工程设计文档示例"
        logger.info(f"模拟提示词: {test_prompt}")
        logger.debug("这是一个模拟的LLM调用，用于测试日志功能")
        
    except Exception as e:
        logger.error(f"LLM客户端测试失败: {e}")

def test_schema_generator_logs():
    """测试Schema生成器日志功能"""
    logger.info("=== 开始测试Schema生成器日志功能 ===")
    
    # 模拟Schema生成过程
    logger.info("模拟Schema生成过程")
    logger.debug("输入文档块数量: 3")
    logger.debug("开始实体提取和标准化")
    
    # 模拟实体处理
    mock_entities = ["工程概念", "设备组件", "技术规范"]
    for i, entity in enumerate(mock_entities):
        logger.debug(f"处理实体 {i+1}/{len(mock_entities)}: {entity}")
        logger.info(f"实体 {entity} 标准化完成")
    
    logger.success(f"Schema生成完成，处理了 {len(mock_entities)} 个实体")

def test_different_log_levels():
    """测试不同级别的日志输出"""
    logger.info("=== 测试不同级别的日志输出 ===")
    
    logger.debug("这是一条DEBUG级别的日志 - 用于调试信息")
    logger.info("这是一条INFO级别的日志 - 用于一般信息")
    logger.success("这是一条SUCCESS级别的日志 - 用于成功操作")
    logger.warning("这是一条WARNING级别的日志 - 用于警告信息")
    logger.error("这是一条ERROR级别的日志 - 用于错误信息")
    
    # 测试异常日志
    try:
        raise ValueError("这是一个测试异常")
    except Exception as e:
        logger.error(f"捕获到异常: {e}", exc_info=True)

def main():
    """主测试函数"""
    logger.info("🚀 开始日志功能测试")
    
    test_different_log_levels()
    test_document_processing()
    test_llm_client_logs()
    test_schema_generator_logs()
    
    logger.success("✅ 日志功能测试完成")
    logger.info("请检查控制台输出和 logs/ 目录中的日志文件")

if __name__ == "__main__":
    main()