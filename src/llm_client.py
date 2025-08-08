import openai
import requests
from typing import List, Dict, Any, Optional, Union
import json
import time
import re
from abc import ABC, abstractmethod
from .logger import logger

class BaseLLMClient(ABC):
    """LLM 客户端基类"""
    
    @abstractmethod
    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """聊天完成接口"""
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """测试连接"""
        pass

class OpenAIClient(BaseLLMClient):
    """OpenAI 客户端"""
    
    def __init__(self, api_key: str, model_name: str = "gpt-4", base_url: Optional[str] = None):
        self.client = openai.OpenAI(api_key=api_key, base_url=base_url)
        self.model_name = model_name
        self.max_retries = 3
        self.retry_delay = 1
    
    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """OpenAI 聊天完成"""
        # 记录完整的提示词
        logger.info(f"OpenAI API 调用开始 - 模型: {self.model_name}")
        logger.debug(f"请求参数: temperature={kwargs.get('temperature', 0.1)}, max_tokens={kwargs.get('max_tokens', 4000)}")
        
        # 记录完整的消息内容
        for i, message in enumerate(messages):
            role = message.get('role', 'unknown')
            content = message.get('content', '')
            logger.info(f"消息 {i+1} [{role}]: {content[:200]}{'...' if len(content) > 200 else ''}")
            if len(content) > 200:
                logger.debug(f"消息 {i+1} 完整内容: {content}")
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"发送请求到 OpenAI (尝试 {attempt + 1}/{self.max_retries})")
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=kwargs.get('temperature', 0.1),
                    max_tokens=kwargs.get('max_tokens', 4000)
                )
                
                result = response.choices[0].message.content.strip()
                logger.success(f"OpenAI API 调用成功，返回 {len(result)} 字符")
                logger.info(f"响应内容: {result[:200]}{'...' if len(result) > 200 else ''}")
                if len(result) > 200:
                    logger.debug(f"完整响应: {result}")
                
                return result
            except Exception as e:
                error_msg = f"OpenAI 调用失败 (尝试 {attempt + 1}/{self.max_retries}): {str(e)}"
                logger.warning(error_msg)
                if attempt < self.max_retries - 1:
                    sleep_time = self.retry_delay * (attempt + 1)
                    logger.debug(f"等待 {sleep_time} 秒后重试")
                    time.sleep(sleep_time)
                else:
                    logger.error(f"OpenAI API 调用最终失败: {str(e)}")
                    raise e
    
    def test_connection(self) -> bool:
        """测试 OpenAI 连接"""
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            return True
        except Exception:
            return False

