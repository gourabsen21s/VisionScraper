# browser_manager/run_demo.py
import time
import signal
import sys
from browser_manager import browser_manager, logger

bm = None

def _signal_handler(sig, frame):
    logger.log("INFO", "signal_received", f"Signal {sig} received — shutting down")
    if bm:
        bm.stop()
    sys.exit(0)

def main():
    global bm
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    bm = browser_manager.BrowserManager()
    bm.start()
    logger.log("INFO", "demo_start", "BrowserManager demo started. Health endpoint is internal via API.")
    try:
        # simple loop to print health every 5s
        while True:
            h = bm.get_health()
            logger.log("INFO", "demo_health", "Health", health=h)
            time.sleep(5)
    finally:
        bm.stop()

if __name__ == "__main__":
    main()
