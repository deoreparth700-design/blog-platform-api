"""
Step 9 -- Cache Invalidation + TTL -- Comprehensive Verification Script

Tests:
 1.  GET /api/posts/?page=1&limit=5 -> first request = MISS
 2.  Same request                   -> second request = HIT
 3.  Direct Redis TTL check         -> 0 < ttl <= 60 seconds (list TTL = 60s)
 4.  GET /api/posts/{id}            -> first request = MISS
 5.  Same request                   -> second request = HIT
 6.  Direct Redis TTL check         -> 60 < ttl <= 300 seconds (item TTL = 300s)
 7.  POST /api/posts/               -> list cache invalidated -> next list = MISS
 8.  PUT /api/posts/{id}            -> item + list invalidated -> next requests = MISS, data updated
 9.  DELETE /api/posts/{id}         -> item + list invalidated -> item = 404, list = MISS
 10. Regression: Comments, Likes, JWT, and pagination still work
 11. Authentication & Permission checks: 401 on unauthorized mutations, 403 on forbidden mutations
 12. Graceful Redis degradation: CacheService failure fallback (no crashes, returns None/False/0)

Run:  python scripts/verify_step9.py
Requires:
  - Server running on localhost:5000
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import requests
import jwt
import asyncio
from dotenv import load_dotenv

load_dotenv()

# --------------------------------------------------
# Configuration
# --------------------------------------------------
BASE_URL = "http://localhost:5000"

JWT_SECRET = os.environ.get("JWT_ACCESS_SECRET", "")
if not JWT_SECRET:
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("JWT_ACCESS_SECRET"):
                    JWT_SECRET = line.split("=", 1)[1].strip().strip('"').strip("'")

USER_A_ID = "99999999-9999-9999-9999-999999999999"
USER_B_ID = "88888888-8888-8888-8888-888888888888"

JWT_TOKEN = os.environ.get("TEST_JWT_TOKEN", "")
if not JWT_TOKEN and JWT_SECRET:
    JWT_TOKEN = jwt.encode(
        {"userId": USER_A_ID, "exp": int(time.time()) + 86400, "iat": int(time.time())},
        JWT_SECRET,
        algorithm="HS256"
    )

USER_B_TOKEN = ""
if JWT_SECRET:
    USER_B_TOKEN = jwt.encode(
        {"userId": USER_B_ID, "exp": int(time.time()) + 86400, "iat": int(time.time())},
        JWT_SECRET,
        algorithm="HS256"
    )

# Load Upstash credentials for direct Redis TTL queries
REDIS_URL = os.environ.get("UPSTASH_REDIS_REST_URL", "")
REDIS_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "")

if not REDIS_URL or not REDIS_TOKEN:
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("UPSTASH_REDIS_REST_URL"):
                    REDIS_URL = line.split("=", 1)[1].strip().strip('"').strip("'")
                elif line.startswith("UPSTASH_REDIS_REST_TOKEN"):
                    REDIS_TOKEN = line.split("=", 1)[1].strip().strip('"').strip("'")

results = []


def test(name, passed, detail=""):
    status_str = "PASS" if passed else "FAIL"
    results.append((name, passed, detail))
    msg = f"  [{status_str}] {name}"
    if detail:
        msg += f" -- {detail}"
    print(msg)


def get(path, **kwargs):
    return requests.get(f"{BASE_URL}{path}", timeout=10, **kwargs)


def post_auth(path, json_data=None, token=None, **kwargs):
    t = token or JWT_TOKEN
    headers = {"Authorization": f"Bearer {t}"} if t else {}
    return requests.post(f"{BASE_URL}{path}", headers=headers, json=json_data, timeout=10, **kwargs)


def put_auth(path, json_data=None, token=None, **kwargs):
    t = token or JWT_TOKEN
    headers = {"Authorization": f"Bearer {t}"} if t else {}
    return requests.put(f"{BASE_URL}{path}", headers=headers, json=json_data, timeout=10, **kwargs)


def delete_auth(path, token=None, **kwargs):
    t = token or JWT_TOKEN
    headers = {"Authorization": f"Bearer {t}"} if t else {}
    return requests.delete(f"{BASE_URL}{path}", headers=headers, timeout=10, **kwargs)


def redis_ttl(key):
    """
    Query the TTL of a Redis key directly via the Upstash REST API.
    Returns the TTL in seconds, or None on failure.
    -1 = key exists without expiry, -2 = key does not exist.
    """
    if not REDIS_URL or not REDIS_TOKEN:
        return None
    try:
        url = f"{REDIS_URL}/ttl/{key}"
        headers = {"Authorization": f"Bearer {REDIS_TOKEN}"}
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        return data.get("result")
    except Exception as e:
        print(f"    [!] Redis TTL query failed: {e}")
        return None


def redis_flushdb():
    """Flush all keys to ensure a clean slate before testing."""
    if not REDIS_URL or not REDIS_TOKEN:
        return
    try:
        url = f"{REDIS_URL}/flushdb"
        headers = {"Authorization": f"Bearer {REDIS_TOKEN}"}
        requests.post(url, headers=headers, timeout=10)
        print("  [i] Redis flushed for clean test state")
    except Exception as e:
        print(f"  [!] Redis flush failed: {e}")


def main():
    print("")
    print("=" * 70)
    print("  Step 9 -- Cache Invalidation + TTL -- Comprehensive Verification")
    print("=" * 70)

    if not JWT_TOKEN:
        print("")
        print("  [!] TEST_JWT_TOKEN not set and JWT_ACCESS_SECRET not found.")

    # -- Flush Redis for deterministic results -------------------------
    redis_flushdb()
    time.sleep(0.5)

    # -- Test 0: Health check ------------------------------------------
    print("")
    print("-- Test 0: Health Check --")
    try:
        r = get("/health")
        test("Health check returns 200", r.status_code == 200, f"status={r.status_code}")
    except Exception as e:
        test("Health check returns 200", False, str(e))
        print("")
        print("  [!] Server not reachable. Aborting.")
        return

    # ==================================================================
    # PART A: TTL VERIFICATION
    # ==================================================================

    # -- Test 1: List cache MISS ---------------------------------------
    print("")
    print("-- Test 1: GET /api/posts/?page=1&limit=5  (MISS) --")
    r1 = get("/api/posts/", params={"page": 1, "limit": 5})
    test("Returns 200", r1.status_code == 200, f"status={r1.status_code}")
    xcache1 = r1.headers.get("x-cache", "")
    test("X-Cache = MISS", xcache1 == "MISS", f"X-Cache={xcache1!r}")
    data1 = r1.json()
    test("Has pagination keys", all(k in data1 for k in ["items", "page", "total", "total_pages"]))

    # -- Test 2: List cache HIT ----------------------------------------
    print("")
    print("-- Test 2: Same list request  (HIT) --")
    r2 = get("/api/posts/", params={"page": 1, "limit": 5})
    xcache2 = r2.headers.get("x-cache", "")
    test("X-Cache = HIT", xcache2 == "HIT", f"X-Cache={xcache2!r}")
    test("Data matches cached", r1.json() == r2.json())

    # -- Test 3: List TTL = 60s ----------------------------------------
    print("")
    print("-- Test 3: Redis TTL for list key (60s policy) --")
    list_key = "posts:list:page:1:limit:5"
    ttl_list = redis_ttl(list_key)
    if ttl_list is not None:
        test("List TTL > 0", ttl_list > 0, f"ttl={ttl_list}s")
        test("List TTL <= 60", ttl_list <= 60, f"ttl={ttl_list}s")
    else:
        test("List TTL query succeeded", False, "Could not query Redis directly")

    # -- Test 4: Item cache MISS ---------------------------------------
    post_id = None
    if data1.get("items") and len(data1["items"]) > 0:
        post_id = data1["items"][0]["id"]

    print("")
    print(f"-- Test 4: GET /api/posts/{post_id}  (MISS) --")
    if post_id:
        r3 = get(f"/api/posts/{post_id}")
        test("Returns 200", r3.status_code == 200, f"status={r3.status_code}")
        xcache3 = r3.headers.get("x-cache", "")
        test("X-Cache = MISS", xcache3 == "MISS", f"X-Cache={xcache3!r}")
    else:
        test("Post available for item tests", False, "No posts in database")
        print("  [!] Skipping remaining item tests.")

    # -- Test 5: Item cache HIT ----------------------------------------
    if post_id:
        print("")
        print(f"-- Test 5: Same item request  (HIT) --")
        r4 = get(f"/api/posts/{post_id}")
        xcache4 = r4.headers.get("x-cache", "")
        test("X-Cache = HIT", xcache4 == "HIT", f"X-Cache={xcache4!r}")
        test("Data matches cached", r3.json() == r4.json())

    # -- Test 6: Item TTL = 300s ---------------------------------------
    if post_id:
        print("")
        print(f"-- Test 6: Redis TTL for item key (300s policy) --")
        item_key = f"posts:item:{post_id}"
        ttl_item = redis_ttl(item_key)
        if ttl_item is not None:
            test("Item TTL > 0", ttl_item > 0, f"ttl={ttl_item}s")
            test("Item TTL <= 300", ttl_item <= 300, f"ttl={ttl_item}s")
            test("Item TTL > 60 (not list TTL)", ttl_item > 60, f"ttl={ttl_item}s")
        else:
            test("Item TTL query succeeded", False, "Could not query Redis directly")

    # ==================================================================
    # PART B: CACHE INVALIDATION
    # ==================================================================

    # -- Test 7: Create post -> list invalidated -----------------------
    print("")
    print("-- Test 7: POST /api/posts/ -> list cache invalidated --")
    created_id = None
    if JWT_TOKEN:
        create_r = post_auth("/api/posts/", {"title": "Cache Test Post", "content": "Testing cache invalidation on create"})
        test("Create post returns 201", create_r.status_code == 201, f"status={create_r.status_code}")
        created_post = create_r.json() if create_r.status_code == 201 else {}
        created_id = created_post.get("id")

        # Next list request should be MISS (cache invalidated)
        r_after_create = get("/api/posts/", params={"page": 1, "limit": 5})
        xcache_ac = r_after_create.headers.get("x-cache", "")
        test("List request after create = MISS", xcache_ac == "MISS", f"X-Cache={xcache_ac!r}")
    else:
        test("Create post (skipped -- no JWT)", False, "TEST_JWT_TOKEN not set")

    # -- Test 8: Update post -> item + list invalidated ----------------
    print("")
    print("-- Test 8: PUT /api/posts/{id} -> item + list invalidated --")
    if JWT_TOKEN and created_id:
        # Prime both caches first
        get(f"/api/posts/{created_id}")                       # prime item
        get("/api/posts/", params={"page": 1, "limit": 5})    # prime list

        # Now update
        update_r = put_auth(f"/api/posts/{created_id}", {"title": "Updated Cache Title"})
        test("Update post returns 200", update_r.status_code == 200, f"status={update_r.status_code}")

        # Verify updated data returned
        updated_data = update_r.json() if update_r.status_code == 200 else {}
        test("Updated title returned", updated_data.get("title") == "Updated Cache Title",
             f"title={updated_data.get('title')!r}")

        # Both caches should be invalidated -> MISS
        r_item_after = get(f"/api/posts/{created_id}")
        xcache_ia = r_item_after.headers.get("x-cache", "")
        test("Item request after update = MISS", xcache_ia == "MISS", f"X-Cache={xcache_ia!r}")

        # Verify item returns updated data
        item_data = r_item_after.json()
        test("Item shows updated title", item_data.get("title") == "Updated Cache Title",
             f"title={item_data.get('title')!r}")

        r_list_after = get("/api/posts/", params={"page": 1, "limit": 5})
        xcache_la = r_list_after.headers.get("x-cache", "")
        test("List request after update = MISS", xcache_la == "MISS", f"X-Cache={xcache_la!r}")
    else:
        test("Update post (skipped)", False, "No JWT or no created post")

    # -- Test 9: Delete post -> item + list invalidated ----------------
    print("")
    print("-- Test 9: DELETE /api/posts/{id} -> item + list invalidated --")
    if JWT_TOKEN and created_id:
        # Prime caches
        get(f"/api/posts/{created_id}")
        get("/api/posts/", params={"page": 1, "limit": 5})

        # Delete
        del_r = delete_auth(f"/api/posts/{created_id}")
        test("Delete post returns 204", del_r.status_code == 204, f"status={del_r.status_code}")

        # Item should now be 404
        r_item_del = get(f"/api/posts/{created_id}")
        test("Deleted item returns 404", r_item_del.status_code == 404, f"status={r_item_del.status_code}")

        # List should be MISS (cache was invalidated)
        r_list_del = get("/api/posts/", params={"page": 1, "limit": 5})
        xcache_ld = r_list_del.headers.get("x-cache", "")
        test("List request after delete = MISS", xcache_ld == "MISS", f"X-Cache={xcache_ld!r}")
    else:
        test("Delete post (skipped)", False, "No JWT or no created post")

    # ==================================================================
    # PART C: AUTHENTICATION & PERMISSIONS
    # ==================================================================

    print("")
    print("-- Test 10: Authentication & Permissions --")

    # Unauthenticated mutations return 401
    r_unauth_post = requests.post(f"{BASE_URL}/api/posts/", json={"title": "Test", "content": "Test"}, timeout=10)
    test("POST /api/posts/ without token returns 401", r_unauth_post.status_code == 401, f"status={r_unauth_post.status_code}")

    r_unauth_put = requests.put(f"{BASE_URL}/api/posts/1", json={"title": "Test"}, timeout=10)
    test("PUT /api/posts/1 without token returns 401", r_unauth_put.status_code == 401, f"status={r_unauth_put.status_code}")

    r_unauth_del = requests.delete(f"{BASE_URL}/api/posts/1", timeout=10)
    test("DELETE /api/posts/1 without token returns 401", r_unauth_del.status_code == 401, f"status={r_unauth_del.status_code}")

    # Create post with User A to test User B permissions
    if JWT_TOKEN and USER_B_TOKEN:
        p_res = post_auth("/api/posts/", {"title": "User A Post", "content": "Owned by user A"})
        if p_res.status_code == 201:
            post_a_id = p_res.json()["id"]
            # User B attempts to edit User A's post -> 403 Forbidden
            put_b = put_auth(f"/api/posts/{post_a_id}", {"title": "Hacked"}, token=USER_B_TOKEN)
            test("User B cannot PUT User A's post (403)", put_b.status_code == 403, f"status={put_b.status_code}")

            # User B attempts to delete User A's post -> 403 Forbidden
            del_b = delete_auth(f"/api/posts/{post_a_id}", token=USER_B_TOKEN)
            test("User B cannot DELETE User A's post (403)", del_b.status_code == 403, f"status={del_b.status_code}")

            # Cleanup
            delete_auth(f"/api/posts/{post_a_id}", token=JWT_TOKEN)
        else:
            test("User A post creation for perm check", False, f"status={p_res.status_code}")
    else:
        test("Permission checks (skipped -- tokens not available)", False, "")

    # ==================================================================
    # PART D: GRACEFUL REDIS DEGRADATION
    # ==================================================================

    print("")
    print("-- Test 11: Redis Failure Graceful Fallback --")
    try:
        from src.services.cache_service import CacheService

        class BrokenRedisClient:
            async def get(self, *args, **kwargs):
                raise ConnectionError("Simulated Redis connection failure")
            async def set(self, *args, **kwargs):
                raise ConnectionError("Simulated Redis connection failure")
            async def delete(self, *args, **kwargs):
                raise ConnectionError("Simulated Redis connection failure")
            async def keys(self, *args, **kwargs):
                raise ConnectionError("Simulated Redis connection failure")

        broken_cache = CacheService(BrokenRedisClient())

        async def verify_fallback():
            g = await broken_cache.get("posts:item:1")
            s = await broken_cache.set("posts:item:1", {"id": 1}, ttl=300)
            d = await broken_cache.delete("posts:item:1")
            dp = await broken_cache.delete_by_pattern("posts:list:*")
            return g, s, d, dp

        g_res, s_res, d_res, dp_res = asyncio.run(verify_fallback())
        test("CacheService.get() returns None on Redis failure", g_res is None, f"result={g_res}")
        test("CacheService.set() returns False on Redis failure", s_res is False, f"result={s_res}")
        test("CacheService.delete() returns False on Redis failure", d_res is False, f"result={d_res}")
        test("CacheService.delete_by_pattern() returns False on Redis failure", dp_res is False, f"result={dp_res}")
    except Exception as e:
        test("Graceful fallback on Redis failure", False, str(e))

    # ==================================================================
    # PART E: REGRESSION TESTS
    # ==================================================================

    print("")
    print("-- Test 12: Regression -- Comments, Likes, JWT, Pagination --")

    # Comments
    if post_id:
        r_comments = get(f"/api/posts/{post_id}/comments")
        test("GET comments returns 200", r_comments.status_code == 200, f"status={r_comments.status_code}")
    else:
        test("GET comments (skipped -- no post_id)", False, "")

    # Likes
    if post_id:
        r_likes = get(f"/api/posts/{post_id}/likes")
        test("GET likes returns 200", r_likes.status_code == 200, f"status={r_likes.status_code}")
    else:
        test("GET likes (skipped -- no post_id)", False, "")

    # JWT auth-test
    if JWT_TOKEN:
        r_auth = requests.get(f"{BASE_URL}/api/auth-test",
                              headers={"Authorization": f"Bearer {JWT_TOKEN}"}, timeout=10)
        test("JWT auth-test returns 200", r_auth.status_code == 200, f"status={r_auth.status_code}")
    else:
        test("JWT auth-test (skipped -- no JWT)", False, "")

    # Pagination -- page 2
    r_page2 = get("/api/posts/", params={"page": 2, "limit": 5})
    test("Page 2 returns 200", r_page2.status_code == 200, f"status={r_page2.status_code}")
    page2_data = r_page2.json()
    test("Page 2 has pagination metadata", "total_pages" in page2_data)

    # 404 for nonexistent post (not cached)
    r_404 = get("/api/posts/999999")
    test("Nonexistent post returns 404", r_404.status_code == 404, f"status={r_404.status_code}")
    xcache_404 = r_404.headers.get("x-cache", "")
    test("404 not served from cache", xcache_404 != "HIT", f"X-Cache={xcache_404!r}")

    # ==================================================================
    # SUMMARY
    # ==================================================================

    print("")
    print("=" * 70)
    passed = sum(1 for _, p, _ in results if p)
    failed = sum(1 for _, p, _ in results if not p)
    print(f"  Results: {passed} passed, {failed} failed, {len(results)} total")

    if failed > 0:
        print("")
        print("  Failed tests:")
        for name, p, detail in results:
            if not p:
                msg = f"    [x] {name}"
                if detail:
                    msg += f" -- {detail}"
                print(msg)

    print("=" * 70)
    print("")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
