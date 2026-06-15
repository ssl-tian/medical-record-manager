# -*- coding: utf-8 -*-
"""
治疗知识库 - 素材消化模块
借鉴 llm-wiki（Karpathy方法论）的设计理念：
- 知识被编译一次，持续维护
- 多源素材（PDF、网页、纯文本）→ 结构化wiki页面
- 置信度标注体系（EXTRACTED / INFERRED / AMBIGUOUS / UNVERIFIED）
"""

import os
import json
import re
import hashlib
from typing import Dict, Optional, List
from datetime import datetime
from pathlib import Path


# 知识库根目录（与treatment_library.py同级）
_WIKI_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "treatment_wiki")
_RAW_DIR = os.path.join(_WIKI_ROOT, "raw")
_WIKI_DIR = os.path.join(_WIKI_ROOT, "wiki")
_CACHE_FILE = os.path.join(_WIKI_ROOT, ".wiki-cache.json")
_LOG_FILE = os.path.join(_WIKI_ROOT, "log.md")


def _ensure_dirs():
    """确保知识库目录结构存在"""
    dirs = [
        os.path.join(_RAW_DIR, "articles"),
        os.path.join(_RAW_DIR, "pdfs"),
        os.path.join(_RAW_DIR, "plain"),
        os.path.join(_WIKI_DIR, "sources"),
        os.path.join(_WIKI_DIR, "entities"),
        os.path.join(_WIKI_DIR, "topics"),
        os.path.join(_WIKI_DIR, "comparisons"),
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)


def _content_hash(text: str) -> str:
    """计算内容SHA256指纹"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _load_cache() -> Dict:
    """加载内容指纹缓存"""
    if os.path.exists(_CACHE_FILE):
        try:
            with open(_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_cache(cache: Dict):
    """保存内容指纹缓存"""
    with open(_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def _append_log(entry: str):
    """追加操作日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    line = f"[{timestamp}] {entry}\n"
    with open(_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)


def get_wiki_root() -> str:
    """返回知识库根目录路径"""
    return _WIKI_ROOT


# ============================================================
# 公共API：供AI Agent调用
# ============================================================

def ingest_text(
    text: str,
    title: str,
    source_type: str = "plain",
    source_url: str = "",
    overwrite: bool = False,
) -> Dict:
    """
    消化纯文本素材。

    AI Agent 应在调用此函数前，先用其他工具将 PDF/网页内容提取为纯文本。
    此函数完成的工作：
    1. 将原文存入 raw/ 目录（不可变）
    2. 根据内容指纹判断是否重复
    3. 返回结构化分析结果（JSON），供 Agent 据此生成 wiki 页面

    Args:
        text: 素材原文（纯文本）
        title: 素材标题
        source_type: 来源类型 (plain/pdf/article)
        source_url: 来源URL（如有）
        overwrite: 是否覆盖已有缓存

    Returns:
        {
            "status": "HIT" | "MISS",
            "source_id": "...",
            "raw_path": "...",
            "hit_reason": "...",      # 仅HIT时
            "analysis_prompt": "...", # 仅MISS时，引导AI做结构化分析
        }
    """
    _ensure_dirs()

    # 1. 计算指纹
    fingerprint = _content_hash(text)
    source_id = f"{source_type}_{fingerprint}"

    # 2. 缓存检查
    cache = _load_cache()
    if source_id in cache and not overwrite:
        entry = cache[source_id]
        _append_log(f"SKIP [{source_id}] 已存在: {title}")
        return {
            "status": "HIT",
            "source_id": source_id,
            "raw_path": entry.get("raw_path", ""),
            "hit_reason": "内容指纹匹配，已处理过",
        }

    # 3. 存入 raw/
    subtype_dir = os.path.join(_RAW_DIR, source_type)
    if not os.path.exists(subtype_dir):
        subtype_dir = os.path.join(_RAW_DIR, "plain")

    safe_title = re.sub(r'[\\/:*?"<>|]', "_", title)[:80]
    raw_filename = f"{fingerprint}_{safe_title}.md"
    raw_path = os.path.join(subtype_dir, raw_filename)

    # 写入原始素材（带元数据头）
    meta = f"---\ntitle: {title}\nsource_type: {source_type}\nsource_url: {source_url}\ningested_at: {datetime.now().isoformat()}\nfingerprint: {fingerprint}\n---\n\n"
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(meta + text)

    # 4. 更新缓存
    cache[source_id] = {
        "raw_path": raw_path,
        "title": title,
        "fingerprint": fingerprint,
        "ingested_at": datetime.now().isoformat(),
    }
    _save_cache(cache)

    _append_log(f"INGEST [{source_id}] {title} → {raw_path}")

    # 5. 返回分析提示（引导AI进行结构化提取）
    analysis_prompt = _build_analysis_prompt(text, title, source_id)

    return {
        "status": "MISS",
        "source_id": source_id,
        "raw_path": raw_path,
        "analysis_prompt": analysis_prompt,
    }


