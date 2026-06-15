# -*- coding: utf-8 -*-
"""
治疗方案库 v1 → v2 升级脚本（2026-06-09 终极版）

任务：为 58 个 v1 历史方案补全 source.guide_name 字段，
      激活知识库 v2.0 双轨制合并系统中的"轨道 A 严格优先级"。

来源映射依据：treatment_wiki/log.md 中 8 条 INGEST 记录的时序与方案命名约定。
每条映射都基于原始素材文件名 + 方案 id 前缀 + category 字段的启发式推断。

回填规则：
  1. 备份当前 treatment_schemes.json 为 .bak.backfill_<timestamp>
  2. 写入 source.guide_name / source.year
  3. 写入 _backfilled_at / _backfill_note 标记
  4. 写入 _version=1（v1方案视为"原始基线版本"）
  5. 不修改其他字段，确保 0 数据丢失
  6. 报告回填结果 + 生成升级报告

执行：python _backfill_scheme_sources_v2.py
"""
import json
import os
import sys
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMES_PATH = os.path.join(SCRIPT_DIR, "treatment_schemes.json")
LOG_PATH = os.path.join(SCRIPT_DIR, "treatment_wiki", "log.md")

# ============================================================
# 58 个方案的来源映射（v1 历史数据 → 原始素材）
# ============================================================
# 依据：treatment_wiki/log.md 的 8 批 INGEST + 原始素材文件 + 方案命名约定
SOURCE_MAP = {
    # ===== 批次1：1c8fd6490c86 (2026-04-18 16:38) — 酒精依赖药物治疗进展综述 =====
    "naltrexone_maintenance": {
        "guide_name": "酒精依赖药物治疗进展综述",
        "year": 2024,
        "source_type": "review",
    },
    "acamprosate_naltrexone_combined": {
        "guide_name": "酒精依赖药物治疗进展综述",
        "year": 2024,
        "source_type": "review",
    },
    # ===== 批次2：29f3cf1d1fa8 (2026-04-18 16:58) — 失眠伴抑郁焦虑专家共识 =====
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
    "insomnia_anxiety_sedative_antidepr": {
        "guide_name": "中国成人失眠伴抑郁焦虑诊治专家共识",
        "year": 2017,
    },
    "insomnia_anxiety_comorbid_combined": {
        "guide_name": "中国成人失眠伴抑郁焦虑诊治专家共识",
        "year": 2017,
    },
    "insomnia_depression_anxiety_combined": {
        "guide_name": "中国成人失眠伴抑郁焦虑诊治专家共识",
        "year": 2017,
    },
    "insomnia_mild_depression_pharmacologic": {
        "guide_name": "中国成人失眠伴抑郁焦虑诊治专家共识",
        "year": 2017,
    },
    # ===== 批次3：a58e9982b944 (2026-04-18 17:08) — 抑郁症专家推荐意见2022 =====
    "mdd_acute_ssris": {
        "guide_name": "抑郁症治疗与管理的专家推荐意见",
        "year": 2022,
    },
    "mdd_acute_snris": {
        "guide_name": "抑郁症治疗与管理的专家推荐意见",
        "year": 2022,
    },
    "mdd_acute_ndri_bupropion": {
        "guide_name": "抑郁症治疗与管理的专家推荐意见",
        "year": 2022,
    },
    "mdd_acute_agomelatine": {
        "guide_name": "抑郁症治疗与管理的专家推荐意见",
        "year": 2022,
    },
    "mdd_acute_vortioxetine": {
        "guide_name": "抑郁症治疗与管理的专家推荐意见",
        "year": 2022,
    },
    "mdd_trd_quetiapine_er": {
        "guide_name": "抑郁症治疗与管理的专家推荐意见",
        "year": 2022,
    },
    "mdd_trd_aripiprazole": {
        "guide_name": "抑郁症治疗与管理的专家推荐意见",
        "year": 2022,
    },
    "mdd_trd_buspirone": {
        "guide_name": "抑郁症治疗与管理的专家推荐意见",
        "year": 2022,
    },
    "mdd_acute_cbt_combined": {
        "guide_name": "抑郁症治疗与管理的专家推荐意见",
        "year": 2022,
    },
    "mdd_acute_rtms_combined": {
        "guide_name": "抑郁症治疗与管理的专家推荐意见",
        "year": 2022,
    },
    "mdd_severe_mect": {
        "guide_name": "抑郁症治疗与管理的专家推荐意见",
        "year": 2022,
    },
    "mdd_adolescent_ssri_cbt": {
        "guide_name": "抑郁症治疗与管理的专家推荐意见",
        "year": 2022,
    },
    "mdd_elderly_ssris": {
        "guide_name": "抑郁症治疗与管理的专家推荐意见",
        "year": 2022,
    },
    "mdd_perinatal_comprehensive": {
        "guide_name": "抑郁症治疗与管理的专家推荐意见",
        "year": 2022,
    },
    "mdd_chronic_disease_ssris": {
        "guide_name": "抑郁症治疗与管理的专家推荐意见",
        "year": 2022,
    },
    "bd2_depression_treatment": {
        "guide_name": "抑郁症治疗与管理的专家推荐意见",
        "year": 2022,
    },
    # ===== 批次4：d4f1ebd925cf (2026-04-22 11:14) — 精神分裂症中国指南+JSCNP =====
    "schizophrenia_first_episode_sga": {
        "guide_name": "中国精神分裂症防治指南（第二版）+JSCNP 2021",
        "year": 2021,
    },
    "schizophrenia_recurrence_dose_up": {
        "guide_name": "中国精神分裂症防治指南（第二版）+JSCNP 2021",
        "year": 2021,
    },
    "schizophrenia_treatment_resistant_clozapine": {
        "guide_name": "中国精神分裂症防治指南（第二版）+JSCNP 2021",
        "year": 2021,
    },
    "schizophrenia_catatonia": {
        "guide_name": "中国精神分裂症防治指南（第二版）+JSCNP 2021",
        "year": 2021,
    },
    "schizophrenia_agitation_im": {
        "guide_name": "中国精神分裂症防治指南（第二版）+JSCNP 2021",
        "year": 2021,
    },
    # ===== 批次5：7ba553c67e54 (2026-04-22 15:27) — CANMAT/ISBD 2018 双相 =====
    "bipolar_mania_first_line": {
        "guide_name": "CANMAT/ISBD 2018 双相障碍管理指南",
        "year": 2018,
    },
    "bipolar_mania_combination": {
        "guide_name": "CANMAT/ISBD 2018 双相障碍管理指南",
        "year": 2018,
    },
    "bipolar_mania_agitation": {
        "guide_name": "CANMAT/ISBD 2018 双相障碍管理指南",
        "year": 2018,
    },
    "bipolar_depression_first_line": {
        "guide_name": "CANMAT/ISBD 2018 双相障碍管理指南",
        "year": 2018,
    },
    "bipolar_depression_second_line": {
        "guide_name": "CANMAT/ISBD 2018 双相障碍管理指南",
        "year": 2018,
    },
    "bipolar_maintenance_first_line": {
        "guide_name": "CANMAT/ISBD 2018 双相障碍管理指南",
        "year": 2018,
    },
    "bipolar2_depression": {
        "guide_name": "CANMAT/ISBD 2018 双相障碍管理指南",
        "year": 2018,
    },
    "bipolar2_maintenance": {
        "guide_name": "CANMAT/ISBD 2018 双相障碍管理指南",
        "year": 2018,
    },
    "bipolar_depression_third_line": {
        "guide_name": "CANMAT/ISBD 2018 双相障碍管理指南",
        "year": 2018,
    },
    "bipolar_refractory": {
        "guide_name": "CANMAT/ISBD 2018 双相障碍管理指南",
        "year": 2018,
    },
    "bipolar_maintenance_precautions": {
        "guide_name": "CANMAT/ISBD 2018 双相障碍管理指南",
        "year": 2018,
    },
    "bipolar_mixed_episode": {
        "guide_name": "CANMAT/ISBD 2018 双相障碍管理指南",
        "year": 2018,
    },
    "bd2_maintenance_treatment": {
        "guide_name": "CANMAT/ISBD 2018 双相障碍管理指南",
        "year": 2018,
    },
    # ===== 批次6：bb471ad496c2 (2026-04-27 15:04) — Rehm 2025 Lancet Seminar =====
    "aud_psychosocial_interventions_2025": {
        "guide_name": "Rehm et al 2025 - Alcohol use disorders (Lancet Seminar)",
        "year": 2025,
    },
    "aud_naltrexone_heavy_drinking_2025": {
        "guide_name": "Rehm et al 2025 - Alcohol use disorders (Lancet Seminar)",
        "year": 2025,
    },
    "aud_disulfiram_supervised_2025": {
        "guide_name": "Rehm et al 2025 - Alcohol use disorders (Lancet Seminar)",
        "year": 2025,
    },
    "aud_nalmefene_controlled_drinking_2025": {
        "guide_name": "Rehm et al 2025 - Alcohol use disorders (Lancet Seminar)",
        "year": 2025,
    },
    "aud_offlabel_baclofen_topiramate_gabapentin_2025": {
        "guide_name": "Rehm et al 2025 - Alcohol use disorders (Lancet Seminar)",
        "year": 2025,
    },
    "aud_semaglutide_glp1_emerging_2025": {
        "guide_name": "Rehm et al 2025 - Alcohol use disorders (Lancet Seminar)",
        "year": 2025,
    },
    "aud_combined_psycho_pharma_2025": {
        "guide_name": "Rehm et al 2025 - Alcohol use disorders (Lancet Seminar)",
        "year": 2025,
    },
    "aud_acamprosate_abstinence_2025": {
        "guide_name": "Rehm et al 2025 - Alcohol use disorders (Lancet Seminar)",
        "year": 2025,
    },
    # ===== 批次7/8：GAD 三篇综述（2026-05-11 12:10-12:12）=====
    "gad_firstline_ssri_2025": {
        "guide_name": "CANMAT 2014 Clinical Practice Guidelines for Anxiety Disorders",
        "year": 2014,
    },
    "gad_firstline_snri_2025": {
        "guide_name": "Duloxetine Dosing and Efficacy for GAD - Systematic Review 2020",
        "year": 2020,
    },
    "gad_augmentation_buspirone_2025": {
        "guide_name": "Pharmacotherapy for Generalized Anxiety Disorder - Strawn et al 2018 Review",
        "year": 2018,
    },
    "gad_augmentation_pregabalin_2025": {
        "guide_name": "Pharmacotherapy for Generalized Anxiety Disorder - Strawn et al 2018 Review",
        "year": 2018,
    },
    "gad_augmentation_sga_2025": {
        "guide_name": "Pharmacotherapy for Generalized Anxiety Disorder - Strawn et al 2018 Review",
        "year": 2018,
    },
    "gad_duloxetine_dose_escalation_2025": {
        "guide_name": "Duloxetine Dosing and Efficacy for GAD - Systematic Review 2020",
        "year": 2020,
    },
    "canmat_anxiety_general_principles_2025": {
        "guide_name": "CANMAT 2014 Clinical Practice Guidelines for Anxiety Disorders",
        "year": 2014,
    },
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
    unmatched_ids = []
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
                scheme["_backfill_note"] = "v1→v2 历史回填，依据 treatment_wiki/log.md 的 8 批 INGEST 时序"
                # 标记为基线版本 v1
                scheme["_version"] = 1
                scheme["_history"] = [
                    {"version": 1, "by": src["guide_name"], "at": now_iso, "action": "backfill"}
                ]
                updated_count += 1
            else:
                skipped_count += 1
        else:
            unmatched_ids.append(sid)

    # 4. 保存
    with open(SCHEMES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # 5. 写升级日志到 log.md
    log_entry = (
        f"\n[2026-06-09 17:30] UPGRADE v1→v2 回填完成："
        f"成功 {updated_count} 个，"
        f"已有 source 跳过 {skipped_count} 个，"
        f"未匹配 {len(unmatched_ids)} 个（备份：{os.path.basename(backup_path)}）\n"
    )
    if unmatched_ids:
        log_entry += f"[2026-06-09 17:30] UNMATCHED: {unmatched_ids}\n"
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(log_entry)

    # 6. 生成报告
    print(f"\n{'='*50}")
    print(f"=== 升级报告 v1 → v2 ===")
    print(f"{'='*50}")
    print(f"总方案数: {len(schemes)}")
    print(f"✅ 已回填 source 字段: {updated_count}")
    print(f"⏭️  已有 source（跳过）: {skipped_count}")
    print(f"❌ 未匹配（需人工）: {len(unmatched_ids)}")
    if unmatched_ids:
        print(f"   未匹配列表: {unmatched_ids}")
    print(f"\n📦 备份: {backup_path}")
    print(f"📝 升级日志: 已追加到 {LOG_PATH}")

    # 7. 验证 v2 轨道 A 是否可触发
    with_source = sum(1 for s in schemes if s.get("source", {}).get("guide_name"))
    no_source = len(schemes) - with_source
    print(f"\n=== 升级后状态 ===")
    print(f"有 source 字段（可走轨道 A 严格）: {with_source}/{len(schemes)}")
    print(f"无 source 字段（仍走轨道 B 宽松）: {no_source}/{len(schemes)}")
    if with_source == len(schemes):
        print(f"\n🎉 全部 58 个方案已激活 v2 严格优先级！")
    else:
        print(f"\n⚠️  仍有 {no_source} 个方案走宽松模式，请检查")

    return 0 if not unmatched_ids else 2


if __name__ == "__main__":
    sys.exit(main())
