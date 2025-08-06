from typing import List, Dict, Any
from .llm_client import LLMClient
from .logger import logger

class SchemaGenerator:
    """Schema 生成器，用于从文档块中提取实体并生成 OpenSPG 格式的 Schema"""
    
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        
        # OpenSPG 标准实体类型映射
        self.entity_type_mapping = {
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
        
        # 标准属性定义
        self.standard_properties = {
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
    
    def extract_entities_from_chunk(self, chunk: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从文档块中提取实体"""
        chunk_content = chunk.get('content', '')
        logger.info(f"开始从文档块提取实体，内容长度: {len(chunk_content)} 字符")
        logger.debug(f"文档块内容预览: {chunk_content[:200]}{'...' if len(chunk_content) > 200 else ''}")
        
        # 使用 LLM 提取实体
        logger.debug("调用 LLM 客户端提取原始实体")
        raw_entities = self.llm_client.extract_entities_from_text(chunk_content)
        logger.info(f"LLM 返回 {len(raw_entities)} 个原始实体")
        
        # 标准化实体格式
        logger.debug("开始标准化实体格式")
        standardized_entities = []
        
        for i, entity in enumerate(raw_entities):
            logger.debug(f"标准化实体 {i+1}/{len(raw_entities)}: {entity.get('name', 'Unknown')}")
            standardized_entity = self._standardize_entity(entity)
            if standardized_entity:
                standardized_entities.append(standardized_entity)
                logger.debug(f"实体 {entity.get('name', 'Unknown')} 标准化成功")
            else:
                logger.warning(f"实体 {entity.get('name', 'Unknown')} 标准化失败，已跳过")
        
        logger.success(f"文档块实体提取完成，成功标准化 {len(standardized_entities)}/{len(raw_entities)} 个实体")
        
        # 记录标准化后的实体名称
        if standardized_entities:
            entity_names = [entity.get('name', 'Unknown') for entity in standardized_entities]
            logger.info(f"标准化后的实体: {', '.join(entity_names)}")
        
        return standardized_entities
    
    def suggest_entity_deletions(self, existing_entities: List[Dict], document_chunks: List[Dict]) -> List[Dict[str, str]]:
        """建议删除的实体"""
        logger.info(f"开始分析实体删除建议，现有实体: {len(existing_entities)} 个，文档块: {len(document_chunks)} 个")
        
        # 记录现有实体名称
        if existing_entities:
            entity_names = [entity.get('name', 'Unknown') for entity in existing_entities]
            logger.debug(f"现有实体列表: {', '.join(entity_names)}")
        
        # 提取文档内容
        logger.debug("提取文档块内容")
        chunk_contents = [chunk.get('content', '') if isinstance(chunk, dict) else str(chunk) for chunk in document_chunks]
        total_content_length = sum(len(content) for content in chunk_contents)
        logger.debug(f"文档内容总长度: {total_content_length} 字符")
        
        # 使用 LLM 分析并建议删除
        logger.debug("调用 LLM 分析实体删除建议")
        suggestions = self.llm_client.suggest_entity_deletions(existing_entities, chunk_contents)
        
        logger.success(f"实体删除建议分析完成，建议删除 {len(suggestions)} 个实体")
        
        # 记录建议删除的实体
        if suggestions:
            suggested_names = [suggestion.get('name', 'Unknown') for suggestion in suggestions]
            logger.info(f"建议删除的实体: {', '.join(suggested_names)}")
        
        return suggestions
    
    def _standardize_entity(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """标准化实体格式"""
        
        if not entity.get('name'):
            return None
        
        # 确定实体类型
        category = entity.get('category', '其他')
        entity_type = self._map_category_to_type(category)
        
        # 构建标准化实体
        standardized = {
            'name': entity['name'].strip(),
            'chinese_name': entity['name'].strip(),
            'description': entity.get('description', '').strip(),
            'type': entity_type,
            'properties': self._build_entity_properties(entity)
        }
        
        return standardized
    
    def _map_category_to_type(self, category: str) -> str:
        """将类别映射到 OpenSPG 实体类型"""
        
        # 直接匹配
        if category in self.entity_type_mapping:
            return self.entity_type_mapping[category]
        
        # 模糊匹配
        for key, value in self.entity_type_mapping.items():
            if key in category or category in key:
                return value
        
        # 默认类型
        return 'Others'
    
    def _build_entity_properties(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """构建实体属性"""
        
        properties = {}
        
        # 添加标准属性
        for prop_key, prop_def in self.standard_properties.items():
            properties[prop_key] = {
                'name': prop_def['name'],
                'type': prop_def['type']
            }
            
            # 添加索引信息（如果有）
            if 'index' in prop_def:
                properties[prop_key]['index'] = prop_def['index']
        
        # 添加自定义属性
        custom_properties = entity.get('properties', {})
        for prop_name, prop_desc in custom_properties.items():
            if prop_name not in properties:
                # 标准化属性名
                standardized_prop_name = self._standardize_property_name(prop_name)
                properties[standardized_prop_name] = {
                    'name': f"{standardized_prop_name}({prop_name})",
                    'type': 'Text',
                    'description': prop_desc
                }
        
        return properties
    
    def _standardize_property_name(self, prop_name: str) -> str:
        """标准化属性名"""
        
        # 移除特殊字符，保留字母、数字和下划线
        import re
        standardized = re.sub(r'[^\w\u4e00-\u9fff]', '', prop_name)
        
        # 确保以字母开头
        if standardized and not standardized[0].isalpha():
            standardized = 'prop_' + standardized
        
        return standardized or 'customProperty'
    
    def generate_entity_schema_string(self, entity: Dict[str, Any]) -> str:
        """生成单个实体的 Schema 字符串"""
        
        lines = []
        
        # 实体定义行
        entity_line = f"{entity['name']}({entity['chinese_name']}): EntityType"
        lines.append(entity_line)
        
        # 属性部分
        if entity.get('properties'):
            lines.append("\tproperties:")
            
            for prop_key, prop_def in entity['properties'].items():
                prop_line = f"\t\t{prop_def['name']}: {prop_def['type']}"
                lines.append(prop_line)
                
                # 添加索引信息
                if 'index' in prop_def:
                    index_line = f"\t\t\tindex: {prop_def['index']}"
                    lines.append(index_line)
        
        return '\n'.join(lines)
    
    def validate_entity(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """验证实体格式"""
        
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # 检查必需字段
        required_fields = ['name', 'type']
        for field in required_fields:
            if not entity.get(field):
                validation_result['valid'] = False
                validation_result['errors'].append(f"缺少必需字段: {field}")
        
        # 检查实体名称格式
        if entity.get('name'):
            name = entity['name']
            if not name.replace('_', '').replace('-', '').isalnum():
                validation_result['warnings'].append(f"实体名称包含特殊字符: {name}")
        
        # 检查实体类型
        if entity.get('type') and entity['type'] not in self.entity_type_mapping.values():
            validation_result['warnings'].append(f"未知的实体类型: {entity['type']}")
        
        return validation_result
    
    def get_supported_entity_types(self) -> List[str]:
        """获取支持的实体类型列表"""
        return list(set(self.entity_type_mapping.values()))
    
    def get_category_mapping(self) -> Dict[str, str]:
        """获取类别映射"""
        return self.entity_type_mapping.copy()