import asyncio
import functools
import random
from typing import Type, Callable, Any, Tuple
from runner.logger import log

def async_retry(
    retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    jitter: bool = True
):
    """
    Decorator for async functions to retry on failure with exponential backoff.
    
    Args:
        retries: Max number of retries (default 3)
        delay: Initial delay in seconds (default 1.0)
        backoff: Multiplier for delay after each failure (default 2.0)
        exceptions: Tuple of exceptions to catch and retry on (default (Exception,))
        jitter: Add random jitter to delay to prevent thundering herd (default True)
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            current_delay = delay
            last_exception = None
            
            for attempt in range(retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == retries:
                        log("ERROR", "retry_failed", f"Function {func.__name__} failed after {retries} retries", error=str(e))
                        raise e
                    
                    # Calculate wait time
                    wait_time = current_delay
                    if jitter:
                        wait_time *= (0.5 + random.random())
                    
                    log("WARN", "retry_attempt", f"Retrying {func.__name__} in {wait_time:.2f}s (Attempt {attempt + 1}/{retries})", error=str(e))
                    
                    await asyncio.sleep(wait_time)
                    current_delay *= backoff
            
            # Should be unreachable given the raise in the loop, but for type safety
            if last_exception:
                raise last_exception
        return wrapper
    return decorator
