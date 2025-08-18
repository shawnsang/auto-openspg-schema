import streamlit as st
import os
from typing import List, Dict, Any
import json
from datetime import datetime
import time
import zipfile
import shutil

from src.document_processor import DocumentProcessor
from src.schema_generator import SchemaGenerator
from src.schema_manager import SchemaManager
from src.llm_client import LLMClient
from src.logger import logger
from src.chunk_logger import ChunkLogger

def create_zip_archive(source_dirs: List[str], zip_filename: str) -> str:
    """创建包含多个目录的zip压缩包
    
    Args:
        source_dirs: 要压缩的目录列表
        zip_filename: 输出的zip文件名
        
    Returns:
        str: 创建的zip文件路径
    """
    try:
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for source_dir in source_dirs:
                if os.path.exists(source_dir):
                    # 获取目录名作为zip内的根目录
                    dir_name = os.path.basename(source_dir)
                    
                    # 遍历目录中的所有文件
                    for root, dirs, files in os.walk(source_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            # 计算在zip中的相对路径
                            arcname = os.path.join(dir_name, os.path.relpath(file_path, source_dir))
                            zipf.write(file_path, arcname)
                            
        logger.info(f"成功创建zip文件: {zip_filename}")
        return zip_filename
    except Exception as e:
        logger.error(f"创建zip文件失败: {str(e)}")
        raise

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
        
        # 专业领域设置
        domain_expertise = st.text_input(
            "专业领域",
            value="",
            placeholder="例如：隧道防排水工程、建筑结构设计、机械制造等",
            help="指定专业领域以提高Schema的专业识别能力，留空则使用通用设置"
        )
        
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
        chunk_size = st.slider("文档分块大小", 200, 1000, 500)
        chunk_overlap = st.slider("分块重叠大小", 20, 100, 50)
        
        # Markdown 处理选项
        enable_markdown_semantic = st.checkbox(
            "启用 Markdown 语义分块",
            value=True,
            help="对 Markdown 文档进行语义分块，保持表格完整性，提高实体关系提取质量"
        )
        
        # Schema 配置
        st.subheader("Schema 设置")
        namespace = st.text_input("命名空间", value="Engineering")
        

    
    # 初始化 session state
    if 'schema_manager' not in st.session_state:
        st.session_state.schema_manager = SchemaManager(namespace)
    
    if 'processing_results' not in st.session_state:
        st.session_state.processing_results = []
    
    if 'document_chunks' not in st.session_state:
        st.session_state.document_chunks = []
    
    # 创建Tab布局
    tab1, tab2 = st.tabs(["📄 文档处理", "📊 分块与实体"])
    
    with tab1:
        show_document_processing_tab(provider, api_key, model_name, base_url, chunk_size, chunk_overlap, namespace, domain_expertise, enable_markdown_semantic)
    
    with tab2:
        show_chunks_and_entities_tab()

def show_document_processing_tab(provider, api_key, model_name, base_url, chunk_size, chunk_overlap, namespace, domain_expertise, enable_markdown_semantic):
    """显示文档处理tab的内容"""
    st.header("📄 文档上传")
    
    # 分批处理提示
    st.info(
        "💡 **分批处理模式**: 您可以分多次上传文档，每次处理后 Schema 会自动累积更新。"
        "支持保存和加载 Schema 文件，便于长期项目的逐步完善。"
    )
    
    # Markdown 文档特殊说明
    st.info(
        "📝 **Markdown 文档优化**: 对于 Markdown 文档，系统会进行语义分块处理，"
        "特别优化表格内容的完整性，有助于更准确地提取实体和关系信息。"
    )
    
    uploaded_files = st.file_uploader(
        "选择文档文件",
        type=["pdf", "docx", "txt", "md", "markdown"],
        accept_multiple_files=True,
        help="支持批量上传，可分多次处理不同的文档集合。支持格式：PDF、Word文档、文本文件、Markdown文档"
    )
    
    # 添加跳过文档处理的选项
    skip_document_processing = st.checkbox(
        "🔧 跳过文档处理，直接进行关系验证",
        value=False,
        help="勾选此选项将跳过文档分析和实体提取，直接对当前Schema进行关系验证和优化"
    )
    
    if uploaded_files:
        st.success(f"已上传 {len(uploaded_files)} 个文件")
        for file in uploaded_files:
            st.write(f"- {file.name} ({file.size} bytes)")
        
        # 显示处理建议
        if len(uploaded_files) > 5:
            st.warning(
                f"⚠️ 当前上传了 {len(uploaded_files)} 个文件，建议分批处理以获得更好的性能。"
                "您可以先处理部分文件，保存 Schema 后再继续处理其余文件。"
            )
    
    st.header("🎯 当前 Schema")
    
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
    can_validate_only = skip_document_processing and 'schema_manager' in st.session_state and st.session_state.schema_manager.entities
    
    # 处理按钮的逻辑
    if skip_document_processing:
        # 跳过文档处理模式
        if st.button("🔧 执行关系验证", type="primary", disabled=not can_validate_only):
            if not can_validate_only:
                st.error("请先加载或创建Schema，然后才能进行关系验证")
            else:
                # 直接执行关系验证
                with st.spinner("正在执行关系验证..."):
                    try:
                        validation_result = st.session_state.schema_manager.validate_and_update_relations()
                        
                        # 检查返回结果的完整性
                        required_keys = ['updated_entities', 'invalid_relations', 'created_entities', 'merged_relations', 'warnings']
                        missing_keys = [key for key in required_keys if key not in validation_result]
                        if missing_keys:
                            error_msg = f"验证结果缺少必要字段: {', '.join(missing_keys)}"
                            logger.error(error_msg)
                            st.error(error_msg)
                        else:
                            # 显示验证结果
                            display_validation_results(validation_result)
                            st.success("✅ 关系验证完成！")
                            
                    except Exception as e:
                        logger.error(f"关系验证失败: {str(e)}", exc_info=True)
                        st.error(f"❌ 关系验证失败: {str(e)}")
    else:
        # 正常文档处理模式
        if st.button("🚀 开始处理文档", type="primary", disabled=not can_process):
            if provider == "OpenAI" and not api_key:
                st.error("请提供 OpenAI API Key")
            elif not uploaded_files:
                st.error("请上传至少一个文档")
            else:
                process_documents(
                    uploaded_files, provider.lower(), api_key, model_name, base_url,
                    chunk_size, chunk_overlap, namespace, domain_expertise, enable_markdown_semantic
                )
    
    # 显示处理结果
    if st.session_state.processing_results:
        st.header("📊 处理结果")
        
        for i, result in enumerate(st.session_state.processing_results):
            with st.expander(f"文档 {i+1}: {result['filename']} - {result['timestamp']}"):
                col_r1, col_r2, col_r3 = st.columns(3)
                
                with col_r1:
                    st.metric("处理分块", result['stats']['chunks_processed'])
                with col_r2:
                    st.metric("文件大小", f"{result.get('file_size', 'N/A')}")
                with col_r3:
                    st.metric("处理时间", result['timestamp'])
    
    # Schema 文本下载
    st.markdown("---")
    st.header("📥 Schema 文本下载")
    
    if st.session_state.document_chunks:
        st.info("💡 文档已处理完成，可以下载提取的Schema文本")
        
        # 合并所有Schema文本
        all_schema_text = "\n\n".join([
            f"# 文件: {chunk['filename']} - 分块 {chunk['chunk_index'] + 1}\n{chunk['schema_text']}"
            for chunk in st.session_state.document_chunks
            if chunk.get('schema_text')
        ])
        
        if all_schema_text:
            # 下载按钮
            st.download_button(
                label="💾 下载所有Schema文本",
                data=all_schema_text,
                file_name=f"extracted_schema_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                use_container_width=True
            )
            
            # 预览选项
            with st.expander("👁️ 预览Schema文本", expanded=False):
                st.code(all_schema_text, language="text")
        else:
            st.warning("⚠️ 没有提取到Schema文本")
        
        # 清空按钮
        if st.button("🗑️ 清空处理结果", type="secondary"):
            st.session_state.processing_results = []
            st.session_state.document_chunks = []
            st.rerun()
        
        # 显示统计信息
        st.markdown("---")
        st.subheader("📊 统计信息")
        total_chunks = len(st.session_state.document_chunks)
        total_files = len(set(chunk['filename'] for chunk in st.session_state.document_chunks))
        st.metric("处理文件数", total_files)
        st.metric("总分块数", total_chunks)
    else:
        # 当没有处理结果时的提示
        st.info("📝 还没有处理过文档，请先上传文档并点击'开始处理文档'按钮")
        st.markdown(
            """
            **使用步骤：**
            1. 📄 上传文档文件（支持 PDF、DOCX、TXT、MD 格式）
            2. ⚙️ 在侧边栏配置 LLM 设置
            3. 🚀 点击"开始处理文档"按钮
            4. 📥 处理完成后在此处下载提取的Schema文本
            """
        )

def show_chunks_and_entities_tab():
    """显示分块与实体tab的内容"""
    st.header("📊 文档分块与实体定义")
    
    if not st.session_state.document_chunks:
        st.info("📝 还没有处理过的文档分块。请先在'文档处理'页面上传并处理文档。")
        return
    
    # 显示处理进度和最新分块信息
    col_info1, col_info2 = st.columns([1, 1])
    with col_info1:
        st.info(f"📄 已处理 {len(st.session_state.document_chunks)} 个文档分块")
    with col_info2:
        if st.session_state.document_chunks:
            latest_chunk = st.session_state.document_chunks[-1]
            st.success(f"🆕 最新: {latest_chunk['filename']} 分块 {latest_chunk['chunk_index'] + 1}")
    
    # 创建左右两列布局
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        st.subheader("📄 文档分块")
        
        # 创建分块选择器
        chunk_options = [f"分块 {i+1} ({chunk['filename']})" for i, chunk in enumerate(st.session_state.document_chunks)]
        selected_chunk_index = st.selectbox(
            "选择要查看的分块",
            range(len(chunk_options)),
            format_func=lambda x: chunk_options[x]
        )
        
        if selected_chunk_index is not None:
            selected_chunk = st.session_state.document_chunks[selected_chunk_index]
            
            # 显示分块信息
            st.write(f"**文件名**: {selected_chunk['filename']}")
            st.write(f"**分块大小**: {len(selected_chunk['content'])} 字符")
            st.write(f"**分块索引**: {selected_chunk['chunk_index'] + 1}/{selected_chunk['total_chunks']}")
            
            # 显示分块内容
            with st.expander("查看分块内容", expanded=True):
                st.text_area(
                    "分块内容",
                    value=selected_chunk['content'],
                    height=400,
                    disabled=True
                )
    
    with col_right:
        st.subheader("🏷️ 实体定义 (OpenSPG Schema)")
        
        if selected_chunk_index is not None:
            selected_chunk = st.session_state.document_chunks[selected_chunk_index]
            
            if 'schema_text' in selected_chunk and selected_chunk['schema_text']:
                st.write(f"**从此分块提取的实体定义**")
                
                # 显示原始的Schema文本
                st.code(selected_chunk['schema_text'], language='text')
            else:
                st.info("此分块没有提取到实体定义")

def process_documents(uploaded_files, provider, api_key, model_name, base_url, chunk_size, chunk_overlap, namespace, domain_expertise="", enable_markdown_semantic=True):
    """处理上传的文档"""
    logger.info(f"开始处理文档批次，共 {len(uploaded_files)} 个文件")
    logger.info(f"配置参数 - 提供商: {provider}, 模型: {model_name}, 分块大小: {chunk_size}, 重叠: {chunk_overlap}")
    
    # 清空之前的分块数据
    st.session_state.document_chunks = []
    
    # 初始化组件
    try:
        logger.debug("初始化 LLM 客户端")
        llm_client = LLMClient(
            provider=provider,
            api_key=api_key,
            model_name=model_name,
            base_url=base_url if base_url else None,
            domain_expertise=domain_expertise
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
    doc_processor = DocumentProcessor(
        chunk_size=chunk_size, 
        chunk_overlap=chunk_overlap,
        enable_markdown_semantic=enable_markdown_semantic
    )
    schema_generator = SchemaGenerator(llm_client)
    
    # 创建专用日志记录器
    chunk_logger = ChunkLogger()
    
    # 确保输出目录存在
    os.makedirs("extracted_entities", exist_ok=True)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # 创建实时显示容器
    realtime_container = st.container()
    with realtime_container:
        st.subheader("🔄 实时处理进度")
        current_file_text = st.empty()
        current_chunk_text = st.empty()
        
        # 分块内容显示区域
        chunk_expander = st.expander("📄 当前分块内容", expanded=False)
        with chunk_expander:
            chunk_content_area = st.empty()
        
        # LLM响应显示区域
        llm_expander = st.expander("🤖 LLM响应内容", expanded=False)
        with llm_expander:
            llm_response_area = st.empty()
    
    for i, uploaded_file in enumerate(uploaded_files):
        file_progress = (i + 1) / len(uploaded_files)
        logger.info(f"处理文件 {i+1}/{len(uploaded_files)}: {uploaded_file.name} ({uploaded_file.size} 字节)")
        status_text.text(f"正在处理: {uploaded_file.name}")
        current_file_text.text(f"📁 当前文件: {uploaded_file.name} ({i + 1}/{len(uploaded_files)})")
        
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
            logger.info(f"开始从 {len(chunks)} 个分块中提取实体Schema")
            
            # 记录文件开始处理
            import time
            file_start_time = time.time()
            
            # 为当前文档创建专门的目录
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_filename = "".join(c for c in uploaded_file.name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            doc_dir = f"extracted_entities/{safe_filename}_{timestamp}"
            os.makedirs(doc_dir, exist_ok=True)
            
            # 创建子目录
            chunks_dir = os.path.join(doc_dir, "chunks")
            schemas_dir = os.path.join(doc_dir, "schemas")
            os.makedirs(chunks_dir, exist_ok=True)
            os.makedirs(schemas_dir, exist_ok=True)
            
            logger.info(f"为文档 {uploaded_file.name} 创建目录: {doc_dir}")
            
            for chunk_idx, chunk in enumerate(chunks):
                chunk_start_time = time.time()
                
                logger.debug(f"处理分块 {chunk_idx + 1}/{len(chunks)} ({len(chunk)} 字符)")
                
                # 更新状态显示当前处理的分块
                status_text.text(f"正在处理文件 {uploaded_file.name} 的分块 {chunk_idx + 1}/{len(chunks)}...")
                current_chunk_text.text(f"📄 当前分块: {chunk_idx + 1}/{len(chunks)} (长度: {len(chunk)} 字符)")
                
                # 显示分块内容
                try:
                    chunk_preview = chunk[:500] + "..." if len(chunk) > 500 else chunk
                except Exception as e:
                    logger.error(f"创建chunk_preview时出错: {str(e)}, chunk类型: {type(chunk)}")
                    chunk_preview = str(chunk)[:500] + "..." if len(str(chunk)) > 500 else str(chunk)
                chunk_content_area.text_area(
                    f"分块 {chunk_idx + 1} 内容预览",
                    value=chunk_preview,
                    height=200,
                    disabled=True
                )
                
                # 记录到专用日志
                chunk_logger.log_chunk_start(uploaded_file.name, chunk_idx, len(chunks))
                chunk_logger.log_chunk_content(chunk, chunk_idx)
                
                # 提取Schema文本
                schema_text = llm_client.extract_entities_from_text(chunk, [])
                logger.debug(f"从分块 {chunk_idx + 1} 提取到Schema文本长度: {len(schema_text)} 字符")
                
                # 显示LLM响应
                try:
                    llm_preview = schema_text[:500] + "..." if len(schema_text) > 500 else schema_text
                except Exception as e:
                    logger.error(f"创建llm_preview时出错: {str(e)}, schema_text类型: {type(schema_text)}")
                    llm_preview = str(schema_text)[:500] + "..." if len(str(schema_text)) > 500 else str(schema_text)
                llm_response_area.text_area(
                    f"分块 {chunk_idx + 1} LLM响应预览",
                    value=llm_preview,
                    height=200,
                    disabled=True
                )
                
                # 记录LLM响应到专用日志
                chunk_logger.log_llm_response(schema_text, chunk_idx)
                
                # 保存分块内容到文件
                chunk_filename = f"chunk_{chunk_idx + 1:03d}.txt"
                chunk_filepath = os.path.join(chunks_dir, chunk_filename)
                try:
                    with open(chunk_filepath, 'w', encoding='utf-8') as f:
                        f.write(f"文件名: {uploaded_file.name}\n")
                        f.write(f"分块序号: {chunk_idx + 1}/{len(chunks)}\n")
                        f.write(f"分块大小: {len(chunk)} 字符\n")
                        f.write(f"处理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write("=" * 50 + "\n")
                        f.write(str(chunk))  # 确保是字符串
                except Exception as e:
                    logger.error(f"保存分块文件时出错: {str(e)}, chunk类型: {type(chunk)}")
                    raise
                
                # 保存Schema内容到文件
                schema_filename = f"schema_{chunk_idx + 1:03d}.txt"
                schema_filepath = os.path.join(schemas_dir, schema_filename)
                try:
                    with open(schema_filepath, 'w', encoding='utf-8') as f:
                        f.write(f"文件名: {uploaded_file.name}\n")
                        f.write(f"分块序号: {chunk_idx + 1}/{len(chunks)}\n")
                        f.write(f"Schema长度: {len(schema_text)} 字符\n")
                        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write("=" * 50 + "\n")
                        f.write(str(schema_text))  # 确保是字符串
                except Exception as e:
                    logger.error(f"保存Schema文件时出错: {str(e)}, schema_text类型: {type(schema_text)}")
                    raise
                
                logger.debug(f"已保存分块文件: {chunk_filepath}")
                logger.debug(f"已保存Schema文件: {schema_filepath}")
                
                chunk_end_time = time.time()
                chunk_processing_time = chunk_end_time - chunk_start_time
                chunk_logger.log_chunk_complete(chunk_idx, chunk_processing_time)
                
                # 保存分块和对应的Schema文本到session state
                try:
                    chunk_info = {
                        'filename': str(uploaded_file.name),
                        'chunk_index': int(chunk_idx),
                        'total_chunks': int(len(chunks)),
                        'content': str(chunk),
                        'schema_text': str(schema_text),
                        'chunk_file': str(chunk_filepath),
                        'schema_file': str(schema_filepath)
                    }
                    st.session_state.document_chunks.append(chunk_info)
                except Exception as e:
                    logger.error(f"创建chunk_info时出错: {str(e)}")
                    logger.error(f"chunk类型: {type(chunk)}, schema_text类型: {type(schema_text)}")
                    raise
                
                # 更新进度
                chunk_progress = (chunk_idx + 1) / len(chunks)
                overall_progress = (i + chunk_progress) / len(uploaded_files)
                progress_bar.progress(overall_progress)
            
            # 记录文件处理完成
            file_end_time = time.time()
            file_processing_time = file_end_time - file_start_time
            chunk_logger.log_file_complete(uploaded_file.name, len(chunks), file_processing_time)
            
            # 创建文档处理汇总文件
            summary_file = os.path.join(doc_dir, "processing_summary.txt")
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(f"文档处理汇总报告\n")
                f.write(f"{'=' * 50}\n")
                f.write(f"原始文件名: {uploaded_file.name}\n")
                f.write(f"文件大小: {uploaded_file.size} 字节\n")
                f.write(f"处理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"处理耗时: {file_processing_time:.2f} 秒\n")
                f.write(f"分块总数: {len(chunks)}\n")
                f.write(f"输出目录: {doc_dir}\n")
                f.write(f"\n分块文件列表:\n")
                f.write(f"{'-' * 30}\n")
                for idx in range(len(chunks)):
                    f.write(f"分块 {idx + 1:03d}: chunks/chunk_{idx + 1:03d}.txt\n")
                f.write(f"\nSchema文件列表:\n")
                f.write(f"{'-' * 30}\n")
                for idx in range(len(chunks)):
                    f.write(f"Schema {idx + 1:03d}: schemas/schema_{idx + 1:03d}.txt\n")
            
            logger.info(f"已创建处理汇总文件: {summary_file}")
            
            # 记录处理结果
            result = {
                'filename': uploaded_file.name,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'output_dir': doc_dir,
                'stats': {
                    'chunks_processed': len(chunks)
                }
            }
            
            st.session_state.processing_results.append(result)
            logger.success(f"文件 {uploaded_file.name} 处理完成，生成了 {len(chunks)} 个分块的Schema定义")
            
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
    
    # 显示处理统计
    total_files = len(uploaded_files)
    successful_files = len([r for r in st.session_state.processing_results if 'stats' in r])
    failed_files = total_files - successful_files

    logger.success(f"文档批次处理完成 - 总计: {total_files}, 成功: {successful_files}, 失败: {failed_files}")

    if st.session_state.processing_results:
        total_chunks = sum(r.get('stats', {}).get('chunks_processed', 0) for r in st.session_state.processing_results)
        logger.info(f"分块统计 - 总分块数: {total_chunks}")

    progress_bar.progress(1.0)
    status_text.text("✅ 所有文档处理完成！")
    
    # 显示处理完成信息和日志文件位置
    st.success(f"成功处理 {len(uploaded_files)} 个文档")
    
    # 显示文件保存信息
    if st.session_state.processing_results:
        st.subheader("📁 文件保存位置")
        for result in st.session_state.processing_results:
            if 'output_dir' in result:
                st.info(f"📄 **{result['filename']}** 的分块和Schema文件已保存到: `{result['output_dir']}`")
                
                # 显示目录结构
                with st.expander(f"查看 {result['filename']} 的输出目录结构", expanded=False):
                    if os.path.exists(result['output_dir']):
                        st.text(f"{result['output_dir']}/")
                        st.text(f"├── processing_summary.txt  (处理汇总报告)")
                        st.text(f"├── chunks/                 (分块文件目录)")
                        chunks_count = result.get('stats', {}).get('chunks_processed', 0)
                        for i in range(chunks_count):
                            st.text(f"│   ├── chunk_{i+1:03d}.txt")
                        st.text(f"└── schemas/                (Schema文件目录)")
                        for i in range(chunks_count):
                            st.text(f"    ├── schema_{i+1:03d}.txt")
    
    # 显示日志文件信息
    log_file_path = chunk_logger.get_log_file_path()
    st.info(f"📝 详细的处理日志已记录到: `{log_file_path}`")
    
    # 提供下载日志文件的选项
    if os.path.exists(log_file_path):
        with open(log_file_path, 'r', encoding='utf-8') as f:
            log_content = f.read()
        
        st.download_button(
            label="📥 下载处理日志",
            data=log_content,
            file_name=f"chunk_processing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
            mime="text/plain"
        )
    
    # 创建并提供zip文件下载
    if st.session_state.processing_results:
        st.subheader("📦 打包下载")
        
        # 收集所有输出目录
        output_dirs = []
        for result in st.session_state.processing_results:
            if 'output_dir' in result and os.path.exists(result['output_dir']):
                output_dirs.append(result['output_dir'])
        
        if output_dirs:
            # 创建zip文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            zip_filename = f"extracted_entities_{timestamp}.zip"
            
            try:
                # 显示打包进度
                with st.spinner("正在打包文件..."):
                    zip_path = create_zip_archive(output_dirs, zip_filename)
                
                # 读取zip文件内容用于下载
                with open(zip_path, 'rb') as f:
                    zip_data = f.read()
                
                # 提供下载按钮
                st.success(f"✅ 打包完成！文件大小: {len(zip_data) / 1024 / 1024:.2f} MB")
                st.download_button(
                    label="📥 下载提取结果压缩包",
                    data=zip_data,
                    file_name=zip_filename,
                    mime="application/zip",
                    help="包含所有文档的分块文件和Schema定义"
                )
                
                # 显示zip文件内容预览
                with st.expander("📋 压缩包内容预览", expanded=False):
                    st.text("压缩包包含以下目录和文件:")
                    for output_dir in output_dirs:
                        dir_name = os.path.basename(output_dir)
                        st.text(f"📁 {dir_name}/")
                        if os.path.exists(output_dir):
                            for root, dirs, files in os.walk(output_dir):
                                level = root.replace(output_dir, '').count(os.sep)
                                indent = '  ' * (level + 1)
                                subdir = os.path.basename(root)
                                if subdir:
                                    st.text(f"{indent}📁 {subdir}/")
                                subindent = '  ' * (level + 2)
                                for file in files:
                                    st.text(f"{subindent}📄 {file}")
                
                # 清理临时zip文件（可选，也可以保留供后续使用）
                # os.remove(zip_path)
                
            except Exception as e:
                st.error(f"打包文件时出错: {str(e)}")
                logger.error(f"创建zip文件失败: {str(e)}", exc_info=True)
    
    st.rerun()

def display_validation_results(validation_result):
    """显示关系验证结果"""
    if validation_result.get('updated_entities'):
        logger.info(f"更新了 {len(validation_result['updated_entities'])} 个实体的relations")
        st.success(f"✅ 成功更新了 {len(validation_result['updated_entities'])} 个实体的关系引用")
        
        # 显示更新详情
        with st.expander("查看关系更新详情"):
            for update in validation_result['updated_entities']:
                st.write(f"**{update['entity']}** - {update['relation']}: {update['old_target']} → {update['new_target']}")
    
    if validation_result.get('created_entities'):
        logger.info(f"自动创建了 {len(validation_result['created_entities'])} 个缺失的实体")
        st.success(f"🆕 自动创建了 {len(validation_result['created_entities'])} 个缺失的实体")
        
        # 显示创建详情
        with st.expander("查看自动创建的实体详情"):
            for created in validation_result['created_entities']:
                st.write(f"**{created['entity']}** - {created['reason']}")
    
    if validation_result.get('merged_relations'):
        logger.info(f"合并了 {len(validation_result['merged_relations'])} 组重复关系")
        st.success(f"🔗 合并了 {len(validation_result['merged_relations'])} 组重复关系")
        
        # 显示合并详情
        with st.expander("查看关系合并详情"):
            for merged in validation_result['merged_relations']:
                st.write(f"**{merged['entity']}** → **{merged['target']}**:")
                st.write(f"  主关系: {merged['primary_relation']}")
                st.write(f"  合并的关系: {', '.join(merged['merged_relations'])}")
                st.write(f"  所有名称: {', '.join(merged['all_names'])}")
    
    if validation_result.get('invalid_relations'):
        logger.warning(f"发现 {len(validation_result['invalid_relations'])} 个无效的关系引用")
        st.warning(f"⚠️ 发现 {len(validation_result['invalid_relations'])} 个无效的关系引用")
        
        # 显示无效关系详情
        with st.expander("查看无效关系详情"):
            for invalid in validation_result['invalid_relations']:
                st.write(f"**{invalid['entity']}** - {invalid['relation']}: {invalid['target']} ({invalid['reason']})")
    
    if (not validation_result.get('updated_entities') and 
        not validation_result.get('created_entities') and 
        not validation_result.get('merged_relations') and 
        not validation_result.get('invalid_relations')):
        st.info("✅ 所有关系引用都是有效的，无需更新")

if __name__ == "__main__":
    main()