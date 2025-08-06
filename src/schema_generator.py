from typing import List, Dict, Any
import re
from .llm_client import LLMClient
from .logger import logger

# 简单的中文转拼音映射（常用字符）
CHINESE_TO_PINYIN = {
    '施': 'Shi', '工': 'Gong', '放': 'Fang', '线': 'Xian',
    '建': 'Jian', '筑': 'Zhu', '设': 'She', '计': 'Ji',
    '材': 'Cai', '料': 'Liao', '混': 'Hun', '凝': 'Ning',
    '土': 'Tu', '钢': 'Gang', '筋': 'Jin', '水': 'Shui',
    '泥': 'Ni', '砂': 'Sha', '石': 'Shi', '子': 'Zi',
    '管': 'Guan', '道': 'Dao', '电': 'Dian', '气': 'Qi',
    '暖': 'Nuan', '通': 'Tong', '风': 'Feng', '空': 'Kong',
    '调': 'Tiao', '系': 'Xi', '统': 'Tong', '装': 'Zhuang',
    '修': 'Xiu', '装': 'Zhuang', '饰': 'Shi', '门': 'Men',
    '窗': 'Chuang', '墙': 'Qiang', '体': 'Ti', '屋': 'Wu',
    '顶': 'Ding', '地': 'Di', '面': 'Mian', '基': 'Ji',
    '础': 'Chu', '梁': 'Liang', '柱': 'Zhu', '板': 'Ban',
    '楼': 'Lou', '层': 'Ceng', '房': 'Fang', '间': 'Jian',
    '厅': 'Ting', '室': 'Shi', '厨': 'Chu', '卫': 'Wei',
    '生': 'Sheng', '阳': 'Yang', '台': 'Tai', '走': 'Zou',
    '廊': 'Lang', '楼': 'Lou', '梯': 'Ti', '电': 'Dian',
    '梯': 'Ti', '消': 'Xiao', '防': 'Fang', '安': 'An',
    '全': 'Quan', '监': 'Jian', '控': 'Kong', '照': 'Zhao',
    '明': 'Ming', '灯': 'Deng', '具': 'Ju', '开': 'Kai',
    '关': 'Guan', '插': 'Cha', '座': 'Zuo', '配': 'Pei',
    '电': 'Dian', '箱': 'Xiang', '变': 'Bian', '压': 'Ya',
    '器': 'Qi', '发': 'Fa', '电': 'Dian', '机': 'Ji',
    '组': 'Zu', '锅': 'Guo', '炉': 'Lu', '热': 'Re',
    '水': 'Shui', '器': 'Qi', '空': 'Kong', '压': 'Ya',
    '机': 'Ji', '冷': 'Leng', '却': 'Que', '塔': 'Ta',
    '泵': 'Beng', '阀': 'Fa', '门': 'Men', '法': 'Fa',
    '兰': 'Lan', '接': 'Jie', '头': 'Tou', '弯': 'Wan',
    '头': 'Tou', '三': 'San', '通': 'Tong', '四': 'Si',
    '通': 'Tong', '异': 'Yi', '径': 'Jing', '管': 'Guan',
    '件': 'Jian', '支': 'Zhi', '架': 'Jia', '吊': 'Diao',
    '架': 'Jia', '托': 'Tuo', '架': 'Jia', '固': 'Gu',
    '定': 'Ding', '夹': 'Jia', '保': 'Bao', '温': 'Wen',
    '隔': 'Ge', '热': 'Re', '防': 'Fang', '火': 'Huo',
    '涂': 'Tu', '料': 'Liao', '密': 'Mi', '封': 'Feng',
    '胶': 'Jiao', '玻': 'Bo', '璃': 'Li', '胶': 'Jiao',
    '结': 'Jie', '构': 'Gou', '胶': 'Jiao', '螺': 'Luo',
    '栓': 'Shuan', '螺': 'Luo', '母': 'Mu', '垫': 'Dian',
    '片': 'Pian', '弹': 'Dan', '簧': 'Huang', '垫': 'Dian',
    '圈': 'Quan', '密': 'Mi', '封': 'Feng', '圈': 'Quan'
}

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
        
        # 获取实体基本信息
        original_name = entity.get('name', '').strip()
        description = entity.get('description', '').strip()
        category = entity.get('category', '其他')
        
        # 获取英文名称（优先使用LLM提供的，否则自动转换）
        llm_english_name = entity.get('english_name', '').strip()
        if llm_english_name and self._is_valid_english_name(llm_english_name):
            english_name = llm_english_name
        else:
            # 回退到自动转换
            english_name = self._convert_chinese_to_english_name(original_name)
            logger.warning(f"实体 '{original_name}' 的LLM英文名称无效或缺失，使用自动转换: {english_name}")
        
        # 确定实体类型
        entity_type = self._map_category_to_type(category)
        
        # 构建关系
        relations = self._build_entity_relations(entity)
        
        # 构建标准化实体
        standardized = {
            'name': english_name,  # 使用英文名称
            'chinese_name': original_name,  # 保留原始中文名称
            'description': description,
            'type': entity_type,
            'properties': self._build_entity_properties(entity),
            'relations': relations
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
        
        # 添加必需的基础属性
        properties['description'] = {
            'name': 'description(描述)',
            'type': 'Text'
        }
        
        properties['name'] = {
            'name': 'name(名称)',
            'type': 'Text'
        }
        
        # 添加其他标准属性
        for prop_key, prop_def in self.standard_properties.items():
            if prop_key not in ['description', 'name']:  # 避免重复基础属性
                properties[prop_key] = {
                    'name': prop_def['name'],
                    'type': prop_def['type']
                }
                
                # 添加索引信息（如果有）
                if 'index' in prop_def:
                    properties[prop_key]['index'] = prop_def['index']
        
        # 处理其他属性
        custom_properties = entity.get('properties', {})
        for prop_name, prop_desc in custom_properties.items():
            # 跳过基础属性，避免重复
            if prop_name in ['description', 'name'] or prop_name in ['description (描述)', 'name (名称)']:
                continue
                
            # 检查是否已经是英文名称加中文说明的格式
            if '(' in prop_name and ')' in prop_name:
                # 已经是正确格式，直接使用
                english_part = prop_name.split('(')[0].strip()
                standardized_prop_name = self._standardize_property_name(english_part)
                properties[standardized_prop_name] = {
                    'name': prop_name,  # 保持原有格式
                    'type': 'Text',
                    'description': prop_desc
                }
            else:
                # 旧格式，需要转换
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
    
    def _is_valid_english_name(self, name: str) -> bool:
        """验证英文名称是否有效"""
        if not name:
            return False
        
        # 检查是否只包含英文字母、数字和下划线
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', name):
            return False
        
        # 检查是否包含拼音模式（连续的大写字母，可能是拼音）
        # 如果包含类似 "ShiGong" 这样的拼音模式，认为无效
        pinyin_pattern = r'[A-Z][a-z]*[A-Z][a-z]*[A-Z][a-z]*'
        if re.search(pinyin_pattern, name) and len(name) > 10:
            # 进一步检查是否包含已知的拼音组合
            pinyin_words = ['Shi', 'Gong', 'Dao', 'Shui', 'Fang', 'Jian', 'Guan', 'Dian']
            pinyin_count = sum(1 for pinyin in pinyin_words if pinyin in name)
            if pinyin_count >= 2:  # 如果包含2个或更多拼音词，认为是拼音组合
                return False
        
        return True
    
    def _convert_chinese_to_english_name(self, chinese_name: str) -> str:
        """将中文名称转换为英文名称"""
        # 清理输入，移除特殊字符和多余的引号、逗号
        cleaned_name = re.sub(r'["\',，。！？；：]', '', chinese_name.strip())
        
        # 如果已经是英文，直接返回（首字母大写）
        if re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', cleaned_name):
            return cleaned_name.capitalize()
        
        # 转换中文字符为拼音
        english_parts = []
        for char in cleaned_name:
            if char in CHINESE_TO_PINYIN:
                english_parts.append(CHINESE_TO_PINYIN[char])
            elif char.isalpha():  # 保留英文字符
                english_parts.append(char.upper())
            elif char.isdigit():  # 保留数字
                english_parts.append(char)
            # 忽略其他字符
        
        # 组合结果
        if english_parts:
            result = ''.join(english_parts)
            # 确保首字母大写
            return result[0].upper() + result[1:] if result else 'Entity'
        else:
            # 如果无法转换，使用通用名称
            return 'Entity'
    
    def _build_entity_relations(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """构建实体关系"""
        relations = {}
        
        # 获取原始关系数据
        raw_relations = entity.get('relations', {})
        
        if not raw_relations:
            return relations
        
        # 处理每个关系
        for relation_key, relation_value in raw_relations.items():
            # 检查是否已经是英文名称加中文说明的格式
            if '(' in relation_key and ')' in relation_key:
                # 已经是正确格式，直接使用
                english_part = relation_key.split('(')[0].strip()
                relation_name = self._standardize_relation_name(english_part)
                relations[relation_name] = {
                    'name': relation_key,  # 保持原有格式
                    'target': self._convert_chinese_to_english_name(relation_value)
                }
            else:
                # 旧格式，需要转换
                relation_name = self._standardize_relation_name(relation_key)
                relations[relation_name] = {
                    'name': f"{relation_name}({relation_key})",
                    'target': self._convert_chinese_to_english_name(relation_value)
                }
        
        return relations
    
    def _standardize_relation_name(self, relation_name: str) -> str:
        """标准化关系名称"""
        # 移除特殊字符
        cleaned = re.sub(r'[^\w\u4e00-\u9fff]', '', relation_name)
        
        # 转换为英文
        english_name = self._convert_chinese_to_english_name(cleaned)
        
        # 关系名称通常是动词，首字母小写
        if english_name:
            return english_name[0].lower() + english_name[1:] if len(english_name) > 1 else english_name.lower()
        
        return 'relatesTo'
    
    def generate_entity_schema_string(self, entity: Dict[str, Any]) -> str:
        """生成单个实体的 Schema 字符串"""
        
        lines = []
        
        # 实体定义行
        entity_line = f"{entity['name']}({entity['chinese_name']}): EntityType"
        lines.append(entity_line)
        
        # 属性部分（必须包含）
        if entity.get('properties'):
            lines.append("\tproperties:")
            
            for prop_key, prop_def in entity['properties'].items():
                prop_line = f"\t\t{prop_def['name']}: {prop_def['type']}"
                lines.append(prop_line)
                
                # 添加索引信息
                if 'index' in prop_def:
                    index_line = f"\t\t\tindex: {prop_def['index']}"
                    lines.append(index_line)
        
        # 关系部分（可选）
        if entity.get('relations'):
            lines.append("\trelations:")
            
            for relation_key, relation_def in entity['relations'].items():
                relation_line = f"\t\t{relation_def['name']}: {relation_def['target']}"
                lines.append(relation_line)
        
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