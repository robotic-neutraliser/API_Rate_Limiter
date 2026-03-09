"""
API Rate Limiter Service
------------------------
Run:  uvicorn main:app --reload
Docs: http://localhost:8000/docs
"""

import math
import time
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from limiter import SlidingWindowRateLimiter


# ── Config ─────────────────────────────────────────────────────────────────────

LIMIT  = 5   # max 5 requests ...
WINDOW = 30  # ... per 30 seconds

limiter = SlidingWindowRateLimiter(limit=LIMIT, window_seconds=WINDOW)
app = FastAPI(title="Rate Limiter Service")


# ── Middleware ─────────────────────────────────────────────────────────────────
# Runs before every request — like a gate.
# Allows the request through or blocks it with a 429.

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Only protect the /ping route
    if request.url.path != "/ping":
        return await call_next(request)

    # Use IP address as the client identifier
    client_key = request.client.host
    result = limiter.is_allowed(client_key)

    if not result["allowed"]:
        retry_after = math.ceil(result["reset_at"] - time.time())
        return JSONResponse(
            status_code=429,
            content={
                "error": "Too Many Requests",
                "message": f"Limit is {LIMIT} requests per {WINDOW}s. Try again in {retry_after}s.",
            },
            headers={
                "X-RateLimit-Limit":     str(result["limit"]),
                "X-RateLimit-Remaining": str(result["remaining"]),
                "Retry-After":           str(retry_after),
            }
        )

    # Allowed — pass to route and attach quota headers
    response = await call_next(request)
    response.headers["X-RateLimit-Limit"]     = str(result["limit"])
    response.headers["X-RateLimit-Remaining"] = str(result["remaining"])
    return response


# ── Route ──────────────────────────────────────────────────────────────────────

@app.get("/ping")
def ping():
    """The only endpoint. Hit it more than 5 times in 30s to trigger the rate limit."""
    return {"status": "ok"}
