import streamlit as st
import os
from typing import List, Dict, Any
import json
from datetime import datetime

# 导入自定义模块
from src.document_processor import DocumentProcessor
from src.schema_generator import SchemaGenerator
from src.schema_manager import SchemaManager
from src.llm_client import LLMClient
from src.logger import logger

def main():
    st.set_page_config(
        page_title="OpenSPG Schema 自动生成器",
        page_icon="🔗",
        layout="wide"
    )
    
    st.title("🔗 OpenSPG Schema 自动生成器")
    st.markdown("---")
    
    # 侧边栏配置
    with st.sidebar:
        st.header("⚙️ 配置")
        
        # LLM 配置
        st.subheader("LLM 设置")
        
        # LLM 提供商选择
        provider = st.selectbox(
            "LLM 提供商",
            ["OpenAI", "Ollama"],
            help="选择要使用的 LLM 服务提供商"
        )
        
        if provider == "OpenAI":
            api_key = st.text_input("OpenAI API Key", type="password")
            base_url = st.text_input(
                "Base URL (可选)", 
                placeholder="https://api.openai.com/v1",
                help="自定义 OpenAI 兼容接口的 URL"
            )
            model_name = st.text_input(
                "模型名称",
                value="gpt-4",
                help="输入模型名称，如 gpt-4, gpt-3.5-turbo, claude-3-sonnet 等"
            )
        else:  # Ollama
            api_key = None
            base_url = st.text_input(
                "Ollama URL", 
                value="http://localhost:11434",
                help="Ollama 服务的 URL 地址"
            )
            model_name = st.text_input(
                "模型名称",
                value="llama2",
                help="Ollama 中的模型名称，如 llama2, mistral 等"
            )
        
        # 文档处理配置
        st.subheader("文档处理设置")
        chunk_size = st.slider("文档分块大小", 500, 3000, 1500)
        chunk_overlap = st.slider("分块重叠大小", 50, 500, 200)
        
        # Schema 配置
        st.subheader("Schema 设置")
        namespace = st.text_input("命名空间", value="Engineering")
    
    # 主界面
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("📄 文档上传")
        uploaded_files = st.file_uploader(
            "选择文档文件",
            type=["pdf", "docx", "txt"],
            accept_multiple_files=True
        )
        
        if uploaded_files:
            st.success(f"已上传 {len(uploaded_files)} 个文件")
            for file in uploaded_files:
                st.write(f"- {file.name} ({file.size} bytes)")
    
    with col2:
        st.header("🎯 当前 Schema")
        
        # 初始化 session state
        if 'schema_manager' not in st.session_state:
            st.session_state.schema_manager = SchemaManager(namespace)
        
        if 'processing_results' not in st.session_state:
            st.session_state.processing_results = []
        
        # 显示当前 schema 统计
        stats = st.session_state.schema_manager.get_statistics()
        col2_1, col2_2, col2_3 = st.columns(3)
        with col2_1:
            st.metric("实体类型", stats['entity_count'])
        with col2_2:
            st.metric("属性总数", stats['property_count'])
        with col2_3:
            st.metric("已处理文档", len(st.session_state.processing_results))
    
    # 处理按钮
    st.markdown("---")
    
    # 检查必要条件
    can_process = uploaded_files and (provider == "Ollama" or api_key)
    
    if st.button("🚀 开始处理文档", type="primary", disabled=not can_process):
        if provider == "OpenAI" and not api_key:
            st.error("请提供 OpenAI API Key")
        elif not uploaded_files:
            st.error("请上传至少一个文档")
        else:
            process_documents(
                uploaded_files, provider.lower(), api_key, model_name, base_url,
                chunk_size, chunk_overlap, namespace
            )
    
    # 显示处理结果
    if st.session_state.processing_results:
        st.header("📊 处理结果")
        
        for i, result in enumerate(st.session_state.processing_results):
            with st.expander(f"文档 {i+1}: {result['filename']} - {result['timestamp']}"):
                col_r1, col_r2, col_r3 = st.columns(3)
                
                with col_r1:
                    st.metric("新增实体", result['stats']['new_entities'])
                with col_r2:
                    st.metric("修改实体", result['stats']['modified_entities'])
                with col_r3:
                    st.metric("建议删除", len(result['stats']['suggested_deletions']))
                
                if result['stats']['suggested_deletions']:
                    st.subheader("建议删除的实体:")
                    for deletion in result['stats']['suggested_deletions']:
                        st.warning(f"**{deletion['entity']}**: {deletion['reason']}")
    
    # Schema 预览和下载
    st.markdown("---")
    st.header("📋 Schema 预览")
    
    col_s1, col_s2 = st.columns([3, 1])
    
    with col_s1:
        schema_content = st.session_state.schema_manager.generate_schema_string()
        st.code(schema_content, language="text")
    
    with col_s2:
        st.subheader("操作")
        
        # 复制按钮
        if st.button("📋 复制 Schema"):
            st.code(schema_content)
            st.success("Schema 已显示，请手动复制")
        
        # 下载按钮
        st.download_button(
            label="💾 下载 Schema",
            data=schema_content,
            file_name=f"{namespace}_schema_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain"
        )
        
        # 清空按钮
        if st.button("🗑️ 清空 Schema", type="secondary"):
            st.session_state.schema_manager = SchemaManager(namespace)
            st.session_state.processing_results = []
            st.rerun()

