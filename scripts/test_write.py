# Test: write a simple Python file with utf-8 encoding
content = '''# -*- coding: utf-8 -*-
"""Test file"""
print("hello")
'''
with open(r'C:/Users/12962/.workbuddy/skills/medical-record-manager/scripts/test_write_output.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Write OK")