class OllamaClient(BaseLLMClient):
    """Ollama 客户端"""
    
    def __init__(self, base_url: str = "http://localhost:11434", model_name: str = "llama2"):
        self.base_url = base_url.rstrip('/')
        self.model_name = model_name
        self.max_retries = 3
        self.retry_delay = 1
    
    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Ollama 聊天完成"""
        # 记录完整的提示词
        logger.info(f"Ollama API 调用开始 - 模型: {self.model_name}")
        logger.debug(f"请求参数: temperature={kwargs.get('temperature', 0.1)}, max_tokens={kwargs.get('max_tokens', 4000)}")
        
        # 记录原始消息
        for i, message in enumerate(messages):
            role = message.get('role', 'unknown')
            content = message.get('content', '')
            logger.info(f"消息 {i+1} [{role}]: {content[:200]}{'...' if len(content) > 200 else ''}")
            if len(content) > 200:
                logger.debug(f"消息 {i+1} 完整内容: {content}")
        
        # 转换消息格式为 Ollama 格式
        prompt = self._convert_messages_to_prompt(messages)
        logger.debug(f"转换后的提示词: {prompt[:300]}{'...' if len(prompt) > 300 else ''}")
        if len(prompt) > 300:
            logger.debug(f"完整提示词: {prompt}")
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"发送请求到 Ollama (尝试 {attempt + 1}/{self.max_retries})")
                response = requests.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": kwargs.get('temperature', 0.1),
                            "num_predict": kwargs.get('max_tokens', 4000)
                        }
                    },
                    timeout=300
                )
                response.raise_for_status()
                result = response.json()
                
                response_text = result.get('response', '').strip()
                logger.success(f"Ollama API 调用成功，返回 {len(response_text)} 字符")
                logger.info(f"响应内容: {response_text[:200]}{'...' if len(response_text) > 200 else ''}")
                if len(response_text) > 200:
                    logger.debug(f"完整响应: {response_text}")
                
                return response_text
            except Exception as e:
                error_msg = f"Ollama 调用失败 (尝试 {attempt + 1}/{self.max_retries}): {str(e)}"
                logger.warning(error_msg)
                if attempt < self.max_retries - 1:
                    sleep_time = self.retry_delay * (attempt + 1)
                    logger.debug(f"等待 {sleep_time} 秒后重试")
                    time.sleep(sleep_time)
                else:
                    raise e
    
    def _convert_messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """将消息列表转换为 Ollama 提示词格式"""
        prompt_parts = []
        
        for message in messages:
            role = message.get('role', 'user')
            content = message.get('content', '')
            
            if role == 'system':
                prompt_parts.append(f"System: {content}")
            elif role == 'user':
                prompt_parts.append(f"Human: {content}")
            elif role == 'assistant':
                prompt_parts.append(f"Assistant: {content}")
        
        prompt_parts.append("Assistant:")
        return "\n\n".join(prompt_parts)
    
    def test_connection(self) -> bool:
        """测试 Ollama 连接"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            return response.status_code == 200
        except Exception:
            return False

