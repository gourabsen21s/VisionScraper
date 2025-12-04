# runner/retry.py
import time
import random
from typing import Callable, Any, Tuple

def exp_backoff_with_jitter(attempt: int, base: float = 0.5, cap: float = 8.0, jitter: float = 0.1) -> float:
    """
    Exponential backoff with small jitter.
    attempt: 0-based attempt number
    base: base seconds
    cap: max backoff seconds
    jitter: max random jitter in seconds
    """
    backoff = min(cap, base * (2 ** attempt))
    return backoff + random.uniform(-jitter, jitter)

def retry(
    attempts: int = 3,
    allowed_exceptions: Tuple = (Exception,),
    before_try: Callable[[int], None] = None
):
    """
    Decorator factory to retry a function `attempts` times.
    allowed_exceptions: tuple of exception classes to catch and retry on.
    before_try: optional callable(attempt_index) called before each retry wait (for logging)
    """
    def deco(fn):
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(attempts):
                try:
                    return fn(*args, **kwargs)
                except allowed_exceptions as e:
                    last_exc = e
                    if attempt + 1 >= attempts:
                        raise
                    if before_try:
                        try:
                            before_try(attempt)
                        except Exception:
                            pass
                    sleep_for = exp_backoff_with_jitter(attempt)
                    time.sleep(sleep_for)
            # If loop exits unexpectedly
            if last_exc:
                raise last_exc
        return wrapper
    return deco
