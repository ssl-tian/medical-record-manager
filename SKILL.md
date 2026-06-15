---
name: medical-record-manager
description: 成瘾医学科患者管理系统。支持患者管理（录入、切换、查询）、首次病程记录生成、日常病程记录生成、风险评估、治疗方案库管理、治疗知识库构建（消化PDF/网页/文本素材）。触发词：病历、首程记录、首次病程、日常病程、病程记录、患者管理、风险评估、治疗方案、入院记录、查房记录、住院记录、成瘾医学、酒精依赖、治疗知识库、知识消化、消化指南、素材导入、治疗方案构建、PDF提取、指南解读。
version: 5.1
author: 成瘾医学科
---

# 成瘾医学科患者管理系统

## 概述

本Skill用于管理成瘾医学科酒精依赖患者的住院记录、病程生成和日常管理。支持15-20名患者的规模化管理，自动生成符合模板规范的Word文档。v5.1 **隐私安全增强**：强制本地LLM模式，新增隐私保护章节和脱敏降级方案。v5.0 架构重构：采用 **AI直驱 + JSON中间格式**，代码只负责文件读取和Word写入，AI负责理解内容并按13条模板格式生成结构化输出。

## 核心功能

1. **患者管理**：录入、切换、查询患者信息
2. **AI直驱首次病程记录** 🆕：AI直接理解AI纪要内容，按13条模板生成结构化JSON，代码确定性写入Word
3. **从AI纪要文件创建患者** 🆕：代码原样读取两份AI纪要文件（现病史+精神检查），传给AI理解，不解析结构
4. **日常病程记录**：三段式模板 + 核心症状量化对比 + 药物反应对比 + 风险按需评估
5. **现病史生成**：完整版现病史模板，支持动态分段、多维度展开、信息源标注
6. **风险评估**：自动识别躯体/精神风险
7. **治疗方案库**：标准化药物治疗方案管理
8. **治疗知识库** 🆕：消化PDF/网页/文本素材，自动提取治疗方案并积累到知识库

## 文件结构

```
scripts/
├── patient_manager.py      # 核心门面模块（所有功能的入口）
├── data_storage.py         # JSON数据持久化
├── course_generator.py     # Word文档生成（首次病程 + 日常病程）
├── history_generator.py    # 🆕 现病史生成模块
├── utils.py                # 工具函数
├── risk_assessment.py      # 风险评估
├── treatment_library.py    # 治疗方案库
├── treatment_schemes.json  # 方案配置数据
├── knowledge_ingest.py     # 🆕 素材消化模块（llm-wiki风格）
├── privacy_filter.py       # 🔒 v5.1 病历隐私脱敏模块（降级方案用）
└── treatment_wiki/         # 🆕 知识库存储
    ├── .wiki-cache.json    # 内容指纹缓存（去重）
    ├── log.md              # 操作日志
    ├── raw/                # 原始素材（不可变）
    │   ├── articles/       # 网页文章
    │   ├── pdfs/           # PDF提取内容
    │   └── plain/          # 纯文本
    └── wiki/               # AI生成的知识页面
        ├── sources/        # 素材摘要页
        ├── entities/       # 实体页（药物、疾病、概念）
        ├── topics/         # 主题页
        └── comparisons/    # 对比分析
```

---

## 🔒 隐私保护模式（强制要求）

> **最高优先级规则**：患者病历含《个人信息保护法》第28条定义的敏感个人信息。所有涉及患者PHI的病历书写任务，必须在本地LLM模式下执行，禁止使用云端AI处理原始患者数据。

### 数据安全架构

```
钉钉AI纪要(.txt) → 本地文件系统读取
    → WorkBuddy本地LLM(Ollama+Qwen3)理解内容
    → 生成结构化JSON
    → Python(python-docx)确定性写入Word
    → 全程本机完成，零网络传输
```

### 启动隐私模式（每次病历书写前必做）

**Step 1: 安装并启动Ollama本地模型**

```bash
# 下载安装 Ollama: https://ollama.com/download/windows
# 拉取推荐中文模型
ollama pull qwen3:8b

# 验证模型就绪
ollama run qwen3:8b "你好，请确认你已就绪"
```

**Step 2: WorkBuddy配置**

