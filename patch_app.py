import re

with open('app_v10.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    if line.startswith('t_halts, t1, t2, t3, t_trace, t4, t5, t6, t7 = st.tabs(['):
        new_lines.append('t_halts, t1, t2, t3, t_trace, t_whale, t4, t5, t6, t7 = st.tabs([\n')
    elif '"🔍 سجل الاستبعاد والقرارات (Decision Trace)",' in line:
        new_lines.append(line)
        new_lines.append('    "🐳 رادار الحيتان",\n')
    else:
        new_lines.append(line)

with open('app_v10.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
    
print("app_v10.py patched successfully using python script!")
