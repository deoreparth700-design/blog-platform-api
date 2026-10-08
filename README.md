# Blog Platform API

A production-style backend REST API for a blog platform built with **FastAPI**, **PostgreSQL (Neon)**, and **Redis (Upstash)**, featuring JWT authentication, ownership-based authorization, cache-aside performance optimization, automated testing, and deployment readiness.

---

## 🚀 Project Status

| Milestone | Scope | Status |
| :--- | :--- | :--- |
| **Step 1** | FastAPI Foundation & Project Setup | ✅ Completed & Verified |
| **Step 2** | Neon PostgreSQL Database Integration | ✅ Completed & Verified |
| **Step 3** | JWT Authentication & Security | ✅ Completed & Verified |
| **Step 4** | Layered Architecture & Database Connection Pool | ✅ Completed & Verified |
| **Step 5** | Posts CRUD API & Ownership Authorization | ✅ Completed & Verified |
| **Step 6** | Comments CRUD API | ✅ Completed & Verified |
| **Step 7** | Likes System & Duplicate Prevention | ✅ Completed & Verified |
| **Step 8** | Redis Cache-Aside Pattern | ✅ Completed & Verified |
| **Step 9** | Cache Invalidation & Multi-Tier TTL Policies | ✅ Completed & Verified |
| **Step 10** | Automated Testing Suite (pytest + HTTPX) | ✅ Completed & Verified |
| **Step 11** | Empirical Performance Measurement & Benchmarking | ✅ Completed & Verified |
| **Step 12** | Deployment Readiness (Render) | ✅ Completed / Deployment-ready for Render |

---

