import openai
import requests
from typing import List, Dict, Any, Optional, Union
import json
import time
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
            
            # 记录提取到的实体名称
            if entities:
                entity_names = [entity.get('name', 'Unknown') for entity in entities]
                logger.info(f"提取到的实体: {', '.join(entity_names)}")
            
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
            system_content = f"你是一个专业的知识图谱构建专家，特别擅长{self.domain_expertise}领域的技术文档分析和结构化信息提取。你对{self.domain_expertise}的专业术语、概念、工艺流程、设备组件等有深入的理解。"
        else:
            system_content = "你是一个专业的知识图谱构建专家，擅长从技术文档中提取结构化信息。"
        
        return [
            {
                "role": "system",
                "content": system_content
            },
            {
                "role": "user",
                "content": f"""
你是一个专业的知识图谱构建专家{f'，特别专精于{self.domain_expertise}领域' if self.domain_expertise else ''}。请从以下{'工程设计' if not self.domain_expertise else self.domain_expertise}文档文本中提取实体信息，并按照 OpenSPG 的标准格式组织。

文档文本：
{text}

请提取以下类型的实体：
1. 工程概念和术语
2. 设备和组件
3. 材料和物质
4. 工艺和流程
5. 标准和规范
6. 人员和组织
7. 地理位置
8. 时间和日期
9. 数值和参数
10. 其他专业概念

对于每个实体，请提供：
- name: 实体名称（使用简洁的标准中文术语，提取核心概念，不要使用完整的文档标题，不包含引号、逗号、空格等特殊字符）
- description: 实体描述
- category: 实体类别（从上述类型中选择最合适的）
- properties: 相关属性（必须包含，如果没有特殊属性，至少包含description和name）
- relations: 与其他实体的关系（推荐包含，积极识别实体间的各种关系）

请以 JSON 格式返回结果：
[
    {{
        "name": "实体中文名称",
        "english_name": "EntityEnglishName",
        "description": "实体描述",
        "category": "实体类别",
        "properties": {{
            "description (描述)": "属性的详细描述",
            "name (名称)": "实体的标准名称",
            "otherPropertyName (其他属性名)": "属性的具体描述"
        }},
        "relations": {{
            "relationName (关系名称)": "目标实体名称"
        }}
    }}
]

注意：
1. 只提取在文档中明确提到的实体
2. name字段：实体的中文名称，应该是标准化的专业术语，使用规范中文，不包含标点符号、空格等特殊字符
3. english_name字段：实体的英文名称，必须以大写字母开头，只能包含字母和数字，总长度不超过50个字符（如：ConstructionTechnology、WaterproofSystem、TunnelConstruction）
4. 描述应该简洁明了
5. 如果文档中没有明确的实体，返回空数组 []
6. 实体命名原则：提取核心概念，不要使用完整的文档标题或长句作为实体名称
7. 中文名称示例："施工放线"、"混凝土"、"钢筋"、"电气系统"、"隧道工程"、"标准化手册"（正确）
8. 英文名称示例："ConstructionLayout"、"Concrete"、"Rebar"、"ElectricalSystem"、"TunnelEngineering"、"StandardManual"（正确）
9. 避免："施工放线,"、"施工放线""、"施工放线,("等包含特殊字符的格式（错误）
10. 避免："中国交建新疆乌尉公路包标准化实施手册 第五分册 隧道工程"等过长的完整标题作为实体名称（错误）
11. 避免："Shi_Gong_Fang_Xian"、"ShiGongFangXian"等拼音形式的英文名称（错误）
12. 避免："3DModel"、"2DDrawing"等以数字开头的英文名称（错误），应使用"ThreeDimensionalModel"、"TwoDimensionalDrawing"（正确）
13. 避免："施工 放线"、"混凝 土"等包含空格的中文名称（错误）
14. properties必须包含：每个实体都必须有properties，至少包含"description (描述)"和"name (名称)"
15. relations推荐：积极识别和提取实体间的关系，包括但不限于：使用关系(usedIn/usedFor)、包含关系(contains/partOf)、连接关系(connectedTo)、依赖关系(dependsOn/requires)、位置关系(locatedIn/installedAt)、材料关系(madeOf/composedOf)、功能关系(serves/supports)等
16. 关系命名：使用英文名称加中文说明的格式，如"requiresMonitoring (要求监测)"、"appliesTo (适用于)"、"contains (包含)"等
17. 属性命名：properties中的键名使用英文加中文说明的格式，如"description (描述)"、"material (材料)"、"specification (规格)"等
18. 属性值：properties中的值应该是属性的中文描述，不是数据类型
19. 英文名称要求：必须是有意义的英文单词，不能是拼音，应该反映实体的实际含义，不能以数字开头
20. 实体粒度：优先提取具体的技术概念、设备、材料、工艺等，而不是抽象的文档名称或组织结构
"""
            }
        ]
    
    def _parse_entity_response(self, response: str) -> List[Dict[str, Any]]:
        """解析 LLM 返回的实体信息"""
        try:
            # 尝试直接解析 JSON
            entities = json.loads(response)
            
            # 如果是单个实体对象，转换为列表
            if isinstance(entities, dict):
                entities = [entities]
            elif not isinstance(entities, list):
                return []
            
            # 验证和标准化实体格式
            standardized_entities = []
            for entity in entities:
                if isinstance(entity, dict) and 'name' in entity:
                    # 直接使用原始名称，不进行清理（LLM提示词已约束格式）
                    entity_name = entity.get('name', '').strip()
                    
                    # 获取英文名称
                    english_name = entity.get('english_name', '').strip()
                    
                    # 验证命名规则
                    if not self._validate_entity_naming(entity_name, english_name):
                        continue
                    
                    standardized_entity = {
                        'name': entity_name,
                        'english_name': english_name,
                        'description': entity.get('description', '').strip(),
                        'category': entity.get('category', 'Others').strip(),
                        'properties': entity.get('properties', {})
                    }
                    
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
                    self.logger.warning(f"发现重复实体名称 '{entity_name}'，跳过重复项")
            
            return unique_entities
            
        except json.JSONDecodeError:
            # 如果 JSON 解析失败，尝试从文本中提取
            return self._extract_entities_from_text_fallback(response)
    
    def _validate_entity_naming(self, entity_name: str, english_name: str) -> bool:
        """验证实体命名规则"""
        # 检查中文名称是否包含空格
        if ' ' in entity_name:
            self.logger.warning(f"实体名称 '{entity_name}' 包含空格，跳过")
            return False
        
        # 检查英文名称格式和长度
        if english_name:
            # 检查英文名称是否符合正则表达式 ^[A-Z][a-zA-Z0-9]*
            if not re.match(r'^[A-Z][a-zA-Z0-9]*$', english_name):
                self.logger.warning(f"英文名称 '{english_name}' 不符合格式要求（必须以大写字母开头，只能包含字母和数字），跳过")
                return False
            
            # 检查英文名称长度是否超过50个字符
            if len(english_name) > 50:
                self.logger.warning(f"英文名称 '{english_name}' 长度超过50个字符，跳过")
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