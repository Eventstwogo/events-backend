import asyncio
import functools
import time
from typing import Any, Awaitable, Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from shared.core.logging_config import get_logger

logger = get_logger(__name__)


class ExecutionTimeMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        start_time = time.perf_counter()
        response = await call_next(request)
        total_time = time.perf_counter() - start_time
        logger.info(
            "[API] %s %s completed in %.4f seconds",
            request.method,
            request.url.path,
            total_time,
        )
        response.headers["X-API-Execution-Time"] = f"{total_time:.4f} seconds"
        return response


def measure_execution_time(label: str = "Function") -> Callable[..., Any]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                start = time.perf_counter()
                result = await func(*args, **kwargs)
                duration = time.perf_counter() - start
                logger.info(
                    "[%s] Async %s executed in %.4f seconds",
                    label,
                    func.__name__,
                    duration,
                )
                return result

            return async_wrapper

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            result = func(*args, **kwargs)
            duration = time.perf_counter() - start
            logger.info(
                "[%s] Sync %s executed in %.4f seconds",
                label,
                func.__name__,
                duration,
            )
            return result

        return sync_wrapper

    return decorator


def retry_on_exception(retries: int = 3, delay: int = 2) -> Callable[..., Any]:
    """
    Decorator to retry an asynchronous function call if it raises an exception.

    Args:
        retries (int): Number of retry attempts.
        delay (int): Delay in seconds between retries.

    Returns:
        Callable: Wrapped function that will retry on exception.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            for attempt in range(1, retries + 1):
                try:
                    logger.info(
                        "Attempt %d of %d for %s",
                        attempt,
                        retries,
                        func.__name__,
                    )
                    return await func(*args, **kwargs)
                except Exception as e:
                    logger.warning(
                        "%s attempt %d failed: %s", func.__name__, attempt, e
                    )
                    if attempt < retries:
                        logger.info(
                            "Retrying %s in %d seconds...", func.__name__, delay
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            "All %d attempts failed for %s",
                            retries,
                            func.__name__,
                        )
                        raise

        return wrapper

    return decorator