def save_analysis_result(source_id: str, analysis: Dict) -> Dict:
    """
    保存AI的结构化分析结果并生成wiki页面。

    AI Agent 在收到 ingest_text 返回的 analysis_prompt 后，
    应根据提示进行结构化分析，然后将结果传入此函数。

    Args:
        source_id: ingest_text 返回的素材ID
        analysis: {
            "summary": "素材摘要",
            "entities": [
                {"name": "药物/疾病/概念名", "type": "drug|disease|concept|guideline",
                 "key_info": "...", "confidence": "EXTRACTED|INFERRED|AMBIGUOUS"}
            ],
            "treatment_schemes": [
                {
                    "id": "英文snake_case",
                    "name": "方案名称",
                    "category": "分类（如 轻度-急性期）",
                    "medications": [
                        {"name": "药物名", "dosage": "剂量", "notes": "备注",
                         "confidence": "EXTRACTED|INFERRED"}
                    ],
                    "indications": "适应症",
                    "evidence_level": "证据级别",
                    "confidence": "EXTRACTED|INFERRED"
                }
            ],
            "topics": ["相关主题标签"],
            "connections": [{"from": "实体A", "to": "实体B", "relation": "关系描述"}]
        }

    Returns:
        {"status": "ok", "files_created": [...], "scheme_count": N}
    """
    _ensure_dirs()

    files_created = []

    # 1. 生成 source 摘要页
    cache = _load_cache()
    entry = cache.get(source_id, {})
    title = entry.get("title", source_id)

    source_content = _render_source_page(source_id, title, analysis)
    source_path = os.path.join(_WIKI_DIR, "sources", f"{source_id}.md")
    with open(source_path, "w", encoding="utf-8") as f:
        f.write(source_content)
    files_created.append(source_path)

    # 2. 生成 entity 页面（药物、疾病、指南等）
    for entity in analysis.get("entities", []):
        entity_name = entity.get("name", "").strip()
        if not entity_name:
            continue
        entity_file = re.sub(r'[\\/:*?"<>|\s]+', "_", entity_name)
        entity_path = os.path.join(_WIKI_DIR, "entities", f"{entity_file}.md")

        # 如果已存在，追加来源引用而非覆盖
        if os.path.exists(entity_path):
            with open(entity_path, "r", encoding="utf-8") as f:
                existing = f.read()
            # 追加新的来源引用
            ref_line = f"\n\n---\n**来源**: [[{source_id}]] | 置信度: {entity.get('confidence', 'N/A')}\n"
            if ref_line not in existing:
                entity_content = existing + ref_line
            else:
                entity_content = existing
        else:
            entity_content = _render_entity_page(entity, source_id)

        with open(entity_path, "w", encoding="utf-8") as f:
            f.write(entity_content)
        files_created.append(entity_path)

    # 3. 生成 topic 页面
    for topic in analysis.get("topics", []):
        topic_file = re.sub(r'[\\/:*?"<>|\s]+', "_", topic)
        topic_path = os.path.join(_WIKI_DIR, "topics", f"{topic_file}.md")

        if os.path.exists(topic_path):
            with open(topic_path, "r", encoding="utf-8") as f:
                existing = f.read()
            ref_line = f"- [[{source_id}]]\n"
            if ref_line not in existing:
                # 追加到来源列表
                if "## 来源" in existing:
                    topic_content = existing.replace("## 来源\n", f"## 来源\n{ref_line}")
                else:
                    topic_content = existing + f"\n## 来源\n{ref_line}\n"
            else:
                topic_content = existing
        else:
            topic_content = _render_topic_page(topic, source_id, analysis)

        with open(topic_path, "w", encoding="utf-8") as f:
            f.write(topic_content)
        files_created.append(topic_path)

    # 4. 提取治疗方案 → 写入 treatment_schemes.json（v2.0 优先级合并）
    merge_result = _merge_schemes_from_analysis(analysis)
    # 兼容旧调用方：schemes_added 既可表示新增也可表示字典
    schemes_added = merge_result["added"] + merge_result["updated"] if isinstance(merge_result, dict) else merge_result

    scheme_count = len(analysis.get("treatment_schemes", []))
    log_msg = f"WIKI [{source_id}] 生成 {len(files_created)} 个wiki页面"
    if isinstance(merge_result, dict):
        log_msg += f", 新增{merge_result['added']}/更新{merge_result['updated']}/跳过{merge_result['skipped']}个方案"
    else:
        log_msg += f", {schemes_added} 个治疗方案入库"
    _append_log(log_msg)

    return {
        "status": "ok",
        "files_created": files_created,
        "scheme_count": schemes_added,
        "merge_detail": merge_result if isinstance(merge_result, dict) else None,
    }


