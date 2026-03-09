"""
Load Test for API Rate Limiter
--------------------------------
Make sure the server is running first:
  uvicorn main:app --reload

Then run this script:
  python load_test.py
"""

import time
import threading
import urllib.request
import urllib.error

URL         = "http://localhost:8000/ping"
TOTAL_REQS  = 50    # total requests to send
THREADS     = 10    # concurrent threads (simulates simultaneous clients)

results = {"allowed": 0, "blocked": 0, "errors": 0}
latencies = []
lock = threading.Lock()


def make_request():
    start = time.time()
    try:
        with urllib.request.urlopen(URL) as response:
            latency = (time.time() - start) * 1000  # ms
            with lock:
                results["allowed"] += 1
                latencies.append(latency)
    except urllib.error.HTTPError as e:
        latency = (time.time() - start) * 1000
        with lock:
            if e.code == 429:
                results["blocked"] += 1
            else:
                results["errors"] += 1
            latencies.append(latency)
    except Exception:
        with lock:
            results["errors"] += 1


# ── Run ────────────────────────────────────────────────────────────────────────

print(f"Sending {TOTAL_REQS} requests across {THREADS} threads...\n")
start_time = time.time()

threads = []
for _ in range(TOTAL_REQS):
    t = threading.Thread(target=make_request)
    threads.append(t)

# Fire all threads in batches
for i in range(0, TOTAL_REQS, THREADS):
    batch = threads[i:i + THREADS]
    for t in batch:
        t.start()
    for t in batch:
        t.join()

total_time = time.time() - start_time

# ── Results ────────────────────────────────────────────────────────────────────

avg_latency = sum(latencies) / len(latencies) if latencies else 0
max_latency = max(latencies) if latencies else 0
rps = TOTAL_REQS / total_time

print("=" * 40)
print(f"  Total requests  : {TOTAL_REQS}")
print(f"  Allowed (200)   : {results['allowed']}")
print(f"  Blocked (429)   : {results['blocked']}")
print(f"  Errors          : {results['errors']}")
print(f"  Total time      : {total_time:.2f}s")
print(f"  Requests/sec    : {rps:.1f}")
print(f"  Avg latency     : {avg_latency:.1f}ms")
print(f"  Max latency     : {max_latency:.1f}ms")
print("=" * 40)
