# -*- coding: utf-8 -*-
"""
风险评估模块
提供患者风险评估、风险清单生成和医生编辑确认功能
"""

from typing import List, Dict, Optional
import re


class RiskAssessment:
    """风险评估类"""

    def __init__(self):
        """初始化风险评估模块"""
        self.somatic_risks = []
        self.psychiatric_risks = []
        self.lab_results = ""

    def get_somatic_disease_keywords(self) -> Dict[str, List[str]]:
        """
        躯体疾病关键词库

        Returns:
            按系统分类的疾病关键词字典
        """
        return {
            "肝脏系统": [
                "肝功能不全", "肝硬化", "脂肪肝", "酒精性肝病", "肝损伤",
                "肝功能异常", "肝酶升高", "转氨酶升高", "ALT升高", "AST升高",
                "乙肝", "丙肝", "肝炎", "肝衰竭"
            ],
            "心血管系统": [
                "高血压", "冠心病", "心律失常", "心肌病", "心力衰竭",
                "心衰", "心肌缺血", "心肌梗死", "心梗", "心脏瓣膜病"
            ],
            "内分泌代谢": [
                "糖尿病", "高血糖", "低血糖", "甲状腺功能异常", "甲亢",
                "甲减", "痛风", "高尿酸血症", "血脂异常", "高脂血症"
            ],
            "神经系统": [
                "脑梗死", "脑出血", "脑卒中", "中风", "癫痫",
                "帕金森病", "脑外伤", "脑震荡", "脑炎", "脑膜炎"
            ],
            "消化系统": [
                "胃炎", "胃溃疡", "十二指肠溃疡", "消化道出血", "胃出血",
                "胰腺炎", "肠梗阻", "胃炎", "胃食管反流"
            ],
            "呼吸系统": [
                "慢性阻塞性肺疾病", "慢阻肺", "肺气肿", "哮喘", "肺炎",
                "肺结核", "肺栓塞", "呼吸衰竭"
            ],
            "肾脏系统": [
                "肾功能不全", "肾衰竭", "肾病综合征", "肾炎", "尿毒症",
                "蛋白尿", "肾功能异常"
            ],
            "其他": [
                "贫血", "白细胞减少", "血小板减少", "凝血功能障碍",
                "免疫功能低下", "恶性肿瘤", "癌症", "肿瘤", "电解质紊乱"
            ]
        }

    def get_psychiatric_risk_items(self) -> List[str]:
        """
        精神风险项目列表

        Returns:
            精神风险项目列表
        """
        return [
            "自伤/自杀风险",
            "攻击/伤人风险"
        ]

    def extract_somatic_risks_from_history(self, past_history: str) -> List[str]:
        """
        从既往史中提取躯体风险

        Args:
            past_history: 既往史文本

        Returns:
            提取到的躯体风险列表
        """
        risks = []

        if not past_history or not isinstance(past_history, str):
            return risks

        past_history = past_history.strip()
        if not past_history or past_history == "否认":
            return risks

        disease_keywords = self.get_somatic_disease_keywords()

        # 遍历各系统的疾病关键词
        for system, diseases in disease_keywords.items():
            for disease in diseases:
                # 使用正则表达式匹配疾病名称
                pattern = re.compile(disease, re.IGNORECASE)
                if pattern.search(past_history):
                    risk_item = f"{system}风险：{disease}"
                    if risk_item not in risks:
                        risks.append(risk_item)

        return risks

    def extract_somatic_risks_from_lab(self, lab_results: str) -> List[str]:
        """
        从检验检查结果中提取躯体风险

        Args:
            lab_results: 检验检查结果文本

        Returns:
            提取到的躯体风险列表
        """
        risks = []

        if not lab_results or not isinstance(lab_results, str):
            return risks

        lab_results = lab_results.strip()
        if not lab_results:
            return risks

        # 常见异常检验指标关键词
        lab_keywords = {
            "肝功能异常": [
                "ALT升高", "AST升高", "转氨酶升高", "GGT升高",
                "肝酶升高", "胆红素升高", "白蛋白降低"
            ],
            "心肌损伤": [
                "肌钙蛋白升高", "CK-MB升高", "肌酸激酶升高"
            ],
            "肾功能异常": [
                "肌酐升高", "尿素氮升高", "尿酸升高", "肾小球滤过率降低"
            ],
            "血糖异常": [
                "血糖升高", "血糖降低", "空腹血糖异常", "糖化血红蛋白升高"
            ],
            "血脂异常": [
                "胆固醇升高", "甘油三酯升高", "LDL升高", "HDL降低"
            ],
            "血液系统异常": [
                "白细胞升高", "白细胞降低", "血小板降低", "贫血",
                "血红蛋白降低", "凝血功能异常"
            ],
            "电解质紊乱": [
                "钠离子异常", "钾离子异常", "氯离子异常",
                "低钠", "高钾", "低钾", "高钠"
            ]
        }

        # 遍历检验指标关键词
        for category, indicators in lab_keywords.items():
            for indicator in indicators:
                pattern = re.compile(indicator, re.IGNORECASE)
                if pattern.search(lab_results):
                    risk_item = f"检验异常风险：{indicator}"
                    if risk_item not in risks:
                        risks.append(risk_item)

        return risks

    def analyze_patient_risks(self, past_history: str, lab_results: str = None) -> Dict[str, List[str]]:
        """
        分析患者风险

        Args:
            past_history: 既往史文本
            lab_results: 检验检查结果文本（可选）

        Returns:
            包含躯体风险和精神风险的字典
        """
        # 提取躯体风险
        self.somatic_risks = []

        # 从既往史中提取
        history_risks = self.extract_somatic_risks_from_history(past_history)
        self.somatic_risks.extend(history_risks)

        # 从检验检查中提取（如果提供）
        if lab_results:
            self.lab_results = lab_results
            lab_risks = self.extract_somatic_risks_from_lab(lab_results)
            self.somatic_risks.extend(lab_risks)

        # 去重
        self.somatic_risks = list(dict.fromkeys(self.somatic_risks))

        # 精神风险（默认提供所有项目）
        self.psychiatric_risks = self.get_psychiatric_risk_items()

        return {
            "somatic_risks": self.somatic_risks,
            "psychiatric_risks": self.psychiatric_risks
        }

    def display_risk_list(self) -> str:
        """
        显示风险清单

        Returns:
            格式化后的风险清单字符串
        """
        output = []
        output.append("=" * 60)
        output.append("风险评估清单")
        output.append("=" * 60)
        output.append("")

        # 躯体风险
        output.append("【躯体风险】")
        if self.somatic_risks:
            for idx, risk in enumerate(self.somatic_risks, 1):
                output.append(f"  {idx}. {risk}")
        else:
            output.append("  未识别到躯体风险")
        output.append("")

        # 精神风险
        output.append("【精神风险】")
        if self.psychiatric_risks:
            for idx, risk in enumerate(self.psychiatric_risks, len(self.somatic_risks) + 1):
                output.append(f"  {idx}. {risk}")
        else:
            output.append("  未识别到精神风险")
        output.append("")

        # 检验检查（如果有）
        if self.lab_results:
            output.append("【输入的检验检查结果】")
            output.append(f"  {self.lab_results}")
            output.append("")

        output.append("=" * 60)
        output.append("【编辑指南】")
        output.append("  - 输入数字删除对应风险项（多个数字用逗号分隔）")
        output.append("  - 输入 'clear' 清空所有风险")
        output.append("  - 输入 'done' 完成编辑，确认风险评估")
        output.append("=" * 60)

        return "\n".join(output)

    def remove_risks_by_indices(self, indices: List[int]) -> bool:
        """
        根据索引删除风险项

        Args:
            indices: 要删除的风险项索引列表

        Returns:
            是否删除成功
        """
        all_risks = self.somatic_risks + self.psychiatric_risks

        # 按从大到小排序，避免删除后索引错位
        indices_sorted = sorted(indices, reverse=True)

        for idx in indices_sorted:
            idx_real = idx - 1  # 转换为0-based索引

            if 0 <= idx_real < len(all_risks):
                # 判断是躯体风险还是精神风险
                if idx_real < len(self.somatic_risks):
                    del self.somatic_risks[idx_real]
                else:
                    mental_idx = idx_real - len(self.somatic_risks)
                    if 0 <= mental_idx < len(self.psychiatric_risks):
                        del self.psychiatric_risks[mental_idx]
            else:
                print(f"[WARNING] 索引 {idx} 超出范围，已跳过")
                return False

        return True

    def clear_all_risks(self) -> None:
        """清空所有风险"""
        self.somatic_risks = []
        self.psychiatric_risks = []

    def get_final_risks(self) -> Dict[str, List[str]]:
        """
        获取最终确认的风险列表

        Returns:
            包含躯体风险和精神风险的字典
        """
        return {
            "somatic_risks": self.somatic_risks,
            "psychiatric_risks": self.psychiatric_risks
        }

    def confirm_assessment(self) -> str:
        """
        确认评估，生成最终报告

        Returns:
            最终风险评估报告字符串
        """
        output = []
        output.append("")
        output.append("=" * 60)
        output.append("【风险评估确认】")
        output.append("=" * 60)
        output.append("")

        # 躯体风险
        output.append("躯体风险：")
        if self.somatic_risks:
            for risk in self.somatic_risks:
                output.append(f"  - {risk}")
        else:
            output.append("  无躯体风险")
        output.append("")

        # 精神风险
        output.append("精神风险：")
        if self.psychiatric_risks:
            for risk in self.psychiatric_risks:
                output.append(f"  - {risk}")
        else:
            output.append("  无精神风险")
        output.append("")

        output.append("=" * 60)

        return "\n".join(output)


def perform_risk_assessment(past_history: str, lab_results: str = None) -> Dict[str, List[str]]:
    """
    执行完整的风险评估流程（简化的便捷函数）

    Args:
        past_history: 既往史文本
        lab_results: 检验检查结果文本（可选）

    Returns:
        风险评估结果字典

    Example:
        >>> result = perform_risk_assessment("否认高血压、糖尿病史", "ALT 200U/L")
        >>> print(result['somatic_risks'])
        ['检验异常风险：ALT升高']
    """
    assessor = RiskAssessment()
    risks = assessor.analyze_patient_risks(past_history, lab_results)

    print(assessor.display_risk_list())

    return risks