1. 设置 → AI模型管理 → 添加本地模型(Ollama)
2. 模型名称填写：`qwen3:8b`（与 `ollama pull` 的模型名一致）
3. 保存并切换为该模型
4. 设置 → 安全与隐私 → 启用**隐私模式** → 点击**强制清空现有缓存**
5. 验证：状态栏显示"本地模型已就绪"且右上角出现"隐私模式:ON"标识

**Step 3: 确认离线**

- Windows：资源监视器 → 筛选 WorkBuddy.exe → 确认网络发送/接收 = 0
- 发送测试消息 → 确认响应来自本地模型（而非云端）

### 模型选择

| 模型 | RAM需求 | 中文能力 | 推荐场景 |
|------|---------|---------|---------|
| `qwen3:8b` | ≥16GB | ⭐⭐⭐⭐⭐ | **首选** — 中文医疗理解最佳 |
| `qwen3:4b` | ≥8GB | ⭐⭐⭐⭐ | 低配机器 |
| `deepseek-r1:8b` | ≥16GB | ⭐⭐⭐⭐ | 备选 |

### 降级策略

若本地模型暂时不可用（首次配置中/硬件不足）：

**降级方案A — 脱敏后云端处理**（需先部署 `privacy_filter.py`）：
```
原始纪要 → 本地脱敏(privacy_filter.py) → 匿名化文本 → 云端AI → JSON → 本地还原 → Word
```

**降级方案B — 手动模式**：
- 医生手动填写13条模板关键字段
- AI仅提供格式排版辅助（不接触PHI内容）

### 隐私铁律

- ❌ **严禁**将含患者姓名、住院号、具体日期、家族史、个人史的原始纪要文件发送至云端AI
- ❌ **严禁**在隐私模式未启用、本地模型未加载的情况下执行 `add_patient_from_minutes_files()`
- ❌ **严禁**将生成的JSON或Word文档上传至任何云存储服务（除非医院内部审批的加密通道）
- ✅ **必须**每次病历书写前验证隐私模式为ON + 本地模型已就绪
- ✅ **必须**定期清空WorkBuddy缓存（设置 → 安全与隐私 → 清空缓存）
- ✅ **必须**在完成病历生成后，从WorkBuddy对话历史中删除含PHI的会话

---

## 使用前置条件

1. **Python依赖**：需要 `python-docx` 包。运行前先安装：
   ```
   pip install python-docx
   ```

2. **隐私环境**：必须配置本地LLM + 隐私模式（见上方🔒隐私保护模式章节）。

3. **工作目录**：系统在当前工作目录下创建 `patients/` 目录存储患者数据。

4. **Python路径**：使用 `sys.path.insert` 将 `scripts/` 目录加入模块搜索路径。

## 使用方法

### 初始化

```python
import sys, os
from pathlib import Path

# 将scripts目录加入模块搜索路径
skill_dir = Path(r"C:\Users\12962\.workbuddy\skills\medical-record-manager\scripts")
sys.path.insert(0, str(skill_dir))

from patient_manager import PatientManager, create_sample_patient_data

# 创建管理器（默认在当前工作目录下创建patients/目录）
pm = PatientManager()
```

### 患者数据结构