## 🛠️ Technology Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.12)
- **ASGI Server**: [Uvicorn](https://www.uvicorn.org/)
- **Primary Database**: [Neon](https://neon.tech/) Serverless PostgreSQL
- **Database Driver**: [asyncpg](https://github.com/MagicStack/asyncpg) asynchronous connection pool
- **Cache Layer**: [Upstash](https://upstash.com/) Serverless Redis (`upstash-redis` async SDK)
- **Authentication**: Stateless HMAC-SHA256 JWT tokens ([PyJWT](https://pyjwt.readthedocs.io/))
- **Data Modeling & Validation**: [Pydantic v2](https://docs.pydantic.dev/)
- **Testing**: [pytest](https://docs.pytest.org/), [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio), [FastAPI TestClient](https://fastapi.tiangolo.com/tutorial/testing/) (HTTPX)
- **Deployment**: [Render](https://render.com/) Web Service (`render.yaml` Blueprint)

> **Testing Architecture Note:** While original fullstack specs suggested Jest + Supertest for Node.js backends, this project is natively implemented in FastAPI/Python and uses the Python standard modern stack: **pytest**, **pytest-asyncio**, and **TestClient (HTTPX)**.

---

## 🏗️ Layered Architecture

The application strictly adheres to N-Tier Separation of Concerns:

```text
Client
   ↓
FastAPI Routes (Thin routing, validation, status codes, X-Cache headers)
   ↓
JWT Authentication Middleware (HMAC-SHA256 token verification)
   ↓
CacheService (Redis cache-aside layer)
   ↓ MISS                               ↓ HIT
Services (Business logic, ownership, authorization) → Return cached JSON
   ↓
Repositories (Raw SQL queries via asyncpg)
   ↓
Neon PostgreSQL (Source of Truth)
```

- **PostgreSQL is the authoritative source of truth.**
- **Redis is an optional performance acceleration layer.** All Redis calls fail open gracefully: if Redis experiences latency or outages, the API seamlessly falls back to PostgreSQL without crashing or dropping requests.

---

## 📁 Repository Structure

```text
blog-platform-api/
├── .github/
│   └── workflows/
│       └── tests.yml                 # Automated CI workflow
├── scripts/
│   ├── benchmark_performance.py      # Cold vs. Warm latency benchmark
│   ├── init_db.py                    # Database table initialization
│   ├── test_connection.py            # DB & Redis connectivity smoke test
│   ├── verify_redis.py               # Step 8 cache verification
│   ├── verify_cache_invalidation.py  # Step 9 invalidation verification
│   └── verify_step9.py               # Comprehensive Step 9 verification
├── src/
│   ├── config/
│   │   ├── db.py                     # asyncpg connection pool & shutdown
│   │   └── redis.py                  # Upstash Redis client & cleanup
│   ├── db/
│   │   └── schema.sql                # Relational DDL schema
│   ├── middleware/
│   │   └── auth.py                   # HTTPBearer & get_current_user
│   ├── repositories/
│   │   ├── post_repository.py        # Post SQL queries
│   │   ├── comment_repository.py     # Comment SQL queries
│   │   └── like_repository.py        # Like SQL queries
│   ├── routes/
│   │   ├── posts.py                  # /api/posts/ endpoints & caching
│   │   ├── comments.py               # /api/ comments endpoints
│   │   └── likes.py                  # /api/ likes endpoints
│   ├── schemas/
│   │   ├── post.py                   # Post Pydantic models
│   │   ├── comment.py                # Comment Pydantic models
│   │   └── like.py                   # Like Pydantic models
│   ├── services/
│   │   ├── cache_service.py          # Redis helpers, TTLs, invalidation
│   │   ├── post_service.py           # Post authorization & logic
│   │   ├── comment_service.py        # Comment authorization & logic
│   │   └── like_service.py           # Like business rules & constraints
│   ├── utils/
│   │   └── jwt_utils.py              # JWT token decoding & validation
│   ├── app.py                        # FastAPI instance, CORS, lifespan
│   └── server.py                     # Entrypoint & Uvicorn runner
├── tests/
│   ├── api/                          # Route, validation & caching tests
│   │   ├── test_health.py
│   │   ├── test_auth.py
│   │   ├── test_posts.py
│   │   ├── test_comments.py
│   │   ├── test_likes.py
│   │   └── test_pagination.py
│   ├── unit/                         # Isolated unit tests with mocks
│   │   ├── test_jwt.py
│   │   ├── test_cache_service.py
│   │   ├── test_schemas.py
│   │   ├── test_post_service.py
│   │   ├── test_comment_service.py
│   │   └── test_like_service.py
│   ├── conftest.py                   # Pytest fixtures, JWT isolation, FakeRedis
│   └── test_infrastructure_smoke.py  # Smoke tests
├── .env.example
├── .gitignore
├── .python-version
├── DEPLOYMENT.md
├── PERFORMANCE.md
├── PROJECT_PROGRESS.md
├── pytest.ini
├── render.yaml
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

---

## ⚡ Caching & Invalidation Policy

Caching is implemented on all post reads with the **cache-aside** pattern and distinct TTL policies:

### Expiration (TTL) Policies
- **Paginated post list (`posts:list:*`)**: `60 seconds` (`POSTS_LIST_TTL = 60`)
- **Individual post (`posts:item:{id}`)**: `300 seconds` / 5 minutes (`POST_ITEM_TTL = 300`)

### Invalidation Triggers
- **`POST /api/posts/`**: Purges all list cache keys (`posts:list:*`) so new posts immediately appear.
- **`PUT /api/posts/{id}`**: Purges the individual item cache (`posts:item:{id}`) AND all list caches (`posts:list:*`).
- **`DELETE /api/posts/{id}`**: Purges the individual item cache (`posts:item:{id}`) AND all list caches (`posts:list:*`).
- **404 Not Found responses are never cached.**
- `X-Cache` HTTP response header indicates cache status: `HIT` or `MISS`.

---

## 📡 API Endpoints

### System & Auth
| Method | Endpoint | Auth | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Public | Health check |
| `GET` | `/docs` | Public | Interactive Swagger API documentation |
| `GET` | `/api/auth-test` | Required | Validates JWT Bearer token and returns `userId` |

### Posts
*Note: Trailing slashes are preserved on post collection routes per FastAPI route configuration.*
| Method | Endpoint | Auth | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/posts/` | Public | Paginated post listing (`?page=1&limit=10`) |
| `GET` | `/api/posts/{id}` | Public | Retrieve single post by ID |
| `POST` | `/api/posts/` | Required | Create post (author assigned from JWT) |
| `PUT` | `/api/posts/{id}` | Required | Update post (author ownership enforced: 403 on mismatch) |
| `DELETE` | `/api/posts/{id}` | Required | Delete post (author ownership enforced: 403 on mismatch) |

### Comments
| Method | Endpoint | Auth | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/posts/{post_id}/comments` | Required | Add comment to post |
| `GET` | `/api/posts/{post_id}/comments` | Public | List comments for post |
| `PUT` | `/api/comments/{comment_id}` | Required | Update comment (ownership enforced: 403 on mismatch) |
| `DELETE` | `/api/comments/{comment_id}` | Required | Delete comment (ownership enforced: 403 on mismatch) |

### Likes
| Method | Endpoint | Auth | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/posts/{post_id}/like` | Required | Like post (returns 409 Conflict if already liked) |
| `DELETE` | `/api/posts/{post_id}/like` | Required | Unlike post (returns 404 if not liked) |
| `GET` | `/api/posts/{post_id}/likes` | Public | Get total like count for post |

---

## 🧪 Automated Testing

The automated test suite runs **128 tests** with complete isolation from cloud credentials:
- **JWT Isolation**: Dedicated `TEST_JWT_SECRET` injected via pytest fixtures without mutating the developer environment.
- **In-Memory FakeRedis**: Full pattern deletion, TTL tracking, and get/set simulation.
- **Mock Repositories**: Real service business logic tested without requiring live PostgreSQL.
- **FastAPI TestClient**: Full HTTP routing, header verification, and status code assertions.

Run the test suite:
```powershell
pytest
```

---

## 📊 Performance Measurement

Empirical latency benchmarking compares **Cold / MISS** (PostgreSQL query + Redis SET) vs. **Warm / HIT** (Redis in-memory retrieval).

Run the benchmark:
```powershell
python scripts/benchmark_performance.py
```

### Empirical Results (from actual benchmark run)
```text
====================================================
Blog Platform API Performance Benchmark
====================================================

Cold / MISS
Requests: 20
Mean:     1158.78 ms
Median:   1055.98 ms
P95:      1179.87 ms

Warm / HIT
Requests: 20
Mean:     64.94 ms
Median:   62.58 ms
P95:      73.93 ms

Median speedup: 16.87x
====================================================
```
*Measurements were obtained from local developer machine + cloud Neon PostgreSQL + cloud Upstash Redis and are not guaranteed production latency. See [PERFORMANCE.md](PERFORMANCE.md) for full statistical breakdown and methodology.*

---

## 🚀 Deployment Status

**Deployment-ready for Render**

The project is fully prepared for deployment to **Render** using the included `render.yaml` Blueprint.

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete instructions.
