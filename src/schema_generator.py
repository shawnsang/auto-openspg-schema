from typing import List, Dict, Any
import re
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
            }
            # 移除semanticType属性，因为这不是必需的标准属性
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
            # 清理实体名称用于日志显示
            display_name = self._clean_name_for_display(entity.get('name', 'Unknown'))
            logger.debug(f"标准化实体 {i+1}/{len(raw_entities)}: {display_name}")
            standardized_entity = self._standardize_entity(entity)
            if standardized_entity:
                standardized_entities.append(standardized_entity)
                logger.debug(f"实体 {display_name} 标准化成功")
            else:
                logger.warning(f"实体 {display_name} 标准化失败，已跳过")
        
        logger.success(f"文档块实体提取完成，成功标准化 {len(standardized_entities)}/{len(raw_entities)} 个实体")
        
        # 记录标准化后的实体名称
        if standardized_entities:
            entity_names = [entity.get('name', 'Unknown') for entity in standardized_entities]
            logger.info(f"标准化后的实体: {', '.join(entity_names)}")
        
        return standardized_entities

    def _clean_name_for_display(self, name: str) -> str:
        """清理实体名称用于日志显示"""
        import re
        
        # 首先移除字符串开头和结尾的引号、逗号等
        cleaned = name.strip().strip('"\',，。')
        
        # 移除常见的特殊字符和标点符号
        cleaned = re.sub(r'["\',，。！？；：()（）\[\]{}【】]', '', cleaned)
        
        # 移除多余的空格
        cleaned = re.sub(r'\s+', '', cleaned)
        
        # 如果清理后为空，返回原始名称的简化版本
        if not cleaned.strip():
            # 尝试提取中文字符
            chinese_chars = re.findall(r'[\u4e00-\u9fff]', name)
            if chinese_chars:
                cleaned = ''.join(chinese_chars)
            else:
                cleaned = 'Unknown'
        
        return cleaned.strip()

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
        """标准化实体格式（符合OpenSPG标准）"""
        try:
            # 获取基本信息
            entity_name = entity.get('name', '').strip()
            chinese_name = entity.get('chinese_name', '').strip()
            description = entity.get('description', '').strip()
            
            # 如果name字段包含中文名称（格式：englishName(中文名)），则提取分离
            if not chinese_name and '(' in entity_name and ')' in entity_name:
                match = re.match(r'^([^()]+)\(([^()]+)\)$', entity_name)
                if match:
                    entity_name = match.group(1).strip()
                    chinese_name = match.group(2).strip()
                    logger.debug(f"从name字段提取: 英文名='{entity_name}', 中文名='{chinese_name}'")
            
            # 验证必需字段
            if not entity_name:
                logger.warning(f"实体缺少英文名称，跳过")
                return None
            
            if not chinese_name:
                # 如果没有中文名称，使用英文名称
                chinese_name = entity_name
                logger.debug(f"实体 '{entity_name}' 缺少中文名称，使用英文名称")
            
            # 修复英文名称格式
            fixed_english_name = self._fix_english_name(entity_name)
            if fixed_english_name != entity_name:
                logger.info(f"修复实体英文名称: {entity_name} -> {fixed_english_name}")
                entity_name = fixed_english_name
            
            # 构建标准化实体
            standardized_entity = {
                'name': entity_name,
                'chinese_name': chinese_name,
                'english_name': entity_name,  # 保持向后兼容
                'description': description,
                'openspg_type': entity.get('openspg_type', 'EntityType'),
                'traditional_type': entity.get('type', '实体'),
                'category': entity.get('category', '其他'),  # 向后兼容
                'type': entity.get('type', '实体'),  # 向后兼容
                'properties': {},
                'relations': {}
            }
            
            # 处理属性
            if entity.get('properties'):
                standardized_entity['properties'] = self._build_entity_properties(entity)
            
            # 处理关系
            if entity.get('relations'):
                standardized_entity['relations'] = self._build_entity_relations(entity)
            
            logger.debug(f"标准化实体完成: {entity_name}")
            return standardized_entity
            
        except Exception as e:
            logger.error(f"标准化实体时发生错误: {e}")
            return None
    
    def _validate_english_name(self, name: str) -> bool:
        """验证英文名称是否符合OpenSPG规范"""
        if not name:
            return False
        
        # 检查是否以大写字母开头
        if not name[0].isupper():
            return False
        
        # 检查是否只包含字母和数字
        if not name.replace('_', '').replace('-', '').isalnum():
            return False
        
        # 检查是否包含非法字符
        if '_' in name or '-' in name or any(c.isspace() for c in name):
            return False
        
        return True
    
    def _fix_english_name(self, name: str) -> str:
        """尝试修复英文名称格式"""
        if not name:
            return ''
        
        # 移除特殊字符和空格
        fixed = re.sub(r'[^a-zA-Z0-9]', '', name)
        
        # 确保首字母大写
        if fixed and fixed[0].islower():
            fixed = fixed[0].upper() + fixed[1:]
        
        # 检查是否以数字开头
        if fixed and fixed[0].isdigit():
            return ''
        
        return fixed if self._validate_english_name(fixed) else ''
    
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
        """构建实体属性（符合OpenSPG标准）"""
        properties = {}
        
        # 处理自定义属性
        if entity.get('properties'):
            for prop_key, prop_value in entity['properties'].items():
                if isinstance(prop_value, dict):
                    # 标准化属性名称（首字母小写）
                    standardized_key = self._standardize_property_name(prop_key)
                    
                    # 获取属性信息
                    prop_name_full = prop_value.get('name', f'{prop_key}({prop_key})')
                    prop_type = prop_value.get('type', 'Text')
                    constraint = prop_value.get('constraint', '')
                    description = prop_value.get('description', '')
                    
                    # 验证属性类型是否符合OpenSPG标准
                    if not self._validate_property_type(prop_type):
                        logger.warning(f"属性 {prop_key} 的类型 {prop_type} 不符合OpenSPG标准，使用Text类型")
                        prop_type = 'Text'
                    
                    # 提取中文名称
                    chinese_name = self._extract_chinese_name_from_property(prop_name_full)
                    
                    # 如果没有提取到中文名称，使用原始key作为中文名称
                    if not chinese_name or chinese_name == prop_name_full:
                        chinese_name = prop_key
                    
                    # 构建属性定义
                    prop_def = {
                        'name': f'{standardized_key}({chinese_name})',
                        'type': prop_type,
                        'chinese_name': chinese_name
                    }
                    
                    if description:
                        prop_def['description'] = description
                    
                    if constraint:
                        prop_def['constraint'] = constraint
                    
                    # 处理子属性
                    if prop_value.get('properties'):
                        prop_def['properties'] = {}
                        for sub_prop_key, sub_prop_value in prop_value['properties'].items():
                            if isinstance(sub_prop_value, dict):
                                sub_standardized_key = self._standardize_property_name(sub_prop_key)
                                sub_prop_name_full = sub_prop_value.get('name', f'{sub_prop_key}({sub_prop_key})')
                                sub_chinese_name = self._extract_chinese_name_from_property(sub_prop_name_full)
                                
                                if not sub_chinese_name or sub_chinese_name == sub_prop_name_full:
                                    sub_chinese_name = sub_prop_key
                                
                                sub_prop_def = {
                                    'name': f'{sub_standardized_key}({sub_chinese_name})',
                                    'type': sub_prop_value.get('type', 'Text'),
                                    'chinese_name': sub_chinese_name
                                }
                                
                                if sub_prop_value.get('description'):
                                    sub_prop_def['description'] = sub_prop_value['description']
                                
                                if sub_prop_value.get('constraint'):
                                    sub_prop_def['constraint'] = sub_prop_value['constraint']
                                
                                prop_def['properties'][sub_standardized_key] = sub_prop_def
                    
                    properties[standardized_key] = prop_def
                
                elif isinstance(prop_value, str):
                    # 简单字符串格式（向后兼容）
                    standardized_key = self._standardize_property_name(prop_key)
                    properties[standardized_key] = {
                        'name': f'{standardized_key}({prop_value})',
                        'type': 'Text',
                        'chinese_name': prop_value
                    }
        
        return properties
    
    def _validate_property_type(self, prop_type: str) -> bool:
        """验证属性类型是否符合OpenSPG标准"""
        # 基本类型
        basic_types = ['Text', 'Integer', 'Float']
        
        # 标准类型
        standard_types = [
            'STD.ChinaMobile', 'STD.Email', 'STD.IdCardNo', 
            'STD.MacAddress', 'STD.Date', 'STD.ChinaTelCode', 'STD.Timestamp'
        ]
        
        # 检查是否为基本类型或标准类型
        if prop_type in basic_types or prop_type in standard_types:
            return True
        
        # 检查是否为实体类型引用（首字母大写的标识符）
        if prop_type and prop_type[0].isupper() and prop_type.replace('_', '').isalnum():
            return True
        
        return False
    
    def _extract_chinese_name_from_property(self, prop_name: str) -> str:
        """从属性名称中提取中文名称"""
        # 匹配格式：propertyName(中文名称)
        import re
        match = re.search(r'\(([^)]+)\)', prop_name)
        if match:
            return match.group(1)
        return prop_name
    
    def _standardize_property_name(self, prop_name: str) -> str:
        """标准化属性名"""
        
        # 移除特殊字符，保留字母、数字和下划线
        import re
        standardized = re.sub(r'[^\w\u4e00-\u9fff]', '', prop_name)
        
        # 如果是纯中文，转换为拼音或使用英文描述
        if standardized and all('\u4e00' <= c <= '\u9fff' for c in standardized):
            # 对于中文属性名，使用简化的英文名称
            chinese_to_english = {
                '名称': 'name',
                '描述': 'description', 
                '类型': 'type',
                '值': 'value',
                '属性': 'property',
                '参数': 'parameter',
                '配置': 'config',
                '设置': 'setting'
            }
            standardized = chinese_to_english.get(standardized, f'prop_{len(standardized)}')
        
        # 确保以字母开头
        if standardized and not standardized[0].isalpha():
            standardized = 'prop_' + standardized
        
        # 确保首字母小写（符合camelCase规范）
        if standardized and standardized[0].isupper():
            standardized = standardized[0].lower() + standardized[1:]
        
        return standardized or 'customProperty'
    

    

    
    def _build_entity_relations(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """构建实体关系（符合OpenSPG标准）"""
        relations = {}
        
        # 处理关系信息
        if entity.get('relations'):
            for rel_key, rel_value in entity['relations'].items():
                if isinstance(rel_value, dict):
                    # 标准化关系名称（首字母小写）
                    standardized_key = self._standardize_relation_name(rel_key)
                    
                    # 获取关系信息
                    rel_name_full = rel_value.get('name', f'{rel_key}({rel_key})')
                    target = rel_value.get('target', 'Entity')
                    constraint = rel_value.get('constraint', '')
                    description = rel_value.get('description', '')
                    
                    # 提取中文名称
                    chinese_name = self._extract_chinese_name_from_property(rel_name_full)
                    if not chinese_name or chinese_name == rel_name_full:
                        chinese_name = rel_key
                    
                    # 构建关系定义
                    rel_def = {
                        'name': f'{standardized_key}({chinese_name})',
                        'target': target,
                        'chinese_name': chinese_name
                    }
                    
                    if description:
                        rel_def['description'] = description
                    
                    if constraint:
                        rel_def['constraint'] = constraint
                    
                    # 处理关系属性（只支持基本类型）
                    if rel_value.get('properties'):
                        rel_def['properties'] = {}
                        for rel_prop_key, rel_prop_value in rel_value['properties'].items():
                            if isinstance(rel_prop_value, dict):
                                rel_prop_standardized_key = self._standardize_property_name(rel_prop_key)
                                
                                # 验证关系属性类型（只支持基本类型）
                                rel_prop_type = rel_prop_value.get('type', 'Text')
                                if rel_prop_type not in ['Text', 'Integer', 'Float']:
                                    logger.warning(f"关系属性 {rel_prop_key} 的类型 {rel_prop_type} 不符合OpenSPG标准（关系属性只支持基本类型），使用Text类型")
                                    rel_prop_type = 'Text'
                                
                                # 处理关系属性名称
                                rel_prop_name_full = rel_prop_value.get('name', f'{rel_prop_key}({rel_prop_key})')
                                rel_prop_chinese_name = self._extract_chinese_name_from_property(rel_prop_name_full)
                                
                                if not rel_prop_chinese_name or rel_prop_chinese_name == rel_prop_name_full:
                                    rel_prop_chinese_name = rel_prop_key
                                
                                rel_prop_def = {
                                    'name': f'{rel_prop_standardized_key}({rel_prop_chinese_name})',
                                    'type': rel_prop_type,
                                    'chinese_name': rel_prop_chinese_name
                                }
                                
                                if rel_prop_value.get('description'):
                                    rel_prop_def['description'] = rel_prop_value['description']
                                
                                if rel_prop_value.get('constraint'):
                                    rel_prop_def['constraint'] = rel_prop_value['constraint']
                                
                                rel_def['properties'][rel_prop_standardized_key] = rel_prop_def
                    
                    relations[standardized_key] = rel_def
                
                elif isinstance(rel_value, str):
                    # 简单字符串格式（向后兼容）
                    standardized_key = self._standardize_relation_name(rel_key)
                    relations[standardized_key] = {
                        'name': f'{standardized_key}({rel_value})',
                        'target': 'Entity',
                        'chinese_name': rel_value
                    }
        
        return relations
    
    def _standardize_relation_name(self, relation_name: str) -> str:
        """标准化关系名称"""
        # 移除特殊字符
        cleaned = re.sub(r'[^\w\u4e00-\u9fff]', '', relation_name)
        
        # 直接使用清理后的关系名称，如果是英文则首字母小写
        if cleaned:
            # 如果是英文，首字母小写
            if re.match(r'^[a-zA-Z]', cleaned):
                return cleaned[0].lower() + cleaned[1:] if len(cleaned) > 1 else cleaned.lower()
            # 如果是中文或其他，直接返回
            return cleaned
        
        return 'relatesTo'
    
    def generate_entity_schema_string(self, entity: Dict[str, Any]) -> str:
        """生成单个实体的 Schema 字符串（符合OpenSPG标准）"""
        
        lines = []
        
        # 实体定义行（使用OpenSPG类型）
        openspg_type = entity.get('openspg_type', 'EntityType')
        entity_line = f"{entity['name']}({entity['chinese_name']}): {openspg_type}"
        lines.append(entity_line)
        
        # 添加描述
        if entity.get('description'):
            lines.append(f"    desc: {entity['description']}")
        
        # 属性部分（必须包含标准属性）
        properties = entity.get('properties', {})
        
        # 确保包含标准属性
        standard_props = {}
        
        # 检查是否已有desc属性
        has_desc = any('desc' in key.lower() or 'description' in key.lower() for key in properties.keys())
        if not has_desc:
            standard_props['desc'] = {
                'name': 'desc(描述)',
                'type': 'Text',
                'constraint': 'NotNull'
            }
        
        # 检查是否已有name属性
        has_name = any('name' in key.lower() and 'chinese' not in key.lower() for key in properties.keys())
        if not has_name:
            standard_props['name'] = {
                'name': 'name(名称)',
                'type': 'Text',
                'constraint': 'NotNull'
            }
        
        # 合并标准属性和自定义属性
        all_properties = {**standard_props, **properties}
        
        if all_properties:
            lines.append("    properties:")
            
            for prop_key, prop_def in all_properties.items():
                # 属性名称和类型（第三层缩进）
                prop_name = prop_def.get('name', f"{prop_key}({prop_def.get('chinese_name', prop_key)})")
                prop_line = f"        {prop_name}: {prop_def['type']}"
                lines.append(prop_line)
                
                # 属性描述（第四层缩进）
                if prop_def.get('description'):
                    lines.append(f"            desc: {prop_def['description']}")
                
                # 添加约束条件（第四层缩进）
                if 'constraint' in prop_def and prop_def['constraint']:
                    lines.append(f"            constraint: {prop_def['constraint']}")
                
                # 子属性（第五层缩进）
                if prop_def.get('properties'):
                    lines.append("            properties:")
                    for sub_prop_key, sub_prop_def in prop_def['properties'].items():
                        sub_prop_line = f"                {sub_prop_key}({sub_prop_def.get('chinese_name', sub_prop_key)}): {sub_prop_def['type']}"
                        lines.append(sub_prop_line)
                        
                        # 子属性描述和约束（第六层缩进）
                        if sub_prop_def.get('description'):
                            lines.append(f"                    desc: {sub_prop_def['description']}")
                        if sub_prop_def.get('constraint'):
                            lines.append(f"                    constraint: {sub_prop_def['constraint']}")
        
        # 关系部分（可选）
        if entity.get('relations'):
            lines.append("    relations:")
            
            for relation_key, relation_def in entity['relations'].items():
                # 关系名称和目标类型（第三层缩进）
                relation_name = relation_def.get('name', f"{relation_key}({relation_def.get('chinese_name', relation_key)})")
                relation_line = f"        {relation_name}: {relation_def['target']}"
                lines.append(relation_line)
                
                # 关系描述（第四层缩进）
                if relation_def.get('description'):
                    lines.append(f"            desc: {relation_def['description']}")
                
                # 关系属性（第四层缩进）
                if relation_def.get('properties'):
                    lines.append("            properties:")
                    for rel_prop_key, rel_prop_def in relation_def['properties'].items():
                        rel_prop_name = rel_prop_def.get('name', f"{rel_prop_key}({rel_prop_def.get('chinese_name', rel_prop_key)})")
                        rel_prop_line = f"                {rel_prop_name}: {rel_prop_def['type']}"
                        lines.append(rel_prop_line)
                        
                        # 关系属性描述和约束（第六层缩进）
                        if rel_prop_def.get('description'):
                            lines.append(f"                    desc: {rel_prop_def['description']}")
                        if rel_prop_def.get('constraint'):
                            lines.append(f"                    constraint: {rel_prop_def['constraint']}")
                
                # 关系约束条件（第四层缩进）
                if 'constraint' in relation_def and relation_def['constraint']:
                    lines.append(f"            constraint: {relation_def['constraint']}")
        
        return '\n'.join(lines)
    
    def generate_complete_schema(self, entities: List[Dict[str, Any]], namespace: str = "DEFAULT") -> str:
        """生成完整的OpenSPG Schema脚本"""
        
        lines = []
        
        # 添加命名空间声明
        lines.append(f"namespace {namespace}")
        lines.append("")
        
        # 按依赖顺序排序实体
        sorted_entities = self._sort_entities_by_dependency(entities)
        
        # 生成每个实体的Schema定义
        for i, entity in enumerate(sorted_entities):
            entity_schema = self.generate_entity_schema_string(entity)
            lines.append(entity_schema)
            
            # 在实体之间添加空行（除了最后一个）
            if i < len(sorted_entities) - 1:
                lines.append("")
        
        return '\n'.join(lines)
    
    def _sort_entities_by_dependency(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """按依赖关系对实体进行排序，确保被引用的实体在引用它的实体之前定义"""
        
        # 创建实体名称到实体的映射
        entity_map = {entity['name']: entity for entity in entities}
        
        # 构建依赖图
        dependencies = {}
        for entity in entities:
            entity_name = entity['name']
            dependencies[entity_name] = set()
            
            # 检查属性中的依赖
            if entity.get('properties'):
                for prop_def in entity['properties'].values():
                    prop_type = prop_def.get('type', '')
                    # 如果属性类型是自定义实体类型
                    if prop_type in entity_map and prop_type != entity_name:
                        dependencies[entity_name].add(prop_type)
            
            # 检查关系中的依赖
            if entity.get('relations'):
                for rel_def in entity['relations'].values():
                    target = rel_def.get('target', '')
                    if target in entity_map and target != entity_name:
                        dependencies[entity_name].add(target)
        
        # 拓扑排序
        sorted_entities = []
        visited = set()
        temp_visited = set()
        
        def dfs(entity_name):
            if entity_name in temp_visited:
                # 检测到循环依赖，记录警告但继续处理
                logger.warning(f"检测到循环依赖，涉及实体: {entity_name}")
                return
            
            if entity_name in visited:
                return
            
            temp_visited.add(entity_name)
            
            # 先访问依赖的实体
            for dep in dependencies.get(entity_name, set()):
                if dep in entity_map:
                    dfs(dep)
            
            temp_visited.remove(entity_name)
            visited.add(entity_name)
            
            if entity_name in entity_map:
                sorted_entities.append(entity_map[entity_name])
        
        # 对所有实体进行DFS
        for entity_name in entity_map.keys():
            if entity_name not in visited:
                dfs(entity_name)
        
        logger.info(f"实体依赖排序完成，排序后顺序: {[e['name'] for e in sorted_entities]}")
        
        return sorted_entities
    
    def validate_entity(self, entity: Dict[str, Any]) -> bool:
        """验证实体格式是否符合OpenSPG标准"""
        try:
            # 检查必需字段
            if not entity.get('name'):
                logger.error(f"实体缺少名称: {entity}")
                return False
            
            if not entity.get('chinese_name'):
                logger.error(f"实体缺少中文名称: {entity}")
                return False
            
            # 检查英文名称格式（首字母大写）
            english_name = entity['name']
            if not self._validate_english_name(english_name):
                logger.error(f"英文名称格式不正确: {english_name}")
                return False
            
            # 检查OpenSPG实体类型
            openspg_type = entity.get('openspg_type')
            if openspg_type not in ['EntityType', 'ConceptType', 'EventType']:
                logger.error(f"OpenSPG实体类型不正确: {openspg_type}")
                return False
            
            # 检查传统实体类型（允许更宽松的验证）
            traditional_type = entity.get('type')
            if traditional_type:
                # 允许所有映射值以及一些常见的类型
                allowed_types = set(self.entity_type_mapping.values())
                allowed_types.update(['实体', 'Entity', 'Concept', 'Object'])
                if traditional_type not in allowed_types:
                    logger.warning(f"传统实体类型可能不标准: {traditional_type}")
                    # 不返回False，只是警告
            
            # 验证属性
            properties = entity.get('properties', {})
            for prop_name, prop_def in properties.items():
                if not self._validate_property(prop_name, prop_def):
                    return False
            
            # 验证关系
            relations = entity.get('relations', {})
            for rel_name, rel_def in relations.items():
                if not self._validate_relation(rel_name, rel_def):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"验证实体时发生错误: {e}")
            return False
    
    def _validate_property(self, prop_name: str, prop_def: Dict[str, Any]) -> bool:
        """验证属性格式"""
        # 检查必需字段
        if not prop_def.get('name'):
            logger.error(f"属性缺少名称: {prop_name}")
            return False
        
        if not prop_def.get('type'):
            logger.error(f"属性缺少类型: {prop_name}")
            return False
        
        # 验证属性类型
        prop_type = prop_def['type']
        valid_basic_types = ['Text', 'Integer', 'Float']
        valid_std_types = ['STD.ChinaMobile', 'STD.Email', 'STD.IdCardNo', 'STD.MacAddress', 
                          'STD.Date', 'STD.ChinaTelCode', 'STD.Timestamp']
        
        if prop_type not in valid_basic_types and prop_type not in valid_std_types:
            # 可能是实体类型引用，暂时允许
            logger.debug(f"属性类型可能是实体引用: {prop_type}")
        
        # 检查约束条件
        constraint = prop_def.get('constraint', '')
        if constraint:
            valid_constraints = ['NotNull', 'MultiValue', 'Enum', 'Regular']
            constraint_parts = [c.strip() for c in constraint.split(',')]
            for part in constraint_parts:
                if '=' in part:
                    constraint_type = part.split('=')[0].strip()
                    if constraint_type not in valid_constraints:
                        logger.warning(f"未知约束类型: {constraint_type}")
                elif part not in valid_constraints:
                    logger.warning(f"未知约束: {part}")
        
        # 验证子属性
        if prop_def.get('properties'):
            for sub_prop_name, sub_prop_def in prop_def['properties'].items():
                if not self._validate_property(sub_prop_name, sub_prop_def):
                    return False
        
        return True
    
    def _validate_relation(self, rel_name: str, rel_def: Dict[str, Any]) -> bool:
        """验证关系格式"""
        # 检查必需字段
        if not rel_def.get('name'):
            logger.error(f"关系缺少名称: {rel_name}")
            return False
        
        if not rel_def.get('target'):
            logger.error(f"关系缺少目标类型: {rel_name}")
            return False
        
        # 检查约束条件
        constraint = rel_def.get('constraint', '')
        if constraint:
            valid_constraints = ['NotNull', 'MultiValue']
            constraint_parts = [c.strip() for c in constraint.split(',')]
            for part in constraint_parts:
                if part not in valid_constraints:
                    logger.warning(f"关系约束不正确: {part}")
        
        # 验证关系属性（只支持基本类型）
        if rel_def.get('properties'):
            for rel_prop_name, rel_prop_def in rel_def['properties'].items():
                rel_prop_type = rel_prop_def.get('type', 'Text')
                if rel_prop_type not in ['Text', 'Integer', 'Float']:
                    logger.error(f"关系属性 {rel_prop_name} 的类型 {rel_prop_type} 不符合OpenSPG标准（关系属性只支持基本类型）")
                    return False
        
        return True
    
    def get_supported_entity_types(self) -> List[str]:
        """获取支持的实体类型列表"""
        return list(set(self.entity_type_mapping.values()))
    
    def get_category_mapping(self) -> Dict[str, str]:
        """获取类别映射"""
        return self.entity_type_mapping.copy()