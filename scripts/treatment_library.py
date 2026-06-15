# -*- coding: utf-8 -*-
"""
治疗方案库模块
提供标准治疗方案的管理、查询和导入功能
"""

import json
import os
from typing import List, Dict, Optional
from pathlib import Path


class TreatmentLibrary:
    """治疗方案库类"""

    def __init__(self, config_file: str = "treatment_schemes.json"):
        """
        初始化治疗方案库

        Args:
            config_file: 治疗方案配置文件路径
        """
        self.config_file = config_file
        self.schemes = []
        self.load_schemes()

    def load_schemes(self) -> bool:
        """
        从配置文件加载治疗方案

        Returns:
            是否加载成功
        """
        try:
            if not os.path.exists(self.config_file):
                print(f"[INFO] 配置文件 {self.config_file} 不存在，将使用空方案库")
                self.schemes = []
                return False

            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.schemes = data.get('schemes', [])

            print(f"[OK] 成功加载 {len(self.schemes)} 个治疗方案")
            return True

        except json.JSONDecodeError as e:
            print(f"[ERROR] 配置文件格式错误: {e}")
            self.schemes = []
            return False
        except Exception as e:
            print(f"[ERROR] 加载方案库失败: {e}")
            self.schemes = []
            return False

    def save_schemes(self) -> bool:
        """
        保存治疗方案到配置文件

        Returns:
            是否保存成功
        """
        temp_file = None
        try:
            data = {'schemes': self.schemes}

            # 先写入临时文件，确保原子性
            temp_file = f"{self.config_file}.tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # 重命名临时文件为正式文件
            os.replace(temp_file, self.config_file)
            temp_file = None

            print(f"[OK] 成功保存 {len(self.schemes)} 个治疗方案到 {self.config_file}")
            return True

        except Exception as e:
            print(f"[ERROR] 保存方案库失败: {e}")
            if temp_file and os.path.exists(temp_file):
                os.remove(temp_file)
            return False

    def get_all_schemes(self) -> List[Dict]:
        """
        获取所有治疗方案

        Returns:
            治疗方案列表
        """
        return self.schemes

    def get_scheme_by_id(self, scheme_id: str) -> Optional[Dict]:
        """
        根据ID获取治疗方案

        Args:
            scheme_id: 方案ID

        Returns:
            治疗方案字典，如果未找到则返回None
        """
        for scheme in self.schemes:
            if scheme.get('id') == scheme_id:
                return scheme
        return None

    def get_schemes_by_severity(self, severity: str) -> List[Dict]:
        """
        根据严重程度获取治疗方案

        Args:
            severity: 严重程度（轻度/中度/重度）

        Returns:
            治疗方案列表
        """
        return [s for s in self.schemes if severity in s.get('category', '')]

    def get_schemes_by_stage(self, stage: str) -> List[Dict]:
        """
        根据治疗阶段获取治疗方案

        Args:
            stage: 治疗阶段（急性期/稳定期/维持期）

        Returns:
            治疗方案列表
        """
        return [s for s in self.schemes if stage in s.get('category', '')]

    def list_schemes_by_category(self) -> Dict[str, List[Dict]]:
        """
        按分类组织治疗方案

        Returns:
            按分类分组的治疗方案字典
        """
        categorized = {}

        for scheme in self.schemes:
            category = scheme.get('category', '未分类')
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(scheme)

        return categorized

    def display_schemes(self) -> str:
        """
        显示所有治疗方案（按分类组织）

        Returns:
            格式化后的治疗方案列表字符串
        """
        output = []
        output.append("=" * 60)
        output.append("治疗方案库")
        output.append("=" * 60)
        output.append("")

        if not self.schemes:
            output.append("【暂无治疗方案】")
            output.append("请先创建或导入治疗方案")
            return "\n".join(output)

        # 按分类显示
        categorized = self.list_schemes_by_category()

        for category, schemes in sorted(categorized.items()):
            output.append(f"【{category}】")
            for scheme in schemes:
                scheme_id = scheme.get('id', 'N/A')
                name = scheme.get('name', 'N/A')
                medications = scheme.get('medications', [])
                med_count = len(medications)

                output.append(f"  {scheme_id}. {name} ({med_count} 种药物)")

                # 显示药物列表（简化版）
                if medications:
                    for med in medications[:2]:  # 只显示前2种
                        med_name = med.get('name', 'N/A')
                        med_dosage = med.get('dosage', '')
                        output.append(f"     - {med_name} {med_dosage}")
                    if med_count > 2:
                        output.append(f"     ... 还有 {med_count - 2} 种药物")

            output.append("")

        output.append("=" * 60)
        output.append(f"共 {len(self.schemes)} 个治疗方案，{len(categorized)} 个分类")
        output.append("=" * 60)

        return "\n".join(output)

    def display_scheme_detail(self, scheme_id: str) -> str:
        """
        显示治疗方案详细信息

        Args:
            scheme_id: 方案ID

        Returns:
            格式化后的方案详情字符串
        """
        scheme = self.get_scheme_by_id(scheme_id)

        if not scheme:
            return f"[ERROR] 未找到ID为 '{scheme_id}' 的治疗方案"

        output = []
        output.append("")
        output.append("=" * 60)
        output.append("治疗方案详情")
        output.append("=" * 60)
        output.append("")

        output.append(f"方案ID: {scheme.get('id', 'N/A')}")
        output.append(f"方案名称: {scheme.get('name', 'N/A')}")
        output.append(f"分类: {scheme.get('category', 'N/A')}")
        output.append("")

        medications = scheme.get('medications', [])
        output.append(f"【药物治疗方案】({len(medications)} 种药物)")
        output.append("")

        if medications:
            for idx, med in enumerate(medications, 1):
                output.append(f"{idx}. {med.get('name', 'N/A')}")
                output.append(f"   剂量: {med.get('dosage', 'N/A')}")

                notes = med.get('notes', '')
                if notes:
                    output.append(f"   备注: {notes}")

                output.append("")
        else:
            output.append("  该方案未包含药物治疗")
            output.append("")

        output.append("=" * 60)

        return "\n".join(output)

    def add_scheme(self, scheme: Dict) -> bool:
        """
        添加新治疗方案

        Args:
            scheme: 治疗方案字典

        Returns:
            是否添加成功
        """
        # 验证必需字段
        required_fields = ['id', 'name', 'category', 'medications']
        for field in required_fields:
            if field not in scheme:
                print(f"[ERROR] 缺少必需字段: {field}")
                return False

        # 检查ID是否重复
        if self.get_scheme_by_id(scheme['id']):
            print(f"[ERROR] 方案ID '{scheme['id']}' 已存在")
            return False

        self.schemes.append(scheme)
        return self.save_schemes()

    def update_scheme(self, scheme_id: str, updated_scheme: Dict) -> bool:
        """
        更新治疗方案

        Args:
            scheme_id: 方案ID
            updated_scheme: 更新后的方案字典

        Returns:
            是否更新成功
        """
        for idx, scheme in enumerate(self.schemes):
            if scheme.get('id') == scheme_id:
                self.schemes[idx] = updated_scheme
                return self.save_schemes()

        print(f"[ERROR] 未找到ID为 '{scheme_id}' 的治疗方案")
        return False

    def delete_scheme(self, scheme_id: str) -> bool:
        """
        删除治疗方案

        Args:
            scheme_id: 方案ID

        Returns:
            是否删除成功
        """
        original_length = len(self.schemes)
        self.schemes = [s for s in self.schemes if s.get('id') != scheme_id]

        if len(self.schemes) == original_length:
            print(f"[ERROR] 未找到ID为 '{scheme_id}' 的治疗方案")
            return False

        return self.save_schemes()

    def format_medication_plan(self, scheme: Dict) -> str:
        """
        格式化治疗方案为字符串（用于导入到患者治疗计划）

        Args:
            scheme: 治疗方案字典

        Returns:
            格式化后的治疗方案字符串
        """
        medications = scheme.get('medications', [])

        if not medications:
            return "无药物治疗"

        lines = []
        lines.append(f"【{scheme.get('name', 'N/A')}】")

        for med in medications:
            line_parts = []

            med_name = med.get('name', '')
            med_dosage = med.get('dosage', '')
            med_notes = med.get('notes', '')

            if med_name:
                line_parts.append(med_name)
            if med_dosage:
                line_parts.append(med_dosage)
            if med_notes:
                line_parts.append(f"({med_notes})")

            if line_parts:
                lines.append(" - " + " ".join(line_parts))

        return "\n".join(lines)


