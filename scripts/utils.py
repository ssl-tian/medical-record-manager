# -*- coding: utf-8 -*-
"""
工具函数模块
提供输入验证、日期格式化、模板提示等通用功能
"""

from datetime import datetime
from typing import List, Dict, Optional


def validate_patient_id(patient_id: str) -> tuple[bool, str]:
    """
    验证住院号格式

    Args:
        patient_id: 住院号

    Returns:
        (是否有效, 错误信息)
    """
    if not patient_id:
        return False, "住院号不能为空"

    if not isinstance(patient_id, str):
        return False, "住院号必须是字符串"

    if len(patient_id.strip()) == 0:
        return False, "住院号不能为空"

    # 基本格式验证：可以是数字或字母数字组合
    # 如果需要更严格的格式，可以在这里添加
    patient_id = patient_id.strip()

    # 检查长度是否合理（根据实际需求调整）
    if len(patient_id) < 4:
        return False, "住院号长度不足"

    if len(patient_id) > 20:
        return False, "住院号长度过长"

    return True, ""


def format_date(date_obj: datetime = None, date_str: str = None) -> str:
    """
    格式化日期为"YYYY-MM-DD"格式

    Args:
        date_obj: 日期对象
        date_str: 日期字符串

    Returns:
        格式化后的日期字符串
    """
    if date_obj:
        return date_obj.strftime("%Y-%m-%d")

    if date_str:
        try:
            # 尝试解析常见日期格式
            for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日", "%Y%m%d"]:
                try:
                    parsed = datetime.strptime(date_str, fmt)
                    return parsed.strftime("%Y-%m-%d")
                except ValueError:
                    continue
            return date_str  # 如果无法解析，返回原字符串
        except:
            return date_str

    return datetime.now().strftime("%Y-%m-%d")


def parse_input_fields(raw_input: str) -> Dict[str, str]:
    """
    解析用户输入的字段数据

    Args:
        raw_input: 原始输入文本

    Returns:
        字段字典
    """
    fields = {}
    lines = raw_input.strip().split('\n')

    current_key = None
    current_value = []

    for line in lines:
        # 尝试识别键值对格式（如："1. 一般特征" 或 "一般特征："）
        if line.strip().startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '10.', '11.', '12.')):
            # 保存前一个字段
            if current_key and current_value:
                fields[current_key] = '\n'.join(current_value).strip()

            # 提取新的字段名
            parts = line.split('.', 1)
            if len(parts) == 2:
                current_key = parts[1].strip()
                current_value = []
            continue

        # 尝试识别冒号分隔格式
        if ':' in line and len(line.split(':')[0]) < 20:
            # 保存前一个字段
            if current_key and current_value:
                fields[current_key] = '\n'.join(current_value).strip()

            current_key = line.split(':')[0].strip()
            current_value = [line.split(':', 1)[1].strip()]
            continue

        # 累积当前字段的值
        if current_key:
            current_value.append(line.strip())

    # 保存最后一个字段
    if current_key and current_value:
        fields[current_key] = '\n'.join(current_value).strip()

    return fields


