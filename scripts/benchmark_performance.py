"""
Performance Benchmark Script for Blog Platform API.

Measures latency comparison between:
1. Cold Cache / MISS: Request hits PostgreSQL database and populates Redis cache (X-Cache: MISS).
2. Warm Cache / HIT: Request is served directly from Upstash Redis (X-Cache: HIT).

Target Endpoint:
GET /api/posts/?page=1&limit=10

Usage:
  python scripts/benchmark_performance.py [BASE_URL]
Example:
  python scripts/benchmark_performance.py http://localhost:5000
"""

import sys
import os
import time
import statistics
import argparse
import requests
from dotenv import load_dotenv
from upstash_redis import Redis

load_dotenv()


def parse_args():
    parser = argparse.ArgumentParser(description="Blog Platform API Performance Benchmark")
    parser.add_argument(
        "base_url",
        nargs="?",
        default=os.environ.get("BASE_URL", "http://localhost:5000"),
        help="Base URL of the running API (default: http://localhost:5000)"
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=20,
        help="Number of iterations for cold and warm runs (default: 20)"
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=3,
        help="Number of warmup requests (default: 3)"
    )
    return parser.parse_args()


def get_redis_client():
    url = os.environ.get("UPSTASH_REDIS_REST_URL")
    token = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
    if not url or not token:
        return None
    try:
        return Redis(url=url, token=token)
    except Exception as e:
        print(f"[!] Warning: Failed to initialize Redis client: {e}")
        return None


def calculate_percentile(data, percentile):
    if not data:
        return 0.0
    k = (len(data) - 1) * (percentile / 100.0)
    f = int(k)
    c = f + 1
    if c >= len(data):
        return data[-1]
    sorted_data = sorted(data)
    d0 = sorted_data[f] * (c - k)
    d1 = sorted_data[c] * (k - f)
    return d0 + d1


def main():
    args = parse_args()
    base_url = args.base_url.rstrip("/")
    endpoint = f"{base_url}/api/posts/?page=1&limit=10"
    target_cache_key = "posts:list:page:1:limit:10"

    print("=" * 60)
    print("Blog Platform API Performance Benchmark")
    print("=" * 60)
    print(f"Target URL:    {endpoint}")
    print(f"Rounds:        {args.rounds} per scenario")
    print(f"Cache key:     {target_cache_key}")
    print("=" * 60)

    # 1. Check health
    try:
        health_resp = requests.get(f"{base_url}/health", timeout=5)
        if health_resp.status_code != 200:
            print(f"[ERROR] Health check failed with status {health_resp.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Could not connect to API at {base_url}: {e}")
        print("Please ensure the FastAPI server is running (`python src/server.py`).")
        sys.exit(1)

    redis_client = get_redis_client()
    if not redis_client:
        print("[ERROR] Upstash Redis credentials not available in environment.")
        sys.exit(1)

    # 2. Warm-up runs
    print(f"\n[1/3] Running {args.warmup} warm-up requests...")
    for _ in range(args.warmup):
        try:
            requests.get(endpoint, timeout=10)
        except Exception:
            pass

    # 3. Cold / MISS Benchmark
    print(f"[2/3] Measuring Cold / MISS latency ({args.rounds} requests)...")
    cold_latencies = []
    cold_miss_count = 0

    session = requests.Session()

    for i in range(args.rounds):
        # Explicitly invalidate ONLY the target cache key to force a clean cold MISS
        try:
            redis_client.delete(target_cache_key)
        except Exception as e:
            print(f"[!] Warning: Failed to invalidate cache key: {e}")

        # Small pause between cold requests to prevent connection reuse skew
        time.sleep(0.05)

        start_time = time.perf_counter()
        resp = session.get(endpoint, timeout=10)
        duration_ms = (time.perf_counter() - start_time) * 1000.0

        if resp.status_code == 200:
            cold_latencies.append(duration_ms)
            cache_header = resp.headers.get("X-Cache", "")
            if cache_header == "MISS":
                cold_miss_count += 1
        else:
            print(f"    [!] Cold request {i+1} returned status {resp.status_code}")

    # 4. Warm / HIT Benchmark
    print(f"[3/3] Measuring Warm / HIT latency ({args.rounds} requests)...")
    # Prime the cache once
    prime_resp = session.get(endpoint, timeout=10)
    if prime_resp.status_code != 200:
        print("[ERROR] Failed to prime cache for warm test.")
        sys.exit(1)

    warm_latencies = []
    warm_hit_count = 0

    for i in range(args.rounds):
        time.sleep(0.02)
        start_time = time.perf_counter()
        resp = session.get(endpoint, timeout=10)
        duration_ms = (time.perf_counter() - start_time) * 1000.0

        if resp.status_code == 200:
            warm_latencies.append(duration_ms)
            cache_header = resp.headers.get("X-Cache", "")
            if cache_header == "HIT":
                warm_hit_count += 1
        else:
            print(f"    [!] Warm request {i+1} returned status {resp.status_code}")

    # 5. Compute Statistics
    if not cold_latencies or not warm_latencies:
        print("[ERROR] Incomplete benchmark measurements.")
        sys.exit(1)

    cold_mean = statistics.mean(cold_latencies)
    cold_median = statistics.median(cold_latencies)
    cold_p95 = calculate_percentile(cold_latencies, 95)
    cold_min = min(cold_latencies)
    cold_max = max(cold_latencies)

    warm_mean = statistics.mean(warm_latencies)
    warm_median = statistics.median(warm_latencies)
    warm_p95 = calculate_percentile(warm_latencies, 95)
    warm_min = min(warm_latencies)
    warm_max = max(warm_latencies)

    median_speedup = cold_median / warm_median if warm_median > 0 else 0.0
    mean_speedup = cold_mean / warm_mean if warm_mean > 0 else 0.0
    warm_hit_rate = (warm_hit_count / len(warm_latencies)) * 100.0

    # 6. Report Results
    print("\n" + "=" * 52)
    print("Blog Platform API Performance Benchmark")
    print("=" * 52)
    print()
    print("Cold / MISS")
    print(f"Requests: {len(cold_latencies)}")
    print(f"Mean:     {cold_mean:.2f} ms")
    print(f"Median:   {cold_median:.2f} ms")
    print(f"P95:      {cold_p95:.2f} ms")
    print(f"Min:      {cold_min:.2f} ms")
    print(f"Max:      {cold_max:.2f} ms")
    print(f"Cache MISS rate: {(cold_miss_count / len(cold_latencies)) * 100.0:.1f}%")
    print()
    print("Warm / HIT")
    print(f"Requests: {len(warm_latencies)}")
    print(f"Mean:     {warm_mean:.2f} ms")
    print(f"Median:   {warm_median:.2f} ms")
    print(f"P95:      {warm_p95:.2f} ms")
    print(f"Min:      {warm_min:.2f} ms")
    print(f"Max:      {warm_max:.2f} ms")
    print(f"Cache HIT rate:  {warm_hit_rate:.1f}%")
    print()
    print(f"Median speedup: {median_speedup:.2f}x")
    print(f"Mean speedup:   {mean_speedup:.2f}x")
    print("=" * 52)
    print("Notice: These measurements reflect local benchmark testing and network")
    print("latency to cloud PostgreSQL (Neon) and cloud Redis (Upstash).")
    print("=" * 52 + "\n")


if __name__ == "__main__":
    main()
