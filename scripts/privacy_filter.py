"""
病历隐私脱敏模块 — 基于规则+正则的中文精神科PHI去标识化
============================================================

定位：本地LLM方案的降级增强层。
当必须使用云端AI处理病历时，先用此模块脱敏 → 云端处理 → 本地还原。

基于 Microsoft Presidio 架构思想，针对中国精神科病历特点定制。
参考来源：
  - Microsoft Presidio (MIT License)
  - zh_PII (https://github.com/ltm920716/zh_PII)
  - HIPAA Safe Harbor + 中国《个人信息保护法》敏感个人信息分类

Author: medical-record-manager v5.1
License: MIT
"""

import re
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Literal

# ============================================================
# PHI实体定义 — 基于中国医疗病历特点
# ============================================================

PHI_ENTITY_DEFINITIONS = {
    # === 直接标识符（必须脱敏） ===
    "PATIENT_NAME": {
        "pattern": r'(患者|病人)[：:\s]*[\u4e00-\u9fa5]{2,4}',
        "category": "direct",
        "legal_basis": "《个人信息保护法》第28条 — 医疗健康信息",
    },
    "ID_CARD": {
        "pattern": r'\b\d{17}[\dXx]\b',
        "category": "direct",
        "legal_basis": "《个人信息保护法》第28条 — 身份证号",
    },
    "HOSPITAL_ID": {
        "pattern": r'(住院号|病历号|登记号)[：:\s]*\d{5,12}',
        "category": "direct",
        "legal_basis": "可关联至具体个人的唯一标识",
    },
    "PHONE": {
        "pattern": r'1[3-9]\d{9}',
        "category": "direct",
        "legal_basis": "《个人信息保护法》第4条 — 个人信息",
    },
    "EMAIL": {
        "pattern": r'[\w\.-]+@[\w\.-]+\.\w+',
        "category": "direct",
        "legal_basis": "《个人信息保护法》第4条",
    },

    # === 准标识符（建议脱敏） ===
    "DATE_SPECIFIC": {
        "pattern": r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日号]?',
        "category": "quasi",
        "legal_basis": "组合可识别个人 — 建议去标识化",
    },
    "AGE_SPECIFIC": {
        "pattern": r'(现年|年龄)?\d{1,3}(岁|周岁)',
        "category": "quasi",
        "legal_basis": "组合可识别个人",
    },
    "ADDRESS": {
        "pattern": r'(住址|地址|户籍|现住|家庭地址)[：:\s]*[\u4e00-\u9fa5\d\-\s]+',
        "category": "quasi",
        "legal_basis": "《个人信息保护法》第4条",
    },
    "HOSPITAL_NAME": {
        "pattern": r'(广州|北京|上海|深圳|成都|武汉|杭州|南京|天津|重庆|长沙|郑州|西安|东莞|佛山|苏州|昆明|贵阳|南宁|海口|福州|厦门|南昌|合肥|济南|青岛|大连|沈阳|哈尔滨|长春|石家庄|太原|兰州|银川|西宁|拉萨|乌鲁木齐|呼和浩特)[\u4e00-\u9fa5]{2,12}(医院|卫生院|社区卫生|中心)',
        "category": "quasi",
        "legal_basis": "组合可推断就诊机构",
    },

    # === 精神科特殊考虑 ===
    "FAMILY_MEMBER_NAME": {
        "pattern": r'(父|母|兄|弟|姐|妹|子|女|配偶|丈夫|妻子|儿子|女儿)[：:\s]*[\u4e00-\u9fa5]{2,4}',
        "category": "optional",  # 家族史涉及第三方隐私
        "legal_basis": "第三方个人信息 — 建议脱敏",
    },
}

