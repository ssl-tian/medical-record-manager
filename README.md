# 成瘾医学科患者管理系统

> AI驱动的精神科病历自动生成系统 — 首次病程记录、日常查房记录、治疗知识库

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/Status-Active-brightgreen.svg)]()

## 这是什么

一个面向**成瘾医学科**（酒精依赖/物质使用障碍）的临床病历管理系统。由广州医科大学附属脑科医院精神科规培医生开发并实际投入使用。

核心能力：钉钉AI听记录音 → 自动理解非结构化对话 → 生成符合13条模板规范的精神科首次病程记录Word文档。

## 快速开始

```bash
# 克隆仓库
git clone https://github.com/ssl-tian/medical-record-manager.git
cd medical-record-manager/scripts

# 安装依赖
pip install python-docx

# 创建患者（从钉钉AI纪要）
python -c "
from patient_manager import PatientManager
pm = PatientManager()
result = pm.add_patient_from_minutes_files(
    patient_id='20260001',
    name='测试患者', gender='男', age=45,
    admission_date='2026-01-01',
    present_illness_file='path/to/现病史纪要.txt',
    mental_exam_file='path/to/精神检查纪要.txt'
)
print(result)
"
```

## 核心功能

| 模块 | 功能 | 状态 |
|------|------|:---:|
| **首次病程记录** | AI理解钉钉纪要 → 13条模板结构化JSON → Word | ✅ v5.1 |
| **日常病程记录** | 三段式模板 + 核心症状量化对比 + 药物反应追踪 | ✅ v4.1 |
| **现病史生成** | 完整版叙事现病史 + 动态分段 + 信息源标注 | ✅ v4.3 |
| **风险评估** | 自杀/冲动伤人/外走/躯体四维风险自动评估 | ✅ |
| **治疗方案库** | 106条标准化药物方案 + 双轨制来源优先级 | ✅ v2.0 |
| **治疗知识库** | 消化PDF/网页素材→SHA256去重→自动提取治疗知识 | ✅ |
| **隐私保护** | Ollama+Qwen3本地LLM + privacy_filter降级方案 | ✅ v5.1 |

## 系统架构

```
钉钉AI听记录音(.txt)
    ↓
本地文件系统读取
    ↓
Ollama + Qwen3本地模型理解非结构化对话
    ↓
生成13条模板结构化JSON
    ↓
python-docx确定性写入Word
    ↓
医师审改 → 打印入档

全程本机完成，零网络传输患者数据
```

## 病历模板规范

系统严格遵循精神科首次病程记录的**13条目模板**：

1. 一般特征及起病形式
2. 病程
3. 病情演变特点（以家属病史描述，200-400字）
4. 既往诊疗经过
5. 本次入院原因
6. 一般情况
7. 与鉴别诊断有关的阳性/阴性资料
8. 既往史
9. 个人史（仅"胞X行X，病前性格XX"）
10. 家族史
11. 体格检查
12. 精神检查（11维度：意识→定向力→…→自知力）
13. 辅助检查

**关键格式规则**：
- 诊断依据 ≤ 200字，连贯段落，不能用编号
- 标题和内容同一行，用冒号连接
- 缺项留空不写"缺项"二字

## 治疗知识库

基于 [llm-wiki](https://github.com/karpathy/llm-wiki) 方法论设计：

| 特性 | 说明 |
|------|------|
| 来源 | 中国精神分裂症/抑郁/双相障碍防治指南(2025版)、CANMAT 2018等 |
| 方案数 | 106条标准化药物治疗方案 |
| 去重 | SHA256内容指纹 |
| 优先级 | 中文国家指南 > 国际学会指南 |
| 置信度 | EXTRACTED → INFERRED → AMBIGUOUS → UNVERIFIED |

## 隐私与合规

- **隐私模式**：支持Ollama+Qwen3本地模型，病历数据全程不出本机
- **降级方案**：`privacy_filter.py` 提供mask/replace/hash/redact四种脱敏方式
- **合规声明**：本系统生成临床文档初稿，最终由执业医师审改并签署

## 适用场景

即使你的科室不是成瘾医学科，这套方法论也适用：

- 精神科各亚专科（情感障碍、精神分裂症、儿少精神科…）
- 其他需要标准化文书的临床科室
- 临床研究中的病历结构化需求

## 作者

**Song (@ssl-tian)** — 精神科住院医/硕博连读，用 WorkBuddy 从零搭建了这套临床文档自动化系统。

## 许可

MIT License — 自由使用、修改、分发。详见 [LICENSE](LICENSE)。
