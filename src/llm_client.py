import openai
import requests
from typing import List, Dict, Any, Optional, Union
import json
import time
from abc import ABC, abstractmethod

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
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=kwargs.get('temperature', 0.1),
                    max_tokens=kwargs.get('max_tokens', 4000)
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                print(f"OpenAI 调用失败 (尝试 {attempt + 1}/{self.max_retries}): {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
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
        # 转换消息格式为 Ollama 格式
        prompt = self._convert_messages_to_prompt(messages)
        
        for attempt in range(self.max_retries):
            try:
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
                return result.get('response', '').strip()
            except Exception as e:
                print(f"Ollama 调用失败 (尝试 {attempt + 1}/{self.max_retries}): {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
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
                 base_url: Optional[str] = None):
        """
        初始化 LLM 客户端
        
        Args:
            provider: LLM 提供商 ('openai' 或 'ollama')
            api_key: API 密钥 (OpenAI 需要)
            model_name: 模型名称
            base_url: 基础 URL (可选)
        """
        self.provider = provider.lower()
        
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
        
        messages = self._create_entity_extraction_messages(text)
        
        try:
            response = self.client.chat_completion(messages)
            entities = self._parse_entity_response(response)
            return entities
        except Exception as e:
            print(f"实体提取失败: {str(e)}")
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
        
        return [
            {
                "role": "system",
                "content": "你是一个专业的知识图谱构建专家，擅长从技术文档中提取结构化信息。"
            },
            {
                "role": "user",
                "content": f"""
你是一个专业的知识图谱构建专家。请从以下工程设计文档文本中提取实体信息，并按照 OpenSPG 的标准格式组织。

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
- name: 实体名称（中文）
- description: 实体描述
- category: 实体类别（从上述类型中选择最合适的）
- properties: 相关属性（如果有的话）

请以 JSON 格式返回结果：
[
    {{
        "name": "实体名称",
        "description": "实体描述",
        "category": "实体类别",
        "properties": {{
            "属性名": "属性描述"
        }}
    }}
]

注意：
1. 只提取在文档中明确提到的实体
2. 实体名称应该是标准化的专业术语
3. 描述应该简洁明了
4. 如果文档中没有明确的实体，返回空数组 []
"""
            }
        ]
    
    def _parse_entity_response(self, response: str) -> List[Dict[str, Any]]:
        """解析 LLM 返回的实体信息"""
        try:
            # 尝试直接解析 JSON
            entities = json.loads(response)
            
            if not isinstance(entities, list):
                return []
            
            # 验证和标准化实体格式
            standardized_entities = []
            for entity in entities:
                if isinstance(entity, dict) and 'name' in entity:
                    standardized_entity = {
                        'name': entity.get('name', '').strip(),
                        'description': entity.get('description', '').strip(),
                        'category': entity.get('category', 'Others').strip(),
                        'properties': entity.get('properties', {})
                    }
                    
                    # 只添加有效的实体
                    if standardized_entity['name']:
                        standardized_entities.append(standardized_entity)
            
            return standardized_entities
            
        except json.JSONDecodeError:
            # 如果 JSON 解析失败，尝试从文本中提取
            return self._extract_entities_from_text_fallback(response)
    
    def _extract_entities_from_text_fallback(self, text: str) -> List[Dict[str, Any]]:
        """从文本中提取实体的备用方法"""
        entities = []
        
        # 简单的文本解析逻辑
        lines = text.split('\n')
        current_entity = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('name:') or line.startswith('"name"'):
                if current_entity and current_entity.get('name'):
                    entities.append(current_entity)
                current_entity = {'name': line.split(':', 1)[1].strip().strip('"')}
            elif line.startswith('description:') or line.startswith('"description"'):
                current_entity['description'] = line.split(':', 1)[1].strip().strip('"')
            elif line.startswith('category:') or line.startswith('"category"'):
                current_entity['category'] = line.split(':', 1)[1].strip().strip('"')
        
        # 添加最后一个实体
        if current_entity and current_entity.get('name'):
            entities.append(current_entity)
        
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