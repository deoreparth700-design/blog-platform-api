"""
Real Integration Tests for Blog Platform API.

Uses a real PostgreSQL database specified by TEST_DATABASE_URL and FakeRedis.
Safety invariants:
- Skips if TEST_DATABASE_URL is unset.
- Refuses to run if TEST_DATABASE_URL == DATABASE_URL.
- Tables are reset and truncated with RESTART IDENTITY CASCADE before each test.

Tests:
a. create post with valid token -> 201; without token -> 401
b. pagination returns correct page size and newest-first order (create 25 posts)
c. liking the same post twice -> second call 409; two concurrent likes (asyncio.gather) -> one 201 and one 409, never 500
d. only the author can delete a post (other user -> 403, author -> 204, then 404)
e. cache invalidation: GET list (MISS), create post, GET list shows the new post (not stale)
f. GET /posts/{id} includes comments and reflects a newly added comment (not stale)
g. cascade delete: deleting a post removes its comments and likes
h. keyset cursor pagination on /api/posts/feed (timestamp ties, feed traversal, invalid cursor)
"""

import os
import asyncio
from datetime import datetime, timezone, timedelta
import pytest
import httpx
from src.app import app

# Top-level safety check for module collection
TEST_DB_URL = os.environ.get("TEST_DATABASE_URL")
PROD_DB_URL = os.environ.get("DATABASE_URL")

if not TEST_DB_URL:
    pytest.skip("TEST_DATABASE_URL not set; skipping integration tests", allow_module_level=True)

if PROD_DB_URL and TEST_DB_URL == PROD_DB_URL:
    raise RuntimeError("TEST_DATABASE_URL cannot be identical to production DATABASE_URL")


# ---------------------------------------------------------------------------
# Test A: Create Post Auth & Unauth
# ---------------------------------------------------------------------------
async def test_create_post_authenticated_and_unauthenticated(integration_client, auth_headers):
    """
    Test A:
    - Creating a post with a valid token returns 201 Created and persists the row.
    - Creating a post without a token returns 401 Unauthorized.
    """
    payload = {"title": "Integration Post", "content": "Integration Content"}

    # 1. Unauthenticated request -> 401
    resp_unauth = await integration_client.post("/api/posts/", json=payload)
    assert resp_unauth.status_code == 401

    # 2. Authenticated request -> 201
    resp_auth = await integration_client.post("/api/posts/", json=payload, headers=auth_headers)
    assert resp_auth.status_code == 201
    data = resp_auth.json()
    assert data["id"] is not None
    assert data["title"] == "Integration Post"
    assert data["content"] == "Integration Content"


# ---------------------------------------------------------------------------
# Test B: Pagination Page Size & Newest-First Ordering
# ---------------------------------------------------------------------------
async def test_pagination_page_size_and_newest_first_order(integration_client, auth_headers):
    """
    Test B:
    Create 25 posts in the real database:
    - GET /api/posts/?page=1&limit=10 returns 10 items, total=25, total_pages=3
    - Results are ordered newest-first (created_at DESC, id DESC)
    """
    # Create 25 posts sequentially
    for i in range(1, 26):
        res = await integration_client.post(
            "/api/posts/",
            json={"title": f"Post {i:02d}", "content": f"Content {i}"},
            headers=auth_headers,
        )
        assert res.status_code == 201

    # Fetch Page 1 with limit=10
    resp_p1 = await integration_client.get("/api/posts/?page=1&limit=10")
    assert resp_p1.status_code == 200
    data_p1 = resp_p1.json()

    assert data_p1["total"] == 25
    assert data_p1["page"] == 1
    assert data_p1["limit"] == 10
    assert data_p1["total_pages"] == 3
    assert len(data_p1["items"]) == 10

    # Verify newest-first ordering (id strictly descending: 25 down to 16)
    ids = [item["id"] for item in data_p1["items"]]
    assert ids == list(range(25, 15, -1))

    # Fetch Page 3 with limit=10
    resp_p3 = await integration_client.get("/api/posts/?page=3&limit=10")
    assert resp_p3.status_code == 200
    data_p3 = resp_p3.json()
    assert len(data_p3["items"]) == 5
    ids_p3 = [item["id"] for item in data_p3["items"]]
    assert ids_p3 == [5, 4, 3, 2, 1]


