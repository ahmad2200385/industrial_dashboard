"""
Utility decorators for logging, error handling, and performance monitoring.
"""
import functools
import time
from typing import Any, Callable, TypeVar

from core.logging import get_logger

F = TypeVar('F', bound=Callable[..., Any])


def log_operation(operation_name: str = None) -> Callable[[F], F]:
    """
    Decorator to log operation entry/exit and execution time.
    
    Args:
        operation_name: Name of the operation (defaults to function name)
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            logger = get_logger(func.__module__)
            op_name = operation_name or func.__name__
            logger.info(f"Starting operation: {op_name}")
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                logger.info(f"Completed operation: {op_name} in {elapsed:.2f}s")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(f"Failed operation: {op_name} after {elapsed:.2f}s: {str(e)}")
                raise
        
        return wrapper
    return decorator


def handle_exceptions(default_return: Any = None) -> Callable[[F], F]:
    """
    Decorator to catch and log exceptions gracefully.
    
    Args:
        default_return: Value to return on exception
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            logger = get_logger(func.__module__)
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.exception(f"Exception in {func.__name__}: {str(e)}")
                return default_return
        
        return wrapper
    return decorator


def measure_performance(threshold_ms: float = 1000) -> Callable[[F], F]:
    """
    Decorator to measure and log performance metrics.
    Logs warning if execution exceeds threshold.
    
    Args:
        threshold_ms: Warning threshold in milliseconds
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            logger = get_logger(func.__module__)
            
            start_time = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                elapsed_ms = (time.time() - start_time) * 1000
                if elapsed_ms > threshold_ms:
                    logger.warning(
                        f"Slow operation: {func.__name__} took {elapsed_ms:.2f}ms "
                        f"(threshold: {threshold_ms}ms)"
                    )
                else:
                    logger.debug(f"Performance: {func.__name__} took {elapsed_ms:.2f}ms")
        
        return wrapper
    return decorator
