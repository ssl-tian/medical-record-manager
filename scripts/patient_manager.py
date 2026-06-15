# -*- coding: utf-8 -*-
"""
患者管理模块
负责患者录入、切换、查询等核心功能
"""

import os
from typing import Dict, Optional, List, Any
from datetime import datetime
from data_storage import PatientStorage
from course_generator import DailyCourseGenerator, FirstCourseGenerator
from history_generator import PresentIllnessGenerator
from admission_notice_generator import AdmissionNoticeGenerator
from utils import (
    validate_patient_id,
    validate_required_fields
)
from risk_assessment import RiskAssessment
from treatment_library import TreatmentLibrary
import knowledge_ingest as ki
import minutes_parser as mp
from pathlib import Path

# Skill模块所在目录（用于定位treatment_schemes.json）
_SKILL_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))


class PatientManager:
    """患者管理器"""

    def __init__(self, base_dir: str = None):
        self.storage = PatientStorage(base_dir)
        self.daily_course_generator = DailyCourseGenerator()
        self.first_course_generator = FirstCourseGenerator()
        self.present_illness_generator = PresentIllnessGenerator()
        self.admission_notice_generator = AdmissionNoticeGenerator()
        self.current_patient_id: Optional[str] = None
        self._risk_assessor = RiskAssessment()
        schemes_path = os.path.join(_SKILL_SCRIPTS_DIR, "treatment_schemes.json")
        self.treatment_library = TreatmentLibrary(schemes_path)

    # ========= 原有方法（保持不变）==========

    def switch_patient(self, patient_id: str) -> Dict:
        is_valid, error_msg = validate_patient_id(patient_id)
        if not is_valid:
            raise ValueError(f"住院号格式错误: {error_msg}")
        if not self.storage.patient_exists(patient_id):
            raise ValueError(f"患者不存在: {patient_id}")
        patient_data = self.storage.load_patient(patient_id)
        if not patient_data:
            raise ValueError(f"加载患者数据失败: {patient_id}")
        self.current_patient_id = patient_id
        return {
            "patient_id": patient_data.get("patient_id"),
            "name": patient_data.get("basic_info", {}).get("name"),
            "age": patient_data.get("basic_info", {}).get("age"),
            "gender": patient_data.get("basic_info", {}).get("gender"),
            "status": patient_data.get("status"),
            "admission_date": patient_data.get("basic_info", {}).get("admission_date")
        }

    def add_patient(self, patient_data: Dict) -> bool:
        patient_id = patient_data.get("patient_id")
        is_valid, error_msg = validate_patient_id(patient_id)
        if not is_valid:
            print(f"错误: {error_msg}")
            return False
        if self.storage.patient_exists(patient_id):
            print(f"错误: 患者已存在: {patient_id}")
            return False
        required_fields = [
            "patient_id",
            "basic_info.name",
            "basic_info.age",
            "basic_info.gender",
            "basic_info.admission_date"
        ]
        is_valid, missing_fields = validate_required_fields(patient_data, required_fields)
        if not is_valid:
            print(f"错误: 缺少必填字段: {', '.join(missing_fields)}")
            return False
        success = self.storage.save_patient(patient_data)
        if success:
            print(f"[OK] 患者添加成功: {patient_data.get('basic_info', {}).get('name')} (住院号: {patient_id})")
            self.current_patient_id = patient_id
        else:
            print(f"[ERROR] 患者添加失败")
        return success

    def list_patients(self, status: str = None) -> List[Dict]:
        patients = self.storage.list_all_patients()
        if status:
            patients = [p for p in patients if p.get("status") == status]
        return patients

    def get_patient_info(self, patient_id: str = None) -> Optional[Dict]:
        if patient_id is None:
            patient_id = self.current_patient_id
        if not patient_id:
            raise ValueError("未指定患者且当前没有活动的患者")
        return self.storage.load_patient(patient_id)

    def print_patient_summary(self, patient_id: str = None):
        if patient_id is None:
            patient_id = self.current_patient_id
        if not patient_id:
            print("未指定患者且当前没有活动的患者")
            return
        patient_data = self.storage.load_patient(patient_id)
        if not patient_data:
            print(f"患者不存在: {patient_id}")
            return
        basic_info = patient_data.get("basic_info", {})
        print("\n" + "="*50)
        print(f"患者信息摘要")
        print("="*50)
        print(f"住院号: {patient_id}")
        print(f"姓名: {basic_info.get('name', '')}")
        print(f"性别: {basic_info.get('gender', '')}")
        print(f"年龄: {basic_info.get('age', '')}")
        print(f"入院日期: {basic_info.get('admission_date', '')}")
        print(f"状态: {patient_data.get('status', '')}")
        print(f"主要诊断: {patient_data.get('diagnosis', {}).get('primary', '')}")
        print("="*50 + "\n")

    # ========= 新架构 v5.0：AI直驱 ==========

    def add_patient_from_minutes_files(
        self,
        patient_id: str,
        name: str,
        gender: str,
        age: int,
        admission_date: str,
        present_illness_file: str,
        mental_exam_file: str,
        chief_complaint: str = ""
    ) -> Dict[str, Any]:
        """
        【新架构 v5.0 — AI直驱】
        从两份 AI 纪要文件创建患者

        流程：
        1. 用 minutes_parser.read_minutes_file() 原样读取文件（不解析）
        2. 将原文存入 patient_data
        3. 创建患者记录
        4. 返回原文 + JSON schema，由 AI 理解后生成结构化 JSON
        5. 调用 generate_first_course_from_ai_json() 生成 Word

        Returns:
            {"status": "success", "patient_id": ...,
             "present_illness_raw": ..., "mental_exam_raw": ...,
             "json_schema": ...}
        """
        try:
            print(f"[INFO] 正在读取现病史纪要：{present_illness_file}")
            present_illness_raw = mp.read_minutes_file(present_illness_file)
            print(f"[OK] 现病史纪要读取完成（{len(present_illness_raw)} 字符）")

            print(f"[INFO] 正在读取精神检查纪要：{mental_exam_file}")
            mental_exam_raw = mp.read_minutes_file(mental_exam_file)
            print(f"[OK] 精神检查纪要读取完成（{len(mental_exam_raw)} 字符）")

            print(f"[INFO] 正在构建患者数据...")
            patient_data = mp.build_patient_data_from_minutes(
                patient_id=patient_id,
                name=name,
                gender=gender,
                age=age,
                admission_date=admission_date,
                present_illness_text=present_illness_raw,
                mental_exam_text=mental_exam_raw,
                chief_complaint=chief_complaint
            )
            print(f"[OK] 患者数据构建完成")

            print(f"[INFO] 正在创建患者记录...")
            success = self.add_patient(patient_data)
            if not success:
                return {
                    "status": "error",
                    "message": "创建患者记录失败，可能是住院号已存在或必填字段缺失"
                }

            self.switch_patient(patient_id)
            print(f"[OK] 已切换到患者：{name} (住院号: {patient_id})")

            return {
                "status": "success",
                "patient_id": patient_id,
                "name": name,
                "present_illness_raw": present_illness_raw,
                "mental_exam_raw": mental_exam_raw,
                "next_step": (
                    "AI直驱步骤："
                    "1. 理解上面 'present_illness_raw' 和 'mental_exam_raw' 内容；"
                    "2. 按13条模板格式生成结构化 JSON（见 json_schema）；"
                    "3. 调用 patient_manager.generate_first_course_from_ai_json() 写入 Word。"
                ),
                "json_schema": self._get_first_course_json_schema()
            }

        except FileNotFoundError as e:
            error_msg = f"文件读取失败：{str(e)}"
            print(f"[ERROR] {error_msg}")
            return {"status": "error", "message": error_msg}
        except Exception as e:
            error_msg = f"从 AI 纪要创建患者失败：{str(e)}"
            print(f"[ERROR] {error_msg}")
            return {"status": "error", "message": error_msg}

    def _get_first_course_json_schema(self) -> Dict:
        """返回首次病程记录的结构化 JSON schema（供 AI 生成）"""
        return {
            "description": "首次病程记录13条模板 + 诊断 + 鉴别 + 诊疗计划，全量结构化 JSON schema",
            "fields": {
                # === 前言 ===
                "introduction": "入院导语：患者XXX，男/女，X岁，因\u201c主诉\u201d于YYYY-MM-DD以\u201c自愿住院/非自愿情形一\u201d第X次入院。",

                # === 13条模板 ===
                "general_features": "1. 一般特征及起病形式：患者系青年/中年/老年男/女性，急性/亚急性/慢性迁延性病程，起病形式（隐匿/急性/诱因），病后社会功能受损情况。",
                "disease_course": "2. 病程：总病程X年X月。",

                "evolution": "3. 病情演变特点：时间锚三段式（起病期\u2192中间变化\u2192近期复发），仅描述客观现象和行为表现，不用精神科术语，不出现认知评估。禁止引用患者原话（如\u201c神经跑了\u201d等），用第三人称客观叙述。示例格式：\u201c约YYYY年开始以XX起病，初期表现为XX，每次持续X，可自行缓解。约YYYY年病情加重，表现为XX，频率增加至X。近X月来进一步恶化，表现为XX，X次/月。\u201d",

                "past_treatment": "4. 既往诊疗经过：曾予\u201c药名通用名\u201dXmg/日等药物治疗，疗程X周/月，疗效（部分缓解/无效/明显改善），不良反应（嗜睡/体重增加/锥体外系反应等），是否规律复诊，是否自行停药。无诊疗史则写\u201c既往未因该问题就诊\u201d。",

                "admission_reason": "5. 本次入院原因：近期最严重症状表现（相对时间锚，如\u201c近1周\u201d\u201c入院前3天\u201d），家属觉其病情严重，遂至门诊就诊，诊断\u201cXX\u201d，以\u201c自愿住院/非自愿情形一\u201d收入我科。门诊/急诊诊断留空待补。",

                "general_condition": "6. 一般情况：饮食（正常/差/流质）、睡眠（入睡困难/早醒/多梦/梦魇/正常）、大小便（如常/便秘/腹泻）、体重（未测/近X月下降Xkg）。否认头颅外伤、昏迷、抽搐、高热惊厥病史。",

                "differential_info": "7. 与鉴别诊断有关的阳性或阴性资料：按主要鉴别诊断逐一列出。格式：\u201c否认既往有XX（如情绪低落、兴趣减退、精力下降等抑郁综合征）表现。否认既往有XX（如情绪高涨、精力旺盛、言语增多等躁狂发作）表现。否认幻觉、妄想等精神病性症状。\u201d阴性用\u201c否认\u201d，阳性用\u201c存在\u201d并描述。",

                "past_history": "8. 既往史：系统回顾。格式：\u201c否认高血压、糖尿病、冠心病等慢性病史。否认肝炎、肺结核等传染病史。否认头颅外伤史，否认癫痫、晕倒史，否认手术史，否认输血史。否认药物过敏史。\u201d有阳性史则写具体（如\u201c2025年11月因XX致右踝关节骨折，经XX治疗，目前XX\u201d）。药物/手术用通用名。",

                "personal_history": "9. 个人史：胞X行X，病前性格（内向/外向/敏感/固执/开朗等），出生及发育史正常/异常，吸烟（X年，X支/日，已戒X年/未戒），饮酒（X年，Xml/日，已戒X年/未戒），否认其他精神活性物质使用史。婚育史（未婚/已婚/X岁结婚，配偶健康/有XX病），育有X子X女。职业/文化程度。",

                "family_history": "10. 家族史：父母两系三代中，否认/存在神经精神疾病（具体病名）。格式：\u201c父母两系三代中，否认有精神分裂症、双相情感障碍、抑郁症、癫痫、酒精依赖等神经精神疾病史。\u201d有阳性家族史则写具体（如\u201c父亲有长期饮酒史，具体诊断不详；二伯有类似饮酒问题\u201d）。",

                "physical_exam": "11. 体格检查：无特殊异常时使用以下标准模板：\u201c查体合作，全身皮肤无黄染、皮疹、瘢痕。咽部无红肿，双侧扁桃体无肿大。双肺呼吸音清，未闻及干湿啰音。心率次/分，心律齐，各瓣膜未闻及病理性杂音。腹部平软，全腹无压痛、反跳痛，未触及腹部包块，肠鸣音正常。四肢活动正常，双下肢无水肿。双侧瞳孔等大等圆，d=3mm，对光反射存在。双侧鼻唇沟对称，示齿双侧嘴角对称，伸舌居中。四肢肌力、肌张力正常，肌力Ⅴ级，生理反射存在，病理反射未引出；感觉系统、共济系统未见明显异常；脑膜刺激征阴性。\u201d有异常时在对应位置修改描述。",

                "mental_exam": "12. 专科检查/精神检查：必须覆盖以下11个维度，每个维度用逗号分隔连续书写，不分行。（1）意识：意识清晰/嗜睡/昏睡/谵妄；（2）定向力：时间、地点、人物定向准确/障碍；（3）接触与配合：接触主动/被动，检查合作/不合作，对答切题/不切题；（4）仪态与外貌：仪容整洁/不整，年貌相符/不符；（5）注意力：集中/不集中/涣散；（6）感知觉：未引出错觉、幻觉及感知综合障碍/存在XX幻觉；（7）思维：思维连贯/散漫/破裂，语速适中/加快/迟缓，未引出/存在XX妄想；（8）情感：情绪稳定/焦虑/抑郁/平淡，情感反应协调/不协调；（9）意志与行为：意志活动正常/减退/增强，主动求治/被动接受；（10）记忆力与智能：记忆力、理解力、判断力大致正常/受损；（11）自知力：自知力部分存在/完全存在/不存在，承认/否认XX问题。可在症状描述后引用患者原话（如\u201c患者诉\u201c\u2026\u201d\u201d）。格式示例：\u201c意识清晰，定向力完整（时间、地点、人物定向准确），接触主动，检查合作，对答切题。仪容整洁，年貌相符。注意力集中，能持续配合访谈全过程。未引出错觉、幻觉及感知综合障碍。思维连贯，语速适中，未引出思维散漫、思维破裂及强迫性思维，未查及妄想内容。情绪略焦虑，情感反应与交谈内容协调，未引出情感高涨、情感低落或情感淡漠。意志活动尚可，主动求治，有明确戒酒动机。记忆力、理解力、判断力大致正常。自知力部分存在，承认饮酒问题，有戒酒意愿。\u201d",

                "auxiliary_exam": "13. 辅助检查：入院后完成的检查及结果。格式：\u201c血常规：XX。生化：XX。心电图：XX。头颅CT/MRI：XX。\u201d尚未出结果或未完成则写\u201c暂缺，待回报。\u201d。阴性结果写正常值范围。",

                # === 诊断与鉴别 ===
                "diagnosis_basis": "诊断依据：连贯段落，不列举①②③。格式：\u201c患者为X性，X岁，急性/慢性病程，总病程X年。据患者自述/家属反映，XX（病史核心症状概括）。精神检查见XX（精神检查核心阳性发现）。根据ICD-10诊断标准，患者存在XX、XX、XX（列出满足的3-4个核心诊断标准），符合XX综合征诊断标准，考虑\u201c诊断名称\u201d。初步诊断：XX。\u201d",

                "diagnosis_primary": "初步诊断：仅写诊断名称，不加解释。如\u201c酒精依赖综合征\u201d或\u201c重度抑郁发作，单次，不伴躯体综合征\u201d。多个诊断用\u201c，\u201d分隔。",

                "diagnosis_differential": "鉴别诊断：分1、2点论述，每点一段连贯文字。格式：\u201c1. 需与\u201cXX\u201d鉴别：本例患者XX（支持点），不支持XX（排除点），不符合XX诊断标准，暂不考虑。2. 需与\u201cXX\u201d鉴别：患者虽有XX表现，但XX（排除理由），不符合XX诊断标准。\u201d不写\u201c鉴别诊断：\u201d标签，直接以编号开头。",

                "treatment_plan": "诊疗计划：整合为一个段落。格式：\u201c1. 药物治疗：予\u201c药名通用名\u201dXmg/日治疗XX；予\u201c药名\u201dXmg/日辅助改善XX。2. 躯体疾病治疗：XX请相关科室会诊/对症处理。3. 心理治疗：待病情稳定后，择期行XX治疗（如动机增强治疗、认知行为治疗）。4. 健康教育：嘱患者XX，指导家属XX。5. 完善检查：完善XX等入院常规检查。\u201d药物用通用名，不用商品名；药物列表用\u201c\u201d引号包裹。"
            },
            "notes": [
                "所有字段生成纯文本（不JSON嵌套），代码直接写入 Word",
                "时间格式：绝对时间（2024年4月、2025年9月），不用相对时间（除第5条入院原因可用相对时间锚）",
                "药物用通用名，不用商品名；药物列表用\u201c\u201d引号包裹",
                "体格检查（physical_exam）：无异常时必须使用schema中提供的标准模板",
                "精神检查（mental_exam）：必须覆盖11个维度，连续书写不分段；可在症状描述后引用患者原话",
                "病情演变（evolution）：禁止引用患者原话，用第三人称客观叙述行为和现象",
                "诊断依据（diagnosis_basis）：连贯段落，不列举①②③",
                "鉴别诊断（diagnosis_differential）：编号开头，不写\u201c鉴别诊断：\u201d标签"
            ]
        }

    def generate_first_course_from_ai_json(
        self,
        patient_id: str,
        ai_json: Dict[str, str],
        output_path: str = None
    ) -> Optional[str]:
        """
        【新架构 v5.0 核心】
        接受 AI 生成的结构化 JSON，确定性写入 Word 文档

        Args:
            patient_id: 住院号
            ai_json: AI 生成的结构化 JSON（符合 _get_first_course_json_schema 格式）
            output_path: 输出路径（可选，自动生成）

        Returns:
            生成的 Word 文件路径，失败返回 None
        """
        try:
            if patient_id is None:
                patient_id = self.current_patient_id
            if not patient_id:
                raise ValueError("未指定患者且当前没有活动的患者")

            patient_data = self.storage.load_patient(patient_id)
            if not patient_data:
                raise ValueError(f"患者不存在: {patient_id}")

            print(f"[INFO] 正在将 AI 生成的结构化内容转换为 Word 格式...")
            ai_content = self._convert_ai_json_to_course_content(ai_json)

            if output_path is None:
                patient_name = patient_data.get("basic_info", {}).get("name", "unknown")
                default_filename = f"首次病程_{patient_name}_{patient_id}.docx"
                output_path = str(Path.cwd() / default_filename)

            file_path = self.first_course_generator.generate_from_ai_content(
                ai_content, output_path
            )
            print(f"[OK] 首次病程记录已生成：{file_path}")

            if "course_records" not in patient_data:
                patient_data["course_records"] = {}
            patient_data["course_records"]["first_course"] = file_path
            patient_data["course_records"]["first_course_date"] = datetime.now().strftime("%Y-%m-%d")
            # 同步保存诊断到患者数据
            if "diagnosis" not in patient_data:
                patient_data["diagnosis"] = {}
            if ai_json.get("diagnosis_primary"):
                patient_data["diagnosis"]["primary"] = ai_json["diagnosis_primary"]
            if ai_json.get("diagnosis_basis"):
                patient_data["diagnosis"]["basis"] = ai_json["diagnosis_basis"]
            if ai_json.get("diagnosis_differential"):
                patient_data["diagnosis"]["differential"] = ai_json["diagnosis_differential"]
            self.storage.save_patient(patient_data)

            return file_path

        except Exception as e:
            print(f"[ERROR] 生成首次病程记录失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _convert_ai_json_to_course_content(self, ai_json: Dict[str, str]) -> Dict[str, List[str]]:
        """
        将 AI 生成的结构化 JSON 转换为 course_generator 需要的格式：
        {
            "病例特点": [...],
            "诊断依据与鉴别诊断": [...],
            "诊疗计划": [...]
        }
        """
        content = {
            "病例特点": [],
            "诊断依据与鉴别诊断": [],
            "诊疗计划": []
        }

        # （一）病例特点
        content["病例特点"].append("（一）病例特点")
        content["病例特点"].append("")

        # 入院导语
        intro = ai_json.get("introduction", "")
        if intro:
            content["病例特点"].append(intro)
            content["病例特点"].append("")

        # 1-13 条
        field_map = [
            ("general_features", "1. 一般特征及起病形式"),
            ("disease_course", "2. 病程"),
            ("evolution", "3. 病情演变特点"),
            ("past_treatment", "4. 既往诊疗经过"),
            ("admission_reason", "5. 本次入院原因"),
            ("general_condition", "6. 一般情况"),
            ("differential_info", "7. 与鉴别诊断有关的阳性或阴性资料"),
            ("past_history", "8. 既往史"),
            ("personal_history", "9. 个人史"),
            ("family_history", "10. 家族史"),
            ("physical_exam", "11. 体格检查"),
            ("mental_exam", "12. 专科检查"),
            ("auxiliary_exam", "13. 辅助检查"),
        ]

        for key, label in field_map:
            val = ai_json.get(key, "")
            if val and val.strip():
                # 如果内容已包含标签（如"1. 一般特征及起病形式：..."），不重复添加
                if val.startswith(label.split()[0]):  # "1." 开头
                    content["病例特点"].append(val)
                else:
                    content["病例特点"].append(f"{label}：{val}")
                content["病例特点"].append("")

        # （二）诊断依据与鉴别诊断
        content["诊断依据与鉴别诊断"].append("（二）诊断依据与鉴别诊断")
        content["诊断依据与鉴别诊断"].append("")

        diagnosis_basis = ai_json.get("diagnosis_basis", "")
        if diagnosis_basis:
            content["诊断依据与鉴别诊断"].append(diagnosis_basis)

        diagnosis_primary = ai_json.get("diagnosis_primary", "")
        if diagnosis_primary:
            content["诊断依据与鉴别诊断"].append(f"初步诊断：{diagnosis_primary}")

        content["诊断依据与鉴别诊断"].append("")

        diagnosis_differential = ai_json.get("diagnosis_differential", "")
        if diagnosis_differential:
            content["诊断依据与鉴别诊断"].append(diagnosis_differential)

        content["诊断依据与鉴别诊断"].append("")

        # （三）诊疗计划
        content["诊疗计划"].append("（三）诊疗计划")
        content["诊疗计划"].append("")

        treatment_plan = ai_json.get("treatment_plan", "")
        if treatment_plan:
            content["诊疗计划"].append(treatment_plan)
        else:
            content["诊疗计划"].append("诊疗计划待主治医师查房后制定。")

        return content



    # ========= 日常病程记录 v5.0 — AI直驱 ==========

    def build_daily_course_context(
        self, patient_id: str = None,
        input_source: Any = None
    ) -> Dict[str, Any]:
        """
        Phase 3 主入口（pre-AI） — 构建传给 AI 的上下文

        Args:
            patient_id: 住院号
            input_source: 当日观察输入，支持三种格式：
                - {"file": "path/to/dingtalk_minutes.txt"}  钉钉AI纪要文件
                - {"text": "自由文本观察描述..."}           手写文本
                - "自由文本字符串"                           简写（向后兼容）

        Returns:
            {"status": "success", "prompt": "...", "patient_id": "..."}
            或 {"status": "error", "message": "..."}
        """
        try:
            if patient_id is None:
                patient_id = self.current_patient_id
            if not patient_id:
                raise ValueError("未指定患者且当前没有活动的患者")

            patient_data = self.storage.load_patient(patient_id)
            if not patient_data:
                raise ValueError(f"患者不存在: {patient_id}")

            input_text = self._read_daily_input(input_source)
            previous_record = self._get_latest_daily_record(patient_id)

            prompt = self.daily_course_generator.build_context_for_ai(
                patient_data, input_text,
                previous_record=previous_record
            )

            return {
                "status": "success",
                "patient_id": patient_id,
                "prompt": prompt,
                "input_length": len(input_text),
                "has_previous": previous_record is not None,
                "next_step": "AI 请根据以上 prompt 生成日常病程记录的 JSON（{markdown, snapshot}），然后调用 save_daily_course_from_ai_json() 保存。"
            }

        except Exception as e:
            print(f"[ERROR] 构建日常病程上下文失败: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": str(e)}

    def save_daily_course_from_ai_json(
        self, patient_id: str = None,
        ai_json: Dict = None
    ) -> Dict[str, Any]:
        """
        Phase 3 后处理（post-AI） — 保存 AI 生成的日常病程记录

        Args:
            patient_id: 住院号
            ai_json: AI 生成的 {"markdown": "...", "snapshot": {...}}

        Returns:
            {"status": "success", "md_path": "...", "snapshot": {...}}
            或 {"status": "error", "message": "..."}
        """
        try:
            if patient_id is None:
                patient_id = self.current_patient_id
            if not patient_id:
                raise ValueError("未指定患者且当前没有活动的患者")
            if not ai_json:
                raise ValueError("缺少 ai_json 参数")

            patient_data = self.storage.load_patient(patient_id)
            if not patient_data:
                raise ValueError(f"患者不存在: {patient_id}")

            result = self.daily_course_generator.process_ai_output(ai_json, patient_data)
            if not result["valid"]:
                return {
                    "status": "error",
                    "message": f"AI 输出验证失败: {'; '.join(result['errors'])}",
                    "errors": result["errors"]
                }

            md_path = self.daily_course_generator._save_markdown(
                result["markdown"], patient_data,
                result["snapshot"].get("record_date", datetime.now().strftime("%Y-%m-%d"))
            )

            if "daily_courses" not in patient_data:
                patient_data["daily_courses"] = []
            patient_data["daily_courses"].append({
                "record_date": result["snapshot"].get("record_date"),
                "hospital_day": result["snapshot"].get("hospital_day"),
                "markdown_path": md_path,
                "snapshot": result["snapshot"]
            })
            self.storage.save_patient(patient_data)

            print(f"[OK] 日常病程记录已保存")
            print(f"     Markdown: {md_path}")
            print(f"     住院天数: 第{result['snapshot'].get('hospital_day','?')}天")
            return {"status": "success", "md_path": md_path,
                    "snapshot": result["snapshot"]}

        except Exception as e:
            print(f"[ERROR] 保存日常病程记录失败: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": str(e)}

    def _read_daily_input(self, input_source: Any) -> str:
        """读取当日临床观察输入（钉钉文件或手写文本）"""
        if input_source is None:
            return ""
        if isinstance(input_source, str):
            return input_source
        if isinstance(input_source, dict):
            if "file" in input_source:
                path = input_source["file"]
                print(f"[INFO] 正在读取当日观察文件：{path}")
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()
            if "text" in input_source:
                return input_source["text"]
        return str(input_source)

    def _get_latest_daily_record(self, patient_id: str) -> Optional[Dict]:
        """获取患者最近一次日常病程记录（用于对比）"""
        patient_data = self.storage.load_patient(patient_id)
        if not patient_data:
            return None
        daily_courses = patient_data.get("daily_courses", [])
        if not daily_courses:
            return None
        return daily_courses[-1]

    def calculate_hospital_day(self, patient_id: str = None) -> int:
        if patient_id is None:
            patient_id = self.current_patient_id
        if not patient_id:
            return 0
        patient_data = self.storage.load_patient(patient_id)
        if not patient_data:
            return 0
        admission_date = patient_data.get("basic_info", {}).get("admission_date")
        if not admission_date:
            return 0
        try:
            admit = datetime.strptime(admission_date, "%Y-%m-%d")
            today = datetime.now()
            return (today - admit).days + 1
        except ValueError:
            return 0

    # ========= Phase 2: 入院须知 ==========

    def generate_admission_notice(
        self,
        patient_id: str = None,
        version: str = "auto",
        output_path: str = None
    ) -> Optional[str]:
        """
        生成入院须知（Markdown 格式）

        Args:
            patient_id: 住院号
            version: "alcohol" / "general" / "auto"（根据诊断自动判断）
            output_path: 输出路径（可选，默认输出到患者目录下）

        Returns:
            Markdown 文件路径，失败返回 None
        """
        try:
            if patient_id is None:
                patient_id = self.current_patient_id
            if not patient_id:
                raise ValueError("未指定患者且当前没有活动的患者")

            patient_data = self.storage.load_patient(patient_id)
            if not patient_data:
                raise ValueError(f"患者不存在: {patient_id}")

            # 生成 Markdown
            if version == "auto":
                diagnosis = patient_data.get("diagnosis", {}).get("primary", "")
                if "酒精" in diagnosis or "依赖" in diagnosis:
                    version = "alcohol"
                else:
                    version = "general"

            if version == "alcohol":
                markdown = self.admission_notice_generator.generate_alcohol_version(patient_data)
            else:
                markdown = self.admission_notice_generator.generate_general_version(patient_data)

            # 保存到文件
            if output_path is None:
                from pathlib import Path
                patient_name = patient_data.get("basic_info", {}).get("name", "unknown")
                default_filename = f"入院须知_{patient_name}_{patient_id}.md"
                output_path = str(Path.cwd() / default_filename)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(markdown)

            print(f"[OK] 入院须知已生成: {output_path}")
            print(f"     版本: {version}")
            return output_path

        except Exception as e:
            print(f"[ERROR] 生成入院须知失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def send_admission_notice(
        self,
        patient_id: str = None,
        user_id: str = None,
        version: str = "auto",
        output_path: str = None
    ) -> Optional[Dict]:
        """
        Step 2.2 — 生成入院须知并通过钉钉私发家属

        Args:
            patient_id: 住院号
            user_id: 接收家属的钉钉 userId（必填）
            version: "alcohol" / "general" / "auto"
            output_path: Markdown 文件保存路径（可选）

        Returns:
            {"notice_path": str, "send_result": str} 或 None
        """
        try:
            if patient_id is None:
                patient_id = self.current_patient_id
            if not patient_id:
                raise ValueError("未指定患者且当前没有活动的患者")
            if not user_id:
                raise ValueError("未指定收件人钉钉 userId")

            # Step 1: 生成入院须知
            notice_path = self.generate_admission_notice(
                patient_id=patient_id,
                version=version,
                output_path=output_path
            )
            if not notice_path:
                raise RuntimeError("入院须知生成失败")

            # Step 2: 读取 Markdown 内容
            with open(notice_path, "r", encoding="utf-8") as f:
                markdown_content = f.read()

            # Step 3: 构造 dws 命令
            patient_data = self.storage.load_patient(patient_id)
            patient_name = patient_data.get("basic_info", {}).get("name", "患者")
            title = f"入院须知 - {patient_name}"

            import subprocess
            import tempfile
            import os

            # 将 Markdown 写入临时文件以避免 shell 转义问题
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".md", encoding="utf-8", delete=False
            ) as tmp:
                tmp.write(markdown_content)
                tmp_path = tmp.name

            # 使用 --text 从文件读取的方式发送
            # dws 支持 --text 参数，换行必须是真实换行符
            cmd_title = title.replace('"', '\\"')

            # 对于长文本，使用 dws 的位置参数
            # 由于 Markdown 包含双引号和特殊字符，通过临时文件 + shell cat 传递内容
            bash_cmd = (
                f'dws chat message send --user "{user_id}" '
                f'--title "{cmd_title}" '
                f'"$(cat {tmp_path})"'
            )

            print(f"[INFO] 钉钉私发: dws chat message send --user {user_id} --title \"{title}\"")

            # 执行发送
            result = subprocess.run(
                ["bash", "-c", bash_cmd],
                capture_output=True,
                text=True,
                timeout=30,
            )

            # 清理临时文件
            os.unlink(tmp_path)

            send_result = result.stdout.strip()
            if result.returncode != 0:
                print(f"[WARN] 钉钉发送可能失败 (exit={result.returncode})")
                if result.stderr:
                    print(f"      stderr: {result.stderr[:200]}")

            return {
                "notice_path": notice_path,
                "send_result": send_result,
                "exit_code": result.returncode,
            }

        except Exception as e:
            print(f"[ERROR] 发送入院须知失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    # ========= 风险评估 ==========

    def perform_risk_assessment(self, patient_id: str = None, lab_results: str = None) -> Dict:
        if patient_id is None:
            patient_id = self.current_patient_id
        if not patient_id:
            raise ValueError("未指定患者且当前没有活动的患者")
        patient_data = self.storage.load_patient(patient_id)
        if not patient_data:
            raise ValueError(f"无法加载患者数据: {patient_id}")
        past_history = patient_data.get("history", {}).get("past_history", "")
        return self._risk_assessor.perform_risk_assessment(past_history, lab_results)

    # ========= 治疗方案库 ==========

    def list_treatment_schemes(self):
        return self.treatment_library.display_schemes()

    def show_treatment_scheme_detail(self, scheme_id: str):
        return self.treatment_library.display_scheme_detail(scheme_id)

    def import_treatment_scheme(self, patient_id: str, scheme_id: str, mode: str = "replace") -> bool:
        if patient_id is None:
            patient_id = self.current_patient_id
        if not patient_id:
            raise ValueError("未指定患者且当前没有活动的患者")
        patient_data = self.storage.load_patient(patient_id)
        if not patient_data:
            raise ValueError(f"无法加载患者数据: {patient_id}")
        scheme = self.treatment_library.get_scheme_by_id(scheme_id)
        if not scheme:
            print(f"错误: 方案不存在: {scheme_id}")
            return False
        medication_plan = self.treatment_library.format_medication_plan(scheme)
        if mode == "replace":
            patient_data["treatment"]["plan"] = medication_plan
        elif mode == "append":
            existing = patient_data["treatment"].get("plan", "")
            patient_data["treatment"]["plan"] = existing + "\n" + medication_plan
        self.storage.save_patient(patient_data)
        print(f"[OK] 方案已导入到患者 {patient_id}")
        return True

    # ========= 治疗知识库 ==========

    def ingest_knowledge_source(self, text: str, title: str, source_type: str = "plain", source_url: str = None) -> Dict:
        return ki.ingest_text(text=text, title=title, source_type=source_type, source_url=source_url)

    def save_knowledge_analysis(self, source_id: str, analysis_result: Dict) -> Dict:
        return ki.save_analysis_result(source_id, analysis_result)

    def get_knowledge_base_status(self) -> Dict:
        return ki.get_wiki_status()

    def list_knowledge_entities(self) -> List[Dict]:
        return ki.list_entities()

    def list_knowledge_topics(self) -> List[Dict]:
        return ki.list_topics()

    def read_knowledge_page(self, page_type: str, name: str) -> Optional[str]:
        return ki.read_wiki_page(page_type, name)


def create_sample_patient_data(hospital_id: str) -> Dict:
    return {
        "patient_id": hospital_id,
        "basic_info": {
            "name": "",
            "age": "",
            "gender": "",
            "admission_date": "",
            "occupation": "",
            "marital_status": ""
        },
        "history": {
            "onset_form": "",
            "disease_duration": "",
            "disease_evolution": {"phases": []},
            "previous_treatments": "",
            "admission_reason": "",
            "general_condition": "",
            "differential_info": "",
            "past_history": "",
            "personal_history": "",
            "family_history": "",
            "auxiliary_exam": "",
            "present_illness": {
                "informant": "",
                "onset": {"time": "", "precipitant": "", "form": "", "first_symptoms": ""},
                "phases": [],
                "general_condition_psych": {},
                "medication_table": []
            }
        },
        "examination": {
            "physical": "",
            "mental": ""
        },
        "diagnosis": {
            "primary": "",
            "basis": "",
            "differential": ""
        },
        "treatment": {
            "plan": ""
        },
        "course_records": {},
        "status": "inpatient",
        "metadata": {
            "created_at": "",
            "updated_at": ""
        }
    }