# Performance Measurement & Benchmarking Report

This document records the empirical performance measurement for the **Blog Platform API**, evaluating the impact of the Redis cache-aside layer compared to direct database queries.

---

## 1. Benchmark Methodology

The benchmark measures end-to-end HTTP request latency against the running FastAPI application serving the paginated posts endpoint:

```http
GET /api/posts/?page=1&limit=10
```

### Cold / MISS Execution Flow
1. Target cache key (`posts:list:page:1:limit:10`) is explicitly invalidated prior to the request.
2. Request arrives at FastAPI.
3. CacheService queries Upstash Redis (`GET posts:list:page:1:limit:10`) &rarr; **MISS**.
4. Request falls back to `PostService` &rarr; `PostRepository`.
5. Database query executes against cloud PostgreSQL (Neon).
6. Result is serialized to JSON and stored in Redis with 60s TTL (`POSTS_LIST_TTL`).
7. Response is returned with header `X-Cache: MISS`.

### Warm / HIT Execution Flow
1. Cache key already exists in Redis with populated JSON payload.
2. Request arrives at FastAPI.
3. CacheService queries Upstash Redis (`GET posts:list:page:1:limit:10`) &rarr; **HIT**.
4. Cached JSON string is deserialized directly into Python dictionary/model.
5. Response is returned immediately with header `X-Cache: HIT`.
6. PostgreSQL database is never touched.

### Test Protocol
- **Rounds**: 20 iterations for Cold / MISS and 20 iterations for Warm / HIT.
- **Warm-up**: 3 unmeasured warm-up requests prior to sampling.
- **Measurement Tool**: `scripts/benchmark_performance.py` using high-resolution monotonic timer (`time.perf_counter()`).
- **Safety**: Only the target benchmark key (`posts:list:page:1:limit:10`) was cleared; no database wipe or full Redis flush occurred.

---

## 2. Environment

- **Operating System**: Windows 11
- **Python Version**: 3.12.10
- **Framework**: FastAPI with Uvicorn ASGI server
- **Primary Database**: Neon Serverless PostgreSQL
- **Cache Store**: Upstash Serverless Redis (REST API)
- **Local Server**: Running on `http://localhost:5000`

---

## 3. Actual Benchmark Results

*The following values are empirical results from an actual benchmark execution on the running platform.*

```text
====================================================
Blog Platform API Performance Benchmark
====================================================

Cold / MISS
Requests: 20
Mean:     1158.78 ms
Median:   1055.98 ms
P95:      1179.87 ms
Min:      1027.05 ms
Max:      3134.42 ms
Cache MISS rate: 100.0%

Warm / HIT
Requests: 20
Mean:     64.94 ms
Median:   62.58 ms
P95:      73.93 ms
Min:      58.27 ms
Max:      76.57 ms
Cache HIT rate:  100.0%

Median speedup: 16.87x
Mean speedup:   17.84x
====================================================
```

### Statistical Comparison Table

| Metric | Cold / MISS (PostgreSQL + Redis SET) | Warm / HIT (Redis Cache) | Improvement / Ratio |
| :--- | :--- | :--- | :--- |
| **Sample Size** | 20 requests | 20 requests | — |
| **Cache Hit Rate** | 0.0% (100% MISS) | 100.0% | — |
| **Minimum Latency** | 1,027.05 ms | 58.27 ms | **17.62x faster** |
| **Median Latency** | **1,055.98 ms** | **62.58 ms** | **16.87x speedup** |
| **Mean Latency** | **1,158.78 ms** | **64.94 ms** | **17.84x speedup** |
| **P95 Latency** | **1,179.87 ms** | **73.93 ms** | **15.96x speedup** |
| **Maximum Latency** | 3,134.42 ms | 76.57 ms | **40.93x faster** |

---

## 4. Analysis and Findings

1. **Dramatic Latency Reduction**:
   - Serving from Redis reduced median response time from **1,055.98 ms** down to **62.58 ms**, yielding an actual measured **16.87x speedup**.
   - Direct database operations incur connection pooling, network round-trips to Neon PostgreSQL, SQL parsing, execution, and subsequent Redis `SET` latency. In contrast, cache hits only require a single lightweight Redis `GET` HTTP call.

2. **Tail Latency Consistency (P95)**:
   - P95 cold latency reached **1,179.87 ms** (with a max of 3,134.42 ms during initial pool acquisition).
   - P95 warm latency remained tightly bounded at **73.93 ms**, demonstrating exceptional predictability under repeat traffic.

3. **Database Offloading**:
   - Every cache HIT completely bypasses PostgreSQL, saving database connection slots, compute units, and I/O capacity for write mutations.

---

## 5. Limitations & Local vs. Production Realities

The benchmark measurements documented above were obtained from:
```text
local developer machine
+
cloud Neon PostgreSQL
+
cloud Upstash Redis
```
and are not guaranteed production latency.

1. **Geographic Network Latency**:
   - During local benchmark execution, the FastAPI server ran on a local development machine while Neon PostgreSQL and Upstash Redis resided in cloud data centers.
   - Consequently, each cold request traversed the public internet twice (to Neon and then to Upstash), explaining the ~1s baseline for cold requests.
2. **Deployment Topology Considerations**:
   - In a production deployment (such as a Render Web Service) co-located in the same cloud region as Neon and Upstash (e.g., US-East / AWS `us-east-1`), deployment topology may possibly affect absolute latency due to reduced network distance between services.
   - However, benchmark numbers documented here represent actual measured values from the test environment, rather than speculative production figures.
3. **Single-client vs. Concurrency**:
   - This benchmark measured sequential requests to eliminate artificial client contention skew. Under heavy concurrent load, cache-aside behavior may further reduce database load as repeated read queries bypass SQL execution entirely.
