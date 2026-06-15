#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试病程计算逻辑
"""
import sys, json, re, os
from pathlib import Path

# 添加脚本目录到路径
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from minutes_parser import parse_present_illness_minutes, build_patient_data_from_minutes

# 读取听记1的AI摘要
summary_file = r'c:\Users\12962\WorkBuddy\20260406080034\temp_summary.json'
with open(summary_file, 'r', encoding='utf-8') as f:
    data = json.load(f)
    present_illness_text = data.get('result', {}).get('fullSummary', '')

print('=== 调试病程计算 ===')
print(f'现病史纪要长度：{len(present_illness_text)} 字符')

# 先解析现病史，看 onset time 是什么
pi_data = parse_present_illness_minutes(present_illness_text)
print(f'\n解析结果：')
print(f'  onset.time: {repr(pi_data.get("onset", {}).get("time", ""))}')
print(f'  onset.form: {repr(pi_data.get("onset", {}).get("form", ""))}')

# 测试病程计算逻辑
admission_date = '2026-05-27'
onset_time = pi_data['onset']['time']
print(f'\n病程计算：')
print(f'  admission_date: {admission_date}')
print(f'  onset_time: {repr(onset_time)}')

# 尝试提取年份
year_match = re.search(r'(\d{4})', onset_time)
print(f'  year_match: {year_match}')
if year_match:
    print(f'  提取到年份：{year_match.group(1)}')
else:
    print(f'  ⚠️ 无法提取年份（因为是"20余年前"格式）')
    # 尝试从"20余年前"提取数字
    num_match = re.search(r'(\d+)\s*余年?前?', onset_time)
    if num_match:
        years = int(num_match.group(1))
        print(f'  提取到年数：{years}年')
        print(f'  建议病程：总病程{years}余年')
    else:
        print(f'  ❌ 无法提取任何数字')

print(f'\n=== 建议修复方案 ===')
print(f'修改 build_patient_data_from_minutes() 中的病程计算逻辑：')
print(f'1. 先尝试提取具体年份（如2006）')
print(f'2. 如果失败，尝试提取"20余年前"中的数字（20）')
print(f'3. 如果都失败，设置为空字符串')