class LLMClient:
    """统一的 LLM 客户端接口"""
    
    def __init__(self, 
                 provider: str = "openai",
                 api_key: Optional[str] = None,
                 model_name: str = "gpt-4",
                 base_url: Optional[str] = None,
                 domain_expertise: str = ""):
        """
        初始化 LLM 客户端
        
        Args:
            provider: LLM 提供商 ('openai' 或 'ollama')
            api_key: API 密钥 (OpenAI 需要)
            model_name: 模型名称
            base_url: 基础 URL (可选)
            domain_expertise: 专业领域 (可选，用于提高专业识别能力)
        """
        self.provider = provider.lower()
        self.domain_expertise = domain_expertise.strip() if domain_expertise else ""
        
        if self.provider == "openai":
            if not api_key:
                raise ValueError("OpenAI 需要提供 API Key")
            self.client = OpenAIClient(api_key, model_name, base_url)
        elif self.provider == "ollama":
            ollama_url = base_url or "http://localhost:11434"
            self.client = OllamaClient(ollama_url, model_name)
        else:
            raise ValueError(f"不支持的 LLM 提供商: {provider}")
        
        self.model_name = model_name
    
    def extract_entities_from_text(self, text: str) -> List[Dict[str, Any]]:
        """从文本中提取实体信息"""
        logger.info(f"开始实体提取，文本长度: {len(text)} 字符")
        logger.debug(f"输入文本: {text[:300]}{'...' if len(text) > 300 else ''}")
        
        messages = self._create_entity_extraction_messages(text)
        logger.debug(f"构建了 {len(messages)} 条消息用于实体提取")
        
        try:
            logger.debug("调用 LLM 进行实体提取")
            response = self.client.chat_completion(messages)
            logger.debug(f"LLM 返回响应，开始解析实体")
            entities = self._parse_entity_response(response)
            logger.success(f"实体提取完成，共提取到 {len(entities)} 个实体")
            
            # 详细记录提取到的实体列表
            if entities:
                entity_names = [entity.get('name', 'Unknown') for entity in entities]
                logger.info(f"提取到的实体: {', '.join(entity_names)}")
                
                # 记录完整的实体详细信息
                logger.info("=== 实体详细信息列表 ===")
                for i, entity in enumerate(entities, 1):
                    logger.info(f"实体 {i}:")
                    logger.info(f"  名称: {entity.get('name', 'N/A')}")
                    logger.info(f"  英文名: {entity.get('english_name', 'N/A')}")
                    logger.info(f"  中文名: {entity.get('chinese_name', 'N/A')}")
                    logger.info(f"  类型: {entity.get('entity_type', 'N/A')}")
                    logger.info(f"  描述: {entity.get('description', 'N/A')}")
                    logger.info(f"  分类: {entity.get('category', 'N/A')}")
                    
                    # 记录属性信息
                    properties = entity.get('properties', {})
                    if properties:
                        logger.info(f"  属性数量: {len(properties)}")
                        for prop_name, prop_info in properties.items():
                            if isinstance(prop_info, dict):
                                prop_type = prop_info.get('type', 'N/A')
                                prop_display_name = prop_info.get('name', prop_name)
                                logger.info(f"    - {prop_name}: {prop_display_name} ({prop_type})")
                            else:
                                logger.info(f"    - {prop_name}: {prop_info}")
                    else:
                        logger.info(f"  属性数量: 0")
                    
                    # 记录关系信息
                    relations = entity.get('relations', {})
                    if relations:
                        logger.info(f"  关系数量: {len(relations)}")
                        for rel_name, rel_info in relations.items():
                            if isinstance(rel_info, dict):
                                rel_target = rel_info.get('target', 'N/A')
                                rel_display_name = rel_info.get('name', rel_name)
                                logger.info(f"    - {rel_name}: {rel_display_name} -> {rel_target}")
                            else:
                                logger.info(f"    - {rel_name}: {rel_info}")
                    else:
                        logger.info(f"  关系数量: 0")
                    
                    logger.info("  ---")
                
                logger.info("=== 实体列表记录完成 ===")
                
                # 记录JSON格式的完整实体数据（便于程序化处理）
                try:
                    entities_json = json.dumps(entities, ensure_ascii=False, indent=2)
                    logger.debug(f"完整实体JSON数据:\n{entities_json}")
                except Exception as e:
                    logger.warning(f"无法序列化实体数据为JSON: {e}")
            else:
                logger.warning("未提取到任何实体")
            
            return entities
        except Exception as e:
            error_msg = f"实体提取失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return []
    
    def suggest_entity_deletions(self, existing_entities: List[Dict], document_chunks: List[str]) -> List[Dict[str, str]]:
        """基于文档内容建议删除的实体"""
        
        if not existing_entities:
            return []
        
        # 构建现有实体的摘要
        entity_summary = "\n".join([
            f"- {entity['name']}: {entity.get('description', '无描述')}"
            for entity in existing_entities
        ])
        
        # 构建文档内容摘要
        content_summary = "\n".join(document_chunks[:5])  # 只取前5个块作为样本
        
        messages = [
            {
                "role": "system",
                "content": "你是一个专业的知识图谱构建专家，擅长分析实体的相关性和重要性。"
            },
            {
                "role": "user",
                "content": f"""
你是一个知识图谱专家。请分析以下现有实体列表，并基于提供的文档内容，建议哪些实体可能不再相关或应该被删除。

现有实体列表：
{entity_summary}

文档内容样本：
{content_summary}

请以 JSON 格式返回建议删除的实体，格式如下：
[
    {{
        "entity": "实体名称",
        "reason": "删除原因"
    }}
]

只建议那些明显不相关或重复的实体。如果没有建议删除的实体，返回空数组 []。
"""
            }
        ]
        
        try:
            response = self.client.chat_completion(messages)
            suggestions = json.loads(response)
            return suggestions if isinstance(suggestions, list) else []
        except Exception as e:
            print(f"删除建议生成失败: {str(e)}")
            return []
    
    def _create_entity_extraction_messages(self, text: str) -> List[Dict[str, str]]:
        """创建实体提取的消息列表"""
        
        # 根据专业领域生成角色定义
        if self.domain_expertise:
            system_content = f"你是一个专业的OpenSPG知识图谱构建专家，特别擅长{self.domain_expertise}领域的技术文档分析和结构化信息提取。你对{self.domain_expertise}的专业术语、概念、工艺流程、设备组件等有深入的理解，并能准确生成符合OpenSPG语法规范的Schema定义。"
        else:
            system_content = "你是一个专业的OpenSPG知识图谱构建专家，擅长从技术文档中提取结构化信息并生成符合OpenSPG语法规范的Schema定义。"
        
        return [
            {
                "role": "system",
                "content": system_content
            },
            {
                "role": "user",
                "content": f"""
你是一个专业的OpenSPG知识图谱构建专家{f'，特别专精于{self.domain_expertise}领域' if self.domain_expertise else ''}。请从以下{'工程设计' if not self.domain_expertise else self.domain_expertise}文档文本中提取实体信息，并按照OpenSPG声明式Schema脚本的标准格式组织。

文档文本：
{text}

## OpenSPG Schema语法规范

### 约束条件
1. 声明式Schema脚本采用逐行解析的方式，定义上要遵循顺序原则，即父类型要在子类型之前定义、属性上使用的类型也需要在其所属类型定义之前先定义好
2. 属性id、name、description为内置属性，不需要再声明
3. 属性类型只支持以下几种：
   - 基本类型：Text(文本)、Integer(整型)、Float(浮点数)
   - 标准类型：STD.ChinaMobile(国内手机号)、STD.Email(电子邮箱)、STD.IdCardNo(身份证)、STD.MacAddress(MAC地址)、STD.Date(日期)、STD.ChinaTelCode(国内通讯号)、STD.Timestamp(时间戳)
4. 属性英文名称首字母必须为小写字母，且只支持英文字母和数字
5. 关系属性类型只支持基本类型

### 语法结构（6层缩进）
- 第一层（无缩进）：定义类型、命名空间
- 第二层：定义类型的元信息，比如描述、属性、关系等
- 第三层：定义属性/关系的名称和类型
- 第四层：定义属性/关系的元信息，比如约束、子属性、逻辑规则等
- 第五层：定义子属性的名称和类型
- 第六层：定义子属性的元信息，比如描述、约束

### 标准格式示例
```
namespace DEFAULT

TypeA(实体类型A): EntityType
    desc: 实体类型描述
    properties:
        property1(属性1): Text
        property2(属性2): Float
    relations:
        relation1(关系1): TypeB
        relation2(关系2): TypeC

TypeB(实体类型B): EntityType
    desc: 实体类型B的描述
```

## 任务要求

请从文档中提取以下类型的实体：
1. 工程概念和术语 (ConceptType)
2. 设备和组件 (EntityType)
3. 材料和物质 (EntityType)
4. 工艺和流程 (ConceptType)
5. 标准和规范 (EntityType)
6. 人员和组织 (EntityType)
7. 地理位置 (EntityType)
8. 时间和日期 (EntityType)
9. 数值和参数 (ConceptType)
10. 事件和活动 (EventType)
11. 其他专业概念 (ConceptType)

对于每个实体，请提供以下信息：
- name: 实体英文名称（首字母大写，驼峰命名，只含字母数字），依照实体中文名称转换为英文名称，如"隧道施工"转换为"TunnelConstruction"
- chinese_name: 实体中文名称,必须从文档中提取（简洁的标准术语）
- description: 实体描述
- entity_type: OpenSPG实体类型（EntityType/ConceptType/EventType）
- properties: 相关属性（符合OpenSPG属性定义标准）
- relations: 与其他实体的关系（符合OpenSPG关系定义标准）


所有识别的实体返回结果必须要包含在一个 json 块中：
{{
    "ConceptEnglishName":{{
        "english_name": "ConceptEnglishName",
        "chinese_name": "概念中文名称",
        "entity_type": "ConceptType"
    }}
    "EntityEnglishName":{{
        "english_name": "EntityEnglishName",
        "chinese_name": "实体中文名称",
        "description": "实体中文描述",
        "entity_type": "EntityType",
        "properties": {{
            "propertyName": {{
                "name": "propertyName(属性中文名)",
                "type": "Text|Float|Integer|STD.Date|STD.Email等",
            }}
        }},
        "relations": {{
            "relationName": {{
                "name": "relationName(关系中文名)",
                "target": "目标实体英文名称",
            }}
        }}
    }}
    "EventEnglishName":{{
        "english_name": "EventEnglishName",
        "chinese_name": "事件中文名称",
        "description": "事件中文描述",
        "entity_type": "EventType",
        "properties": {{
            "subject": {{
                "target": "事件的主体实体的英文名称",
            }},
        }},
    }}
}}

## 重要注意事项

1. **命名规范**：
   - 英文名称：首字母大写，驼峰命名，如"TunnelConstruction"、"ConcreteStrength"
   - 属性名称：首字母小写，如"materialType"、"constructionDate"
   - 避免使用拼音、数字开头、特殊字符

2. **类型选择和输出格式**：
   - EntityType: 具体物理实体（设备、材料、人员、组织等）- 使用完整格式
   - ConceptType: 抽象概念（术语、工艺、参数等）- 使用简化格式，只需english_name、chinese_name和entity_type
   - EventType: 事件和活动（施工、检测、验收等）- 使用完整格式，**必须定义主体subject属性**

3. **属性类型**：
   - 优先使用基本类型：Text、Integer、Float
   - 特殊情况使用标准类型：STD.Date、STD.Email等
   - 关系属性只能使用基本类型

4. **EventType特殊要求**：
   - EventType必须定义subject属性，指定事件的主体实体
   - subject属性的type应该是具体的实体类型名称（如Company、Person、Equipment等）
   - 示例：CompanyRiskEvent的subject为Company，表示公司风险事件的主体是公司

5. **依赖顺序**：
   - 确保被引用的实体类型在引用它的实体之前定义
   - 属性中使用的自定义类型需要先定义

6. 只提取文档中明确提到的实体，优先提取核心的技术概念、设备、材料、工艺等
7. 如果文档中没有明确的实体，返回空数组 []
8. 确保生成的Schema能够直接用于OpenSPG系统
"""
            }
        ]
    
    def _parse_entity_response(self, response: str) -> List[Dict[str, Any]]:
        """解析 LLM 返回的实体信息"""
        try:
            # 清理markdown代码块标记
            cleaned_response = response.strip()
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]  # 移除 ```json
            if cleaned_response.startswith('```'):
                cleaned_response = cleaned_response[3:]   # 移除 ```
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]  # 移除结尾的 ```
            cleaned_response = cleaned_response.strip()
          
            # 尝试直接解析 JSON
            logger.info(f"开始解析JSON内容: {cleaned_response}")
            try:
                entities = json.loads(cleaned_response)
                logger.info(f"JSON解析成功，实体数量: {len(entities) if isinstance(entities, list) else 1}")
            except json.JSONDecodeError as json_error:
                logger.error(f"JSON解析失败: {str(json_error)}")
                logger.error(f"解析失败的JSON内容: {cleaned_response}")
                raise json.JSONDecodeError(f"无法解析LLM返回的JSON格式: {str(json_error)}", cleaned_response, json_error.pos)
            
            # 处理不同的JSON格式
            if isinstance(entities, dict):
                # 检查是否是包含多个实体的字典（每个key是实体名，value是实体信息）
                if all(isinstance(v, dict) and ('english_name' in v or 'chinese_name' in v) for v in entities.values()):
                    # 将字典中的每个实体转换为列表
                    entities = list(entities.values())
                    logger.info(f"检测到实体字典格式，转换为列表，包含 {len(entities)} 个实体")
                else:
                    # 单个实体对象，转换为列表
                    entities = [entities]
            elif not isinstance(entities, list):
                return []
            
            # 验证和标准化实体格式
            standardized_entities = []
            for entity in entities:
                if isinstance(entity, dict):
                    # 获取英文名称和中文名称
                    english_name = entity.get('english_name', '').strip()
                    chinese_name = entity.get('chinese_name', '').strip()
                    
                    # 如果有english_name，优先使用english_name作为name
                    # 否则使用原有的name字段
                    if english_name:
                        entity_name = english_name
                    else:
                        entity_name = entity.get('name', '').strip()
                    
                    # 必须有实体名称才能继续处理
                    if not entity_name:
                        continue
                    
                    # 验证命名规则
                    if not self._validate_entity_naming(entity_name, english_name):
                        continue
                    
                    standardized_entity = {
                        'name': entity_name,
                        'english_name': english_name,
                        'chinese_name': chinese_name,
                        'description': entity.get('description', '').strip(),
                        'category': entity.get('category', 'Others').strip(),
                        'properties': entity.get('properties', {})
                    }
                    
                    # 添加entity_type信息（如果有）
                    if 'entity_type' in entity:
                        standardized_entity['entity_type'] = entity['entity_type']
                    
                    # 添加关系信息（如果有）
                    if 'relations' in entity:
                        standardized_entity['relations'] = entity['relations']
                    
                    # 只添加有效的实体
                    if standardized_entity['name']:
                        standardized_entities.append(standardized_entity)
            
            # 去重处理：确保没有重名的实体
            unique_entities = []
            seen_names = set()
            
            for entity in standardized_entities:
                entity_name = entity['name']
                if entity_name not in seen_names:
                    unique_entities.append(entity)
                    seen_names.add(entity_name)
                else:
                    logger.warning(f"发现重复实体名称 '{entity_name}'，跳过重复项")
            
            return unique_entities
            
        except json.JSONDecodeError:
            # 如果 JSON 解析失败，尝试从文本中提取
            return self._extract_entities_from_text_fallback(response)
    
    def _validate_entity_naming(self, entity_name: str, english_name: str) -> bool:
        """增强的实体命名验证规则，专门解决属性字段被误识别为实体的问题"""
        
        # 1. 检查是否为属性字段模式（最严格的过滤）
        property_field_patterns = [
            r'^name\s*\([^)]*\)$',  # name(名称)
            r'^desc\s*\([^)]*\)$',  # desc(描述)
            r'^description\s*\([^)]*\)$',  # description(描述)
            r'^english_name\s*\([^)]*\)$',  # english_name(英文名称)
            r'^type\s*\([^)]*\)$',  # type(类型)
            r'^constraint\s*\([^)]*\)$',  # constraint(约束)
            r'^target\s*\([^)]*\)$',  # target(目标)
            r'^.*\s*\([^)]*\)$'  # 任何包含括号的格式
        ]
        
        for pattern in property_field_patterns:
            if re.match(pattern, entity_name.strip(), re.IGNORECASE):
                logger.warning(f"过滤属性字段: {entity_name}")
                return False
        
        # 2. 检查是否为关系字段模式
        relation_field_patterns = [
            r'^.*By\s*\([^)]*\)$',  # triggeredBy(由...引发)
            r'^.*To\s*\([^)]*\)$',  # appliedTo(应用于)
            r'^.*In\s*\([^)]*\)$',  # usedIn(使用于)
            r'^.*With\s*\([^)]*\)$',  # coordinatedWith(与...协调)
            r'^includes.*\s*\([^)]*\)$',  # includesStep(包含步骤)
            r'^uses.*\s*\([^)]*\)$',  # usesMaterial(使用材料)
            r'^has.*\s*\([^)]*\)$',  # hasResponseMeasure(具有应急处置措施)
            r'^follows.*\s*\([^)]*\)$',  # followsPrinciple(遵循原则)
            r'^comprises.*\s*\([^)]*\)$'  # comprisesElement(包含要素)
        ]
        
        for pattern in relation_field_patterns:
            if re.match(pattern, entity_name.strip(), re.IGNORECASE):
                logger.warning(f"过滤关系字段: {entity_name}")
                return False
        
        # 3. 检查是否为明显的非实体概念
        non_entity_patterns = [
            r'^[a-zA-Z]+\s*\([^)]*\)$',  # 英文单词+括号格式
            r'^\w{1,10}\s*\([^)]*\)$',  # 短单词+括号格式
        ]
        
        for pattern in non_entity_patterns:
            if re.match(pattern, entity_name.strip(), re.IGNORECASE):
                logger.warning(f"过滤非实体概念: {entity_name}")
                return False
        
        # 4. 检查中文名称是否包含空格或特殊字符
        if ' ' in entity_name or re.search(r'[^\w\u4e00-\u9fff\-]', entity_name):
            logger.warning(f"实体名称包含无效字符: {entity_name}")
            return False
        
        # 5. 检查英文名称格式
        if english_name:
            if not re.match(r'^[A-Z][a-zA-Z0-9]*$', english_name):
                logger.warning(f"英文名称格式错误: {english_name}")
                return False
            
            if len(english_name) > 50:
                logger.warning(f"英文名称过长: {english_name}")
                return False
        
        # 6. 检查已知的错误映射
        known_error_mappings = {
            "文明施工管理目标": "ReflectiveVest",
            "隧道火灾": "WeakBlasting",
            "name(名称)": "FrequentMonitoring",
            "desc(描述)": "StrongSupport",
            "name名称": "Name",
            "desc描述": "Description"
        }
        
        if entity_name in known_error_mappings and english_name == known_error_mappings[entity_name]:
            logger.warning(f"过滤已知错误映射: {entity_name} -> {english_name}")
            return False
        
        # 7. 检查实体名称长度（过短或过长都可能有问题）
        if len(entity_name.strip()) < 2:
            logger.warning(f"实体名称过短: {entity_name}")
            return False
        
        if len(entity_name.strip()) > 30:
            logger.warning(f"实体名称过长: {entity_name}")
            return False
        
        # 检查实体名称与英文名称的一致性
        # 如果中文名称是专业术语，英文名称应该相关
        inconsistent_mappings = [
            ('文明施工管理目标', 'ReflectiveVest'),
            ('施工告示牌', 'DustMask'),
            ('混凝土', 'SafetyHelmet'),
            ('钢筋', 'SafetyGloves'),
            ('隧道火灾', 'WeakBlasting'),  # 新增：隧道火灾不应该映射为弱爆破
            ('name(名称)', 'FrequentMonitoring'),  # 新增：属性字段错误映射
            ('desc(描述)', 'StrongSupport')  # 新增：属性字段错误映射
        ]
        
        for chinese, english in inconsistent_mappings:
            if entity_name == chinese and english_name == english:
                self.logger.warning(f"发现明显错误的实体映射: '{entity_name}' -> '{english_name}'，跳过")
                return False
        
        return True
    
    def _clean_entity_name(self, name: str) -> str:
        """清理实体名称，移除特殊字符"""
        import re
        
        if not name:
            return ''
        
        # 多次清理，确保彻底移除特殊字符
        cleaned = name.strip()
        
        # 移除开头和结尾的引号、逗号、句号等（多次清理确保彻底）
        for _ in range(3):  # 多次清理确保彻底
            cleaned = cleaned.strip('"\',，。；：！？()（）[]【】{}')
            cleaned = re.sub(r'^["\',，。；：！？()（）\[\]【】{}]+', '', cleaned)
            cleaned = re.sub(r'["\',，。；：！？()（）\[\]【】{}]+$', '', cleaned)
            if not re.search(r'["\',，。；：！？()（）\[\]【】{}]', cleaned):
                break  # 如果没有特殊字符了，跳出循环
        
        # 移除中间的特殊标点符号（保留中文字符、英文字符、数字、下划线、连字符）
        cleaned = re.sub(r'[^\w\u4e00-\u9fff\-]', '', cleaned)
        
        # 移除多余的空格和连字符
        cleaned = re.sub(r'\s+', '', cleaned)
        cleaned = re.sub(r'-+', '-', cleaned).strip('-')
        
        # 如果清理后为空，尝试提取有效字符
        if not cleaned:
            # 提取中文字符
            chinese_chars = re.findall(r'[\u4e00-\u9fff]', name)
            if chinese_chars:
                cleaned = ''.join(chinese_chars)
            else:
                # 提取英文字符和数字
                english_chars = re.findall(r'[a-zA-Z0-9]', name)
                if english_chars:
                    cleaned = ''.join(english_chars)
                else:
                    cleaned = 'Entity'
        
        return cleaned.strip()
    
    def _extract_entities_from_text_fallback(self, text: str) -> List[Dict[str, Any]]:
        """从文本中提取实体的备用方法"""
        import re
        entities = []
        
        # 尝试修复JSON格式
        try:
            # 移除开头的非JSON字符
            text = text.strip()
            if text.startswith('},'):
                text = text[2:].strip()
            if text.startswith('{'):
                text = '[' + text + ']'
            elif not text.startswith('['):
                # 查找第一个{开始的位置
                start_pos = text.find('{')
                if start_pos != -1:
                    text = '[' + text[start_pos:] + ']'
            
            # 尝试解析修复后的JSON
            entities = json.loads(text)
            if isinstance(entities, list):
                # 标准化实体格式
                standardized_entities = []
                for entity in entities:
                    if isinstance(entity, dict) and 'name' in entity:
                        entity_name = entity.get('name', '').strip()
                        english_name = entity.get('english_name', '').strip()
                        
                        standardized_entity = {
                            'name': entity_name,
                            'english_name': english_name,
                            'description': entity.get('description', '').strip(),
                            'category': entity.get('category', 'Others').strip(),
                            'properties': entity.get('properties', {})
                        }
                        
                        if 'relations' in entity:
                            standardized_entity['relations'] = entity['relations']
                        
                        if standardized_entity['name']:
                            standardized_entities.append(standardized_entity)
                
                return standardized_entities
        except:
            pass
        
        # 如果JSON修复失败，使用正则表达式提取
        name_pattern = r'"name"\s*:\s*"([^"]+)"'
        english_name_pattern = r'"english_name"\s*:\s*"([^"]+)"'
        description_pattern = r'"description"\s*:\s*"([^"]+)"'
        
        names = re.findall(name_pattern, text)
        english_names = re.findall(english_name_pattern, text)
        descriptions = re.findall(description_pattern, text)
        
        # 组合提取的信息
        for i, name in enumerate(names):
            entity = {
                'name': name.strip(),
                'english_name': english_names[i] if i < len(english_names) else '',
                'description': descriptions[i] if i < len(descriptions) else '',
                'category': 'Others',
                'properties': {}
            }
            if entity['name']:
                entities.append(entity)
        
        return entities
    
    def test_connection(self) -> bool:
        """测试 LLM 连接"""
        return self.client.test_connection()
    
    def get_provider_info(self) -> Dict[str, str]:
        """获取提供商信息"""
        return {
            'provider': self.provider,
            'model': self.model_name,
            'client_type': type(self.client).__name__
        }
    
    @classmethod
    def create_openai_client(cls, api_key: str, model_name: str = "gpt-4", base_url: Optional[str] = None):
        """创建 OpenAI 客户端的便捷方法"""
        return cls(provider="openai", api_key=api_key, model_name=model_name, base_url=base_url)
    
    @classmethod
    def create_ollama_client(cls, model_name: str = "llama2", base_url: str = "http://localhost:11434"):
        """创建 Ollama 客户端的便捷方法"""
        return cls(provider="ollama", model_name=model_name, base_url=base_url)