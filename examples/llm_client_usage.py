#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM 客户端使用示例

本文件展示了如何使用统一的 LLM 客户端接口来支持不同的 LLM 提供商。
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.llm_client import LLMClient

def example_openai_usage():
    """OpenAI 使用示例"""
    print("=== OpenAI 使用示例 ===")
    
    # 方法1: 使用构造函数
    try:
        client = LLMClient(
            provider="openai",
            api_key="your-openai-api-key",
            model_name="gpt-4"
        )
        
        # 测试连接
        if client.test_connection():
            print("✅ OpenAI 连接成功")
            
            # 提取实体示例
            sample_text = "智能制造车间包含PLC控制器、HMI触摸屏和工业机器人等设备。"
            entities = client.extract_entities_from_text(sample_text)
            print(f"提取到 {len(entities)} 个实体")
            
        else:
            print("❌ OpenAI 连接失败")
            
    except Exception as e:
        print(f"OpenAI 客户端错误: {e}")
    
    # 方法2: 使用便捷方法
    try:
        client2 = LLMClient.create_openai_client(
            api_key="your-openai-api-key",
            model_name="gpt-3.5-turbo"
        )
        print(f"客户端信息: {client2.get_provider_info()}")
        
    except Exception as e:
        print(f"OpenAI 便捷方法错误: {e}")

def example_openai_compatible_usage():
    """OpenAI 兼容接口使用示例"""
    print("\n=== OpenAI 兼容接口使用示例 ===")
    
    try:
        # 使用自定义的 OpenAI 兼容接口
        client = LLMClient(
            provider="openai",
            api_key="your-api-key",
            model_name="gpt-3.5-turbo",
            base_url="https://your-custom-api.com/v1"  # 自定义接口地址
        )
        
        if client.test_connection():
            print("✅ 自定义 OpenAI 兼容接口连接成功")
        else:
            print("❌ 自定义 OpenAI 兼容接口连接失败")
            
    except Exception as e:
        print(f"自定义接口错误: {e}")

def example_ollama_usage():
    """Ollama 使用示例"""
    print("\n=== Ollama 使用示例 ===")
    
    # 方法1: 使用构造函数
    try:
        client = LLMClient(
            provider="ollama",
            model_name="llama2",
            base_url="http://localhost:11434"
        )
        
        # 测试连接
        if client.test_connection():
            print("✅ Ollama 连接成功")
            
            # 提取实体示例
            sample_text = "工程项目包含设计阶段、施工阶段和验收阶段。"
            entities = client.extract_entities_from_text(sample_text)
            print(f"提取到 {len(entities)} 个实体")
            
        else:
            print("❌ Ollama 连接失败 (请确保 Ollama 服务正在运行)")
            
    except Exception as e:
        print(f"Ollama 客户端错误: {e}")
    
    # 方法2: 使用便捷方法
    try:
        client2 = LLMClient.create_ollama_client(
            model_name="mistral",
            base_url="http://localhost:11434"
        )
        print(f"客户端信息: {client2.get_provider_info()}")
        
    except Exception as e:
        print(f"Ollama 便捷方法错误: {e}")

def example_entity_extraction():
    """实体提取完整示例"""
    print("\n=== 实体提取完整示例 ===")
    
    # 示例文档文本
    sample_document = """
    智能制造车间自动化系统设计项目位于上海市浦东新区。
    主要设备包括西门子S7-1500 PLC控制器、10寸触摸屏HMI、
    6轴工业机器人和AGV自动导航车。系统采用Profinet工业以太网通信协议，
    控制柜采用不锈钢材质，防护等级为IP65。
    项目负责人为张工程师，预计2024年6月完成。
    """
    
    # 尝试使用 Ollama (本地部署，无需 API Key)
    try:
        client = LLMClient.create_ollama_client(model_name="llama2")
        
        if client.test_connection():
            print("使用 Ollama 进行实体提取...")
            entities = client.extract_entities_from_text(sample_document)
            
            print(f"\n提取到 {len(entities)} 个实体:")
            for i, entity in enumerate(entities, 1):
                print(f"{i}. {entity.get('name', 'N/A')} - {entity.get('category', 'N/A')}")
                print(f"   描述: {entity.get('description', 'N/A')}")
                print()
        else:
            print("Ollama 服务未运行，跳过实体提取示例")
            
    except Exception as e:
        print(f"实体提取示例错误: {e}")

def example_provider_comparison():
    """提供商对比示例"""
    print("\n=== 提供商对比 ===")
    
    providers_config = [
        {
            "name": "OpenAI GPT-4",
            "provider": "openai",
            "model": "gpt-4",
            "api_key": "your-openai-api-key",
            "pros": ["高质量输出", "强大的理解能力", "稳定的服务"],
            "cons": ["需要 API Key", "按使用量付费", "需要网络连接"]
        },
        {
            "name": "Ollama Llama2",
            "provider": "ollama",
            "model": "llama2",
            "api_key": None,
            "pros": ["本地部署", "免费使用", "数据隐私", "离线可用"],
            "cons": ["需要本地安装", "硬件要求高", "输出质量可能较低"]
        }
    ]
    
    for config in providers_config:
        print(f"\n{config['name']}:")
        print(f"  优点: {', '.join(config['pros'])}")
        print(f"  缺点: {', '.join(config['cons'])}")
        
        try:
            if config['provider'] == 'openai':
                client = LLMClient.create_openai_client(
                    api_key=config['api_key'],
                    model_name=config['model']
                )
            else:
                client = LLMClient.create_ollama_client(
                    model_name=config['model']
                )
            
            if client.test_connection():
                print(f"  状态: ✅ 可用")
            else:
                print(f"  状态: ❌ 不可用")
                
        except Exception as e:
            print(f"  状态: ❌ 错误 - {e}")

def main():
    """主函数"""
    print("LLM 客户端统一接口使用示例\n")
    
    # 运行各种示例
    example_openai_usage()
    example_openai_compatible_usage()
    example_ollama_usage()
    example_entity_extraction()
    example_provider_comparison()
    
    print("\n=== 使用建议 ===")
    print("1. 开发和测试阶段推荐使用 Ollama (免费、本地)")
    print("2. 生产环境推荐使用 OpenAI GPT-4 (质量更高)")
    print("3. 企业内部部署可考虑 OpenAI 兼容接口")
    print("4. 对数据隐私要求高的场景使用 Ollama")

if __name__ == "__main__":
    main()