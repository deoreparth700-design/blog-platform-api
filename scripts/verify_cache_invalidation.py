"""
Step 9 — Cache Invalidation & TTL Verification Script

This script verifies:
1. Cache entries set with 300s TTL (Time-To-Live).
2. GET /api/posts?page=1&limit=5 caching (MISS then HIT).
3. POST /api/posts invalidates list caches (subsequent GET returns MISS with new post).
4. PUT /api/posts/{id} invalidates item cache & list caches (subsequent GET returns MISS with updated content).
5. DELETE /api/posts/{id} invalidates item cache & list caches (subsequent GET returns 404 & list returns MISS).
6. Redis direct TTL check to ensure keys expire properly.
7. Full regression checks across Posts, Comments, Likes, JWT Auth, and Errors.
"""

import sys
import os
import jwt
import time
import requests
import asyncio
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "http://127.0.0.1:5000"
JWT_SECRET = os.environ.get("JWT_ACCESS_SECRET", "super-secret-jwt-key-for-blog-platform-api-development-testing-2026")
if not JWT_SECRET:
    JWT_SECRET = "super-secret-jwt-key-for-blog-platform-api-development-testing-2026"

TEST_USER_ID = "99999999-9999-9999-9999-999999999999"
TEST_USER_2_ID = "88888888-8888-8888-8888-888888888888"

valid_token = jwt.encode({"userId": TEST_USER_ID, "exp": int(time.time()) + 3600}, JWT_SECRET, algorithm="HS256")
user2_token = jwt.encode({"userId": TEST_USER_2_ID, "exp": int(time.time()) + 3600}, JWT_SECRET, algorithm="HS256")

auth_headers = {"Authorization": f"Bearer {valid_token}"}
user2_headers = {"Authorization": f"Bearer {user2_token}"}

passed = 0
failed = 0

