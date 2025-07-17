import time
from typing import Any, Awaitable, Callable, Dict


class AsyncPerformanceTracker:
    def __init__(self):
        self.metrics: Dict[str, Any] = {}

    async def track_operation(
        self, name: str, func: Callable[[], Awaitable[Any]]
    ) -> Any:
        start = time.time()
        try:
            result = await func()
            success = True
        except Exception as e:
            result, success = e, False
        self.metrics[name] = {
            "duration": time.time() - start,
            "success": success,
            "result": result,
        }
        return result

    def get_metrics(self) -> Dict[str, Any]:
        return self.metrics

    def assert_performance(self, name: str, max_duration: float):
        if name not in self.metrics:
            raise AssertionError(f"Operation '{name}' not tracked")
        dur = self.metrics[name]["duration"]
        if dur > max_duration:
            raise AssertionError(
                f"'{name}' took {dur:.3f}s (max {max_duration}s)"
            )