def process_documents(uploaded_files, provider, api_key, model_name, base_url, chunk_size, chunk_overlap, namespace):
    """处理上传的文档"""
    logger.info(f"开始处理文档批次，共 {len(uploaded_files)} 个文件")
    logger.info(f"配置参数 - 提供商: {provider}, 模型: {model_name}, 分块大小: {chunk_size}, 重叠: {chunk_overlap}")
    
    # 初始化组件
    try:
        logger.debug("初始化 LLM 客户端")
        llm_client = LLMClient(
            provider=provider,
            api_key=api_key,
            model_name=model_name,
            base_url=base_url if base_url else None
        )
        
        # 测试连接
        logger.debug(f"测试 {provider} 连接")
        if not llm_client.test_connection():
            error_msg = f"无法连接到 {provider} 服务，请检查配置"
            logger.error(error_msg)
            st.error(error_msg)
            return
        
        success_msg = f"✅ 成功连接到 {provider} ({model_name})"
        logger.success(success_msg)
        st.success(success_msg)
        
    except Exception as e:
        error_msg = f"LLM 客户端初始化失败: {str(e)}"
        logger.error(error_msg)
        st.error(error_msg)
        return
    
    logger.debug("初始化文档处理器和Schema生成器")
    doc_processor = DocumentProcessor(chunk_size, chunk_overlap)
    schema_generator = SchemaGenerator(llm_client)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, uploaded_file in enumerate(uploaded_files):
        file_progress = (i + 1) / len(uploaded_files)
        logger.info(f"处理文件 {i+1}/{len(uploaded_files)}: {uploaded_file.name} ({uploaded_file.size} 字节)")
        status_text.text(f"正在处理: {uploaded_file.name}")
        
        try:
            # 保存临时文件
            temp_path = f"temp_{uploaded_file.name}"
            logger.debug(f"保存临时文件: {temp_path}")
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # 处理文档
            logger.info(f"开始处理文档: {uploaded_file.name}")
            chunks = doc_processor.process_document(temp_path)
            logger.success(f"文档处理完成，生成 {len(chunks)} 个分块")
            
            # 生成 schema
            logger.info(f"开始从 {len(chunks)} 个分块中提取实体")
            new_entities = 0
            modified_entities = 0
            suggested_deletions = []
            
            for chunk_idx, chunk in enumerate(chunks):
                logger.debug(f"处理分块 {chunk_idx + 1}/{len(chunks)} ({len(chunk)} 字符)")
                entities = schema_generator.extract_entities_from_chunk(chunk)
                logger.debug(f"从分块 {chunk_idx + 1} 提取到 {len(entities)} 个实体")
                
                for entity in entities:
                    logger.debug(f"处理实体: {entity['name']}")
                    result = st.session_state.schema_manager.add_or_update_entity(
                        entity['name'], entity['description'], entity.get('properties', {})
                    )
                    
                    if result['action'] == 'created':
                        new_entities += 1
                        logger.info(f"创建新实体: {entity['name']}")
                    elif result['action'] == 'updated':
                        modified_entities += 1
                        logger.info(f"更新实体: {entity['name']}")
                    else:
                        logger.debug(f"实体无变化: {entity['name']}")
                
                # 更新进度
                chunk_progress = (chunk_idx + 1) / len(chunks)
                overall_progress = (i + chunk_progress) / len(uploaded_files)
                progress_bar.progress(overall_progress)
            
            # 检查建议删除的实体
            logger.debug("检查建议删除的实体")
            suggested_deletions = schema_generator.suggest_entity_deletions(
                st.session_state.schema_manager.get_all_entities(),
                chunks
            )
            logger.info(f"建议删除 {len(suggested_deletions)} 个实体")
            
            # 记录处理结果
            result = {
                'filename': uploaded_file.name,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'stats': {
                    'new_entities': new_entities,
                    'modified_entities': modified_entities,
                    'suggested_deletions': suggested_deletions
                }
            }
            
            st.session_state.processing_results.append(result)
            logger.success(f"文件 {uploaded_file.name} 处理完成 - 新增: {new_entities}, 修改: {modified_entities}, 建议删除: {len(suggested_deletions)}")
            
            # 清理临时文件
            logger.debug(f"清理临时文件: {temp_path}")
            os.remove(temp_path)
            
        except Exception as e:
            error_msg = f"处理文档 {uploaded_file.name} 时出错: {str(e)}"
            logger.error(error_msg, exc_info=True)
            st.error(error_msg)
            
            # 清理可能存在的临时文件
            temp_path = f"temp_{uploaded_file.name}"
            if os.path.exists(temp_path):
                logger.debug(f"清理错误处理中的临时文件: {temp_path}")
                os.remove(temp_path)
        
        # 更新进度
        progress_bar.progress((i + 1) / len(uploaded_files))
    
    # 处理完成总结
    total_files = len(uploaded_files)
    successful_files = len([r for r in st.session_state.processing_results if 'stats' in r])
    failed_files = total_files - successful_files
    
    logger.success(f"文档批次处理完成 - 总计: {total_files}, 成功: {successful_files}, 失败: {failed_files}")
    
    if st.session_state.processing_results:
        total_new = sum(r.get('stats', {}).get('new_entities', 0) for r in st.session_state.processing_results)
        total_modified = sum(r.get('stats', {}).get('modified_entities', 0) for r in st.session_state.processing_results)
        logger.info(f"实体统计 - 新增: {total_new}, 修改: {total_modified}")
    
    progress_bar.progress(1.0)
    status_text.text("处理完成！")
    
    status_text.text("处理完成!")
    st.success(f"成功处理 {len(uploaded_files)} 个文档")
    st.rerun()

if __name__ == "__main__":
    main()