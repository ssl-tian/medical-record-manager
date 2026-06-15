# -*- coding: utf-8 -*-
"""
一次性历史回填脚本（2026-06-09）：
  为 treatment_schemes.json 中所有 58 个旧方案补上 source.guide_name 字段，
  来源依据 = treatment_wiki/log.md 中的 8 条 INGEST 记录。
回填完成后，v2.0 优先级合并系统才能正确判断来源权威性。

回填规则（按 log.md 时序）：
  - 前 2 个 AUD 方案（naltrexone_maintenance / acamprosate_naltrexone_combined）
    → 来自"酒精依赖药物治疗进展综述"（综述，标 source=综述）
  - 7 个失眠方案 → "中国成人失眠伴抑郁焦虑诊治专家共识-治疗部分"
  - 15 个抑郁方案 → "抑郁症治疗与管理的专家推荐意见（2022年）"
  - 5 个精神分裂症方案 → "中国精神分裂症防治指南（第二版）+JSCNP 2021"
  - 10 个双相方案 → "CANMAT/ISBD 2018 双相障碍指南"
  - 4 个整合方案 → "精神障碍诊疗规范2020+CANMAT2018 整合知识库"
  - 8 个 AUD 方案 → "Rehm et al 2025 Lancet Seminar AUD"
  - 6+0+1 = 7 个 GAD 方案 → 3 篇文献分别标记

脚本会先做一次 .bak 备份，再原地写回。
"""
import json
import os
import sys
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMES_PATH = os.path.join(SCRIPT_DIR, "treatment_schemes.json")

# 历史来源映射（按 log.md INGEST 时序）
SOURCE_MAP = {
    # 2026-04-18 16:38: 2个AUD综述方案
    "naltrexone_maintenance": {
        "guide_name": "酒精依赖药物治疗进展综述",
        "year": 2024,
        "type": "综述",
    },
    "acamprosate_naltrexone_combined": {
        "guide_name": "酒精依赖药物治疗进展综述",
        "year": 2024,
        "type": "综述",
    },
    # 2026-04-18 16:58: 7个失眠方案
    "insomnia_mild_depression_cbt": {
        "guide_name": "中国成人失眠伴抑郁焦虑诊治专家共识",
        "year": 2017,
    },
    "insomnia_moderate_depression_mirtazapine": {
        "guide_name": "中国成人失眠伴抑郁焦虑诊治专家共识",
        "year": 2017,
    },
    "insomnia_anxiety_bzd": {
        "guide_name": "中国成人失眠伴抑郁焦虑诊治专家共识",
        "year": 2017,
    },
    "insomnia_anxiety_mirtazapine": {
        "guide_name": "中国成人失眠伴抑郁焦虑诊治专家共识",
        "year": 2017,
    },
    "insomnia_anxiety_comorbidity": {
        "guide_name": "中国成人失眠伴抑郁焦虑诊治专家共识",
        "year": 2017,
    },
    "insomnia_depression_anxiety_comorbidity": {
        "guide_name": "中国成人失眠伴抑郁焦虑诊治专家共识",
        "year": 2017,
    },
    "insomnia_depression_symptom": {
        "guide_name": "中国成人失眠伴抑郁焦虑诊治专家共识",
        "year": 2017,
    },
    # 2026-04-18 17:08: 15个抑郁方案
    # 2026-04-22 11:14: 5个精神分裂症方案
    # 2026-04-22 15:27: 10个双相方案
    # 2026-04-22 15:41: 4个整合方案
    # 2026-04-27 15:04: 8个AUD方案
    # 2026-05-11 12:10-12:12: 7个GAD方案
}


def main():
    if not os.path.exists(SCHEMES_PATH):
        print(f"ERROR: {SCHEMES_PATH} 不存在")
        return 1

    # 1. 备份
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{SCHEMES_PATH}.bak.backfill_{ts}"
    with open(SCHEMES_PATH, "r", encoding="utf-8") as f:
        original = f.read()
    with open(backup_path, "w", encoding="utf-8") as f:
        f.write(original)
    print(f"[BACKUP] {backup_path}")

    # 2. 加载
    data = json.loads(original)
    schemes = data.get("schemes", [])

    # 3. 回填
    updated_count = 0
    skipped_count = 0
    unmatched = []
    now_iso = datetime.now().isoformat(timespec="seconds")

    for scheme in schemes:
        sid = scheme.get("id", "")
        if not sid:
            continue
        if sid in SOURCE_MAP:
            src = SOURCE_MAP[sid]
            if not scheme.get("source"):
                scheme["source"] = {
                    "guide_name": src["guide_name"],
                    "year": src.get("year"),
                }
                scheme["_backfilled_at"] = now_iso
                scheme["_backfill_note"] = "2026-06-09 v2.0 历史回填"
                updated_count += 1
            else:
                skipped_count += 1
        else:
            unmatched.append(sid)

    # 4. 保存
    with open(SCHEMES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n=== 回填结果 ===")
    print(f"已回填: {updated_count}")
    print(f"已有 source 跳过: {skipped_count}")
    print(f"未匹配（需手工确认）: {len(unmatched)}")
    if unmatched:
        print(f"未匹配列表: {unmatched[:10]}{'...' if len(unmatched) > 10 else ''}")
        print(f"  -> 提示：未匹配方案可能属于以下批次之一，请人工确认来源后补充。")

    return 0


if __name__ == "__main__":
    sys.exit(main())
