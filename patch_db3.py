import re

with open('app_v10.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Make database connection absolute to prevent Streamlit working directory path issues
old_conn = "sqlite3.connect('quant_platform.db')"
new_conn = "sqlite3.connect(r'C:\\Users\\sahar\\.gemini\\antigravity\\scratch\\jil2_os_v9\\quant_platform.db')"

if old_conn in content:
    content = content.replace(old_conn, new_conn)
    with open('app_v10.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("app_v10.py patched with ABSOLUTE PATH to quant_platform.db!")
else:
    print("Error: sqlite3.connect('quant_platform.db') not found in app_v10.py")
