import os
import random
import string
import time

import redis
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))

app = FastAPI()
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True, socket_connect_timeout=3, socket_timeout=5)

REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP requests", ["endpoint", "method", "status"]
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", "Request latency in seconds", ["endpoint"]
)


@app.middleware("http")
async def track_metrics(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    REQUEST_LATENCY.labels(endpoint=request.url.path).observe(time.time() - start)
    REQUEST_COUNT.labels(
        endpoint=request.url.path, method=request.method, status=response.status_code
    ).inc()
    return response


def generate_code(length: int = 6) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


@app.post("/shorten")
def shorten(url: str):
    code = generate_code()
    r.set(f"url:{code}", url)
    r.set(f"clicks:{code}", 0)
    return {"code": code, "short_url": f"/{code}"}


@app.get("/stats/{code}")
def stats(code: str):
    url = r.get(f"url:{code}")
    if url is None:
        raise HTTPException(status_code=404, detail="unknown code")
    clicks = r.get(f"clicks:{code}")
    return {"code": code, "url": url, "clicks": int(clicks or 0)}


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/readyz")
def readyz():
    try:
        is_connected = r.ping()
    except redis.RedisError:
        raise HTTPException(status_code=503)



@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/{code}")
def redirect(code: str):
    url = r.get(f"url:{code}")
    if url is None:
        raise HTTPException(status_code=404, detail="unknown code")
    r.incr(f"clicks:{code}")
    return RedirectResponse(url)