# ---------------------------------------------------------------------------
# Test C: Duplicate Likes & Concurrency
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_like_duplicate_prevention_and_concurrency(integration_client, auth_headers):
    """
    Test C:
    1. Sequential liking: first call -> 201, second call -> 409 Conflict.
    2. Concurrent liking: two requests via asyncio.gather -> exactly one 201, one 409, never 500.
    """
    # Create Post 1 for sequential testing
    res1 = await integration_client.post("/api/posts/", json={"title": "Like Post 1", "content": "Content"}, headers=auth_headers)
    assert res1.status_code == 201
    post1_id = res1.json()["id"]

    # 1. Sequential duplicate like
    like1 = await integration_client.post(f"/api/posts/{post1_id}/like", headers=auth_headers)
    assert like1.status_code == 201
    assert like1.json()["message"] == "Post liked"

    like2 = await integration_client.post(f"/api/posts/{post1_id}/like", headers=auth_headers)
    assert like2.status_code == 409
    assert like2.json()["detail"] == "Post already liked"

    # Create Post 2 for concurrent like testing
    res2 = await integration_client.post("/api/posts/", json={"title": "Like Post 2", "content": "Content"}, headers=auth_headers)
    assert res2.status_code == 201
    post2_id = res2.json()["id"]

    # 2. Concurrent likes using AsyncClient with ASGI transport
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        resps = await asyncio.gather(
            ac.post(f"/api/posts/{post2_id}/like", headers=auth_headers),
            ac.post(f"/api/posts/{post2_id}/like", headers=auth_headers),
        )

    statuses = sorted([r.status_code for r in resps])
    assert statuses == [201, 409], f"Expected exactly one 201 and one 409, got {statuses}"


# ---------------------------------------------------------------------------
# Test D: Ownership Enforcement on Post Deletion
# ---------------------------------------------------------------------------
async def test_post_deletion_ownership_enforcement(integration_client, auth_headers, user_b_headers):
    """
    Test D:
    - Author A creates a post.
    - User B attempts to delete it -> 403 Forbidden.
    - Author A deletes it -> 204 No Content.
    - Subsequent fetch -> 404 Not Found.
    """
    res = await integration_client.post("/api/posts/", json={"title": "Owner Post", "content": "Author A"}, headers=auth_headers)
    assert res.status_code == 201
    post_id = res.json()["id"]

    # User B attempts delete -> 403
    del_forbidden = await integration_client.delete(f"/api/posts/{post_id}", headers=user_b_headers)
    assert del_forbidden.status_code == 403

    # Author A deletes -> 204
    del_owner = await integration_client.delete(f"/api/posts/{post_id}", headers=auth_headers)
    assert del_owner.status_code == 204

    # Subsequent GET -> 404
    get_gone = await integration_client.get(f"/api/posts/{post_id}")
    assert get_gone.status_code == 404


# ---------------------------------------------------------------------------
# Test E: Cache Invalidation on Post Creation
# ---------------------------------------------------------------------------
async def test_cache_invalidation_list_after_post_create(integration_client, auth_headers):
    """
    Test E:
    1. GET /api/posts/ returns cold cache (MISS).
    2. Second GET returns cached data (HIT).
    3. Creating a new post invalidates list cache.
    4. Third GET returns fresh data including the new post (MISS).
    """
    # Step 1: Initial GET -> MISS
    resp1 = await integration_client.get("/api/posts/?page=1&limit=10")
    assert resp1.status_code == 200
    assert resp1.headers.get("X-Cache") == "MISS"
    assert resp1.json()["total"] == 0

    # Step 2: Second GET -> HIT
    resp2 = await integration_client.get("/api/posts/?page=1&limit=10")
    assert resp2.status_code == 200
    assert resp2.headers.get("X-Cache") == "HIT"

    # Step 3: Create post
    create_res = await integration_client.post(
        "/api/posts/",
        json={"title": "Cache Breaker", "content": "New content"},
        headers=auth_headers,
    )
    assert create_res.status_code == 201
    new_id = create_res.json()["id"]

    # Step 4: Third GET -> Cache was invalidated, returns MISS and reflects new post
    resp3 = await integration_client.get("/api/posts/?page=1&limit=10")
    assert resp3.status_code == 200
    assert resp3.headers.get("X-Cache") == "MISS"
    data3 = resp3.json()
    assert data3["total"] == 1
    assert data3["items"][0]["id"] == new_id


