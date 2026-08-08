import re

with open('app_v10.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace incorrect jil2_data.db with quant_platform.db
old_conn = "sqlite3.connect('jil2_data.db')"
new_conn = "sqlite3.connect('quant_platform.db')"

if old_conn in content:
    content = content.replace(old_conn, new_conn)
    with open('app_v10.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("app_v10.py patched successfully to use quant_platform.db!")
else:
    print("Error: jil2_data.db not found in app_v10.py")
