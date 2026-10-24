import time
from collections import deque
from threading import Lock


class SlidingWindowLimiter:
    def __init__(self, max_requests: int, window_seconds: float = 60.0) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._events: deque[float] = deque()
        self._lock = Lock()

    def allow(self) -> bool:
        now = time.monotonic()
        with self._lock:
            while self._events and now - self._events[0] > self.window_seconds:
                self._events.popleft()
            if len(self._events) >= self.max_requests:
                return False
            self._events.append(now)
            return True

