import asyncio
from typing import Any, Awaitable, Callable, Sequence


async def wait_for_condition(
    condition_func: Callable[[], Awaitable[bool]],
    timeout: float = 5.0,
    interval: float = 0.1,
) -> bool:
    import time

    start = time.time()
    while time.time() - start < timeout:
        if await condition_func():
            return True
        await asyncio.sleep(interval)
    return False


async def run_with_timeout(coro: Awaitable[Any], timeout: float = 10.0) -> Any:
    return await asyncio.wait_for(coro, timeout)


async def run_concurrent_tasks(
    tasks: Sequence[Awaitable[Any]], max_concurrent: int = 5
) -> list[Any]:
    semaphore = asyncio.Semaphore(max_concurrent)

    async def run(task):
        async with semaphore:
            return await task

    return await asyncio.gather(*[run(t) for t in tasks])


def async_test_timeout(timeout: float = 30.0):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            return await asyncio.wait_for(func(*args, **kwargs), timeout)

        return wrapper

    return decorator


def async_test_retry(max_retries: int = 3, delay: float = 1.0):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_ex = None
            for _ in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_ex = e
                    await asyncio.sleep(delay)
            if last_ex is not None:
                raise last_ex
            else:
                raise RuntimeError(
                    f"Function failed after {max_retries} retries with"
                    " no exception captured"
                )

        return wrapper

    return decorator