def get_wiki_status() -> Dict:
    """
    获取知识库状态统计

    Returns:
        各目录的文件数量和最近活动
    """
    _ensure_dirs()
    status = {
        "wiki_root": _WIKI_ROOT,
        "raw": {"total": 0, "articles": 0, "pdfs": 0, "plain": 0},
        "wiki": {"total": 0, "sources": 0, "entities": 0, "topics": 0, "comparisons": 0},
        "cache_entries": 0,
    }

    for subtype in ["articles", "pdfs", "plain"]:
        d = os.path.join(_RAW_DIR, subtype)
        if os.path.exists(d):
            files = [f for f in os.listdir(d) if not f.startswith(".")]
            status["raw"][subtype] = len(files)
            status["raw"]["total"] += len(files)

    for subtype in ["sources", "entities", "topics", "comparisons"]:
        d = os.path.join(_WIKI_DIR, subtype)
        if os.path.exists(d):
            files = [f for f in os.listdir(d) if f.endswith(".md")]
            status["wiki"][subtype] = len(files)
            status["wiki"]["total"] += len(files)

    cache = _load_cache()
    status["cache_entries"] = len(cache)

    return status


def list_entities() -> List[Dict]:
    """
    列出知识库中所有已识别的实体

    Returns:
        [{"name": "...", "type": "...", "path": "..."}, ...]
    """
    _ensure_dirs()
    entities = []
    d = os.path.join(_WIKI_DIR, "entities")
    if os.path.exists(d):
        for f in sorted(os.listdir(d)):
            if f.endswith(".md"):
                name = f[:-3].replace("_", " ")
                entities.append({"name": name, "type": "entity", "path": os.path.join(d, f)})
    return entities


def list_topics() -> List[Dict]:
    """列出知识库中所有主题"""
    _ensure_dirs()
    topics = []
    d = os.path.join(_WIKI_DIR, "topics")
    if os.path.exists(d):
        for f in sorted(os.listdir(d)):
            if f.endswith(".md"):
                name = f[:-3].replace("_", " ")
                topics.append({"name": name, "path": os.path.join(d, f)})
    return topics


def read_wiki_page(page_type: str, name: str) -> Optional[str]:
    """
    读取指定wiki页面的内容

    Args:
        page_type: "sources" / "entities" / "topics" / "comparisons"
        name: 页面文件名（不含.md后缀）
    """
    safe_name = re.sub(r'[\\/:*?"<>|\s]+', "_", name)
    path = os.path.join(_WIKI_DIR, page_type, f"{safe_name}.md")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return None


