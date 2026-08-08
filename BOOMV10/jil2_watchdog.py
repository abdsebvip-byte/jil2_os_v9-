"""
watchdog.py — حارس المنصة الدائم
يراقب جميع الخدمات ويعيد تشغيلها تلقائياً فور توقفها
"""
import subprocess
import time
import sys
import os
import logging

logging.basicConfig(
    filename="jil2_watchdog.log",
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    encoding="utf-8"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON = os.path.join(BASE_DIR, ".venv", "Scripts", "python.exe")
NGROK  = os.path.join(BASE_DIR, "ngrok.exe")

# ملفات PID التي يجب حذفها قبل كل إعادة تشغيل
PID_FILES = {
    "auto_scanner": "auto_scanner.pid",
    "bot_listener": "bot_listener.pid",
}

# الخدمات المطلوب حراستها
SERVICES = {
    "streamlit": {
        "cmd": [PYTHON, "-m", "streamlit", "run", "app_v10.py",
                "--server.port", "8501", "--server.headless", "true",
                "--server.address", "0.0.0.0",
                "--server.enableCORS", "false", "--server.enableXsrfProtection", "false",
                "--server.enableWebsocketCompression", "false"],
        "process": None,
        "log_file": "streamlit_out.log"
    },
    "auto_scanner": {
        "cmd": [PYTHON, "auto_scanner.py"],
        "process": None
    },
    "bot_listener": {
        "cmd": [PYTHON, "bot_listener.py"],
        "process": None
    },
    "ngrok": {
        "cmd": [NGROK, "http", "8501"],
        "process": None
    },
    "cloudflared": {
        "cmd": ["cloudflared.exe", "tunnel", "--url", "http://localhost:8501", "--logfile", "cloudflared.log"],
        "process": None
    },
    "pinggy": {
        "cmd": ["ssh", "-p", "443", "-R0:localhost:8501", "-o", "StrictHostKeyChecking=no", "-o", "ServerAliveInterval=30", "a.pinggy.io"],
        "process": None,
        "log_file": "pinggy.log"
    }
}

def clear_pid(name):
    """احذف ملف PID لهذه الخدمة حتى لا يمنعها guard من الإعادة"""
    pid_file = PID_FILES.get(name)
    if pid_file:
        pid_path = os.path.join(BASE_DIR, pid_file)
        if os.path.exists(pid_path):
            try:
                os.remove(pid_path)
            except Exception:
                pass

def is_running(proc):
    if proc is None:
        return False
    return proc.poll() is None

def start_service(name, svc):
    clear_pid(name)  # ← حذف PID القديم قبل التشغيل دائماً
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    
    out_target = subprocess.DEVNULL
    if "log_file" in svc:
        out_target = open(os.path.join(BASE_DIR, svc["log_file"]), "a", encoding="utf-8")
        
    proc = subprocess.Popen(
        svc["cmd"],
        cwd=BASE_DIR,
        env=env,
        stdout=out_target,
        stderr=out_target
    )
    msg = f"[WATCHDOG] ✅ تم تشغيل: {name} (PID: {proc.pid})"
    print(msg)
    logging.info(msg)
    return proc

def main():
    print("=" * 50)
    print("🛡️  WATCHDOG — حارس المنصة الدائم")
    print("=" * 50)
    logging.info("Watchdog started.")

    # تنظيف أي PID قديمة قبل البداية
    for name in PID_FILES:
        clear_pid(name)

    # تشغيل جميع الخدمات
    for name, svc in SERVICES.items():
        svc["process"] = start_service(name, svc)
        time.sleep(2)

    # حلقة المراقبة الدائمة — كل 20 ثانية
    while True:
        time.sleep(20)
        for name, svc in SERVICES.items():
            if not is_running(svc["process"]):
                msg = f"[WATCHDOG] ⚠️  {name} توقف — إعادة التشغيل..."
                print(msg)
                logging.warning(msg)
                time.sleep(3)
                svc["process"] = start_service(name, svc)
                time.sleep(5)

if __name__ == "__main__":
    main()

