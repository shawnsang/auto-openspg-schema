# 应用配置文件

# OpenSPG Schema 配置
DEFAULT_NAMESPACE = "Engineering"

# 文档处理配置
DEFAULT_CHUNK_SIZE = 1500
DEFAULT_CHUNK_OVERLAP = 200
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# LLM 配置
DEFAULT_PROVIDER = "openai"
DEFAULT_MODEL = "gpt-4"

# 支持的 LLM 提供商
SUPPORTED_PROVIDERS = ["openai", "ollama"]

# OpenAI 模型
OPENAI_MODELS = [
    "gpt-4",
    "gpt-3.5-turbo",
    "gpt-4-turbo-preview",
    "gpt-4o"
]

# Ollama 常用模型
OLLAMA_MODELS = [
    "llama2",
    "mistral",
    "codellama",
    "vicuna",
    "alpaca"
]

# 默认 URL
DEFAULT_OPENAI_URL = "https://api.openai.com/v1"
DEFAULT_OLLAMA_URL = "http://localhost:11434"

# 支持的文件格式
SUPPORTED_FILE_TYPES = ["pdf", "docx", "txt"]

# OpenSPG 实体类型映射
ENTITY_TYPE_MAPPING = {
    '工程概念和术语': 'Concept',
    '设备和组件': 'ArtificialObject',
    '材料和物质': 'ArtificialObject',
    '工艺和流程': 'Concept',
    '标准和规范': 'Works',
    '人员和组织': 'Organization',
    '地理位置': 'GeographicLocation',
    '时间和日期': 'Date',
    '数值和参数': 'Concept',
    '自然科学': 'NaturalScience',
    '建筑': 'Building',
    '药物': 'Medicine',
    '作品': 'Works',
    '事件': 'Event',
    '人物': 'Person',
    '运输': 'Transport',
    '组织机构': 'Organization',
    '人造物体': 'ArtificialObject',
    '生物': 'Creature',
    '关键词': 'Keyword',
    '天文学': 'Astronomy',
    '语义概念': 'SemanticConcept',
    '概念': 'Concept',
    '其他': 'Others'
}

# OpenSPG 标准实体类型
OPENSPG_ENTITY_TYPES = [
    'NaturalScience',
    'Building', 
    'GeographicLocation',
    'Medicine',
    'Works',
    'Event',
    'Person',
    'Transport',
    'Organization',
    'Date',
    'ArtificialObject',
    'Creature',
    'Keyword',
    'Astronomy',
    'SemanticConcept',
    'Concept',
    'Others'
]

# 标准属性定义
STANDARD_PROPERTIES = {
    'description': {
        'name': 'description(描述)',
        'type': 'Text'
    },
    'name': {
        'name': 'name(名称)',
        'type': 'Text'
    },
    'semanticType': {
        'name': 'semanticType(semanticType)',
        'type': 'Text',
        'index': 'Text'
    }
}

# UI 配置
APP_TITLE = "OpenSPG Schema 自动生成器"
APP_ICON = "🔗"
PAGE_LAYOUT = "wide"

# 处理限制
MAX_CONCURRENT_FILES = 10
MAX_CHUNKS_PER_FILE = 100
MAX_ENTITIES_PER_CHUNK = 20

# 错误消息
ERROR_MESSAGES = {
    'no_api_key': '请提供 OpenAI API Key',
    'no_files': '请上传至少一个文档',
    'file_too_large': f'文件大小超过限制 ({MAX_FILE_SIZE // (1024*1024)}MB)',
    'unsupported_format': '不支持的文件格式',
    'processing_error': '文档处理时出错',
    'llm_error': 'LLM 调用失败',
    'schema_error': 'Schema 生成失败'
}

# 成功消息
SUCCESS_MESSAGES = {
    'files_uploaded': '文件上传成功',
    'processing_complete': '文档处理完成',
    'schema_generated': 'Schema 生成成功',
    'schema_exported': 'Schema 导出成功'
}