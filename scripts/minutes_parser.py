"""
AI 纪要读取器 - 原样读取文件，不解析内容
新架构：代码只负责读文件，内容理解交给 AI（WorkBuddy）

支持格式：
- .txt 纯文本
- .json 钉钉AI纪要JSON（提取 fullSummary 或 aiSummary）
- .docx Word文档（提取段落文本）
- .md Markdown文件
"""

import os
import json
from typing import Optional


def read_minutes_file(file_path: str) -> str:
    """
    原样读取 AI 纪要文件，返回纯文本
    
    Args:
        file_path: 文件路径（支持 .txt/.json/.docx/.md）
    
    Returns:
        文件的纯文本内容
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.txt':
        return _read_txt(file_path)
    elif ext == '.json':
        return _read_json(file_path)
    elif ext == '.docx':
        return _read_docx(file_path)
    elif ext == '.md':
        return _read_txt(file_path)  # markdown 也按纯文本读
    else:
        # 未知格式，尝试按纯文本读取
        return _read_txt(file_path)


def _read_txt(file_path: str) -> str:
    """读取纯文本文件（自动检测编码）"""
    for encoding in ['utf-8', 'gbk', 'gb2312', 'utf-16']:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
    
    # 所有编码都失败，使用 binary mode + decode with errors='replace'
    with open(file_path, 'rb') as f:
        raw = f.read()
    return raw.decode('utf-8', errors='replace')


def _read_json(file_path: str) -> str:
    """
    读取钉钉 AI 纪要 JSON 文件
    提取 fullSummary / aiSummary / summary 字段
    如果找不到这些字段，返回整个 JSON 的格式化文本
    """
    text = _read_txt(file_path)
    try:
        data = json.loads(text)
        
        # 尝试提取钉钉 AI 纪要的常见字段
        # 钉钉格式1: {"result": {"fullSummary": "..."}}
        result = data.get('result', data)
        if isinstance(result, dict):
            summary = (
                result.get('fullSummary') or
                result.get('aiSummary') or
                result.get('summary') or
                result.get('content') or
                ''
            )
            if summary:
                return summary
        
        # 如果是数组，尝试提取第一个元素的摘要
        if isinstance(data, list) and len(data) > 0:
            first = data[0]
            if isinstance(first, dict):
                summary = (
                    first.get('fullSummary') or
                    first.get('aiSummary') or
                    first.get('summary') or
                    ''
                )
                if summary:
                    return summary
        
        # 找不到摘要字段，返回格式化的 JSON
        return json.dumps(data, ensure_ascii=False, indent=2)
        
    except json.JSONDecodeError:
        # 不是合法 JSON，按纯文本返回
        return text


def _read_docx(file_path: str) -> str:
    """读取 Word 文档的段落文本"""
    try:
        from docx import Document
        doc = Document(file_path)
        paragraphs = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                paragraphs.append(text)
        return '\n'.join(paragraphs)
    except ImportError:
        raise ImportError("需要 python-docx 包来读取 .docx 文件，请运行: pip install python-docx")


def build_patient_data_from_minutes(
    patient_id: str,
    name: str,
    gender: str,
    age: int,
    admission_date: str,
    present_illness_text: str,
    mental_exam_text: str,
    chief_complaint: str = ""
) -> dict:
    """
    【新架构 v5.0】
    不再用 regex 解析内容，而是将原文保存，
    由 AI（WorkBuddy）来理解内容并生成结构化数据。
    
    此方法仅做一件事：构建包含原文的患者数据骨架，
    具体字段由 AI 后续填充。
    
    Args:
        patient_id: 住院号
        name: 姓名
        gender: 性别
        age: 年龄
        admission_date: 入院日期 (YYYY-MM-DD)
        present_illness_text: 现病史 AI 纪要原文（不解析）
        mental_exam_text: 精神检查 AI 纪要原文（不解析）
        chief_complaint: 主诉（可选）
    
    Returns:
        包含原文的患者数据字典，待 AI 理解后填充
    """
    # 计算总病程（如果主诉有时间信息）
    disease_duration = ""
    if chief_complaint:
        # 尝试从主诉提取时间（如"饮酒20余年"）
        import re
        duration_match = re.search(r'(\d+\.?\d*)\s*余?\s*年', chief_complaint)
        if duration_match:
            years = float(duration_match.group(1))
            # 四舍五入
            if years == int(years):
                disease_duration = f"总病程{int(years)}年"
            else:
                disease_duration = f"总病程{years}年"
    
    patient_data = {
        "patient_id": patient_id,
        "basic_info": {
            "name": name,
            "age": str(age),
            "gender": gender,
            "admission_date": admission_date,
            "chief_complaint": chief_complaint or "待医生提供",
            "chief_complaint_duration": disease_duration or "总病程待核算",
            "admission_type": "自愿住院",
            "admission_count": 1
        },
        "history": {
            # 原文保存（由 AI 理解后填充各字段）
            "present_illness_raw": present_illness_text,
            "mental_exam_raw": mental_exam_text,
            # 以下字段待 AI 理解后填充
            "onset_form": "",
            "disease_evolution": "",
            "previous_treatments": "",
            "admission_reason": "",
            "general_condition": "",
            "differential_info": "",
            "past_history": "",
            "personal_history": "",
            "family_history": "",
            "auxiliary_exam": ""
        },
        "examination": {
            "physical": "",
            "mental": mental_exam_text  # 精神检查原文暂存，待 AI 整理
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
            "created_at": __import__('datetime').datetime.now().isoformat(),
            "updated_at": __import__('datetime').datetime.now().isoformat(),
            "ai_minutes_parsing": "pending"  # 标记：待 AI 理解
        }
    }
    
    return patient_data


def extract_structured_content(ai_understanding_result: dict) -> dict:
    """
    【由 AI 调用】
    将 AI 对纪要的理解结果（结构化 dict）合并到 patient_data
    
    Args:
        ai_understanding_result: AI 理解后的结构化结果，格式：
        {
            "introduction": "患者XXX，男，X岁，因...",
            "item1_general": "...",
            "item2_course": "...",
            ...
        }
    
    Returns:
        更新后的 history/examination 字段
    """
    # 此函数由 AI 在理解纪要后调用
    # 直接将 AI 的输出合并到对应字段
    return ai_understanding_result


if __name__ == '__main__':
    # 测试：读取文件
    import sys
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        print(f"[TEST] 读取文件: {file_path}")
        try:
            content = read_minutes_file(file_path)
            print(f"[OK] 读取成功，共 {len(content)} 字符")
            print("=" * 50)
            print(content[:500])
            if len(content) > 500:
                print("... (截断)")
        except Exception as e:
            print(f"[ERROR] {e}")
    else:
        print("用法: python minutes_parser.py <文件路径>")
        print("支持格式: .txt .json .docx .md")