# ---------------------------------------------------------------------------
# Test F: Post Detail Reflects Newly Created Comment
# ---------------------------------------------------------------------------
async def test_post_detail_reflects_new_comment(integration_client, auth_headers):
    """
    Test F:
    1. Create post.
    2. GET /api/posts/{id} -> MISS (empty comments).
    3. Second GET /api/posts/{id} -> HIT.
    4. Create comment on the post.
    5. Third GET /api/posts/{id} -> MISS and reflects the newly added comment.
    """
    # Step 1: Create post
    post_res = await integration_client.post(
        "/api/posts/",
        json={"title": "Detail Post", "content": "Body"},
        headers=auth_headers,
    )
    assert post_res.status_code == 201
    post_id = post_res.json()["id"]

    # Step 2: Cold GET -> MISS (0 comments)
    get1 = await integration_client.get(f"/api/posts/{post_id}")
    assert get1.status_code == 200
    assert get1.headers.get("X-Cache") == "MISS"
    assert get1.json()["comments"] == []

    # Step 3: Warm GET -> HIT
    get2 = await integration_client.get(f"/api/posts/{post_id}")
    assert get2.status_code == 200
    assert get2.headers.get("X-Cache") == "HIT"

    # Step 4: Create comment (invalidates posts:item:{post_id})
    comment_res = await integration_client.post(
        f"/api/posts/{post_id}/comments",
        json={"content": "Fresh comment"},
        headers=auth_headers,
    )
    assert comment_res.status_code == 201
    comment_id = comment_res.json()["id"]

    # Step 5: Third GET -> MISS and includes the comment
    get3 = await integration_client.get(f"/api/posts/{post_id}")
    assert get3.status_code == 200
    assert get3.headers.get("X-Cache") == "MISS"
    comments = get3.json()["comments"]
    assert len(comments) == 1
    assert comments[0]["id"] == comment_id
    assert comments[0]["content"] == "Fresh comment"


# ---------------------------------------------------------------------------
# Test G: Database Cascade Deletion
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_cascade_deletion(integration_client, auth_headers, test_pool):
    """
    Test G:
    Creating a post, adding comments and likes, then deleting the post:
    PostgreSQL ON DELETE CASCADE constraint cleanly removes child comment and like rows.
    """
    # 1. Create post
    post_res = await integration_client.post(
        "/api/posts/",
        json={"title": "Parent Post", "content": "Will be deleted"},
        headers=auth_headers,
    )
    assert post_res.status_code == 201
    post_id = post_res.json()["id"]

    # 2. Add comment
    c_res = await integration_client.post(
        f"/api/posts/{post_id}/comments",
        json={"content": "Child comment"},
        headers=auth_headers,
    )
    assert c_res.status_code == 201

    # 3. Add like
    l_res = await integration_client.post(f"/api/posts/{post_id}/like", headers=auth_headers)
    assert l_res.status_code == 201

    # Verify rows exist in PostgreSQL directly
    async with test_pool.acquire() as conn:
        assert await conn.fetchval("SELECT COUNT(*) FROM posts WHERE id = $1", post_id) == 1
        assert await conn.fetchval("SELECT COUNT(*) FROM comments WHERE post_id = $1", post_id) == 1
        assert await conn.fetchval("SELECT COUNT(*) FROM likes WHERE post_id = $1", post_id) == 1

    # 4. Delete the parent post
    del_res = await integration_client.delete(f"/api/posts/{post_id}", headers=auth_headers)
    assert del_res.status_code == 204

    # 5. Verify all child rows were deleted by PostgreSQL cascade
    async with test_pool.acquire() as conn:
        assert await conn.fetchval("SELECT COUNT(*) FROM posts WHERE id = $1", post_id) == 0
        assert await conn.fetchval("SELECT COUNT(*) FROM comments WHERE post_id = $1", post_id) == 0
        assert await conn.fetchval("SELECT COUNT(*) FROM likes WHERE post_id = $1", post_id) == 0


