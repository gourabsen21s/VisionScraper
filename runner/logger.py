# browser_manager/logger.py
import json
import os
import sys
import time
from datetime import datetime
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
        "ts": datetime.utcnow().isoformat(),
        "level": level,
        "event": event,
        "message": str(message),
        "payload": kwargs
    }
    try:
        print(json.dumps(entry, default=str), flush=True)
    except Exception as e:
        # Fallback if something is really broken
        print(json.dumps({
            "ts": datetime.utcnow().isoformat(),
            "level": "ERROR",
            "event": "log_serialization_error",
            "message": f"Failed to log event {event}: {str(e)}",
            "payload": {"original_message": str(message)}
        }), flush=True)

class Logger:
    def debug(self, message: str):
        log("DEBUG", "debug", message)

    def info(self, message: str):
        log("INFO", "info", message)

    def warning(self, message: str):
        log("WARN", "warning", message)

    def error(self, message: str):
        log("ERROR", "error", message)

logger = Logger()

def _log_pretty_path(path: os.PathLike) -> str:
    try:
        return str(path).replace(os.path.expanduser("~"), "~")
    except:
        return str(path)
