from prometheus_client import start_http_server, Counter, Gauge
import threading
import logging

# Metrics
RESTART_COUNTER = Counter("browser_manager_restarts_total", "Total browser restarts")
LAST_RESTART_TS = Gauge("browser_manager_last_restart_timestamp", "Unix timestamp of last browser restart")
BROWSER_UP = Gauge("browser_manager_up", "1 if browser is up, 0 otherwise")

_metrics_server_started = False
_metrics_lock = threading.Lock()

def start_metrics_server(port: int):
    global _metrics_server_started
    with _metrics_lock:
        if _metrics_server_started:
            return
        start_http_server(port)
        _metrics_server_started = True
        logging.getLogger("browser_manager.metrics").info(f"Prometheus metrics server started on port {port}")
