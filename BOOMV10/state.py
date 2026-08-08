# state.py — Shared state between Flask and background scanner
scanner_status = {
    "started_at": None,
    "last_scan": None,
    "scans_completed": 0,
    "errors": [],
    "is_running": False
}