# ============================================================
# 内部渲染函数
# ============================================================

def _build_analysis_prompt(text: str, title: str, source_id: str) -> str:
    """构建结构化分析提示词"""
    # 截断处理
    content_preview = text[:8000] if len(text) <= 8000 else text[:8000] + "\n[...内容过长，已截断前8000字...]"
    closing = "```" if len(text) <= 8000 else ""

    return f"""请分析以下医学素材，提取治疗相关知识。

## 素材信息
- 标题：{title}
- 来源ID：{source_id}
- 内容长度：{len(text)} 字

## 分析要求

请从素材中提取以下信息，并以JSON格式返回：

```json
{{
  "summary": "100-200字的素材摘要，重点提取与酒精依赖/成瘾医学治疗相关的内容",
  "entities": [
    {{
      "name": "实体名称（药物名/疾病名/概念/指南名）",
      "type": "drug|disease|concept|guideline",
      "key_info": "该实体的关键信息（50-100字）",
      "confidence": "EXTRACTED（原文明确）/ INFERRED（推断）/ AMBIGUOUS（有歧义）/ UNVERIFIED（AI背景知识）"
    }}
  ],
  "treatment_schemes": [
    {{
      "id": "英文snake_case_id（如 naltrexone_moderate）",
      "name": "方案名称（中文）",
      "category": "分类（如 轻度-急性期 / 中度-稳定期 / 维持期 / 特殊人群）",
      "medications": [
        {{
          "name": "药物名称",
          "dosage": "剂量和用法",
          "notes": "备注（疗程、注意事项等）",
          "confidence": "EXTRACTED / INFERRED"
        }}
      ],
      "indications": "适应症描述",
      "evidence_level": "证据级别（如 A级推荐 / RCT / 专家共识 / 指南推荐）",
      "confidence": "EXTRACTED / INFERRED"
    }}
  ],
  "topics": ["相关主题标签（如 纳曲酮、抗渴求治疗、戒断综合征管理）"],
  "connections": [
    {{"from": "实体A", "to": "实体B", "relation": "关系描述（如 纳曲酮和阿坎酸可联用）"}}
  ]
}}
```

### 重要原则
1. **置信度标注**：只标注为EXTRACTED（原文明确出现的），不要推测
2. **方案提取**：只提取文中明确描述的治疗方案，不要自行编造
3. **剂量精确**：药物剂量必须原文中有依据，否则标为INFERRED并说明来源
4. **分类合理**：根据方案描述的严重程度和治疗阶段合理分类
5. **如果没有治疗方案信息**，treatment_schemes返回空数组

### 素材内容
```
{content_preview}
```{closing}"""


def _render_source_page(source_id: str, title: str, analysis: Dict) -> str:
    """渲染素材摘要页"""
    lines = [
        f"# {title}",
        "",
        f"**来源ID**: {source_id}",
        f"**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## 摘要",
        "",
        analysis.get("summary", "（无摘要）"),
        "",
    ]

    # 提取的实体
    entities = analysis.get("entities", [])
    if entities:
        lines.append("## 识别的实体")
        lines.append("")
        for e in entities:
            conf = e.get("confidence", "N/A")
            lines.append(f"- [[{e.get('name', '')}]] ({e.get('type', '')}) — 置信度: {conf}")
            if e.get("key_info"):
                lines.append(f"  > {e['key_info']}")
        lines.append("")

    # 提取的治疗方案
    schemes = analysis.get("treatment_schemes", [])
    if schemes:
        lines.append("## 提取的治疗方案")
        lines.append("")
        for s in schemes:
            conf = s.get("confidence", "N/A")
            evidence = s.get("evidence_level", "")
            lines.append(f"### {s.get('name', 'N/A')} [{conf}]")
            if evidence:
                lines.append(f"**证据级别**: {evidence}")
            lines.append(f"**分类**: {s.get('category', 'N/A')}")
            lines.append(f"**适应症**: {s.get('indications', 'N/A')}")
            lines.append("")
            for m in s.get("medications", []):
                mconf = m.get("confidence", "")
                lines.append(f"- {m.get('name', '')} {m.get('dosage', '')} [{mconf}]")
                if m.get("notes"):
                    lines.append(f"  > {m['notes']}")
            lines.append("")

    # 主题
    topics = analysis.get("topics", [])
    if topics:
        lines.append("## 主题标签")
        lines.append("")
        lines.append(", ".join(f"[[{t}]]" for t in topics))
        lines.append("")

    # 关联
    conns = analysis.get("connections", [])
    if conns:
        lines.append("## 知识关联")
        lines.append("")
        for c in conns:
            lines.append(f"- [[{c.get('from', '')}]] → [[{c.get('to', '')}]]: {c.get('relation', '')}")
        lines.append("")

    return "\n".join(lines)


