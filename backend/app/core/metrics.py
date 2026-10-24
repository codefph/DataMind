import time
from threading import Lock


class Metrics:
    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: dict[str, int] = {}
        self.started_at = time.time()

    def inc(self, key: str, value: int = 1) -> None:
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + value

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._counters)


metrics = Metrics()