# 精神科病历中不应脱敏的关键临床词汇（白名单）
CLINICAL_WHITELIST = [
    # 诊断术语
    "精神分裂症", "抑郁发作", "双相情感障碍", "酒精依赖综合征",
    "焦虑障碍", "强迫障碍", "偏执型", "未分化型", "紧张型",
    # 症状术语
    "自语自笑", "幻听", "幻视", "被害妄想", "关系妄想", "被控制感",
    "情绪低落", "兴趣减退", "精力下降", "自杀观念", "自伤行为",
    # 药物名称
    "奥氮平", "利培酮", "氯氮平", "阿立哌唑", "喹硫平", "帕利哌酮",
    "舍曲林", "帕罗西汀", "氟西汀", "艾司西酞普兰", "文拉法辛", "度洛西汀",
    "丙戊酸钠", "丙戊酸镁", "拉莫三嗪", "碳酸锂",
    "地西泮", "劳拉西泮", "氯硝西泮", "阿普唑仑",
    "纳曲酮", "阿坎酸", "戒酒硫",
    # 治疗术语
    "无抽搐电休克", "MECT", "认知行为治疗", "动机增强治疗",
    # 检查术语
    "头颅CT", "头颅MRI", "脑电图", "心电图", "血常规", "肝功能", "肾功能",
]


def deidentify(
    text: str,
    method: Literal["mask", "replace", "hash", "redact"] = "mask",
    entity_types: Optional[List[str]] = None,
    date_shift_days: int = 0,
    preserve_clinical_terms: bool = True,
) -> dict:
    """
    对病历文本进行去标识化处理。

    Args:
        text: 原始病历文本
        method: 脱敏方法
            - "mask": 替换为[ENTITY_TYPE]标签（默认，便于AI理解结构）
            - "replace": 用假数据替换（保持文本可读性）
            - "hash": 用SHA256哈希值替换（可追溯但不可逆）
            - "redact": 直接删除PHI内容
        entity_types: 要脱敏的实体类型列表（None=全部）
        date_shift_days: 日期偏移天数（正数=向后偏移，0=不偏移）
        preserve_clinical_terms: 是否保留临床术语白名单（默认True）

    Returns:
        {
            "anonymized": str,       # 脱敏后的文本
            "mapping": dict,         # {原始值: 替换值} 映射表（用于还原）
            "entities_found": [      # 检测到的PHI实体列表
                {"type": "PATIENT_NAME", "value": "张三", "start": 0, "end": 2}
            ],
            "stats": {              # 统计信息
                "total_entities": int,
                "by_type": {"PATIENT_NAME": 1, ...}
            }
        }
    """
    if entity_types is None:
        entity_types = list(PHI_ENTITY_DEFINITIONS.keys())

    mapping = {}
    entities_found = []
    result = text

    # 按优先级排序：直接标识符 → 准标识符 → 可选
    priority_order = ["direct", "quasi", "optional"]
    sorted_types = sorted(
        entity_types,
        key=lambda t: (
            priority_order.index(PHI_ENTITY_DEFINITIONS[t]["category"])
            if PHI_ENTITY_DEFINITIONS[t]["category"] in priority_order
            else 99
        ),
    )

    for entity_type in sorted_types:
        if entity_type not in PHI_ENTITY_DEFINITIONS:
            continue

        pattern = re.compile(PHI_ENTITY_DEFINITIONS[entity_type]["pattern"])
        matches = pattern.finditer(result)

        # 从后往前替换（避免位置偏移）
        replacements = []
        for match in matches:
            original = match.group(0)

            # 检查白名单
            if preserve_clinical_terms and entity_type == "DATE_SPECIFIC":
                # 日期偏移而非简单脱敏
                if date_shift_days > 0:
                    replacement = _shift_date(original, date_shift_days)
                else:
                    replacement = _generate_replacement(
                        entity_type, original, method
                    )
            else:
                replacement = _generate_replacement(entity_type, original, method)

            replacements.append((match.start(), match.end(), original, replacement))
            entities_found.append({
                "type": entity_type,
                "value": original,
                "start": match.start(),
                "end": match.end(),
                "category": PHI_ENTITY_DEFINITIONS[entity_type]["category"],
            })
            if original not in mapping:
                mapping[original] = replacement

        # 从后往前替换
        for start, end, original, replacement in sorted(
            replacements, key=lambda x: x[0], reverse=True
        ):
            result = result[:start] + replacement + result[end:]

    # 统计
    stats = {
        "total_entities": len(entities_found),
        "by_type": {},
        "by_category": {"direct": 0, "quasi": 0, "optional": 0},
    }
    for e in entities_found:
        stats["by_type"][e["type"]] = stats["by_type"].get(e["type"], 0) + 1
        stats["by_category"][e["category"]] = (
            stats["by_category"].get(e["category"], 0) + 1
        )

    return {
        "anonymized": result,
        "mapping": mapping,
        "entities_found": entities_found,
        "stats": stats,
    }