def _render_entity_page(entity: Dict, source_id: str) -> str:
    """渲染实体页面"""
    lines = [
        f"# {entity.get('name', '未知实体')}",
        "",
        f"**类型**: {entity.get('type', 'N/A')}",
        f"**置信度**: {entity.get('confidence', 'N/A')}",
        "",
        "## 关键信息",
        "",
        entity.get("key_info", "（待补充）"),
        "",
        "---",
        f"**来源**: [[{source_id}]]",
        "",
    ]
    return "\n".join(lines)


def _render_topic_page(topic: str, source_id: str, analysis: Dict) -> str:
    """渲染主题页面"""
    lines = [
        f"# {topic}",
        "",
        "## 来源",
        "",
        f"- [[{source_id}]]",
        "",
    ]

    # 列出该主题相关的实体
    entities = analysis.get("entities", [])
    related = [e for e in entities if any(t.lower() in e.get("name", "").lower() or e.get("name", "").lower() in t.lower() for t in analysis.get("topics", []))]
    if related:
        lines.append("## 相关实体")
        lines.append("")
        for e in related:
            lines.append(f"- [[{e.get('name', '')}]]")
        lines.append("")

    return "\n".join(lines)


# ============================================================
# 方案优先级与冲突处理（v2.0，2026-06-09）
# ============================================================
# 来源权威性优先级（数字越小越优先）
# 中文官方指南永远 > 国际指南（与 treatment-knowledge-curator 铁律一致）
SOURCE_PRIORITY = {
    # Tier 1：中文官方（最高优先）
    "精神障碍诊疗规范": 1, "国家卫健委": 1, "国家卫生健康委员会": 1,
    "中华医学会精神病学分会": 1, "中华医学会": 1,
    "中国抑郁障碍防治指南": 1, "中国双相情感障碍防治指南": 1,
    "中国精神分裂症防治指南": 1, "中国物质使用障碍防治指南": 1,
    "中国成人失眠诊断与治疗指南": 1, "中国成人失眠伴抑郁焦虑诊治专家共识": 1,
    "抑郁症治疗与管理的专家推荐意见": 1,
    # Tier 2：专业学会共识
    "中国神经精神药理学": 2, "中国医师协会精神科医师分会": 2,
    "专家共识": 2, "学会共识": 2,
    # Tier 3：高质量国际指南
    "CANMAT": 3, "ISBD": 3, "JSCNP": 3, "NICE": 3, "APA": 3, "WFSBP": 3,
    "Lancet": 3, "Cochrane": 3,
    # Tier 4：其他来源
    "wiki_ingest": 4, "期刊综述": 4, "meta分析": 4,
}

# 证据等级优先级（数字越小越优先）
EVIDENCE_PRIORITY = [
    ("1级证据", 1), ("Level 1", 1), ("A级", 1), ("A 级", 1), ("A级推荐", 1),
    ("1级证据（多中心RCT支持）", 1), ("1级证据（多项RCT+Meta分析）", 1),
    ("1-2级证据", 2), ("Level 1-2", 2), ("CANMAT Level 1-2", 2),
    ("1级证据（指南推荐）", 2), ("1级证据（CANMAT/国际指南推荐）", 2),
    ("CANMAT Level 1-3", 3), ("CANMAT Level 1-4", 3),
    ("2级证据", 3), ("Level 2", 3), ("B级", 3), ("B 级", 3), ("B级推荐", 3),
    ("CANMAT Level 2-4", 4),
    ("指南推荐", 5),
    ("3级证据", 6), ("Level 3", 6), ("C级", 6), ("C 级", 6), ("C级推荐", 6),
    ("专家共识推荐", 7), ("专家共识A级推荐", 7),
    ("专家共识/指南推荐", 7),
    ("4级证据", 8), ("专家意见", 8), ("Level 4", 8), ("D级", 8),
    ("RCT证实", 9), ("研究证实", 9), ("CANMAT 2014指南", 9),
]