```python
patient_data = {
    "patient_id": "住院号",
    "basic_info": {
        "name": "姓名", "age": "年龄", "gender": "性别",
        "admission_date": "入院日期(YYYY-MM-DD)",
        "chief_complaint": "主诉",
        "chief_complaint_duration": "总病程[X]年（根据主诉时间填写）"
    },
    "history": {
        "onset_form": "一般特征及起病形式（患者系青/中/老年男/女性，慢性迁延性/反复/急性病程，起病特点？，病后社会功能受损）",
        "disease_duration": "病程（总病程X年）",
        "disease_evolution": {"phases": [{"label": "YYYY.MM—YYYY.MM", "source": "家属关系", "phenomena": "原始现象（原话+行为），禁止精神科术语和认知评估"}]},
        "previous_treatments": "既往诊疗经过（无则写：既往未予诊治）",
        "admission_reason": "本次入院原因（最严重症状表现+家属觉其病情严重，遂至门诊/急诊就诊）",
        "general_condition": "一般情况",
        "differential_info": "与鉴别诊断有关的阳性或阴性资料",
        "past_history": "既往史",
        "personal_history": "个人史（胞X行X，否认吸烟、酗酒嗜好；不足时留空）",
        "family_history": "家族史",
        "auxiliary_exam": "辅助检查",
        "present_illness": {  # 🆕 现病史（完整版，v4.1）
            "informant": "信息提供者声明",
            "onset": {"time": "", "precipitant": "", "form": "急性/亚急性/慢性", "first_symptoms": ""},
            "phases": [{
                "label": "YYYY.MM—YYYY.MM", "trigger": "", 
                "perception": "", "thought": "", "mood": "", "volition": "",
                "cognition": "", "social_function": "",
                "treatment": {"institution": "", "date": "", "diagnosis": "", "medication": "", 
                              "dosage": "", "response": "", "adverse_effects": "", "adherence": ""}
            }],
            "general_condition_psych": {"sleep": "", "appetite": "", "bowel_bladder": "", "weight": "",
                                         "impulsivity": "", "self_harm": "", "suicide": "", "elopement": "", "substance_use": ""},
            "medication_table": []
        }
    },
    "examination": {
        "physical": "体格检查（无特殊使用标准模板）",
        "mental": "专科检查"
    },
    "diagnosis": {
        "primary": "主要诊断",
        "basis": "诊断依据",
        "differential": "鉴别诊断"
    },
    "treatment": {
        "plan": "治疗方案"
    }
}
```

### 患者管理

```python
# 添加患者
pm.add_patient(patient_data)

# 切换患者
pm.switch_patient("住院号")

# 列出所有患者
patients = pm.list_patients()

# 查看患者摘要
pm.print_patient_summary()
```

### 从AI纪要创建患者 🆕（v5.0 新架构）

**触发条件**：用户通过钉钉录音卡完成新病人及家属对话后，在钉钉 AI 纪要中分别导出「现病史」和「精神检查」两份纪要文件（.txt/.docx）。用户 @skill 并附上文件路径时，自动触发此功能。

**v5.0 架构（AI直驱 + JSON中间格式）**：

```
AI纪要文件(.txt) → 代码原样读取 → 传给WorkBuddy(AI)
       ↓
  AI理解内容，按13条模板生成结构化JSON
       ↓
   代码用JSON确定性写入Word（格式100%可控）
```

**使用方式**：

```python
import sys, os
from pathlib import Path

skill_dir = Path(r"C:/Users/12962/.workbuddy/skills/medical-record-manager/scripts")
sys.path.insert(0, str(skill_dir))

from patient_manager import PatientManager

pm = PatientManager()

# 两份 AI 纪要文件路径
present_illness_file = r"C:/Users/12962/Desktop/现病史_酒精依赖_20260524.txt"
mental_exam_file = r"C:/Users/12962/Desktop/精神检查_20260524.txt"

# Step 1: 从AI纪要文件创建患者（代码只读取，不解析）
result = pm.add_patient_from_minutes_files(
    patient_id="20260524001",  # 住院号
    name="张三",
    gender="男",
    age=45,
    admission_date="2026-05-24",
    present_illness_file=present_illness_file,
    mental_exam_file=mental_exam_file,
    chief_complaint="反复饮酒20余年，停饮后不适1周"  # 可选
)

if result["status"] == "success":
    print(f"患者创建成功！")
    print(f"住院号：{result['patient_id']}")
    print(f"
[下一步] AI请理解以下内容，按13条模板生成结构化JSON：")
    print(f"现病史原文：{result['present_illness_raw'][:200]}...")
    print(f"精神检查原文：{result['mental_exam_raw'][:200]}...")
    print(f"
JSON Schema：{result['json_schema']}")
else:
    print(f"创建失败：{result['message']}")
```

**Step 2: AI理解纪要内容，生成结构化JSON**

AI收到Step 1的 `present_illness_raw` 和 `mental_exam_raw` 后，按13条模板格式生成如下JSON（MVP阶段前5条必填）：