def get_template_prompts(template_type: str = "first_course") -> List[str]:
    """
    获取模板提示信息

    Args:
        template_type: 模板类型（"first_course"、"daily_course" 或 "present_illness"）

    Returns:
        提示信息列表
    """
    if template_type == "first_course":
        return [
            "入院导语：仅写主诉，格式：因\"[主诉内容]\"入院。",
            "1. 一般特征及起病形式：[由系统根据患者基本信息自动填充：年龄、性别、起病形式]",
            "2. 病程：[由系统根据主诉时间自动填充]",
            "3. 病情演变特点：[单段落流式叙述，按时间顺序连贯描述，禁止分段标签。来源为家属描述，禁止精神科术语、禁止认知评估。]",
            "4. 既往诊疗经过：既往未予诊治。",
            "5. 本次入院原因：近期患者最严重的症状表现+家属觉其病情严重，遂至门诊/急诊就诊，诊断\u201c\u201d，以\u201c自愿住院/非自愿情形一\u201d收入我科。",
            "6. 一般情况：无头颅外伤，昏迷，抽搐等病史，近期饮食差，睡眠欠佳，大小便如常，体重未测。",
            "7. 与鉴别诊断有关的阳性或阴性资料：否认既往有情绪低落、兴趣减退、精力下降等抑郁综合征表现。",
            "8. 既往史：否认高血压、糖尿病、冠心病等慢性病史。否认肝炎、肺结核等传染病史。否认头颅外伤史，否认癫痫、晕倒史，否认手术史，否认输血史。否认药物过敏史。",
            "9. 个人史：胞X行X，否认吸烟、酗酒嗜好。",
            "10. 家族史：父母两系三代中，否认有神经、精神疾病或者类似疾病的个体。",
            "11. 体格检查：[标准模板，由病房医师填写或修改]",
            "12. 专科检查：[一般情况、感知觉、思维活动、情感反应、意志行为、智力、自知力]",
            "13. 辅助检查：[入院时检验检查结果]",
            "诊断依据与鉴别诊断：",
            "  - 诊断依据：[病史概况+精神检查要点 → 满足什么综合征 → 根据ICD-10/CCMD-3考虑诊断。连贯叙述，不分①②③，不逐条对应诊断标准。末尾直接接初步诊断。]",
            "  - 初步诊断：[由系统自动在诊断依据末尾追加：初步诊断：XXX]",
            "  - 鉴别诊断：[沿用连贯叙述格式，不写\u201c鉴别诊断：\u201d标签]",
        ]
    elif template_type == "daily_course":
        return [
            "病情变化（精神状况、情绪状态、进食睡眠、二便体重等）",
            "【核心症状量化对比】幻觉（前次→本次）、妄想（前次→本次）、情绪（前次→本次）、行为（前次→本次）",
            "精神检查（意识、定向、接触、感知觉、思维、情感、意志行为、自知力）",
            "处理意见（30-50字，合并治疗调整+病情分析+诊疗计划）",
            "【药物反应对比】疗效变化、新发副作用、血药浓度（可选）",
            "【风险评估（按需）】自杀/冲动/外走/躯体 — 仅风险等级变化时记录"
        ]
    elif template_type == "present_illness":
        return [
            "【信息提供者声明】病史来源及可靠性评估（必填）",
            "【起病总述】起病时间、诱因、起病形式（急性/亚急性/慢性）、首发症状",
            "【时间段 N】YYYY.MM — YYYY.MM（医生自行分段）",
            "  - 变化诱因（如有）",
            "  - 感知障碍：现象（原话+行为）+ 信息源",
            "  - 思维障碍：现象（原话+行为）+ 信息源",
            "  - 情感障碍：现象（原话+行为）+ 信息源 + 性质",
            "  - 意志行为：现象（原话+行为）+ 信息源",
            "  - 认知功能（现象层）：行为表现",
            "  - 社会功能：工作/人际/自理变化",
            "  - 本期诊疗：就诊时间/机构/诊断/用药/剂量/疗效/不良反应/依从性",
            "【发病以来一般情况】睡眠/饮食/二便/体重",
            "【精神科专项】冲动行为、自伤行为、自杀行为/意念、外走行为、物质使用轨迹",
            "【药物汇总表】（可选）时间段/机构/诊断/药物/剂量/疗程疗效副作用"
        ]
    else:
        return []


def get_personal_history_template() -> str:
    """
    获取个人史标准模板

    Returns:
        个人史模板文本
    """
    return "胞X行X，否认吸烟、酗酒嗜好。"


def validate_required_fields(patient_data: Dict, required_fields: List[str]) -> tuple[bool, List[str]]:
    """
    验证必填字段

    Args:
        patient_data: 患者数据
        required_fields: 必填字段列表

    Returns:
        (是否全部有效, 缺失字段列表)
    """
    missing_fields = []

    for field in required_fields:
        # 支持嵌套字段（如 "basic_info.name"）
        keys = field.split('.')
        value = patient_data

        try:
            for key in keys:
                value = value[key]

            if not value or (isinstance(value, str) and value.strip() == ""):
                missing_fields.append(field)
        except (KeyError, TypeError):
            missing_fields.append(field)

    return len(missing_fields) == 0, missing_fields


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除非法字符

    Args:
        filename: 原始文件名

    Returns:
        清理后的文件名
    """
    # Windows文件名非法字符
    illegal_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']

    for char in illegal_chars:
        filename = filename.replace(char, '_')

    # 去除首尾空格
    filename = filename.strip()

    return filename


def truncate_text(text: str, max_length: int = 1000, suffix: str = "...") -> str:
    """
    截断文本

    Args:
        text: 原始文本
        max_length: 最大长度
        suffix: 截断后缀

    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def calculate_hospital_day(admission_date: str, current_date: str = None) -> int:
    """
    计算住院天数

    Args:
        admission_date: 入院日期（YYYY-MM-DD格式）
        current_date: 当前日期（YYYY-MM-DD格式，默认为今天）

    Returns:
        住院天数（第N天）

    Example:
        >>> calculate_hospital_day("2026-04-06", "2026-04-07")
        2
    """
    if not admission_date:
        return 0

    try:
        # 解析入院日期
        if isinstance(admission_date, datetime):
            admission = admission_date
        else:
            admission = datetime.strptime(admission_date, "%Y-%m-%d")

        # 解析当前日期
        if current_date:
            if isinstance(current_date, datetime):
                current = current_date
            else:
                current = datetime.strptime(current_date, "%Y-%m-%d")
        else:
            current = datetime.now()

        # 计算天数差（第N天）
        days = (current - admission).days + 1

        return days if days > 0 else 0

    except Exception as e:
        print(f"[ERROR] 计算住院天数失败: {e}")
        return 0