def _get_source_priority(scheme: Dict) -> int:
    """计算方案的来源权威性优先级（数字越小越优先）。

    严格只检查 source.guide_name 与 _source 两个字段，
    避免 evidence_level 等其他字段中的关键词（如"专家共识"）被误识别。
    """
    source_field = ""
    if isinstance(scheme.get("source"), dict):
        source_field = scheme["source"].get("guide_name", "") or ""
    explicit_source = scheme.get("_source", "")
    combined = f"{source_field} {explicit_source}".strip()
    if not combined:
        return 50  # 未知来源
    best = 99
    for keyword, prio in SOURCE_PRIORITY.items():
        if keyword in combined:
            best = min(best, prio)
    return best if best < 99 else 50


def _get_evidence_priority(evidence: str) -> int:
    """根据证据等级字符串返回优先级（数字越小越优先）"""
    if not evidence:
        return 50
    for keyword, prio in EVIDENCE_PRIORITY:
        if keyword in evidence:
            return prio
    return 50


def _backup_schemes_file(schemes_path: str) -> str:
    """在覆盖前备份 treatment_schemes.json"""
    if not os.path.exists(schemes_path):
        return ""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{schemes_path}.bak.{ts}"
    with open(schemes_path, "r", encoding="utf-8") as f:
        content = f.read()
    with open(backup_path, "w", encoding="utf-8") as f:
        f.write(content)
    return backup_path


def _should_overwrite(existing: Dict, incoming: Dict) -> tuple:
    """
    判定 incoming 是否应覆盖 existing。
    Returns: (should_overwrite: bool, reason: str)

    规则（与 2026-06-09 用户确认一致）：
      1. 同一 id 才比较（不同 id 直接共存）
      2. 双轨制：
         A. 如果 incoming 和 existing 都带 source.guide_name → 启用严格优先级
            (中文官方 > 学会共识 > 国际指南；同源看证据等级)
         B. 否则（任一方缺 source） → 使用宽松策略：保留旧版
            （避免 v1.0 入库的 58 个无 source 方案被批量误覆盖）
      3. 同源同等级 → 保留旧版（避免反复覆盖）
    """
    inc_has_source = bool(isinstance(incoming.get("source"), dict) and incoming["source"].get("guide_name"))
    exi_has_source = bool(isinstance(existing.get("source"), dict) and existing["source"].get("guide_name"))

    # 规则2B：双轨制——任一方缺 source 走宽松模式
    if not (inc_has_source and exi_has_source):
        return False, "宽松模式：任一方缺 source 字段，保留旧版（避免误覆盖 v1.0 历史数据）"

    inc_source_prio = _get_source_priority(incoming)
    exi_source_prio = _get_source_priority(existing)
    inc_ev_prio = _get_evidence_priority(incoming.get("evidence_level", ""))
    exi_ev_prio = _get_evidence_priority(existing.get("evidence_level", ""))

    # 规则2A-步骤1：来源权威性
    if inc_source_prio < exi_source_prio:
        return True, f"来源更权威({inc_source_prio}<{exi_source_prio})"
    if inc_source_prio > exi_source_prio:
        return False, f"来源权威性较低({inc_source_prio}>{exi_source_prio})"

    # 规则2A-步骤2：同源比证据等级
    if inc_ev_prio < exi_ev_prio:
        return True, f"证据等级更高({incoming.get('evidence_level','')}>{existing.get('evidence_level','')})"
    if inc_ev_prio > exi_ev_prio:
        return False, f"证据等级较低({incoming.get('evidence_level','')}<{existing.get('evidence_level','')})"

    # 规则3：同源同等级 → 保留旧版
    return False, "同源同等级，保留旧版"


