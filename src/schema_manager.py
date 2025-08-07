from typing import Dict, List, Any, Optional
import json
import yaml
from datetime import datetime

class SchemaManager:
    """Schema 管理器，用于管理和维护 OpenSPG Schema"""
    
    def __init__(self, namespace: str = "Engineering"):
        self.namespace = namespace
        self.entities = {}  # 存储所有实体
        self.creation_time = datetime.now()
        self.last_modified = datetime.now()
        
        # 统计信息
        self.stats = {
            'total_entities': 0,
            'total_properties': 0,
            'entity_types': {},
            'modifications': []
        }
    
    def add_or_update_entity(self, entity_name: str, description: str, properties: Dict[str, Any] = None, chinese_name: str = None, relations: Dict[str, Any] = None, openspg_type: str = None, entity_type: str = None) -> Dict[str, str]:
        """添加或更新实体（支持OpenSPG标准）"""
        
        properties = properties or {}
        relations = relations or {}
        
        # 检查实体是否已存在
        if entity_name in self.entities:
            # 更新现有实体
            old_entity = self.entities[entity_name].copy()
            
            # 合并属性 - 如果传入的properties已经是完整的属性定义，直接使用；否则合并
            if properties and any(isinstance(v, dict) and 'name' in v for v in properties.values()):
                # 传入的是完整的属性定义，直接使用
                merged_properties = properties
            else:
                # 传入的是简单属性，需要合并和标准化
                merged_properties = old_entity.get('properties', {}).copy()
                merged_properties.update(self._build_standard_properties(properties))
            
            # 合并关系
            merged_relations = old_entity.get('relations', {}).copy()
            merged_relations.update(relations)
            
            # 更新实体
            update_data = {
                'description': description,
                'properties': merged_properties,
                'relations': merged_relations,
                'last_modified': datetime.now().isoformat()
            }
            
            # 如果提供了中文名称，则更新
            if chinese_name:
                update_data['chinese_name'] = chinese_name
            
            # 如果提供了OpenSPG类型，则更新
            if openspg_type:
                update_data['openspg_type'] = openspg_type
            
            # 如果提供了实体类型，则更新
            if entity_type:
                update_data['type'] = entity_type
                
            self.entities[entity_name].update(update_data)
            
            # 记录修改
            self._record_modification('updated', entity_name, old_entity, self.entities[entity_name])
            
            return {'action': 'updated', 'entity': entity_name}
        
        else:
            # 创建新实体
            # 处理属性 - 如果传入的properties已经是完整的属性定义，直接使用；否则标准化
            if properties and any(isinstance(v, dict) and 'name' in v for v in properties.values()):
                # 传入的是完整的属性定义，直接使用
                final_properties = properties
            else:
                # 传入的是简单属性，需要标准化
                final_properties = self._build_standard_properties(properties)
            
            new_entity = {
                'name': entity_name,
                'chinese_name': chinese_name or entity_name,
                'description': description,
                'type': entity_type or self._determine_entity_type(entity_name, description),
                'openspg_type': openspg_type or 'EntityType',  # OpenSPG标准类型
                'properties': final_properties,
                'relations': relations,
                'created': datetime.now().isoformat(),
                'last_modified': datetime.now().isoformat()
            }
            
            self.entities[entity_name] = new_entity
            
            # 记录创建
            self._record_modification('created', entity_name, None, new_entity)
            
            return {'action': 'created', 'entity': entity_name}
    
    def remove_entity(self, entity_name: str) -> bool:
        """删除实体"""
        
        if entity_name in self.entities:
            old_entity = self.entities[entity_name].copy()
            del self.entities[entity_name]
            
            # 记录删除
            self._record_modification('deleted', entity_name, old_entity, None)
            
            return True
        
        return False
    
    def get_entity(self, entity_name: str) -> Optional[Dict[str, Any]]:
        """获取指定实体"""
        return self.entities.get(entity_name)
    
    def get_all_entities(self) -> List[Dict[str, Any]]:
        """获取所有实体"""
        return list(self.entities.values())
    
    def get_entities_by_type(self, entity_type: str) -> List[Dict[str, Any]]:
        """根据类型获取实体"""
        return [entity for entity in self.entities.values() if entity.get('type') == entity_type]
    
    def search_entities(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索实体"""
        keyword = keyword.lower()
        results = []
        
        for entity in self.entities.values():
            # 在名称和描述中搜索
            if (keyword in entity.get('name', '').lower() or 
                keyword in entity.get('description', '').lower() or
                keyword in entity.get('chinese_name', '').lower()):
                results.append(entity)
        
        return results
    
    def generate_schema_string(self) -> str:
        """生成完整的 OpenSPG Schema 字符串"""
        
        lines = []
        
        # 命名空间
        lines.append(f"namespace {self.namespace}")
        lines.append("")
        
        # 按类型分组实体
        entities_by_type = {}
        for entity in self.entities.values():
            entity_type = entity.get('type', 'Others')
            if entity_type not in entities_by_type:
                entities_by_type[entity_type] = []
            entities_by_type[entity_type].append(entity)
        
        # 生成每个实体的定义
        for entity_type in sorted(entities_by_type.keys()):
            for entity in sorted(entities_by_type[entity_type], key=lambda x: x['name']):
                entity_schema = self._generate_entity_schema_string(entity)
                lines.append(entity_schema)
                lines.append("")
        
        return '\n'.join(lines).strip()
    
    def _generate_entity_schema_string(self, entity: Dict[str, Any]) -> str:
        """生成单个实体的 Schema 字符串（符合OpenSPG标准）"""
        
        lines = []
        
        # 实体定义行（使用OpenSPG标准类型）
        openspg_type = entity.get('openspg_type', 'EntityType')
        entity_line = f"{entity['name']}({entity['chinese_name']}): {openspg_type}"
        lines.append(entity_line)
        
        # 属性部分（符合OpenSPG标准）
        properties = entity.get('properties', {})
        if properties:
            lines.append("\tproperties:")
            
            # 按OpenSPG标准顺序排列属性：desc, name, 然后是其他属性
            standard_order = ['desc', 'name']
            
            # 先添加标准属性
            for prop_key in standard_order:
                if prop_key in properties:
                    prop_def = properties[prop_key]
                    prop_line = f"\t\t{prop_def['name']}: {prop_def['type']}"
                    lines.append(prop_line)
                    
                    # 添加约束条件（OpenSPG标准）
                    if 'constraint' in prop_def and prop_def['constraint']:
                        constraint_line = f"\t\t\tconstraint: {prop_def['constraint']}"
                        lines.append(constraint_line)
                    
                    # 添加索引信息（向后兼容）
                    if 'index' in prop_def:
                        index_line = f"\t\t\tindex: {prop_def['index']}"
                        lines.append(index_line)
            
            # 再添加自定义属性
            for prop_key, prop_def in properties.items():
                if prop_key not in standard_order:
                    prop_line = f"\t\t{prop_def['name']}: {prop_def['type']}"
                    lines.append(prop_line)
                    
                    # 添加约束条件（OpenSPG标准）
                    if 'constraint' in prop_def and prop_def['constraint']:
                        constraint_line = f"\t\t\tconstraint: {prop_def['constraint']}"
                        lines.append(constraint_line)
                    
                    # 添加索引信息（向后兼容）
                    if 'index' in prop_def:
                        index_line = f"\t\t\tindex: {prop_def['index']}"
                        lines.append(index_line)
        
        # 关系部分（符合OpenSPG标准）
        relations = entity.get('relations', {})
        if relations:
            lines.append("\trelations:")
            
            for relation_key, relation_def in relations.items():
                if isinstance(relation_def, dict) and 'name' in relation_def and 'target' in relation_def:
                    relation_line = f"\t\t{relation_def['name']}: {relation_def['target']}"
                    lines.append(relation_line)
                    
                    # 添加关系约束条件（OpenSPG标准）
                    if 'constraint' in relation_def and relation_def['constraint']:
                        constraint_line = f"\t\t\tconstraint: {relation_def['constraint']}"
                        lines.append(constraint_line)
                else:
                    # 兼容旧格式
                    relation_line = f"\t\t{relation_key}: {relation_def}"
                    lines.append(relation_line)
        
        return '\n'.join(lines)
    
    def validate_and_update_relations(self) -> Dict[str, Any]:
        """验证并更新所有实体的relations，将中文实体名称替换为英文实体名称"""
        
        validation_result = {
            'updated_entities': [],
            'invalid_relations': [],
            'warnings': []
        }
        
        # 构建实体名称映射表（中文名 -> 英文名）
        chinese_to_english = {}
        english_names = set()
        
        for entity in self.entities.values():
            chinese_name = entity.get('chinese_name', '')
            english_name = entity.get('name', '')
            
            if chinese_name and english_name:
                chinese_to_english[chinese_name] = english_name
                english_names.add(english_name)
        
        # 遍历所有实体，验证和更新relations
        for entity_key, entity in self.entities.items():
            relations = entity.get('relations', {})
            if not relations:
                continue
                
            updated_relations = {}
            entity_updated = False
            
            for relation_key, relation_def in relations.items():
                if isinstance(relation_def, dict) and 'target' in relation_def:
                    target = relation_def['target']
                    original_target = target
                    
                    # 检查target是否为中文实体名称，需要转换为英文名称
                    if target in chinese_to_english:
                        # 找到对应的英文名称
                        english_target = chinese_to_english[target]
                        relation_def['target'] = english_target
                        entity_updated = True
                        
                        validation_result['updated_entities'].append({
                            'entity': entity.get('name', entity_key),
                            'relation': relation_key,
                            'old_target': original_target,
                            'new_target': english_target
                        })
                    
                    # 检查target是否为有效的实体名称
                    elif target not in english_names and target not in chinese_to_english:
                        validation_result['invalid_relations'].append({
                            'entity': entity.get('name', entity_key),
                            'relation': relation_key,
                            'target': target,
                            'reason': '目标实体不存在'
                        })
                    
                    updated_relations[relation_key] = relation_def
                
                else:
                    # 兼容旧格式：relation_key: target_value
                    target = relation_def
                    original_target = target
                    
                    if target in chinese_to_english:
                        # 转换为新格式并更新target
                        english_target = chinese_to_english[target]
                        updated_relations[relation_key] = {
                            'name': relation_key,
                            'target': english_target
                        }
                        entity_updated = True
                        
                        validation_result['updated_entities'].append({
                            'entity': entity.get('name', entity_key),
                            'relation': relation_key,
                            'old_target': original_target,
                            'new_target': english_target
                        })
                    
                    elif target not in english_names and target not in chinese_to_english:
                        validation_result['invalid_relations'].append({
                            'entity': entity.get('name', entity_key),
                            'relation': relation_key,
                            'target': target,
                            'reason': '目标实体不存在'
                        })
                        
                        # 保持原格式但标记为无效
                        updated_relations[relation_key] = relation_def
                    
                    else:
                        # target已经是英文名称，转换为新格式
                        updated_relations[relation_key] = {
                            'name': relation_key,
                            'target': target
                        }
            
            # 如果有更新，保存到实体中
            if entity_updated or updated_relations != relations:
                self.entities[entity_key]['relations'] = updated_relations
                self.last_modified = datetime.now()
        
        return validation_result
    
    def get_entity_by_chinese_name(self, chinese_name: str) -> Optional[Dict[str, Any]]:
        """根据中文名称查找实体"""
        for entity in self.entities.values():
            if entity.get('chinese_name') == chinese_name:
                return entity
        return None
    
    def get_entity_by_english_name(self, english_name: str) -> Optional[Dict[str, Any]]:
        """根据英文名称查找实体"""
        return self.entities.get(english_name)
    
    def _build_standard_properties(self, custom_properties: Dict[str, Any] = None) -> Dict[str, Any]:
        """构建标准属性（符合OpenSPG标准）"""
        
        properties = {}
        
        # 检查自定义属性中是否已经包含标准属性
        has_desc = False
        has_name = False
        
        if custom_properties:
            for prop_name in custom_properties.keys():
                prop_lower = prop_name.lower().replace(' ', '').replace('(', '').replace(')', '')
                if 'desc' in prop_lower or 'description' in prop_lower or '描述' in prop_name:
                    has_desc = True
                elif 'name' in prop_lower or '名称' in prop_name:
                    has_name = True
        
        # 只添加不存在的标准属性（符合OpenSPG标准）
        if not has_desc:
            properties['desc'] = {
                'name': 'desc(描述)',
                'type': 'Text',
                'constraint': 'NotNull'
            }
        
        if not has_name:
            properties['name'] = {
                'name': 'name(名称)',
                'type': 'Text',
                'constraint': 'NotNull'
            }
        
        # 添加自定义属性
        if custom_properties:
            for prop_name, prop_value in custom_properties.items():
                # 跳过已经处理的标准属性
                prop_lower = prop_name.lower().replace(' ', '').replace('(', '').replace(')', '')
                if ('desc' in prop_lower or 'description' in prop_lower or '描述' in prop_name or
                    'name' in prop_lower or '名称' in prop_name):
                    continue
                
                # 检查是否是新的OpenSPG格式（包含name、type、constraint字段）
                if isinstance(prop_value, dict) and 'name' in prop_value and 'type' in prop_value:
                    # 新的OpenSPG格式，直接使用
                    properties[prop_name] = {
                        'name': prop_value.get('name', f"{prop_name}({prop_name})"),
                        'type': prop_value.get('type', 'Text'),
                        'constraint': prop_value.get('constraint', 'NotNull')
                    }
                else:
                    # 检查属性名是否已经包含中文说明
                    if '(' in prop_name and ')' in prop_name:
                        # 已经是正确格式（如："property(属性)"），直接使用
                        properties[prop_name] = {
                            'name': prop_name,
                            'type': 'Text',
                            'constraint': 'NotNull'
                        }
                    else:
                        # 旧格式，添加中文说明
                        properties[prop_name] = {
                            'name': f"{prop_name}({prop_name})",
                            'type': 'Text',
                            'constraint': 'NotNull'
                        }
        
        return properties
    
    def _determine_entity_type(self, entity_name: str, description: str) -> str:
        """根据实体名称和描述确定实体类型"""
        
        # 简单的类型推断逻辑
        text = (entity_name + " " + description).lower()
        
        type_keywords = {
            'Person': ['人员', '人物', '工程师', '设计师', '专家', '负责人'],
            'Organization': ['公司', '组织', '机构', '部门', '团队', '单位'],
            'Building': ['建筑', '房屋', '厂房', '车间', '办公楼', '结构'],
            'ArtificialObject': ['设备', '机器', '工具', '仪器', '装置', '系统', '组件'],
            'GeographicLocation': ['地点', '位置', '区域', '场所', '地址', '坐标'],
            'Date': ['时间', '日期', '期限', '周期', '阶段'],
            'Event': ['事件', '活动', '会议', '检查', '测试', '验收'],
            'Works': ['文档', '图纸', '标准', '规范', '手册', '报告'],
            'Concept': ['概念', '理论', '方法', '技术', '工艺', '流程']
        }
        
        for entity_type, keywords in type_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    return entity_type
        
        return 'Others'
    
    def _record_modification(self, action: str, entity_name: str, old_entity: Optional[Dict], new_entity: Optional[Dict]):
        """记录修改历史"""
        
        modification = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'entity_name': entity_name,
            'old_entity': old_entity,
            'new_entity': new_entity
        }
        
        self.stats['modifications'].append(modification)
        self.last_modified = datetime.now()
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        
        # 计算实时统计
        entity_count = len(self.entities)
        property_count = sum(len(entity.get('properties', {})) for entity in self.entities.values())
        
        # 按类型统计实体
        type_counts = {}
        for entity in self.entities.values():
            entity_type = entity.get('type', 'Others')
            type_counts[entity_type] = type_counts.get(entity_type, 0) + 1
        
        # 统计最近的修改
        recent_modifications = self.stats['modifications'][-10:]  # 最近10次修改
        
        return {
            'entity_count': entity_count,
            'property_count': property_count,
            'entity_types': type_counts,
            'creation_time': self.creation_time.isoformat(),
            'last_modified': self.last_modified.isoformat(),
            'total_modifications': len(self.stats['modifications']),
            'recent_modifications': recent_modifications
        }
    
    def export_to_json(self) -> str:
        """导出为 JSON 格式"""
        
        export_data = {
            'namespace': self.namespace,
            'entities': self.entities,
            'statistics': self.get_statistics(),
            'export_time': datetime.now().isoformat()
        }
        
        return json.dumps(export_data, ensure_ascii=False, indent=2)
    
    def import_from_json(self, json_data: str) -> bool:
        """从 JSON 数据导入"""
        
        try:
            data = json.loads(json_data)
            
            if 'entities' in data:
                self.entities = data['entities']
            
            if 'namespace' in data:
                self.namespace = data['namespace']
            
            self.last_modified = datetime.now()
            
            return True
            
        except Exception as e:
            print(f"导入失败: {str(e)}")
            return False
    
    def export_to_yaml(self) -> str:
        """导出为 YAML 格式，使用 tab 缩进"""
        
        export_data = {
            'namespace': self.namespace,
            'entities': self.entities,
            'statistics': self.get_statistics(),
            'export_time': datetime.now().isoformat()
        }
        
        # 使用 tab 缩进的 YAML 输出
        yaml_str = yaml.dump(
            export_data, 
            default_flow_style=False, 
            allow_unicode=True,
            indent=1,  # 基础缩进
            width=float('inf')  # 避免自动换行
        )
        
        # 将空格缩进替换为 tab 缩进
        lines = yaml_str.split('\n')
        tab_lines = []
        for line in lines:
            if line.strip():  # 非空行
                # 计算前导空格数
                leading_spaces = len(line) - len(line.lstrip())
                # 将空格转换为 tab（每个缩进级别用一个 tab）
                tab_count = leading_spaces // 2  # YAML 默认 2 空格为一个缩进级别
                tab_lines.append('\t' * tab_count + line.lstrip())
            else:
                tab_lines.append(line)
        
        return '\n'.join(tab_lines)
    
    def import_from_yaml(self, yaml_data: str) -> bool:
        """从 YAML 数据导入"""
        
        try:
            # 将 tab 缩进转换为空格缩进以便 YAML 解析
            lines = yaml_data.split('\n')
            space_lines = []
            for line in lines:
                if line.strip():  # 非空行
                    # 计算前导 tab 数
                    leading_tabs = len(line) - len(line.lstrip('\t'))
                    # 将 tab 转换为空格（每个 tab 转换为 2 个空格）
                    space_lines.append('  ' * leading_tabs + line.lstrip('\t'))
                else:
                    space_lines.append(line)
            
            space_yaml = '\n'.join(space_lines)
            data = yaml.safe_load(space_yaml)
            
            if 'entities' in data:
                self.entities = data['entities']
            
            if 'namespace' in data:
                self.namespace = data['namespace']
            
            self.last_modified = datetime.now()
            
            return True
            
        except Exception as e:
            print(f"YAML 导入失败: {str(e)}")
            return False
    
    def save_to_file(self, file_path: str, format_type: str = 'yaml') -> bool:
        """保存 Schema 到文件"""
        
        try:
            if format_type.lower() == 'yaml':
                content = self.export_to_yaml()
            elif format_type.lower() == 'json':
                content = self.export_to_json()
            else:
                raise ValueError(f"不支持的格式: {format_type}")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True
            
        except Exception as e:
            print(f"保存文件失败: {str(e)}")
            return False
    
    def load_from_file(self, file_path: str) -> bool:
        """从文件加载 Schema"""
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 根据文件扩展名判断格式
            if file_path.lower().endswith('.yaml') or file_path.lower().endswith('.yml'):
                return self.import_from_yaml(content)
            elif file_path.lower().endswith('.json'):
                return self.import_from_json(content)
            else:
                # 尝试自动检测格式
                try:
                    # 先尝试 YAML
                    return self.import_from_yaml(content)
                except:
                    # 再尝试 JSON
                    return self.import_from_json(content)
            
        except Exception as e:
            print(f"加载文件失败: {str(e)}")
            return False
    
    def clear_all(self):
        """清空所有数据"""
        self.entities = {}
        self.stats = {
            'total_entities': 0,
            'total_properties': 0,
            'entity_types': {},
            'modifications': []
        }
        self.last_modified = datetime.now()