```json
{
    "introduction": "患者张三，男，45岁，因「反复饮酒20余年，停饮后不适1周」于2026-05-24以「自愿住院」第1次入院。",
    "general_features": "患者系中年男性，慢性病程，起病隐匿，病后社会功能逐渐受损。",
    "disease_course": "总病程20余年。",
    "evolution": "据家属反映，患者20余年前开始饮酒，初期为社交性饮酒。约10年前饮酒量逐渐增加，每日饮酒约500ml白酒，无法自控。5年前曾因「酒精所致精神障碍」在外院住院治疗，好转后出院。1周前患者停饮后出现手抖、心慌、睡眠障碍，家属觉其病情加重，遂至我院就诊。",
    "past_treatment": "曾予「地西泮、纳曲酮」等药物治疗，疗效尚可，但因经济原因未坚持服药。未定期复诊。",
    "admission_reason": "1周前患者停饮后出现手抖、心慌、失眠，家属觉其病情严重，遂至门诊就诊，拟「酒精依赖综合征」以「自愿住院」收入我科。",
    "diagnosis_basis": "患者为中年男性，慢性病程20余年。据家属反映，患者反复饮酒无法自控，停饮后出现戒断症状。精神检查见戒断综合征（焦虑、躯体不适），未引出幻觉、妄想等精神病性症状，自知力部分存在。根据ICD-10诊断标准，考虑「酒精依赖综合征」",
    "diagnosis_primary": "酒精依赖综合征",
    "diagnosis_differential": "1. 需与「焦虑症」鉴别：患者虽有焦虑情绪，但有明确的长期饮酒史及戒断症状，焦虑症状与戒断相关，不支持原发性焦虑症。2. 需与「双相情感障碍」鉴别：患者无典型躁狂或轻躁狂发作史，情绪变化与饮酒及戒断相关，不支持双相情感障碍。",
    "treatment_plan": "1. 药物治疗：予地西泮替代治疗，逐渐减量；予纳曲酮降低复饮风险；对症支持治疗。2. 心理治疗：待患者病情稳定后，择期行动机增强治疗及认知行为治疗。3. 健康教育：嘱家属监督患者，避免复饮。"
}
```

**Step 3: 调用 `generate_first_course_from_ai_json()` 写入Word**

```python
# AI生成上述JSON后，调用此方法确定性写入Word
word_path = pm.generate_first_course_from_ai_json(
    patient_id="20260524001",
    ai_json=ai_json,   # 上一步AI生成的结构化JSON
    output_path=r"C:/Users/12962/Desktop/首次病程_张三_20260524.docx"  # 可选
)
print(f"首次病程记录已生成：{word_path}")
```

**MVP阶段范围**（前5条 + 诊断 + 诊疗计划）：

| 模板条目 | JSON字段名 | 必填 | 说明 |
|----------|------------|------|------|
| 入院导语 | `introduction` | ✅ | 姓名/性别/年龄/主诉/入院日期/方式/次数 |
| 1.一般特征及起病形式 | `general_features` | ✅ | 年龄表述/起病形式 |
| 2.病程 | `disease_course` | ✅ | 总病程X年 |
| 3.病情演变特点 | `evolution` | ✅ | 时间锚三段式，家属描述，**200-400字** |
| 4.既往诊疗经过 | `past_treatment` | ✅ | 药物用「」包裹 |
| 5.本次入院原因 | `admission_reason` | ✅ | 相对时间，门诊/急诊留空 |
| 诊断依据 | `diagnosis_basis` | ✅ | ≤200字；病史高度凝练+精神检查→综合征归纳+ICD-10诊断 |
| 初步诊断 | `diagnosis_primary` | ✅ | 主要诊断名称 |
| 鉴别诊断 | `diagnosis_differential` | ✅ | 分1、2点论述 |
| 诊疗计划 | `treatment_plan` | ✅ | 整合为一个段落 |
| 6-13条 | `general_condition`~`auxiliary_exam` | ⬜ | MVP阶段留空，医生手写 |

**返回结果**：
- `status`: `"success"` 或 `"error"`
- `patient_id`: 住院号
- `present_illness_raw`: 现病史纪要原文（供AI理解）
- `mental_exam_raw`: 精神检查纪要原文（供AI理解）
- `json_schema`: 13条模板的JSON schema（供AI参考）
- `message`: 错误信息（如失败）

**后续操作**：
1. AI理解 `present_illness_raw` 和 `mental_exam_raw`，生成结构化JSON
2. 调用 `pm.generate_first_course_from_ai_json(patient_id, ai_json)` 写入Word
3. 生成的Word文档格式100%符合13条模板，可直接打印或编辑
4. 精神检查（item12）MVP阶段留空，由医生手写补充


