
import re
import os

file_path = r'c:\Users\HP\Documents\GitHub\apivendo\apps\sri_integration\services\soap_client.py'
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'def ' in line:
        print(f"{i+1}: {line.strip()}")