def validate_daily_course_info(daily_info: Dict) -> tuple[bool, List[str]]:
    """
    验证日常病程信息完整性

    Args:
        daily_info: 日常病程信息

    Returns:
        (是否有效, 缺失字段列表)

    Example:
        >>> daily_info = {
        ...     "date": "2026-04-07",
        ...     "condition_change": "患者今日情绪稳定...",
        ...     "mental_exam": "意识清楚，定向力完整...",
        ...     "treatment_opinion": "维持原治疗方案..."
        ... }
        >>> is_valid, missing = validate_daily_course_info(daily_info)
    """
    missing_fields = []

    # 必填字段
    required_fields = {
        "date": "记录日期",
        "condition_change": "病情变化",
        "mental_exam": "精神检查",
        "treatment_opinion": "处理意见"
    }

    for field, field_name in required_fields.items():
        if field not in daily_info:
            missing_fields.append(field_name)
        elif not daily_info[field] or (isinstance(daily_info[field], str) and daily_info[field].strip() == ""):
            missing_fields.append(field_name)

    # 可选字段验证（如果提供则格式正确）
    optional_fields = ["treatment_adjustment", "medication_change", "lab_results"]
    for field in optional_fields:
        if field in daily_info and not isinstance(daily_info[field], str):
            missing_fields.append(f"{field}（格式错误）")

    return len(missing_fields) == 0, missing_fields


def validate_risk_assessment(risk_data: Dict) -> tuple[bool, List[str]]:
    """
    验证风险评估数据格式

    Args:
        risk_data: 风险评估字典

    Returns:
        (是否有效, 错误列表)
    """
    errors = []
    valid_risks = ["suicide", "impulse", "elopement", "somatic"]
    valid_levels = ["无", "低", "中", "高"]

    for risk_key in valid_risks:
        if risk_key in risk_data:
            item = risk_data[risk_key]
            if not isinstance(item, dict):
                errors.append(f"风险评估.{risk_key} 格式错误，应为字典")
                continue
            if item.get("changed"):
                level_from = item.get("from", "")
                level_to = item.get("to", "")
                if level_from not in valid_levels:
                    errors.append(f"风险评估.{risk_key}.from 不是有效等级: {level_from}")
                if level_to not in valid_levels:
                    errors.append(f"风险评估.{risk_key}.to 不是有效等级: {level_to}")
                if not item.get("basis"):
                    errors.append(f"风险评估.{risk_key} 等级变化但缺少依据")

    return len(errors) == 0, errors


def validate_disease_evolution_phases(phases: list) -> tuple[bool, List[str]]:
    """
    验证病情演变特点结构化分段数据

    Args:
        phases: 时间段列表 [{"label": ..., "source": ..., "phenomena": ...}, ...]

    Returns:
        (是否有效, 错误列表)
    """
    errors = []
    if not isinstance(phases, list):
        return False, ["病情演变特点应为列表格式"]

    for i, phase in enumerate(phases):
        if not isinstance(phase, dict):
            errors.append(f"时间段 {i+1} 格式错误")
            continue
        if not phase.get("label", "").strip():
            errors.append(f"时间段 {i+1} 缺少时间段标注")
        if not phase.get("phenomena", "").strip():
            errors.append(f"时间段 {i+1} 缺少现象描述")

    return len(errors) == 0, errors