### 日常病程记录生成

```python
daily_info = {
    "date": "2026-04-07",
    "condition_change": "患者今日情绪稳定，夜间睡眠改善",
    "mental_exam": "意识清楚，定向力完整，接触主动，情绪平稳",
    "treatment_opinion": "维持原治疗方案，继续观察"
    # 可选: treatment_adjustment, medication_change, lab_results
    # 🆕 v4.1 新增:
    # "symptom_comparison": {"previous": {"hallucination": "", ...}, "current": {"hallucination": "", ...}}
    # "medication_response": {"efficacy_change": "", "new_adverse_effects": "", "blood_drug_level": ""}
    # "risk_assessment": {"suicide": {"changed": True, "from": "低", "to": "中", "basis": "...", "intervention": "..."}}
}

file_path = pm.add_daily_course_record("住院号", daily_info)
```

### 现病史生成（v4.3）

```python
# 生成现病史文档（需先加载患者数据）
patient_data = pm.storage.load_patient("住院号")
file_path = pm.present_illness_generator.generate(patient_data)

# 查看缺少哪些字段（交互式提示）
prompts = pm.present_illness_generator.prompt_missing_fields(patient_data)
print(prompts)
```

### 风险评估

```python
# 基于既往史的风险评估
risks = pm.perform_risk_assessment("住院号")

# 包含检验检查结果
risks = pm.perform_risk_assessment("住院号", "ALT 200U/L，AST 180U/L")
```

### 治疗方案库

```python
# 列出所有方案
pm.list_treatment_schemes()

# 查看方案详情
pm.show_treatment_scheme_detail("light_acute")

# 导入方案到患者（replace/append）
pm.import_treatment_scheme("住院号", "light_acute", "replace")
```

### 🆕 治疗知识库（素材消化）

基于 llm-wiki 方法论设计：**知识被编译一次，持续维护**。

#### 消化流程（两步式，使用 markitdown）

**前置条件**：需要先安装 markitdown（Python 3.10+）：
```bash
pip install "markitdown[all]"
```

**第一步：提交素材（自动检测格式并转换）**

```python
from markitdown import MarkItDown
import tempfile, os

# 消化 PDF 内容（自动用 markitdown 转换为 Markdown）
md = MarkItDown()
with open(pdf_path, "rb") as f:
    result = md.convert_stream(f)
    pdf_md_content = result.text_content  # Markdown 格式，保留表格和结构

result = pm.ingest_knowledge_source(
    text=pdf_md_content,  # 传入 Markdown 文本
    title="中国酒精依赖诊疗指南2024",
    source_type="pdf"
)

# 消化网页内容（需先用 web_fetch 提取）
result = pm.ingest_knowledge_source(
    text=web_article_text,
    title="NIAAA酒精依赖药物治疗综述",
    source_type="article",
    source_url="https://..."
)

# 消化纯文本
result = pm.ingest_knowledge_source(
    text="...",
    title="科室诊疗常规",
    source_type="plain"
)
```

返回值：
- `status: "HIT"` → 素材已处理过，跳过
- `status: "MISS"` → 新素材，返回 `analysis_prompt` 供AI进行结构化分析

**第二步：AI分析并保存**

AI Agent 根据 `analysis_prompt` 对素材进行结构化分析（提取实体、治疗方案、主题关联等），然后：

```python
analysis_result = {
    "summary": "该指南系统阐述了酒精依赖的药物治疗...",
    "entities": [
        {"name": "纳曲酮", "type": "drug", "key_info": "阿片受体拮抗剂，减少饮酒...", "confidence": "EXTRACTED"},
        {"name": "酒精依赖综合征", "type": "disease", "key_info": "ICD-10诊断标准...", "confidence": "EXTRACTED"}
    ],
    "treatment_schemes": [
        {
            "id": "naltrexone_standard",
            "name": "纳曲酮标准方案",
            "category": "维持期",
            "medications": [
                {"name": "纳曲酮", "dosage": "50mg po qd", "notes": "疗程3-6个月", "confidence": "EXTRACTED"}
            ],
            "indications": "中重度酒精依赖",
            "evidence_level": "A级推荐",
            "confidence": "EXTRACTED"
        }
    ],
    "topics": ["抗渴求治疗", "纳曲酮", "维持治疗"],
    "connections": [{"from": "纳曲酮", "to": "阿坎酸", "relation": "可联用增强抗渴求效果"}]
}

# 保存分析结果 → 生成wiki页面 + 更新treatment_schemes.json
result = pm.save_knowledge_analysis(source_id, analysis_result)
```