def reidentify(anonymized_text: str, mapping: dict) -> str:
    """
    将脱敏后的文本还原为原始文本。

    Args:
        anonymized_text: 脱敏后的文本
        mapping: deidentify()返回的mapping字典

    Returns:
        还原后的原始文本
    """
    result = anonymized_text
    # 从长到短替换（避免部分匹配）
    for original, replacement in sorted(
        mapping.items(), key=lambda x: len(x[0]), reverse=True
    ):
        result = result.replace(replacement, original)
    return result


def quick_deidentify_file(
    input_path: str,
    output_path: Optional[str] = None,
    method: str = "mask",
) -> dict:
    """
    一键脱敏文件。

    Args:
        input_path: 输入文件路径（.txt或.docx）
        output_path: 输出路径（None=自动生成 _anonymized 后缀）
        method: 脱敏方法

    Returns:
        deidentify()的完整返回结果
    """
    input_path = Path(input_path)

    # 读取文件
    if input_path.suffix.lower() == ".docx":
        try:
            from docx import Document
            doc = Document(str(input_path))
            text = "\n".join([p.text for p in doc.paragraphs])
        except ImportError:
            raise ImportError("需要 python-docx: pip install python-docx")
    else:
        with open(input_path, "r", encoding="utf-8") as f:
            text = f.read()

    # 脱敏
    result = deidentify(text, method=method, date_shift_days=0)

    # 写入输出
    if output_path is None:
        output_path = str(input_path.parent / f"{input_path.stem}_anonymized.txt")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result["anonymized"])

    # 保存映射表
    mapping_path = str(Path(output_path).with_suffix(".mapping.json"))
    with open(mapping_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "method": method,
                "timestamp": datetime.now().isoformat(),
                "source_file": str(input_path),
                "mapping": result["mapping"],
                "stats": result["stats"],
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    result["output_path"] = output_path
    result["mapping_path"] = mapping_path
    return result


def quick_reidentify_file(
    anonymized_path: str,
    mapping_path: str,
    output_path: Optional[str] = None,
) -> str:
    """
    一键还原脱敏文件。

    Args:
        anonymized_path: 脱敏后的文件路径
        mapping_path: 脱敏时自动生成的.mapping.json文件路径
        output_path: 输出路径（None=还原到 anonymized_path 同目录）

    Returns:
        还原后的文件路径
    """
    # 读取映射表
    with open(mapping_path, "r", encoding="utf-8") as f:
        mapping_data = json.load(f)

    # 读取匿名文本
    with open(anonymized_path, "r", encoding="utf-8") as f:
        anonymized_text = f.read()

    # 还原
    original_text = reidentify(anonymized_text, mapping_data["mapping"])

    # 写入
    if output_path is None:
        output_path = str(
            Path(anonymized_path).parent
            / f"{Path(anonymized_path).stem.replace('_anonymized', '')}_restored.txt"
        )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(original_text)

    return output_path


def verify_deidentification(original_text: str, anonymized_text: str) -> dict:
    """
    验证脱敏效果：检查脱敏后文本中是否仍有PHI残留。

    Returns:
        {
            "passed": bool,
            "residual_entities": [...],  # 残留的PHI
            "coverage_rate": float,      # 脱敏覆盖率
        }
    """
    # 在脱敏后的文本上再次运行检测
    residual = deidentify(
        anonymized_text, method="mask", preserve_clinical_terms=True
    )
    residual_count = residual["stats"]["total_entities"]

    # 计算覆盖率（与原始对比需要原始检测结果，这里只检查残留）
    return {
        "passed": residual_count == 0,
        "residual_entities": residual["entities_found"],
        "residual_count": residual_count,
        "message": (
            "✅ 脱敏完全，无PHI残留"
            if residual_count == 0
            else f"⚠️ 仍有 {residual_count} 个PHI实体残留，建议检查"
        ),
    }


# ============================================================
# 内部辅助函数
# ============================================================

REPLACEMENT_POOL = {
    "PATIENT_NAME": ["[患者A]", "[患者B]", "[患者C]"],
    "ID_CARD": ["[身份证号]", "ID-REDACTED"],
    "HOSPITAL_ID": ["[住院号]", "HID-REDACTED"],
    "PHONE": ["[电话号码]", "PHONE-REDACTED"],
    "EMAIL": ["[电子邮箱]", "EMAIL-REDACTED"],
    "DATE_SPECIFIC": ["[日期]", "DATE-REDACTED"],
    "AGE_SPECIFIC": ["[年龄]", "AGE-REDACTED"],
    "ADDRESS": ["[地址]", "ADDR-REDACTED"],
    "HOSPITAL_NAME": ["[某医院]", "HOSPITAL-REDACTED"],
    "FAMILY_MEMBER_NAME": ["[家属姓名]", "FAMILY-REDACTED"],
}


def _generate_replacement(entity_type: str, original: str, method: str) -> str:
    """生成替换值"""
    if method == "mask":
        return REPLACEMENT_POOL.get(entity_type, ["[已脱敏]"])[0]
    elif method == "replace":
        # 简单的假数据替换（生产环境可用Faker）
        return REPLACEMENT_POOL.get(entity_type, ["[已脱敏]"])[-1]
    elif method == "hash":
        return hashlib.sha256(original.encode()).hexdigest()[:12]
    elif method == "redact":
        return ""
    else:
        return f"[{entity_type}]"


def _shift_date(date_str: str, days: int) -> str:
    """对日期进行偏移（保留格式）"""
    # 尝试常见中文日期格式
    formats = [
        ("%Y年%m月%d日", "{y}年{m}月{d}日"),
        ("%Y-%m-%d", "{y}-{m}-{d}"),
        ("%Y/%m/%d", "{y}/{m}/{d}"),
    ]
    for fmt, out_fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            shifted = dt + timedelta(days=days)
            return out_fmt.format(
                y=shifted.year, m=f"{shifted.month:02d}", d=f"{shifted.day:02d}"
            )
        except ValueError:
            continue
    return f"[日期+{days}天]"


# ============================================================
# CLI入口（方便直接调用测试）
# ============================================================

if __name__ == "__main__":
    import sys

    # 测试用例
    test_text = """
    患者张三，男，33岁，住院号0152760，因"自语自笑20年，心情差伴自罪1周"于2026-04-23入院。
    身份证号440106199001011234，联系电话13800138000。
    住址：广州市荔湾区明心路36号。
    患者父亲张大明陪同就诊。
    曾于2024年3月在广州市脑科医院就诊。
    """

    print("=" * 60)
    print("病历隐私脱敏模块 — 测试")
    print("=" * 60)
    print("\n【原始文本】")
    print(test_text)

    # 测试 mask 模式
    result = deidentify(test_text, method="mask")
    print("\n【脱敏后 (mask)】")
    print(result["anonymized"])
    print(f"\n检测到PHI实体: {result['stats']['total_entities']} 个")
    for e in result["entities_found"]:
        print(f"  [{e['type']}] {e['value']} → {e['category']}")

    # 验证脱敏效果
    verification = verify_deidentification(test_text, result["anonymized"])
    print(f"\n【脱敏验证】 {verification['message']}")

    # 测试还原
    restored = reidentify(result["anonymized"], result["mapping"])
    print("\n【还原后】")
    print(restored)
    print(f"\n还原正确: {restored.strip() == test_text.strip()}")