def convert_legacy_disease_evolution(patient_data: Dict) -> Dict:
    """
    向后兼容：将旧的 String 格式 disease_evolution 转换为新的结构化分段格式

    Args:
        patient_data: 患者数据

    Returns:
        转换后的患者数据（原地修改）
    """
    history = patient_data.get("history", {})
    de = history.get("disease_evolution")

    if de is None:
        return patient_data

    # 已经是有 phases 字段的对象，无需转换
    if isinstance(de, dict) and "phases" in de:
        return patient_data

    # String → 单段 Object
    if isinstance(de, str):
        patient_data["history"]["disease_evolution"] = {
            "phases": [
                {
                    "label": "",
                    "source": "",
                    "phenomena": de.strip()
                }
            ]
        }

    return patient_data


def format_hospital_day(day: int) -> str:
    """
    格式化住院天数显示

    Args:
        day: 住院天数

    Returns:
        格式化后的字符串（如"第2天"）
    """
    return f"第{day}天" if day > 0 else "未知"


def normalize_numerals(text: str) -> str:
    """
    v4.3: 将常见中文数字转换为阿拉伯数字

    Args:
        text: 原始文本

    Returns:
        数字规范化的文本
    """
    if not text:
        return text

    result = text

    # 保留的特殊短语（不转换）
    protected = [
        ("父母两系三代", "__PROTECTED_FAMILY__"),
        ("胞三行八", "__PROTECTED_SIB38__"),
        ("胞一", "__PROTECTED_SIB1__"),
        ("胞二", "__PROTECTED_SIB2__"),
        ("胞三", "__PROTECTED_SIB3__"),
        ("胞四", "__PROTECTED_SIB4__"),
        ("胞五", "__PROTECTED_SIB5__"),
        ("胞六", "__PROTECTED_SIB6__"),
        ("胞七", "__PROTECTED_SIB7__"),
        ("胞八", "__PROTECTED_SIB8__"),
        ("胞九", "__PROTECTED_SIB9__"),
    ]
    for orig, placeholder in protected:
        result = result.replace(orig, placeholder)

    # === 长模式优先（避免子串误匹配） ===

    # 二十余/三十余 等（在"十余"之前）
    result = result.replace("二十余", "20余")
    result = result.replace("三十余", "30余")
    result = result.replace("四十余", "40余")
    result = result.replace("十余", "10余")

    # 组合数字：七八→7-8, 两三→2-3 等
    result = result.replace("七八", "7-8")
    result = result.replace("两三", "2-3")
    result = result.replace("三四", "3-4")
    result = result.replace("五六", "5-6")
    result = result.replace("六七", "6-7")
    result = result.replace("八九", "8-9")

    # 整十数字（二十/三十 等，在单字之前）
    result = result.replace("九十", "90")
    result = result.replace("八十", "80")
    result = result.replace("七十", "70")
    result = result.replace("六十", "60")
    result = result.replace("五十", "50")
    result = result.replace("四十", "40")
    result = result.replace("三十", "30")
    result = result.replace("二十", "20")

    # 十几→1X
    result = result.replace("十九", "19")
    result = result.replace("十八", "18")
    result = result.replace("十七", "17")
    result = result.replace("十六", "16")
    result = result.replace("十五", "15")
    result = result.replace("十四", "14")
    result = result.replace("十三", "13")
    result = result.replace("十二", "12")
    result = result.replace("十一", "11")
    result = result.replace("十几", "10几")

    # 保护"两"作为重量单位（在单字数字转换之前）
    # 中文数字 + 两 → 阿拉伯数字 + __LIANG__
    for ch_digit, ar_digit in [("一", "1"), ("二", "2"), ("三", "3"), ("四", "4"),
                                ("五", "5"), ("六", "6"), ("七", "7"), ("八", "8"), ("九", "9")]:
        result = result.replace(f"{ch_digit}两", f"{ar_digit}__LIANG__")
    result = result.replace("半两", "__HALF_LIANG__")

    # 单字数字
    result = result.replace("九", "9")
    result = result.replace("八", "8")
    result = result.replace("七", "7")
    result = result.replace("六", "6")
    result = result.replace("五", "5")
    result = result.replace("四", "4")
    result = result.replace("三", "3")
    result = result.replace("二", "2")
    result = result.replace("一", "1")
    result = result.replace("十", "10")

    # 两→2
    result = result.replace("两", "2")

    # 恢复受保护的"两"（重量单位）
    result = result.replace("__LIANG__", "两")
    result = result.replace("__HALF_LIANG__", "半两")

    # 恢复受保护的短语
    for orig, placeholder in protected:
        result = result.replace(placeholder, orig)

    return result