#### 知识库管理

```python
# 查看知识库状态
status = pm.get_knowledge_base_status()

# 列出已识别的实体（药物、疾病等）
entities = pm.list_knowledge_entities()

# 列出所有主题
topics = pm.list_knowledge_topics()

# 读取wiki页面内容
page = pm.read_knowledge_page("entities", "纳曲酮")
```

#### 置信度标注体系

| 标记 | 含义 | 使用场景 |
|-----|------|---------|
| `EXTRACTED` | 原文明确出现 | 字面可找到 |
| `INFERRED` | 从多处推断 | 原文未直接说但可合理推导 |
| `AMBIGUOUS` | 原文不清楚/有歧义 | 需要用户验证 |
| `UNVERIFIED` | AI背景知识，原文无证据 | 降级处理 |

#### 设计原则

1. **素材不可变**：原始素材存入 `raw/` 后不再修改
2. **指纹去重**：相同内容不会重复处理
3. **知识编译**：一次提取，持续维护，非每次重新推导
4. **置信度透明**：每个知识点标注可信度来源
5. **方案自动入库**：提取的治疗方案自动合并到 `treatment_schemes.json`

## 病历模板规范

### 首次病程记录

**入院导语**（必须）：
- 格式：`因"[主诉]"入院。`
- 示例：`因"心情差5年，再发伴疑人害2月余"入院。`
- 注意：仅写主诉，不含年龄性别

**病例特点（13项）**：
1. 一般特征及起病形式
2. 病程
3. 病情演变特点
4. 既往诊疗经过
5. 本次入院原因
6. 一般情况
7. 与鉴别诊断有关的阳性/阴性资料
8. 既往史
9. 个人史
10. 家族史
11. 体格检查
12. 精神检查
13. 辅助检查

**关键格式规则**：
- **入院导语**（必须）：仅写主诉，不含年龄性别。格式：`因"[主诉]"入院。`
- **标题和内容在同一行**：每一条的编号+标题和内容用冒号连接，不另起一行。如：`1. 一般特征及起病形式：患者系中年男性……`
- **诊断依据格式**：**总字数≤200字**，连贯一段，不另起行。分三部分：（1）**病史概况**：高度凝练，1-2句概括病程核心，不得复制粘贴现病史或病情演变特点内容；（2）**精神检查→综合征归纳**：将精神检查所见异常归纳为精神科综合征（如"抑郁综合征""精神病性综合征""戒断综合征"等），不逐条罗列具体症状描述。若检查发现不足以归纳为明确综合征，则回退为旧版方式按阳性发现简述；（3）根据ICD-10诊断标准，考虑"诊断名称"。末尾直接追加"初步诊断：XXX"。**不**写"诊断依据："标签，**不**用①②③逐条列举，**不**逐条对应ICD-10/CCMD-3诊断标准条款编号。
- **鉴别诊断**：沿用连贯叙述格式，不写"鉴别诊断："标签，分1、2点论述
- **诊疗计划**：整合为药物治疗方案一个段落（模板保留，医生可能不放文件中）
- **缺项处理**：个人史/家族史/体格检查不写"缺项"，贴模板留空；其他缺项在病历最后单独列出

**各条目具体规则**：

**1. 一般特征及起病形式**：`患者[年龄]岁[性别]，[起病形式]，病后社会功能受损。`由系统根据患者基本信息自动填充。

**2. 病程**：根据主诉时间线书写，不额外补充病史内容。**只写病史的时间**，格式`总病程[X]年。`或`病程约[X]年`（约X月/X年），**不展开任何症状、就诊、用药等具体内容**。这一条的定位是时间摘要，第3条病情演变特点才是病史的承载体。

