# Auto OpenSPG Schema Generator

一个基于 Streamlit 的自动化工具，用于从工程设计文档中提取实体信息并生成符合 OpenSPG 标准的知识图谱 Schema。

## 功能特性

- 📄 **多格式文档支持**: 支持 PDF、DOCX、TXT 格式的文档上传和解析
- 🤖 **多 LLM 提供商支持**: 支持 OpenAI API 和 Ollama 本地部署，统一接口调用
- 🔗 **OpenSPG 标准**: 严格遵循 OpenSPG 知识图谱的 Schema 格式和标准
- 📊 **实时统计**: 显示新增、修改的实体数量和建议删除的实体
- 💾 **Schema 管理**: 支持 Schema 的预览、复制和下载
- 🎯 **增量更新**: 支持多文档的增量处理和 Schema 合并
- 🔒 **数据隐私**: 支持本地 LLM 部署，保护数据隐私

## 技术栈

- **Python 3.11**
- **Streamlit**: Web 应用框架
- **Poetry**: 依赖管理
- **OpenAI GPT**: 实体提取和分析
- **LangChain**: LLM 应用开发框架

## 安装和运行

### 1. 环境要求

- Python 3.11+
- Poetry (用于依赖管理)

### 2. 安装依赖

```bash
# 安装 Poetry (如果尚未安装)
curl -sSL https://install.python-poetry.org | python3 -

# 安装项目依赖
poetry install
```

### 3. LLM 服务配置

#### 方式一：配置 Ollama (推荐用于开发测试)

1. 安装 Ollama:
   - 访问 [Ollama 官网](https://ollama.ai/) 下载安装
   - Windows: 下载 .exe 安装包
   - macOS: `brew install ollama`
   - Linux: `curl -fsSL https://ollama.ai/install.sh | sh`

2. 下载模型:
   ```bash
   ollama pull llama2
   ollama pull mistral
   ollama pull codellama
   ```

3. 启动 Ollama 服务:
   ```bash
   ollama serve
   ```

#### 方式二：配置 OpenAI API

1. 获取 OpenAI API Key:
   - 访问 [OpenAI 平台](https://platform.openai.com/)
   - 创建 API Key

2. 设置环境变量 (可选):
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

### 4. 运行应用

```bash
# 激活虚拟环境
poetry shell

# 启动 Streamlit 应用
streamlit run app.py
```

应用将在 `http://localhost:8501` 启动。

## 使用指南

### 1. LLM 配置

应用支持两种 LLM 提供商，可在侧边栏中选择和配置:

#### OpenAI API
- 选择 "OpenAI" 提供商
- 输入 OpenAI API Key
- 可选择自定义 Base URL (支持 OpenAI 兼容接口)
- 选择模型 (推荐 gpt-4)
- 测试连接确保配置正确

#### Ollama 本地部署
- 选择 "Ollama" 提供商
- 配置 Ollama 服务地址 (默认: http://localhost:11434)
- 选择已安装的模型 (如 llama2, mistral 等)
- 确保 Ollama 服务正在运行

**推荐配置:**
- 开发测试: 使用 Ollama (免费、本地)
- 生产环境: 使用 OpenAI GPT-4 (质量更高)
- 企业内部: 使用 OpenAI 兼容接口

### 2. 基本配置

在侧边栏中配置以下参数：

- **文档分块大小**: 控制文档分割的粒度 (默认 1500 字符)
- **命名空间**: Schema 的命名空间 (默认 "Engineering")

### 3. 文档上传

- 支持同时上传多个文档
- 支持的格式：PDF、DOCX、TXT
- 系统会自动检测文件编码

### 4. 处理流程

1. **文档解析**: 自动提取文档文本内容
2. **智能分块**: 将文档分割成合适大小的文本块
3. **实体提取**: 使用 LLM 从每个文本块中提取实体
4. **Schema 生成**: 将提取的实体转换为 OpenSPG 格式
5. **增量合并**: 将新实体合并到现有 Schema 中

### 5. 结果查看

处理完成后，你可以：

- 查看处理统计（新增、修改、建议删除的实体）
- 预览生成的 Schema
- 复制或下载 Schema 文件
- 查看详细的处理日志

## OpenSPG Schema 格式

生成的 Schema 严格遵循 OpenSPG 标准格式：

```
namespace Engineering

Concept(概念): EntityType
    properties:
        description(描述): Text
        name(名称): Text
        semanticType(semanticType): Text
            index: Text

ArtificialObject(人造物体): EntityType
    properties:
        description(描述): Text
        name(名称): Text
        semanticType(semanticType): Text
            index: Text
```

## 支持的实体类型

系统支持以下 OpenSPG 标准实体类型：

- **NaturalScience** (自然科学)
- **Building** (建筑)
- **GeographicLocation** (地理位置)
- **Medicine** (药物)
- **Works** (作品)
- **Event** (事件)
- **Person** (人物)
- **Transport** (运输)
- **Organization** (组织机构)
- **Date** (日期)
- **ArtificialObject** (人造物体)
- **Creature** (生物)
- **Keyword** (关键词)
- **Astronomy** (天文学)
- **SemanticConcept** (语义概念)
- **Concept** (概念)
- **Others** (其他)

## 项目结构

```
auto-openspg-schema/
├── app.py                 # 主应用文件
├── src/
│   ├── __init__.py
│   ├── document_processor.py    # 文档处理模块
│   ├── llm_client.py           # LLM 客户端
│   ├── schema_generator.py     # Schema 生成器
│   └── schema_manager.py       # Schema 管理器
├── pyproject.toml         # Poetry 配置文件
└── README.md             # 项目说明
```

## 开发和贡献

### 开发环境设置

```bash
# 克隆项目
git clone <repository-url>
cd auto-openspg-schema

# 安装开发依赖
poetry install --with dev

# 激活虚拟环境
poetry shell
```

### 代码格式化

```bash
# 使用 Black 格式化代码
black .

# 使用 Flake8 检查代码质量
flake8 .
```

### 运行测试

```bash
pytest
```

## 注意事项

1. **API 费用**: 使用 OpenAI API 会产生费用，请合理控制使用量
2. **文档质量**: 文档质量直接影响实体提取的准确性
3. **模型选择**: 推荐使用 GPT-4 以获得更好的提取效果
4. **数据安全**: 请确保上传的文档不包含敏感信息

## 许可证

MIT License

## 联系方式

如有问题或建议，请提交 Issue 或 Pull Request。


poetry add streamlit openai python-docx pypdf2 chardet pandas numpy streamlit-extras requests langchain langchain-openai