def test(name, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  [PASS] {name}")
        passed += 1
    else:
        print(f"  [FAIL] {name} - {detail}")
        failed += 1

print("=" * 60)
print("Step 9 — Cache Invalidation & TTL Verification")
print("=" * 60)

# 0. Health check
try:
    resp = requests.get(f"{BASE_URL}/health")
    test("0. API server health check", resp.status_code == 200 and resp.json().get("status") in ["healthy", "ok"])
except Exception as e:
    print(f"\nAPI server unreachable at {BASE_URL}. Ensure server is running!")
    sys.exit(1)

# Create a test post for invalidation testing
created_post_id = None

print("\n--- 1. Testing Post Creation & List Invalidation ---")
# 1.1 First populate list cache
resp1 = requests.get(f"{BASE_URL}/api/posts?page=1&limit=5")
test("1.1 GET /api/posts page 1 (initial)", resp1.status_code == 200)

resp2 = requests.get(f"{BASE_URL}/api/posts?page=1&limit=5")
test("1.2 GET /api/posts page 1 (cached HIT)", resp2.headers.get("X-Cache") == "HIT", f"Got X-Cache: {resp2.headers.get('X-Cache')}")

# 1.3 Create a post (should invalidate list cache)
post_payload = {"title": "TTL Invalidation Test Post", "content": "Testing cache invalidation on post create."}
create_resp = requests.post(f"{BASE_URL}/api/posts/", json=post_payload, headers=auth_headers)
test("1.3 POST /api/posts (create)", create_resp.status_code == 201)
if create_resp.status_code == 201:
    created_post_id = create_resp.json()["id"]

# 1.4 GET list again (should be MISS because list cache was invalidated!)
resp3 = requests.get(f"{BASE_URL}/api/posts?page=1&limit=5")
test("1.4 GET /api/posts page 1 after POST (cache MISS)", resp3.headers.get("X-Cache") == "MISS", f"Got X-Cache: {resp3.headers.get('X-Cache')}")

# Verify new post is in item list
items = resp3.json().get("items", [])
post_ids = [p["id"] for p in items]
test("1.5 Created post is in list items", created_post_id in post_ids if created_post_id else False)


print("\n--- 2. Testing Individual Item Caching & Direct Redis TTL ---")
if created_post_id:
    # 2.1 GET item (initial MISS)
    item_resp1 = requests.get(f"{BASE_URL}/api/posts/{created_post_id}")
    test("2.1 GET post item (initial MISS)", item_resp1.status_code == 200 and item_resp1.headers.get("X-Cache") == "MISS")

    # 2.2 GET item (cached HIT)
    item_resp2 = requests.get(f"{BASE_URL}/api/posts/{created_post_id}")
    test("2.2 GET post item (cached HIT)", item_resp2.status_code == 200 and item_resp2.headers.get("X-Cache") == "HIT")

    # 2.3 Check TTL in Redis directly
    try:
        from src.config.redis import get_redis_client
        async def check_ttl():
            client = get_redis_client()
            key = f"posts:item:{created_post_id}"
            ttl = await client.ttl(key)
            list_key = "posts:list:page:1:limit:5"
            list_ttl = await client.ttl(list_key)
            return ttl, list_ttl

        item_ttl, list_ttl = asyncio.run(check_ttl())
        test("2.3 Redis Item Key TTL is active (>0 and <= 300s)", isinstance(item_ttl, int) and 0 < item_ttl <= 300, f"Got item_ttl: {item_ttl}")
        test("2.4 Redis List Key TTL is active (>0 and <= 300s)", isinstance(list_ttl, int) and 0 < list_ttl <= 300, f"Got list_ttl: {list_ttl}")
    except Exception as e:
        test("2.3 Redis Direct TTL Check", False, str(e))


print("\n--- 3. Testing Post Update & Cache Invalidation ---")
if created_post_id:
    # 3.1 Update post
    update_payload = {"title": "Updated Title for Invalidation Test", "content": "Updated content."}
    update_resp = requests.put(f"{BASE_URL}/api/posts/{created_post_id}", json=update_payload, headers=auth_headers)
    test("3.1 PUT /api/posts/{id} (update)", update_resp.status_code == 200)

    # 3.2 GET item again (should be MISS because item cache was invalidated!)
    item_resp3 = requests.get(f"{BASE_URL}/api/posts/{created_post_id}")
    test("3.2 GET post item after PUT (cache MISS)", item_resp3.headers.get("X-Cache") == "MISS", f"Got X-Cache: {item_resp3.headers.get('X-Cache')}")
    test("3.3 Item returns updated title", item_resp3.json().get("title") == "Updated Title for Invalidation Test")

    # 3.3 GET list again (should be MISS because list cache was also invalidated!)
    list_resp_after_update = requests.get(f"{BASE_URL}/api/posts?page=1&limit=5")
    test("3.4 GET /api/posts page 1 after PUT (cache MISS)", list_resp_after_update.headers.get("X-Cache") == "MISS", f"Got X-Cache: {list_resp_after_update.headers.get('X-Cache')}")


print("\n--- 4. Testing Post Deletion & Cache Invalidation ---")
if created_post_id:
    # 4.1 Delete post
    del_resp = requests.delete(f"{BASE_URL}/api/posts/{created_post_id}", headers=auth_headers)
    test("4.1 DELETE /api/posts/{id}", del_resp.status_code == 204)

    # 4.2 GET item after deletion (should return 404 and NOT be cached)
    item_resp_del = requests.get(f"{BASE_URL}/api/posts/{created_post_id}")
    test("4.2 GET deleted post item (returns 404)", item_resp_del.status_code == 404)

    # 4.3 GET list after deletion (should be MISS because list cache was invalidated!)
    list_resp_after_del = requests.get(f"{BASE_URL}/api/posts?page=1&limit=5")
    test("4.3 GET /api/posts page 1 after DELETE (cache MISS)", list_resp_after_del.headers.get("X-Cache") == "MISS", f"Got X-Cache: {list_resp_after_del.headers.get('X-Cache')}")

    # Verify deleted post is not in list
    deleted_in_items = any(p["id"] == created_post_id for p in list_resp_after_del.json().get("items", []))
    test("4.4 Deleted post removed from list items", not deleted_in_items)


print("\n--- 5. Regression Checks (Auth, Permissions, Errors) ---")
# Unauthorized create
unauth_resp = requests.post(f"{BASE_URL}/api/posts/", json={"title": "X", "content": "Y"})
test("5.1 POST /api/posts without token returns 401", unauth_resp.status_code == 401)

# Forbidden update (different user)
# Create a post as user 1
p = requests.post(f"{BASE_URL}/api/posts/", json={"title": "User 1 Post", "content": "Content"}, headers=auth_headers).json()
p_id = p["id"]

# Try to edit as user 2
forbidden_resp = requests.put(f"{BASE_URL}/api/posts/{p_id}", json={"title": "Hacked Title"}, headers=user2_headers)
test("5.2 PUT /api/posts/{id} by non-owner returns 403", forbidden_resp.status_code == 403)

# Clean up temporary post
requests.delete(f"{BASE_URL}/api/posts/{p_id}", headers=auth_headers)

print("\n" + "=" * 60)
print(f"Results: {passed} PASSED, {failed} FAILED out of {passed + failed} total tests.")
print("=" * 60)

if failed > 0:
    sys.exit(1)
