import re

with open('app_v10.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace get_db_connection with sqlite3 inline
old_conn = "conn = get_db_connection()"
new_conn = "import sqlite3\n    conn = sqlite3.connect('jil2_data.db')"

if old_conn in content:
    content = content.replace(old_conn, new_conn)
    with open('app_v10.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("app_v10.py DB connection patched successfully!")
else:
    print("get_db_connection not found in file. It might have been already patched or the string doesn't match exactly.")