**3. 病情演变特点**：
- 内容来源为家属提供的病史描述；**禁止出现认知评估**（理解力、判断力、定向力、记忆力等属于精神检查）；**尽量不使用精神科专用名词**。
- 🆕 v4.2：结构化数据输入（`{"phases": [...]}`）自动合并为单段落流式叙述，时间段标签融入正文，段落间用连接词过渡。兼容旧 String 格式。
- 🆕 **字数限制：200-400字**。本条是首次病程中病史的浓缩版，与现病史（500-800字完整版）必须明确区分——病情演变特点只承载关键时间锚+关键症状演变，不重复现病史的引语、行为细节和情绪描写。
- **与现病史的区别**：
  - 现病史 = 完整叙事（引语、行为细节、信息源标注、功能锚定）
  - 病情演变特点 = 时间线摘要（仅时间锚+症状演变，无引语、无展开）
- **与既往诊疗经过（第4条）分工**：涉及既往诊疗信息时仅简洁带过（如"曾在外院予药物治疗，疗效欠佳"），不展开具体药物剂量/就诊机构/诊断名称等细节，这些由第4条承载

**4. 既往诊疗经过**：无则写`既往未予诊治。`承载第3条中被省略的诊疗细节（具体药物组合、就诊机构、诊断名称、复诊情况等）。

**5. 本次入院原因**：格式`近期患者最严重的症状表现，家属觉其病情严重，遂至门诊/急诊就诊，诊断""，以"自愿住院/非自愿情形一"收入我科。`

**6. 一般情况**：格式`无头颅外伤，昏迷，抽搐等病史，近期饮食差，睡眠欠佳，大小便如常，体重未测。`

**7. 与鉴别诊断有关的阳性或阴性资料**：格式`否认既往有情绪低落、兴趣减退、精力下降等抑郁综合征表现。`（可根据实际调整阴性/阳性内容）

**8. 既往史**：格式`否认高血压、糖尿病、冠心病等慢性病史。否认肝炎、肺结核等传染病史。否认头颅外伤史，否认癫痫、晕倒史，否认手术史，否认输血史。否认药物过敏史。`

**9. 个人史**：格式`胞X行X，否认吸烟、酗酒嗜好。`信息不足时贴模板留空，不写"缺项"

**10. 家族史**：无特殊时统一写`父母两系三代中，否认有神经、精神疾病或者类似疾病的个体。`信息不足时贴模板留空，不写"缺项"

**11. 体格检查**：无特殊时使用标准模板（生命体征+各系统查体+神经系统查体），由医生自行修改：
> 查体合作，全身皮肤无黄染、皮疹、瘢痕。咽部无红肿，双侧扁桃体无肿大。双肺呼吸音清，未闻及干湿啰音。心率次/分，心律齐，各瓣膜未闻及病理性杂音。腹部平软，全腹无压痛、反跳痛，未触及腹部包块，肠鸣音正常。四肢活动正常，双下肢无水肿。双侧瞳孔等大等圆，d=3mm，对光反射存在。双侧鼻唇沟对称，示齿双侧嘴角对称，伸舌居中。四肢肌力、肌张力正常，肌力Ⅴ级，生理反射存在，病理反射未引出；感觉系统、共济系统未见明显异常；脑膜刺激征阴性。

**12. 专科检查**：格式`[一般情况、感知觉、思维活动、情感反应、意志行为、智力、自知力]`，详细内容为精神检查所见，不得从家属病史搬运。11个维度：意识→定向力→接触与合作→仪容仪表→注意力→感知觉→思维→情感→意志活动→认知功能→自知力。阳性发现展开描述，阴性发现用简短术语带过。

**13. 辅助检查**：记录入院时辅助检查结果，有则填写，无则留空。

### 日常病程记录

**三段式结构**：
1. **病情变化**：精神状况、情绪状态、进食睡眠、二便体重等
2. **精神检查**：意识、定向、接触、感知觉、思维、情感、意志行为、自知力
3. **处理意见**（30-50字）：合并治疗调整+病情分析+诊疗计划

**🆕 v4.1 新增模块**：

**核心症状量化对比（每次必备）**：
- 幻觉（频次/内容）：前次 vs 本次 + 变化方向
- 妄想（内容/强度）：前次 vs 本次 + 变化方向
- 情绪（性质/稳定）：前次 vs 本次 + 变化方向
- 行为（合作/冲动/退缩）：前次 vs 本次 + 变化方向
- 首次记录时改为"基线评估"