# ---------------------------------------------------------------------------
# Test H: Keyset Cursor Pagination on /api/posts/feed
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_posts_feed_cursor_pagination_with_timestamp_ties(integration_client, test_pool):
    """
    Test H:
    1. Insert 7 posts directly with SQL so that 4 of them share the exact same
       created_at timestamp, and the others have distinct ones.
    2. Walk the feed with limit=3 following next_cursor until has_more is false.
    3. Assert:
       - Every post appears exactly once (no duplicates, no gaps).
       - The order is created_at DESC then id DESC.
       - The last page has next_cursor null.
       - A bad cursor returns 400.
    """
    author_id = 1
    t_shared = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    t_newest = t_shared + timedelta(minutes=10)
    t_older_1 = t_shared - timedelta(minutes=5)
    t_older_2 = t_shared - timedelta(minutes=10)

    # 7 posts: 1 newer, 4 sharing exact same created_at, 2 older
    posts_to_insert = [
        {"title": "Post Newest", "created_at": t_newest},
        {"title": "Post Tied 1", "created_at": t_shared},
        {"title": "Post Tied 2", "created_at": t_shared},
        {"title": "Post Tied 3", "created_at": t_shared},
        {"title": "Post Tied 4", "created_at": t_shared},
        {"title": "Post Older 1", "created_at": t_older_1},
        {"title": "Post Older 2", "created_at": t_older_2},
    ]

    inserted_posts = []
    async with test_pool.acquire() as conn:
        for p in posts_to_insert:
            row = await conn.fetchrow(
                """
                INSERT INTO posts (author_id, title, content, created_at, updated_at)
                VALUES ($1, $2, 'Content for ' || $2, $3, $3)
                RETURNING id, created_at, title
                """,
                author_id,
                p["title"],
                p["created_at"],
            )
            inserted_posts.append(dict(row))

    inserted_ids = {p["id"] for p in inserted_posts}
    assert len(inserted_ids) == 7

    # Walk the feed with limit=3 following next_cursor until has_more is false
    feed_posts = []
    cursor = None
    pages = []

    while True:
        url = "/api/posts/feed?limit=3"
        if cursor:
            url += f"&cursor={cursor}"
        resp = await integration_client.get(url)
        assert resp.status_code == 200
        data = resp.json()
        pages.append(data)
        feed_posts.extend(data["items"])
        cursor = data["next_cursor"]
        if not data["has_more"]:
            break

    # 1. Assert the last page has next_cursor null
    assert pages[-1]["next_cursor"] is None

    # 2. Assert every post appears exactly once (no duplicates, no gaps)
    feed_ids = [p["id"] for p in feed_posts]
    assert len(feed_ids) == 7
    assert len(set(feed_ids)) == 7
    assert set(feed_ids) == inserted_ids

    # 3. Assert the order is created_at DESC then id DESC
    for i in range(len(feed_posts) - 1):
        curr_dt = datetime.fromisoformat(feed_posts[i]["created_at"])
        next_dt = datetime.fromisoformat(feed_posts[i + 1]["created_at"])
        curr_id = feed_posts[i]["id"]
        next_id = feed_posts[i + 1]["id"]
        assert (curr_dt > next_dt) or (curr_dt == next_dt and curr_id > next_id), (
            f"Ordering violation at index {i}: ({curr_dt}, {curr_id}) vs ({next_dt}, {next_id})"
        )

    # 4. Assert a bad cursor returns 400
    bad_resp = await integration_client.get("/api/posts/feed?cursor=invalid_not_base64_cursor!")
    assert bad_resp.status_code == 400
    assert "Invalid cursor format" in bad_resp.json().get("detail", "")

