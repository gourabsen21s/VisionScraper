# browser_manager/logger.py
import json
import time
import os
from typing import Any

LOG_LEVEL = os.getenv("BM_LOG_LEVEL", "INFO").upper()
print(f"DEBUG: Effective LOG_LEVEL is {LOG_LEVEL}")
LEVELS = {"DEBUG": 10, "INFO": 20, "WARN": 30, "ERROR": 40, "CRITICAL": 50}

def _should_log(level: str) -> bool:
    return LEVELS.get(level, 20) >= LEVELS.get(LOG_LEVEL, 20)

def log(level: str, event: str, message: str = "", **kwargs: Any) -> None:
    if not _should_log(level):
        return
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        "level": level,
        "event": event,
        "message": message,
        "payload": kwargs
    }
    print(json.dumps(entry), flush=True)