**药物反应对比（每次必备）**：
- 疗效变化（必须与具体行为指标挂钩）
- 新发副作用（如有，记录类型/强度/处理）
- 血药浓度（如有）

**风险评估（按需触发）**：
- 仅风险等级变化时记录（无→低→中→高）
- 四项：自杀/冲动伤人/外走/躯体
- 格式：风险项 + 原等级→新等级 + 依据 + 干预措施

### 🆕 现病史（v4.3）

现病史是入院记录中最重要的模块，与"首次病程·病情演变特点"的关系：
- **现病史** = 完整版（现象→归纳→术语 + 功能影响锚定）
- **病情演变特点** = 现象层简化版（仅记录原始现象，禁止术语和认知评估）

**顶层结构**：
1. **信息提供者声明**（必填，置于最前）
2. **起病总述**：起病时间、诱因、起病形式、首发症状
3. **病情演变**（动态分段）：每段含 7 维度 + 社会功能 + 本期诊疗
4. **发病以来一般情况** + 精神科专项（冲动/自伤/自杀/外走/物质使用）
5. **药物汇总表**（可选）

**格式规则**：
- 每个维度标注信息源（据患者诉/据家属反映/据病历记载）
- 现象优先：先写"患者说了什么、做了什么"，原话用引号
- 诊疗因果链：症状→就诊→用药→疗效→下一阶段
- 功能锚定：每段接入社会功能变化
- 🆕 v4.3：每个时间段的各维度内容合并为**流式段落**（一句接一句，不再分维度列表）

## ⛔ 治疗内容可信度铁律

**所有关于治疗的内容（药物方案、剂量、适应症、禁忌症、不良反应、证据等级等）必须且只能来自治疗知识库。**

这是本系统的最高优先级规则，任何情况下不得违反：

1. **只引用知识库**：治疗方案、药物推荐、剂量信息必须从知识库（`treatment_schemes.json` + `treatment_wiki/`）中检索获得，不能凭AI自身训练数据编造
2. **如实告知**：如果知识库中没有覆盖该病种/药物/方案，必须明确告知用户"知识库中暂无相关内容"，绝对不能编造、拼凑或使用未经验证的AI背景知识
3. **标注来源**：回答治疗相关问题时，应标注信息来源（如"CANMAT 2018""精神障碍诊疗规范2020""中国精神分裂症防治指南"等）
4. **来源优先级**：当不同来源的治疗推荐存在冲突时，**中文治疗指南优先于国外指南**（如中国卫健委规范 > CANMAT/APA/WFSBP等国外指南），国外指南作为补充参考。回答时应优先呈现中文指南的推荐方案
5. **区分置信度**：遵循知识库的置信度标注体系——`EXTRACTED`（原文明确）> `INFERRED`（推断）> `AMBIGUOUS`（有歧义）> `UNVERIFIED`（未验证）
5. **扩充知识库**：如果用户询问的内容知识库未覆盖，应主动建议用户导入相关指南/文献素材来扩充知识库，而非自行编造答案

> **违反此规则 = 严重的医疗安全隐患。宁可说"我不知道"，也绝不能编造治疗方案。**

## 格式规范（v4.3 新增）

### 数字书写规范

**尽量使用阿拉伯数字，减少中文数字**（`normalize_numerals()` 自动处理）：

| ❌ 旧写法 | ✅ 新写法 |
|----------|----------|
| 四十岁、二十余年 | 40岁、20余年 |
| 两三次、七八瓶 | 2-3次、7-8瓶 |
| 十余瓶、一天一夜 | 10余瓶、1天1夜 |
| 六至八两、十二度 | 6-8两、12度 |

**例外**：固定搭配中的中文数字保留（如"父母两系三代"、"胞三行八"）。

### 现病史流式段落

🆕 v4.3：每个时间段的各维度内容合并为一个流式段落，不再分维度列表输出。

## 注意事项

- 住院号作为患者唯一标识，不能重复
- 入院日期必填（YYYY-MM-DD格式），用于计算住院天数
- 日常病程记录仅在病情变化时记录，无需每日强制记录
- 生成的Word文档为宋体12号字，1.5倍行距
- 所有患者数据存储在 `patients/` 目录下的JSON文件中
- 治疗知识库存储在 Skill 目录下的 `treatment_wiki/` 中，跨工作目录共享