def _merge_schemes_from_analysis(analysis: Dict) -> int:
    """
    将分析结果中的治疗方案合并到 treatment_schemes.json

    v2.0 改进（2026-06-09）：
      - 加入"中文官方 > 学会共识 > 国际指南"的来源权威性优先级
      - 加入"1级 > 2级 > 3级 > 4级"的证据等级优先级
      - 覆盖前自动备份 .bak.YYYYMMDD_HHMMSS
      - 每个方案追加 _version / _history / last_updated_by 字段
      - 返回字典 {added, updated, skipped, conflicts} 供上层决策
    """
    schemes_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "treatment_schemes.json"
    )

    # 1. 读取现有方案
    if os.path.exists(schemes_path):
        try:
            with open(schemes_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            existing_schemes = data.get("schemes", [])
        except Exception:
            existing_schemes = []
    else:
        existing_schemes = []

    existing_by_id = {s.get("id"): s for s in existing_schemes if s.get("id")}

    # 2. 合并新方案
    new_schemes = analysis.get("treatment_schemes", [])
    added, updated, skipped = 0, 0, 0
    conflicts_log = []
    now_iso = datetime.now().isoformat(timespec="seconds")

    for scheme in new_schemes:
        sid = scheme.get("id", "")
        if not sid:
            skipped += 1
            continue

        # 自动打来源标签（若未标）
        if "_source" not in scheme:
            scheme["_source"] = "wiki_ingest"

        # 推断来源指南名（用于 last_updated_by）
        source_field = scheme.get("source", {}) if isinstance(scheme.get("source"), dict) else {}
        guide_name = source_field.get("guide_name", scheme.get("_source", "wiki_ingest"))
        scheme["last_updated_by"] = guide_name
        scheme["last_updated_at"] = now_iso

        if sid not in existing_by_id:
            # 全新方案：直接添加，version=1
            scheme["_version"] = 1
            scheme["_history"] = [
                {"version": 1, "by": guide_name, "at": now_iso, "action": "created"}
            ]
            existing_schemes.append(scheme)
            existing_by_id[sid] = scheme
            added += 1
        else:
            existing = existing_by_id[sid]
            should_overwrite, reason = _should_overwrite(existing, scheme)
            if should_overwrite:
                # 保留旧 history，追加新条目
                old_version = existing.get("_version", 1)
                new_version = old_version + 1
                history = list(existing.get("_history", []))
                history.append({
                    "version": new_version,
                    "by": guide_name,
                    "at": now_iso,
                    "action": "updated",
                    "previous_evidence": existing.get("evidence_level", ""),
                    "reason": reason,
                })
                scheme["_version"] = new_version
                scheme["_history"] = history
                # 替换现有方案
                idx = existing_schemes.index(existing)
                existing_schemes[idx] = scheme
                existing_by_id[sid] = scheme
                updated += 1
                conflicts_log.append(f"UPDATE [{sid}] {reason}")
            else:
                skipped += 1
                conflicts_log.append(f"SKIP [{sid}] {reason}")

    # 3. 覆盖前自动备份
    backup_path = _backup_schemes_file(schemes_path)

    # 4. 保存
    data = {"schemes": existing_schemes}
    with open(schemes_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # 5. 写日志
    if added > 0 or updated > 0:
        parts = []
        if added:
            parts.append(f"新增 {added}")
        if updated:
            parts.append(f"更新 {updated}")
        if skipped:
            parts.append(f"跳过 {skipped}")
        _append_log(f"SCHEMES {', '.join(parts)} (v2.0 优先级合并)")
    if backup_path:
        _append_log(f"BACKUP {os.path.basename(backup_path)}")
    for entry in conflicts_log:
        _append_log(f"  {entry}")

    return {"added": added, "updated": updated, "skipped": skipped,
            "conflicts": conflicts_log, "backup": backup_path}
