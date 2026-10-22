# Blog Platform API

[![Tests](https://github.com/deoreparth700-design/blog-platform-api/actions/workflows/tests.yml/badge.svg)](https://github.com/deoreparth700-design/blog-platform-api/actions/workflows/tests.yml)

A production-style backend REST API for a blog platform built with **FastAPI**, **PostgreSQL (Neon)**, and **Redis (Upstash)**, featuring JWT authentication, ownership-based authorization, cache-aside performance optimization, automated testing, and deployment readiness.


## 🌐 Live Demo

The demo database may be empty on first visit; sign up in /app to create the first post.

The API is deployed on Render. Use these live endpoints to explore and test it:

- **[Interactive API documentation (Swagger)](https://blog-platform-api-db7a.onrender.com/docs)** — browse endpoints and try API requests.
- **[Live Frontend Demo](https://blog-platform-api-db7a.onrender.com/app)** — open the interactive blog UI to browse posts, sign up or log in, create posts, comment, and like.
- **[Health check](https://blog-platform-api-db7a.onrender.com/health)** — confirm the service is running.
- **[View blog posts](https://blog-platform-api-db7a.onrender.com/api/posts/?page=1&limit=10)** — retrieve a paginated list of posts as JSON.
- **Single post example** — Create a post via /app or Swagger, then open /api/posts/{id}

> Open `/app` for the interactive demo UI and `/docs` to explore interactive API documentation.


---

## ✨ Highlights

- **JWT-secured REST API** with ownership-based authorization: only a post's or comment's author can edit or delete it (403 otherwise).
- **Redis cache-aside layer** with separate TTLs and explicit invalidation on every write. Redis failures never break a request; the API falls back to PostgreSQL.
- **Measured performance gain:** median 1055.98 ms (cache miss) vs 62.58 ms (cache hit), about 16.9x faster in a local benchmark against cloud Neon and Upstash (method and caveats in [PERFORMANCE.md](PERFORMANCE.md)).
- **Two pagination styles:** offset pages and a keyset (cursor) feed backed by a `(created_at, id)` index.
- **Atomic likes:** a composite primary key plus `ON CONFLICT DO NOTHING` prevents duplicate likes under concurrent requests.
- **Tested at two levels:** 205 fast unit/API tests with mocked Redis, plus 8 integration tests against real PostgreSQL that run in GitHub Actions.
- **Deployed on Render** from a `render.yaml` blueprint, with a small built-in demo UI at `/app`.

---

<details>
<summary><strong>🚀 Project Status (build milestones)</strong></summary>


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
| **Step 12** | Render Deployment | ✅ Deployed & Verified |

### 🔧 Enterprise Hardening & Engineering Upgrades

| Phase | Enhancement Scope | Status |
| :--- | :--- | :--- |
| **Phase 1** | Security & Input Hardening (`exp` claim required, atomic like concurrency, FK 404, Pydantic bounds, CORS) | ✅ Completed & Verified |
| **Phase 2 & 2b** | Post Detail with Comments (`LEFT JOIN`), Lightweight Lookup Separation & Cache Invalidation | ✅ Completed & Verified |
| **Phase 3** | Keyset / Cursor Pagination (`GET /api/posts/feed`), Base64 Cursors & Feed Caching | ✅ Completed & Verified |
| **Phase 4** | Real PostgreSQL Integration Suite (`tests/integration/`), DB Isolation & CI Service Container | ✅ Completed & Verified |
| **Phase 5** | Benchmark CLI Extension (`--post-id`), Checklist Updates & Documentation Audit | ✅ Completed & Verified |

</details>

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

## ▶️ Run Locally

**Requirements:** Python 3.12, a PostgreSQL database (a free [Neon](https://neon.tech) project works), an [Upstash](https://upstash.com) Redis database, and a JWT secret that matches the one used by the external Auth Service.

```bash
git clone https://github.com/deoreparth700-design/blog-platform-api.git
cd blog-platform-api

python -m venv .venv
source .venv/bin/activate        # Windows PowerShell: .\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
cp .env.example .env             # Windows PowerShell: Copy-Item .env.example .env
# open .env and fill in the values from the table below

python scripts/init_db.py        # creates the tables and indexes
uvicorn src.app:app --reload --port 8000
```

Then open `http://localhost:8000/docs` (Swagger) or `http://localhost:8000/app` (demo UI).

**Getting a token:** this API does not issue tokens. Sign up or log in through the Auth Service (`https://auth-service-17bm.onrender.com`, or the `/app` UI, which does it for you), then send the access token as `Authorization: Bearer <token>`. For tokens to verify, `JWT_ACCESS_SECRET` here must equal the Auth Service's value.

### Environment Variables

| Variable | Required | Purpose |
| :--- | :--- | :--- |
| `DATABASE_URL` | Yes | PostgreSQL connection string (Neon) |
| `JWT_ACCESS_SECRET` | Yes | Secret used to verify HS256 tokens; must match the Auth Service |
| `UPSTASH_REDIS_REST_URL` | Yes for caching | Upstash Redis REST endpoint |
| `UPSTASH_REDIS_REST_TOKEN` | Yes for caching | Upstash Redis REST token |
| `ALLOWED_ORIGINS` | No | Comma-separated CORS origins. If unset, all origins are allowed (`*`) |
| `PORT` | No | Port used by `python src/server.py` (default 5000) |
| `TEST_DATABASE_URL` | Only for integration tests | Separate PostgreSQL database used by `tests/integration/` |

### Database Schema

Three tables, defined in [`src/db/schema.sql`](src/db/schema.sql):

| Table | Key columns | Notes |
| :--- | :--- | :--- |
| `posts` | `id`, `author_id`, `title`, `content`, `created_at`, `updated_at` | Index on `(created_at DESC, id DESC)` serves the cursor feed |
| `comments` | `id`, `post_id`, `author_id`, `content`, `created_at` | `post_id` references `posts` with `ON DELETE CASCADE`; indexed on `post_id` |
| `likes` | `post_id`, `user_id`, `created_at` | Primary key `(post_id, user_id)` makes duplicates impossible; cascades on post delete |

There is no `users` table here: user accounts live in the Auth Service, so `author_id` and `user_id` are plain integers taken from the verified token, with no foreign key.

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
├── frontend/
│   └── index.html                    # Lightweight demo UI (HTML/CSS/JS)
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
│   │   ├── schema.sql                # Relational DDL schema (integer user IDs)
│   │   └── migrations/
│   │       └── 001_user_id_integer.sql # Disposable test migration script
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
│   │   ├── jwt_utils.py              # JWT token decoding & validation
│   │   └── user_id.py                # User ID validation & parsing helper
│   ├── app.py                        # FastAPI instance, CORS, lifespan
│   └── server.py                     # Entrypoint & Uvicorn runner
├── tests/
│   ├── api/                          # Route, validation & caching tests
│   │   ├── test_health.py
│   │   ├── test_frontend.py
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
│   │   ├── test_like_service.py
│   │   └── test_user_id.py
│   ├── integration/                  # Real PostgreSQL end-to-end tests (8)
│   │   ├── conftest.py               # DB setup and isolation
│   │   └── test_e2e.py
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
- **Paginated post lists & feeds (`posts:list:*`)**: `60 seconds` (`POSTS_LIST_TTL = 60`)
  - Offset lists: `posts:list:page:{page}:limit:{limit}`
  - Cursor feeds: `posts:list:cursor:{cursor_or_start}:limit:{limit}`
- **Individual post details (`posts:item:{id}`)**: `300 seconds` / 5 minutes (`POST_ITEM_TTL = 300`)

### Invalidation Triggers
- **`POST /api/posts/`**: Purges all list and feed cache keys (`posts:list:*`) so new posts immediately appear.
- **`PUT /api/posts/{id}`**: Purges the individual item cache (`posts:item:{id}`) AND all list/feed caches (`posts:list:*`).
- **`DELETE /api/posts/{id}`**: Purges the individual item cache (`posts:item:{id}`) AND all list/feed caches (`posts:list:*`).
- **`POST/PUT/DELETE` comments**: Purges the parent post item cache (`posts:item:{post_id}`) so embedded comments in post detail stay synchronized.
- **404 Not Found responses are never cached.**
- `X-Cache` HTTP response header indicates cache status: `HIT` or `MISS`.

---

## 📡 API Endpoints

### System & Auth
| Method | Endpoint | Auth | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Public | Health check |
| `GET` | `/app` | Public | Serves the demo frontend single-page interface |
| `GET` | `/docs` | Public | Interactive Swagger API documentation |
| `GET` | `/api/auth-test` | Required | Validates JWT Bearer token and returns `userId` |

### Posts
*Note: Trailing slashes are preserved on post collection routes per FastAPI route configuration.*
| Method | Endpoint | Auth | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/posts/` | Public | Offset paginated post listing (`?page=1&limit=10`) |
| `GET` | `/api/posts/feed` | Public | Keyset cursor paginated feed (`?limit=10&cursor=<opaque>`) |
| `GET` | `/api/posts/{id}` | Public | Retrieve single post detail with embedded comments list |
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
| `POST` | `/api/posts/{post_id}/like` | Required | Atomic like (returns 409 Conflict if already liked) |
| `DELETE` | `/api/posts/{post_id}/like` | Required | Unlike post (returns 404 if not liked) |
| `GET` | `/api/posts/{post_id}/likes` | Public | Get total like count for post |

---

## 🖥️ Frontend (Demo UI)

A minimal, single-file demo frontend is served directly by the API at [`/app`](http://localhost:8000/app):
- **Editorial UI Architecture**: Built as a single-file application with vanilla HTML, CSS, and JavaScript (no external libraries, no frameworks, no CDN dependencies, and no build step). It uses system font stacks (serif stack for article titles and reading content; sans-serif stack for navigational UI elements) and an 8px spacing grid.
- **Client-Side Hash Routing**: Supports full browser back/forward history and shareable URLs:
  - `#/`: Home feed with keyset cursor pagination (`GET /api/posts/feed`), skeleton loaders, empty states, and "Load more" button.
  - `#/post/<id>`: Shareable post view with preserved formatting (`pre-wrap`), atomic like button with state toggle and counts, and embedded comment stream with composition form.
  - `#/write`: Authenticated publishing view with live character counters matching server validation bounds (title: 200, content: 20,000), disabled submit states while in-flight, and unsaved changes warning before navigation.
- **Theme Customization**: Responsive light and dark modes adhering to `prefers-color-scheme`, plus an explicit visible toggle persisted safely in `localStorage`. Both themes maintain WCAG AA color contrast (>= 4.5:1).
- **Native `<dialog>` Modals & Accessibility**: Uses native HTML `<dialog>` elements for authentication (login and signup with tab switching and password visibility toggle) and post deletion confirmations. Features full keyboard navigation, Escape-to-close behavior, and live ARIA status alerts for toasts.
- **Strict DOM Security**: Fully adheres to strict XSS prevention by never utilizing `innerHTML` with API or user-generated content (all text nodes constructed via `document.createElement` and `textContent`).
- **Cold-Start Resilience**: Built-in latency observer displays a friendly notification if server wake-up exceeds 4 seconds on free hosting tiers.
- **Cache Observability**: Displays a `Cache: HIT` / `Cache: MISS` pill in the footer and post views reflecting Upstash Redis performance via the `X-Cache` response header.
- **Auth Service Configuration**: The frontend includes top-level constants `const AUTH_URL = "https://auth-service-17bm.onrender.com";` and `const BLOG_API_BASE = "";` (same-origin calls) in [`frontend/index.html`](frontend/index.html).
- **Token Storage Trade-off**: Authentication JWTs are held in memory and persisted in `sessionStorage` for demo convenience across page reloads, with proactive `exp` claim inspection for session expiry. For high-security enterprise production deployments, consider storing tokens in `HttpOnly`, `SameSite`, `Secure` cookies to eliminate client-side token exfiltration risks.

---

## 🔐 Authentication & User Identity Alignment

User identities in this system are managed centrally by the external **Auth Service**:
- **Integer User IDs**: The Auth Service issues JWTs with `userId` as an integer (`users.id SERIAL`). The Blog Platform API stores `posts.author_id`, `comments.author_id`, and `likes.user_id` as `INTEGER NOT NULL`.
- **Shared Secret (`JWT_ACCESS_SECRET`)**: The `JWT_ACCESS_SECRET` configuration **must be identical in both the Auth Service and Blog Platform API** for stateless HMAC-SHA256 signature verification to succeed.
- **Identity Parsing**: Incoming tokens are validated using `parse_user_id(value) -> int`. Tokens with missing, non-numeric, non-integer, or non-positive IDs are rejected with `401 Unauthorized ("Invalid user token")`.

### ⚠️ Database Migration
For disposable test environments transitioning from legacy schemas, a migration script is provided at [`src/db/migrations/001_user_id_integer.sql`](src/db/migrations/001_user_id_integer.sql) which drops and recreates `likes`, `comments`, and `posts` with integer author/user IDs.
> **Warning**: *Destroys all existing posts, comments and likes - only use when data is disposable test data.*

---

## 🧪 Automated Testing

The automated test suite contains **213 tests: 205 unit, API and smoke tests, plus 8 live database integration tests** (the integration tests are skipped when `TEST_DATABASE_URL` is not set):
- **205 Unit, API & Smoke Tests**: Run in about 1 second with complete isolation from cloud credentials using FakeRedis and mock repositories.
- **8 Live Database Integration Tests**: Run against real PostgreSQL in `tests/integration/` (and automatically in GitHub Actions CI via a postgres service container).
- **JWT Isolation**: Dedicated `TEST_JWT_SECRET` injected via pytest fixtures without mutating the developer environment.
- **In-Memory FakeRedis**: Full pattern deletion, TTL tracking, and get/set simulation.
- **Database Safety Invariant**: Integration tests strictly require `TEST_DATABASE_URL`. If unset, integration tests are automatically skipped. If `TEST_DATABASE_URL` equals production `DATABASE_URL`, tests abort immediately with a `RuntimeError` to prevent data loss.

### Running Unit and API Tests Only (Fast, No Database Required)
```powershell
pytest tests/unit tests/api
```

### Running Real Database Integration Tests
Integration tests run against a real PostgreSQL database (local or separate branch):

**Windows PowerShell:**
```powershell
$env:TEST_DATABASE_URL="postgresql://user:password@localhost:5432/blog_test"
pytest tests/integration
```

**Linux / macOS / Bash:**
```bash
export TEST_DATABASE_URL="postgresql://user:password@localhost:5432/blog_test"
pytest tests/integration
```

### Running the Entire Test Suite
```powershell
# If TEST_DATABASE_URL is unset, integration tests will cleanly skip
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

## 🧠 Design Decisions

- **PostgreSQL is the source of truth; Redis is optional.** Every cache call is wrapped so a Redis error is logged and the request continues against the database. A cache outage costs speed, not availability.
- **Cache-aside with short TTLs.** Lists expire after 60 seconds and single posts after 5 minutes, and every create, update or delete purges the affected keys, so users see their own changes immediately. 404 responses are never cached.
- **Keyset pagination for the feed.** Offset pages (`?page=`) get slower and can skip or repeat rows as data changes. The `/feed` endpoint instead continues from the last `(created_at, id)` pair, which the composite index serves directly.
- **Ownership checks live in the service layer**, not in the routes, so the rule (403 for non-authors) is unit-tested without HTTP.
- **Tokens must carry an expiry.** The JWT decoder requires the `exp` claim and rejects tokens without a valid integer `userId`.
- **Integration tests refuse to touch production.** If `TEST_DATABASE_URL` equals `DATABASE_URL`, the suite aborts before running.

## ⚠️ Known Limits

- **Coarse cache invalidation.** Any post write clears all list and feed keys, which is simple and correct but not the most efficient for write-heavy workloads.
- **Authentication is delegated.** There is no signup, login or token refresh in this service, and it depends on the Auth Service sharing the same secret.
- **No rate limiting** on any endpoint.
- **CORS is open by default.** Set `ALLOWED_ORIGINS` for a locked-down deployment.
- **Benchmark numbers are local.** They were measured from a developer laptop against cloud services, not from inside the production environment.
- **Free-tier cold starts.** The first request after idle time on Render can take several seconds.
- **Docker is not set up yet.**

---

## 🚀 Deployment Status

**Deployed on Render:** [https://blog-platform-api-db7a.onrender.com](https://blog-platform-api-db7a.onrender.com)

The live health check, posts endpoint, Swagger documentation, and Redis cache HIT behavior have been verified. See [DEPLOYMENT.md](DEPLOYMENT.md) for deployment configuration and verification instructions.