def create_default_schemes(config_file: str = "treatment_schemes.json") -> bool:
    """
    创建默认治疗方案配置文件

    Args:
        config_file: 配置文件路径

    Returns:
        是否创建成功
    """
    # 默认治疗方案
    default_schemes = {
        "schemes": [
            {
                "id": "light_acute",
                "name": "轻度酒精依赖-急性期",
                "category": "轻度-急性期",
                "medications": [
                    {
                        "name": "地西泮",
                        "dosage": "5mg po tid",
                        "notes": "递减治疗，疗程7-10天"
                    },
                    {
                        "name": "维生素B1",
                        "dosage": "100mg po tid",
                        "notes": "预防Wernicke脑病"
                    },
                    {
                        "name": "叶酸",
                        "dosage": "5mg po qd",
                        "notes": "补充叶酸缺乏"
                    }
                ]
            },
            {
                "id": "moderate_acute",
                "name": "中度酒精依赖-急性期",
                "category": "中度-急性期",
                "medications": [
                    {
                        "name": "地西泮",
                        "dosage": "10mg po qid",
                        "notes": "递减治疗，疗程10-14天"
                    },
                    {
                        "name": "纳曲酮",
                        "dosage": "50mg po qd",
                        "notes": "抗渴求，长期使用"
                    },
                    {
                        "name": "维生素B1",
                        "dosage": "100mg po tid",
                        "notes": "预防Wernicke脑病"
                    },
                    {
                        "name": "叶酸",
                        "dosage": "5mg po qd",
                        "notes": "补充叶酸缺乏"
                    }
                ]
            },
            {
                "id": "severe_acute",
                "name": "重度酒精依赖-急性期",
                "category": "重度-急性期",
                "medications": [
                    {
                        "name": "地西泮",
                        "dosage": "10-20mg po qid",
                        "notes": "递减治疗，疗程14-21天，密切监测"
                    },
                    {
                        "name": "纳曲酮",
                        "dosage": "50mg po qd",
                        "notes": "抗渴求，长期使用"
                    },
                    {
                        "name": "阿坎酸",
                        "dosage": "666mg po tid",
                        "notes": "抗渴求，可联用纳曲酮"
                    },
                    {
                        "name": "维生素B1",
                        "dosage": "100mg im/iv qd",
                        "notes": "急性期静脉或肌注"
                    },
                    {
                        "name": "叶酸",
                        "dosage": "5mg po qd",
                        "notes": "补充叶酸缺乏"
                    }
                ]
            },
            {
                "id": "light_stable",
                "name": "轻度酒精依赖-稳定期",
                "category": "轻度-稳定期",
                "medications": [
                    {
                        "name": "纳曲酮",
                        "dosage": "50mg po qd",
                        "notes": "抗渴求，疗程3-6个月"
                    },
                    {
                        "name": "维生素B1",
                        "dosage": "100mg po qd",
                        "notes": "维持治疗"
                    }
                ]
            },
            {
                "id": "moderate_stable",
                "name": "中度酒精依赖-稳定期",
                "category": "中度-稳定期",
                "medications": [
                    {
                        "name": "纳曲酮",
                        "dosage": "50mg po qd",
                        "notes": "抗渴求，疗程6-12个月"
                    },
                    {
                        "name": "阿坎酸",
                        "dosage": "666mg po tid",
                        "notes": "可单用或联用纳曲酮"
                    },
                    {
                        "name": "维生素B1",
                        "dosage": "100mg po qd",
                        "notes": "维持治疗"
                    }
                ]
            },
            {
                "id": "severe_stable",
                "name": "重度酒精依赖-稳定期",
                "category": "重度-稳定期",
                "medications": [
                    {
                        "name": "纳曲酮",
                        "dosage": "50mg po qd",
                        "notes": "抗渴求，疗程12个月以上"
                    },
                    {
                        "name": "阿坎酸",
                        "dosage": "666mg po tid",
                        "notes": "联用纳曲酮增强效果"
                    },
                    {
                        "name": "维生素B1",
                        "dosage": "100mg po qd",
                        "notes": "维持治疗"
                    },
                    {
                        "name": "叶酸",
                        "dosage": "5mg po qd",
                        "notes": "维持补充"
                    }
                ]
            },
            {
                "id": "maintenance",
                "name": "酒精依赖-维持期",
                "category": "维持期",
                "medications": [
                    {
                        "name": "纳曲酮",
                        "dosage": "50mg po qd 或 prn",
                        "notes": "按需使用，维持1-2年"
                    },
                    {
                        "name": "维生素B1",
                        "dosage": "100mg po qd",
                        "notes": "长期维持"
                    }
                ]
            }
        ]
    }

    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(default_schemes, f, ensure_ascii=False, indent=2)

        print(f"[OK] 成功创建默认治疗方案配置文件: {config_file}")
        print(f"[INFO] 共包含 {len(default_schemes['schemes'])} 个治疗方案")
        return True

    except Exception as e:
        print(f"[ERROR] 创建配置文件失败: {e}")
        return False
