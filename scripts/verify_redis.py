"""
Step 8 — Redis Integration Verification Script

This script verifies the cache-aside pattern implementation:
1. GET /api/posts?page=1&limit=5 → X-Cache: MISS, then X-Cache: HIT
2. GET /api/posts/{post_id}     → X-Cache: MISS, then X-Cache: HIT
3. GET /api/posts/{invalid_id}  → 404 without caching
4. Other API endpoints still function (Comments, Likes)
5. Health check still works

Run with: python scripts/verify_redis.py
Requires the server to be running on localhost:5000
"""

import requests
import sys
import os

BASE_URL = "http://localhost:5000"
JWT_TOKEN = os.environ.get("TEST_JWT_TOKEN", "")

# Collect results
results = []


def test(name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    results.append((name, passed, detail))
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))


def get(path, **kwargs):
    """Helper for unauthenticated GET requests."""
    return requests.get(f"{BASE_URL}{path}", timeout=10, **kwargs)


def get_auth(path, **kwargs):
    """Helper for authenticated GET requests."""
    headers = {"Authorization": f"Bearer {JWT_TOKEN}"}
    return requests.get(f"{BASE_URL}{path}", headers=headers, timeout=10, **kwargs)


def post_auth(path, json_data=None, **kwargs):
    """Helper for authenticated POST requests."""
    headers = {"Authorization": f"Bearer {JWT_TOKEN}"}
    return requests.post(f"{BASE_URL}{path}", headers=headers, json=json_data, timeout=10, **kwargs)


def main():
    print("\n" + "=" * 60)
    print("Step 8 — Redis Integration Verification")
    print("=" * 60)

    # ─────────────────────────────────────────────────────
    # Test 1: Health check still works
    # ─────────────────────────────────────────────────────
    print("\n--- Test 1: Health Check ---")
    try:
        r = get("/health")
        test("Health check returns 200", r.status_code == 200, f"status={r.status_code}")
    except Exception as e:
        test("Health check returns 200", False, str(e))
        print("\n  ⚠ Server not reachable. Aborting.")
        return

    # ─────────────────────────────────────────────────────
    # Test 2: Paginated posts — first call should be MISS
    # ─────────────────────────────────────────────────────
    print("\n--- Test 2: GET /api/posts (cache MISS) ---")
    r1 = get("/api/posts", params={"page": 1, "limit": 5})
    test("Returns 200", r1.status_code == 200, f"status={r1.status_code}")
    xcache1 = r1.headers.get("x-cache", "")
    test("X-Cache header present", xcache1 != "", f"X-Cache={xcache1!r}")
    test("X-Cache is MISS on first call", xcache1 == "MISS", f"X-Cache={xcache1!r}")

    # Verify response structure is still correct
    data1 = r1.json()
    test("Response has 'items' key", "items" in data1)
    test("Response has 'page' key", "page" in data1)
    test("Response has 'total' key", "total" in data1)
    test("Response has 'total_pages' key", "total_pages" in data1)

    # ─────────────────────────────────────────────────────
    # Test 3: Same paginated request — should be HIT
    # ─────────────────────────────────────────────────────
    print("\n--- Test 3: GET /api/posts (cache HIT) ---")
    r2 = get("/api/posts", params={"page": 1, "limit": 5})
    test("Returns 200", r2.status_code == 200, f"status={r2.status_code}")
    xcache2 = r2.headers.get("x-cache", "")
    test("X-Cache is HIT on second call", xcache2 == "HIT", f"X-Cache={xcache2!r}")

    # Verify data consistency between MISS and HIT
    data2 = r2.json()
    test("Cached data matches original", data1 == data2,
         f"items_count_1={len(data1.get('items', []))}, items_count_2={len(data2.get('items', []))}")

    # ─────────────────────────────────────────────────────
    # Test 4: Individual post — first call should be MISS
    # ─────────────────────────────────────────────────────
    print("\n--- Test 4: GET /api/posts/{id} (cache MISS) ---")
    # Use a post_id from the list
    post_id = None
    if data1.get("items") and len(data1["items"]) > 0:
        post_id = data1["items"][0]["id"]

    if post_id:
        r3 = get(f"/api/posts/{post_id}")
        test("Returns 200", r3.status_code == 200, f"status={r3.status_code}")
        xcache3 = r3.headers.get("x-cache", "")
        test("X-Cache is MISS on first call", xcache3 == "MISS", f"X-Cache={xcache3!r}")

        # ─────────────────────────────────────────────────
        # Test 5: Same individual post — should be HIT
        # ─────────────────────────────────────────────────
        print("\n--- Test 5: GET /api/posts/{id} (cache HIT) ---")
        r4 = get(f"/api/posts/{post_id}")
        test("Returns 200", r4.status_code == 200, f"status={r4.status_code}")
        xcache4 = r4.headers.get("x-cache", "")
        test("X-Cache is HIT on second call", xcache4 == "HIT", f"X-Cache={xcache4!r}")

        data3 = r3.json()
        data4 = r4.json()
        test("Cached post data matches original", data3 == data4)
    else:
        print("  ⚠ No posts found in database, skipping individual post cache tests")

    # ─────────────────────────────────────────────────────
    # Test 6: Invalid post ID — should return 404, no caching
    # ─────────────────────────────────────────────────────
    print("\n--- Test 6: GET /api/posts/{invalid_id} (404) ---")
    r5 = get("/api/posts/999999")
    test("Returns 404 for nonexistent post", r5.status_code == 404, f"status={r5.status_code}")
    xcache5 = r5.headers.get("x-cache", "")
    test("No X-Cache HIT for 404", xcache5 != "HIT", f"X-Cache={xcache5!r}")

    # ─────────────────────────────────────────────────────
    # Test 7: Different pagination params — independent cache
    # ─────────────────────────────────────────────────────
    print("\n--- Test 7: Different pagination params ---")
    r6 = get("/api/posts", params={"page": 2, "limit": 5})
    test("Returns 200", r6.status_code == 200, f"status={r6.status_code}")
    xcache6 = r6.headers.get("x-cache", "")
    test("Page 2 has its own cache (MISS)", xcache6 == "MISS", f"X-Cache={xcache6!r}")

    # ─────────────────────────────────────────────────────
    # Test 8: Comments API still works
    # ─────────────────────────────────────────────────────
    print("\n--- Test 8: Comments API regression ---")
    if post_id:
        r7 = get(f"/api/posts/{post_id}/comments")
        test("GET comments returns 200", r7.status_code == 200, f"status={r7.status_code}")
    else:
        print("  ⚠ No post_id available, skipping comments regression")

    # ─────────────────────────────────────────────────────
    # Test 9: Likes API still works
    # ─────────────────────────────────────────────────────
    print("\n--- Test 9: Likes API regression ---")
    if post_id:
        r8 = get(f"/api/posts/{post_id}/likes")
        test("GET likes returns 200", r8.status_code == 200, f"status={r8.status_code}")
    else:
        print("  ⚠ No post_id available, skipping likes regression")

    # ─────────────────────────────────────────────────────
    # Summary
    # ─────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    passed = sum(1 for _, p, _ in results if p)
    failed = sum(1 for _, p, _ in results if not p)
    print(f"Results: {passed} passed, {failed} failed, {len(results)} total")
    if failed > 0:
        print("\nFailed tests:")
        for name, p, detail in results:
            if not p:
                print(f"  ✗ {name} — {detail}")
    print("=" * 60 + "\n")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
