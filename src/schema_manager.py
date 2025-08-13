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
            # 确定OpenSPG类型
            final_openspg_type = openspg_type or entity_type or 'EntityType'
            
            # 处理属性 - ConceptType使用简化格式，不添加标准属性
            if final_openspg_type == 'ConceptType':
                # ConceptType使用简化格式，只保留传入的自定义属性（如果有）
                final_properties = properties or {}
            else:
                # EntityType和EventType需要标准化属性
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
                'openspg_type': final_openspg_type,  # OpenSPG标准类型
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
    
    def merge_and_remove_duplicate_entities(self) -> Dict[str, Any]:
        """自动识别并删除重复实体，删除前合并properties和relations"""
        import logging
        logger = logging.getLogger(__name__)
        
        result = {
            'merged_entities': [],
            'removed_entities': [],
            'total_removed': 0
        }
        
        # 构建实体相似性映射
        entity_groups = self._group_similar_entities()
        
        for group in entity_groups:
            if len(group) > 1:
                # 选择主实体（通常是名称最短或最标准的）
                primary_entity = self._select_primary_entity(group)
                duplicates = [e for e in group if e != primary_entity]
                
                logger.info(f"发现重复实体组，主实体: {primary_entity}, 重复实体: {[e for e in duplicates]}")
                
                # 合并properties和relations到主实体
                merged_properties, merged_relations = self._merge_entity_data(primary_entity, duplicates)
                
                # 更新主实体
                if primary_entity in self.entities:
                    self.entities[primary_entity]['properties'].update(merged_properties)
                    self.entities[primary_entity]['relations'].update(merged_relations)
                    self.entities[primary_entity]['last_modified'] = datetime.now().isoformat()
                
                # 删除重复实体
                for duplicate in duplicates:
                    if duplicate in self.entities:
                        old_entity = self.entities[duplicate].copy()
                        del self.entities[duplicate]
                        
                        # 记录删除
                        self._record_modification('deleted', duplicate, old_entity, None)
                        result['removed_entities'].append(duplicate)
                        result['total_removed'] += 1
                        
                        logger.info(f"删除重复实体: {duplicate}")
                
                result['merged_entities'].append({
                    'primary': primary_entity,
                    'merged_from': duplicates,
                    'merged_properties_count': len(merged_properties),
                    'merged_relations_count': len(merged_relations)
                })
        
        logger.info(f"重复实体清理完成，删除了 {result['total_removed']} 个重复实体")
        return result
    
    def _group_similar_entities(self) -> List[List[str]]:
        """将相似的实体分组"""
        groups = []
        processed = set()
        
        for entity_name in self.entities.keys():
            if entity_name in processed:
                continue
                
            similar_group = [entity_name]
            processed.add(entity_name)
            
            # 查找相似实体
            for other_name in self.entities.keys():
                if other_name != entity_name and other_name not in processed:
                    if self._are_entities_similar(entity_name, other_name):
                        similar_group.append(other_name)
                        processed.add(other_name)
            
            if len(similar_group) > 1:
                groups.append(similar_group)
        
        return groups
    
    def _are_entities_similar(self, entity1: str, entity2: str) -> bool:
        """判断两个实体是否相似（可能是重复的）"""
        e1 = self.entities.get(entity1, {})
        e2 = self.entities.get(entity2, {})
        
        # 检查英文名称相似性
        name1 = entity1.lower().replace('_', '').replace('-', '')
        name2 = entity2.lower().replace('_', '').replace('-', '')
        
        # 完全相同的名称（忽略大小写和分隔符）
        if name1 == name2:
            return True
        
        # 检查中文名称是否相同
        chinese1 = e1.get('chinese_name', '').strip()
        chinese2 = e2.get('chinese_name', '').strip()
        if chinese1 and chinese2 and chinese1 == chinese2:
            return True
        
        # 检查一个是另一个的子串（可能是缩写）
        if (len(name1) > 3 and len(name2) > 3 and 
            (name1 in name2 or name2 in name1)):
            return True
        
        # 检查描述相似性（简单的关键词匹配）
        desc1 = e1.get('description', '').lower()
        desc2 = e2.get('description', '').lower()
        if desc1 and desc2 and len(desc1) > 10 and len(desc2) > 10:
            # 计算描述的相似度（简单的词汇重叠）
            words1 = set(desc1.split())
            words2 = set(desc2.split())
            if len(words1) > 0 and len(words2) > 0:
                overlap = len(words1.intersection(words2))
                total = len(words1.union(words2))
                similarity = overlap / total if total > 0 else 0
                if similarity > 0.7:  # 70%的词汇重叠
                    return True
        
        return False
    
    def _select_primary_entity(self, entity_group: List[str]) -> str:
        """从实体组中选择主实体（保留的实体）"""
        # 优先选择名称最短且最标准的实体
        # 标准性判断：包含完整单词、没有特殊字符、有完整描述等
        
        scored_entities = []
        
        for entity_name in entity_group:
            entity = self.entities.get(entity_name, {})
            score = 0
            
            # 名称长度评分（较短的名称通常更标准）
            score += max(0, 50 - len(entity_name))
            
            # 描述完整性评分
            desc = entity.get('description', '')
            if len(desc) > 20:
                score += 20
            elif len(desc) > 10:
                score += 10
            
            # 中文名称存在性评分
            if entity.get('chinese_name'):
                score += 15
            
            # 属性数量评分
            props_count = len(entity.get('properties', {}))
            score += min(props_count * 5, 25)
            
            # 关系数量评分
            relations_count = len(entity.get('relations', {}))
            score += min(relations_count * 3, 15)
            
            # 名称标准性评分（驼峰命名、无特殊字符）
            if entity_name.replace('_', '').replace('-', '').isalnum():
                score += 10
            
            scored_entities.append((entity_name, score))
        
        # 返回得分最高的实体
        scored_entities.sort(key=lambda x: x[1], reverse=True)
        return scored_entities[0][0]
    
    def _merge_entity_data(self, primary_entity: str, duplicate_entities: List[str]) -> tuple:
        """合并重复实体的properties和relations到主实体"""
        merged_properties = {}
        merged_relations = {}
        
        # 收集所有重复实体的数据
        all_entities = [primary_entity] + duplicate_entities
        
        for entity_name in all_entities:
            entity = self.entities.get(entity_name, {})
            
            # 合并properties
            entity_props = entity.get('properties', {})
            for prop_key, prop_value in entity_props.items():
                if prop_key not in merged_properties:
                    merged_properties[prop_key] = prop_value
                else:
                    # 如果属性已存在，保留更完整的定义
                    existing = merged_properties[prop_key]
                    if isinstance(prop_value, dict) and isinstance(existing, dict):
                        # 合并字典类型的属性定义
                        for k, v in prop_value.items():
                            if k not in existing or not existing[k]:
                                existing[k] = v
            
            # 合并relations
            entity_relations = entity.get('relations', {})
            for rel_key, rel_value in entity_relations.items():
                if rel_key not in merged_relations:
                    merged_relations[rel_key] = rel_value
                else:
                    # 如果关系已存在，保留更完整的定义
                    existing = merged_relations[rel_key]
                    if isinstance(rel_value, dict) and isinstance(existing, dict):
                        for k, v in rel_value.items():
                            if k not in existing or not existing[k]:
                                existing[k] = v
        
        # 移除主实体原有的properties和relations（避免重复计算）
        primary_props = self.entities.get(primary_entity, {}).get('properties', {})
        primary_relations = self.entities.get(primary_entity, {}).get('relations', {})
        
        # 只返回新增的properties和relations
        new_properties = {k: v for k, v in merged_properties.items() if k not in primary_props}
        new_relations = {k: v for k, v in merged_relations.items() if k not in primary_relations}
        
        return new_properties, new_relations
    
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
        
        # 为ConceptType添加hypernymPredicate并使用简化格式
        if openspg_type == 'ConceptType':
            lines.append("\thypernymPredicate: isA")
            # ConceptType使用简化格式，不包含properties和relations
            return '\n'.join(lines)
        
        # 属性部分（符合OpenSPG标准）- 仅对EntityType和EventType
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
        
        # 关系部分（符合OpenSPG标准）- 仅对EntityType和EventType
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
        """验证并更新所有实体的relations，将中文实体名称替换为英文实体名称，自动创建缺失实体，合并重复关系"""
        from src.logger import logger
        
        logger.info(f"开始验证和更新关系，共有 {len(self.entities)} 个实体")
        
        validation_result = {
            'updated_entities': [],
            'invalid_relations': [],
            'created_entities': [],
            'merged_relations': [],
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
        
        # 遍历所有实体，验证和更新relations（使用列表避免字典大小变化问题）
        entities_to_process = list(self.entities.items())
        for entity_key, entity in entities_to_process:
            from src.logger import logger
            logger.debug(f"开始处理实体: {entity_key} ({entity.get('chinese_name', 'N/A')})")
            
            relations = entity.get('relations', {})
            if not relations:
                logger.debug(f"实体 {entity_key} 没有关系定义，跳过")
                continue
                
            logger.debug(f"实体 {entity_key} 有 {len(relations)} 个关系需要验证: {list(relations.keys())}")
                
            updated_relations = {}
            entity_updated = False
            
            # 用于检测重复关系的字典：target -> [relation_keys]
            target_to_relations = {}
            
            for relation_key, relation_def in relations.items():
                logger.debug(f"处理实体 {entity_key} 的关系: {relation_key} -> {relation_def}")
                
                if isinstance(relation_def, dict) and 'target' in relation_def:
                    target = relation_def['target']
                    original_target = target
                    logger.debug(f"关系 {entity_key}.{relation_key} 的目标: {target} (类型: {type(target)})")
                    
                    # 检查target是否为有效值
                    if target is None or not isinstance(target, str) or not target.strip():
                        logger.warning(f"跳过实体 {entity_key} 的无效关系 {relation_key}: target={target} (类型: {type(target)})")
                        continue  # 跳过无效的关系定义
                    
                    # 检查target是否为中文实体名称，需要转换为英文名称
                    if target in chinese_to_english:
                        # 找到对应的英文名称
                        english_target = chinese_to_english[target]
                        relation_def['target'] = english_target
                        target = english_target
                        entity_updated = True
                        
                        validation_result['updated_entities'].append({
                            'entity': entity.get('name', entity_key),
                            'relation': relation_key,
                            'old_target': original_target,
                            'new_target': english_target
                        })
                    
                    # 检查target是否为有效的实体名称
                    elif target not in english_names and target not in chinese_to_english:
                        # 自动创建缺失的目标实体
                        self._create_missing_entity(target)
                        english_names.add(target)
                        entity_updated = True
                        
                        validation_result['created_entities'].append({
                            'entity': target,
                            'reason': f'为关系 {entity.get("name", entity_key)}.{relation_key} 自动创建'
                        })
                    
                    # 检测重复关系（相同target，不同relation名称）
                    if target in target_to_relations:
                        target_to_relations[target].append(relation_key)
                    else:
                        target_to_relations[target] = [relation_key]
                    
                    updated_relations[relation_key] = relation_def
                
                else:
                    # 兼容旧格式：relation_key: target_value
                    target = relation_def
                    original_target = target
                    logger.debug(f"处理旧格式关系 {entity_key}.{relation_key}: {target} (类型: {type(target)})")
                    
                    # 检查target是否为有效值
                    if target is None or not isinstance(target, str) or not target.strip():
                        logger.warning(f"跳过实体 {entity_key} 的无效旧格式关系 {relation_key}: target={target} (类型: {type(target)})")
                        continue  # 跳过无效的关系定义
                    
                    if target in chinese_to_english:
                        # 转换为新格式并更新target
                        english_target = chinese_to_english[target]
                        target = english_target
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
                        # 自动创建缺失的目标实体
                        self._create_missing_entity(target)
                        english_names.add(target)
                        entity_updated = True
                        
                        validation_result['created_entities'].append({
                            'entity': target,
                            'reason': f'为关系 {entity.get("name", entity_key)}.{relation_key} 自动创建'
                        })
                        
                        # 转换为新格式
                        updated_relations[relation_key] = {
                            'name': relation_key,
                            'target': target
                        }
                    
                    else:
                        # target已经是英文名称，转换为新格式
                        updated_relations[relation_key] = {
                            'name': relation_key,
                            'target': target
                        }
                    
                    # 检测重复关系（相同target，不同relation名称）
                    if target in target_to_relations:
                        target_to_relations[target].append(relation_key)
                    else:
                        target_to_relations[target] = [relation_key]
            
            # 处理重复关系：合并相同target的不同关系名称
            for target, relation_keys in target_to_relations.items():
                if len(relation_keys) > 1:
                    # 选择第一个关系作为主关系，其他关系名称作为别名
                    primary_relation = relation_keys[0]
                    merged_names = [updated_relations[key].get('name', key) for key in relation_keys]
                    
                    # 更新主关系，添加别名信息
                    if 'aliases' not in updated_relations[primary_relation]:
                        updated_relations[primary_relation]['aliases'] = []
                    
                    for i, key in enumerate(relation_keys[1:], 1):
                        updated_relations[primary_relation]['aliases'].append(merged_names[i])
                        # 移除重复的关系
                        del updated_relations[key]
                    
                    validation_result['merged_relations'].append({
                        'entity': entity.get('name', entity_key),
                        'target': target,
                        'primary_relation': primary_relation,
                        'merged_relations': relation_keys[1:],
                        'all_names': merged_names
                    })
                    
                    entity_updated = True
            
            # 如果有更新，保存到实体中
            if entity_updated or updated_relations != relations:
                self.entities[entity_key]['relations'] = updated_relations
                self.last_modified = datetime.now()
                logger.info(f"实体 {entity_key} 的关系已更新，最终关系数量: {len(updated_relations)}")
            else:
                logger.debug(f"实体 {entity_key} 的关系无需更新")
        
        logger.info(f"关系验证完成 - 更新: {len(validation_result['updated_entities'])}, 创建: {len(validation_result['created_entities'])}, 合并: {len(validation_result['merged_relations'])}, 无效: {len(validation_result['invalid_relations'])}")
        return validation_result
    
    def _create_missing_entity(self, entity_name: str) -> None:
        """自动创建缺失的目标实体（最简单形式）"""
        from src.logger import logger
        
        # 生成中文名称（如果实体名称包含中文字符，则使用原名称，否则使用英文名称）
        chinese_name = entity_name
        if not any('\u4e00' <= char <= '\u9fff' for char in entity_name):
            # 如果是纯英文名称，尝试生成一个简单的中文名称
            chinese_name = entity_name
        
        # 创建最简单的实体结构
        new_entity = {
            'name': entity_name,
            'english_name': entity_name,
            'chinese_name': chinese_name,
            'description': f'自动创建的实体：{chinese_name}',
            'openspg_type': 'EntityType',
            'entity_type': 'Concept',
            'properties': self._build_standard_properties(),
            'relations': {},
            'created_at': datetime.now().isoformat(),
            'auto_created': True
        }
        
        # 添加到实体集合中
        self.entities[entity_name] = new_entity
        self.last_modified = datetime.now()
        
        logger.info(f"自动创建实体: {entity_name} ({chinese_name})")
    
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