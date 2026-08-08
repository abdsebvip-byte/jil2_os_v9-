import os
import re
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

print("=" * 60)
print("🚀 الروابط الثلاثة لمنصة JIL-2 OS (جاهزة للاستخدام)")
print("=" * 60)

# 1. Ngrok
print("\n[1] الرابط الأساسي (Ngrok) - رابط ثابت:")
print("    https://bush-subdued-epilogue.ngrok-free.dev")

# 2. Cloudflare
print("\n[2] الرابط الاحتياطي الأول (Cloudflare) - سريع جداً ومستقر:")
cf_log = os.path.join(BASE_DIR, "cloudflared.log")
cf_link = "جاري الاتصال بالسحابة... (شغل السكربت مرة أخرى بعد 10 ثوانٍ)"
if os.path.exists(cf_log):
    try:
        with open(cf_log, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in reversed(lines):
                if "trycloudflare.com" in line and "https://" in line:
                    match = re.search(r'(https://[a-zA-Z0-9-]+\.trycloudflare\.com)', line)
                    if match:
                        cf_link = match.group(1)
                        break
    except Exception:
        pass
print(f"    {cf_link}")

# 3. Pinggy
print("\n[3] الرابط الاحتياطي الثاني (Pinggy) - عبر نفق SSH:")
pinggy_log = os.path.join(BASE_DIR, "pinggy.log")
pinggy_link = "جاري الاتصال بنفق SSH... (شغل السكربت مرة أخرى بعد 10 ثوانٍ)"
if os.path.exists(pinggy_log):
    try:
        with open(pinggy_log, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            for line in reversed(lines):
                if "http" in line and "pinggy.link" in line:
                    match = re.search(r'(https?://[a-zA-Z0-9-]+\.pinggy\.link)', line)
                    if match:
                        pinggy_link = match.group(1)
                        break
    except Exception:
        pass
print(f"    {pinggy_link}")

print("\n" + "=" * 60)
print("💡 تلميحة: إذا توقف رابط، ببساطة افتح الرابط الآخر. المنصة تعمل في الخلفية بأمان.")
print("=" * 60)
