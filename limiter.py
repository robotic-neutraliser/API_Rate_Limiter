import time
import threading
from collections import defaultdict, deque


class SlidingWindowRateLimiter:
    """
    Sliding Window Rate Limiter

    Idea: For each user, keep a list of timestamps of their recent requests.
    Before every new request, remove timestamps that are too old (outside the window).
    If the remaining count is under the limit, allow. Otherwise, block.

    Example: limit=5, window=30s
      - User makes 5 requests at t=0s → all allowed
      - User makes a 6th request at t=10s → blocked (5 still in window)
      - User makes a request at t=31s → allowed (first request has expired)
    """

    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit                          # max requests allowed
        self.window = window_seconds                # rolling window size

        # Stores a list of request timestamps for each user
        # { "user_123": deque([1700000001.2, 1700000010.5, ...]) }
        self.request_log = defaultdict(deque)

        # Lock per user so two requests at the same time don't corrupt the count
        self.locks = defaultdict(threading.Lock)

    def is_allowed(self, user_key: str) -> dict:
        """
        Check if the user is allowed to make a request right now.
        Returns a dict with the decision and metadata.
        """
        now = time.time()
        window_start = now - self.window            # anything before this is too old

        with self.locks[user_key]:
            log = self.request_log[user_key]

            # Step 1: Remove timestamps that are outside the current window
            while log and log[0] < window_start:
                log.popleft()

            # Step 2: Count how many requests are left in the window
            current_count = len(log)

            # Step 3: Decide allow or block
            if current_count < self.limit:
                log.append(now)                     # record this request
                return {
                    "allowed": True,
                    "limit": self.limit,
                    "remaining": self.limit - current_count - 1,
                    "reset_at": log[0] + self.window,   # when the oldest request expires
                }
            else:
                return {
                    "allowed": False,
                    "limit": self.limit,
                    "remaining": 0,
                    "reset_at": log[0] + self.window,   # when a slot opens up
                }
