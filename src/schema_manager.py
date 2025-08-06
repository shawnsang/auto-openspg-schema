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
    
    def add_or_update_entity(self, entity_name: str, description: str, properties: Dict[str, Any] = None) -> Dict[str, str]:
        """添加或更新实体"""
        
        properties = properties or {}
        
        # 检查实体是否已存在
        if entity_name in self.entities:
            # 更新现有实体
            old_entity = self.entities[entity_name].copy()
            
            # 合并属性
            merged_properties = old_entity.get('properties', {}).copy()
            merged_properties.update(properties)
            
            # 更新实体
            self.entities[entity_name].update({
                'description': description,
                'properties': merged_properties,
                'last_modified': datetime.now().isoformat()
            })
            
            # 记录修改
            self._record_modification('updated', entity_name, old_entity, self.entities[entity_name])
            
            return {'action': 'updated', 'entity': entity_name}
        
        else:
            # 创建新实体
            new_entity = {
                'name': entity_name,
                'chinese_name': entity_name,
                'description': description,
                'type': self._determine_entity_type(entity_name, description),
                'properties': self._build_standard_properties(properties),
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
        """生成单个实体的 Schema 字符串"""
        
        lines = []
        
        # 实体定义行
        entity_line = f"{entity['name']}({entity['chinese_name']}): EntityType"
        lines.append(entity_line)
        
        # 属性部分
        properties = entity.get('properties', {})
        if properties:
            lines.append("\tproperties:")
            
            # 按标准顺序排列属性
            standard_order = ['description', 'name', 'semanticType']
            
            # 先添加标准属性
            for prop_key in standard_order:
                if prop_key in properties:
                    prop_def = properties[prop_key]
                    prop_line = f"\t\t{prop_def['name']}: {prop_def['type']}"
                    lines.append(prop_line)
                    
                    # 添加索引信息
                    if 'index' in prop_def:
                        index_line = f"\t\t\tindex: {prop_def['index']}"
                        lines.append(index_line)
            
            # 再添加自定义属性
            for prop_key, prop_def in properties.items():
                if prop_key not in standard_order:
                    prop_line = f"\t\t{prop_def['name']}: {prop_def['type']}"
                    lines.append(prop_line)
                    
                    if 'index' in prop_def:
                        index_line = f"\t\t\tindex: {prop_def['index']}"
                        lines.append(index_line)
        
        return '\n'.join(lines)
    
    def _build_standard_properties(self, custom_properties: Dict[str, Any] = None) -> Dict[str, Any]:
        """构建标准属性"""
        
        properties = {
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
        
        # 添加自定义属性
        if custom_properties:
            for prop_name, prop_value in custom_properties.items():
                if prop_name not in properties:
                    properties[prop_name] = {
                        'name': f"{prop_name}({prop_name})",
                        'type': 'Text'
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