# Blog Platform API — Project Progress & Learning Record

# 1. Project Objective

The real objective of this project is to serve as a practical, comprehensive backend engineering learning vehicle—not just a collection of CRUD endpoints. 

The goal is to deeply understand how a full backend system operates from end to end:

Client
→ HTTP request
→ FastAPI
→ Authentication
→ Business Logic
→ Database / Cache
→ Response

This project is progressively introducing core backend concepts in a hands-on manner:
- API development
- database integration
- authentication
- authorization
- relationships
- pagination
- caching
- testing
- performance
- deployment

**Learning Philosophy:** We are building one real backend system step by step. This ensures that the developer understands precisely why each component exists, how the layers interact, and can confidently explain the complete system in a technical interview.

==================================================

# 2. Project Architecture

The current backend architecture follows a strict, modular N-Tier layered design. 

Client
↓
FastAPI Routes
↓
JWT Authentication (where required)
↓
Services
↓
Repositories
↓
PostgreSQL

### Why we use these specific layers:

- **Routes (`src/routes/`)**: They are the entry points that handle HTTP concerns (parsing URLs, JSON bodies, checking dependencies). They stay "thin" and do not contain business logic.
- **Schemas (`src/schemas/`)**: Using Pydantic, these models guarantee data correctness (validation) before it hits our application, instantly rejecting malformed JSON.
- **Services (`src/services/`)**: The "brain" of the application. This layer holds the business rules, orchestrates authorization checks (like ownership verification), and coordinates operations before talking to the database.
- **Repositories (`src/repositories/`)**: The database experts. They encapsulate all raw SQL and strictly handle `asyncpg` queries, knowing nothing about HTTP requests.
- **Middleware (`src/middleware/`)**: Global interceptors, such as `auth.py`, which validates JWT tokens and extracts the identity of the user securely.
- **Configuration (`src/config/`)**: Centralized setup logic, such as initializing the database connection pool.
- **Utilities (`src/utils/`)**: Standalone helper functions like cryptographic token signing.

### Why we did NOT create a controllers layer:
In traditional MVC frameworks (like Spring or Laravel), controllers are heavily utilized. However, in FastAPI, the combination of `APIRouter` (routes) and dependency injection naturally handles what a controller normally does (request shaping and HTTP response formatting). By keeping routes thin and moving logic directly to `Services`, adding a separate `controllers` layer would only introduce unnecessary boilerplate without providing any real architectural benefit.

*(Note: Redis caching is a planned future architectural layer and is not currently implemented).*

==================================================

# 3. Project Roadmap and Current Progress

| Step | Feature | Status |
| ---- | ------- | ------ |
| Step 1 | FastAPI Foundation | Completed |
| Step 2 | Neon PostgreSQL Database | Completed |
| Step 3 | JWT Authentication | Completed |
| Step 4 | Posts API | Completed & Verified |
| Step 5 | Comments API | Completed & Verified |
| Step 6 | Likes API | Completed & Verified |
| Step 7 | Pagination | Completed & Verified |
| Step 8 | Redis Integration | Not Implemented |
| Step 9 | Cache Invalidation + TTL | Not Implemented |
| Step 10 | Automated Testing | Not Implemented |
| Step 11 | Performance Measurement | Not Implemented |
| Step 12 | Deployment | Not Implemented |

==================================================

# 4. Completed Steps

# Step 1 — FastAPI Foundation

## Status
Completed

## Why We Needed This Step
We needed a high-performance web server capable of handling asynchronous requests. The project initially started with a minimal Python/Flask health-check foundation. However, Flask is traditionally synchronous, which creates bottlenecks when thousands of requests wait on database I/O. We needed to evolve the project to a modern async framework to support the high concurrency expected of a blog platform.

## What We Built
We replaced Flask with FastAPI and established the core application structure. We set up Uvicorn as the ASGI server to run the application, configured CORS middleware to allow frontend clients to connect, and created a basic, unauthenticated `/health` endpoint for infrastructure monitoring.

## Files Created / Modified
- `src/app.py`
- `src/server.py`
- `requirements.txt`

## Why We Chose This Technology / Approach
FastAPI was chosen because it natively supports asynchronous Python (`async`/`await`), provides automatic request validation via Pydantic, and generates self-documenting APIs (Swagger UI). Uvicorn was selected as the ASGI web server because it is the standard, lightning-fast engine that translates incoming HTTP packets into Python async events.

## How It Works
Uvicorn listens on a port (e.g., 5000) for HTTP requests. When a request arrives, Uvicorn translates it into an ASGI event and passes it to the FastAPI application object defined in `src/app.py`. FastAPI then routes the event to the matching function decorator (like `@app.get("/health")`), executes the function, and serializes the returned Python dictionary back into a JSON HTTP response.

## Request / Data Flow
Client HTTP GET `/health`
→ Uvicorn (ASGI server)
→ FastAPI (`app.py`)
→ `health_check()` function
→ JSON Response `{"status": "ok"}`

## Important Concepts Learned
- **FastAPI Framework vs Application Server**: FastAPI defines the rules and routes; Uvicorn (the server) actually runs the network socket.
- **ASGI**: Asynchronous Server Gateway Interface, the modern standard for async Python web servers.
- **CORS**: Cross-Origin Resource Sharing, a security feature that dictates which external web domains can talk to our API.

## Verification
Started the application programmatically using `python src/server.py`.

## Actual Result
Navigating to `http://localhost:5000/health` successfully returned the `{"status": "ok"}` JSON payload.

## What I Learned From This Step
I learned how to bootstrap a modern Python web application, separating the server startup logic (`server.py`) from the application configuration (`app.py`), and the fundamental difference between synchronous (Flask) and asynchronous (FastAPI) web frameworks.

==================================================

# Step 2 — Neon PostgreSQL Database

## Status
Completed

## Why We Needed This Step
A blog platform contains highly relational, structured data (users, posts, comments, likes). We needed a robust, ACID-compliant database to persistently store this state and enforce relational integrity (e.g., ensuring a comment cannot exist without a valid post).

## What We Built
We integrated Neon (a serverless PostgreSQL provider). We implemented a connection pool management system using `asyncpg`, securely stored our credentials in a `.env` file via `DATABASE_URL`, and executed a SQL schema script to generate our foundational tables.

## Files Created / Modified
- `src/config/db.py`
- `scripts/init_db.py`
- `scripts/test_connection.py`
- `src/db/schema.sql`
- `.env`

## Why We Chose This Technology / Approach
PostgreSQL is the industry standard for relational databases. Neon was chosen because it separates storage and compute, allowing instant scaling for connection pooling without infrastructure management. `asyncpg` was chosen because it is an asyncio-native Postgres driver that is significantly faster than traditional ORMs and synchronous drivers, ensuring our FastAPI endpoints never block while waiting for SQL queries.

## How It Works
When the application starts, `src/config/db.py` creates a "pool" of open TCP connections to the Neon PostgreSQL database. When a route needs to run a query, it "checks out" a connection from the pool, runs the parameterized query asynchronously, and returns the connection to the pool. This completely avoids the massive overhead of establishing a new database connection for every single HTTP request.

## Request / Data Flow
FastAPI App Startup
→ `asyncpg.create_pool(DATABASE_URL)`
→ Pool maintains N open connections
→ Application logic checks out connection
→ Executes SQL
→ Returns connection to pool

## Important Concepts Learned
- **Connection Pooling**: Reusing database connections for maximum performance under concurrent load.
- **Parameterized SQL**: Using placeholders (`$1`, `$2`) to pass data to the database, explicitly separating executable code from user data to eliminate SQL injection vulnerabilities.
- **Relational Tables**: `posts`, `comments`, and `likes`.
- **Primary Keys**: Uniquely identifying rows (e.g., `id SERIAL PRIMARY KEY`).
- **Composite Primary Keys**: Using multiple columns (e.g., `post_id, user_id` in the `likes` table) to guarantee uniqueness (a user can only like a post once).
- **Foreign Keys and ON DELETE CASCADE**: Creating strict relationships (`comments.post_id REFERENCES posts(id)`), where deleting a parent row automatically forces the database engine to clean up child rows.
- **Indexes**: Creating data structures (`idx_posts_created_at_id`) to make retrieving specific or sorted data blazingly fast.

## Verification
A custom test script (`test_connection.py`) was executed to connect to the Neon database and query `information_schema.tables` to verify table creation.

## Actual Result
The script successfully connected and returned `True` for the existence of the `posts` table, confirming the schema executed accurately in the cloud database.

## What I Learned From This Step
I learned that modern backend scale relies heavily on how database connections are managed. Directing every request to open its own connection will crash a database; connection pools act as the necessary throttle and cache for database connectivity.

==================================================

# Step 3 — JWT Authentication

## Status
Completed

## Why We Needed This Step
We need to know *who* is interacting with the API (Authentication) to ensure anonymous internet users cannot create, edit, or delete blog posts and comments.

## What We Built
We implemented stateless JSON Web Token (JWT) authentication. We created cryptographic utilities to decode and verify tokens, and a FastAPI middleware dependency (`get_current_user`) to intercept protected routes, parse the HTTP `Authorization` header, and securely extract the `userId`.

## Files Created / Modified
- `src/middleware/auth.py`
- `src/utils/jwt_utils.py`
- `src/app.py` (added `/api/auth-test`)

## Why We Chose This Technology / Approach
JWT was chosen because it is "stateless". Instead of querying the database to look up a session ID for every single HTTP request, the API can mathematically verify the user's identity by validating the cryptographic signature of the token in memory, dramatically reducing database load.

## How It Works
The server holds a secret (`JWT_ACCESS_SECRET`). When a request comes in, FastAPI's `HTTPBearer` extracts the `Bearer <token>` string. The `verify_jwt_token` function hashes the token payload using the `HS256` algorithm and the secret key. If the resulting signature matches the signature embedded in the token, the payload has not been tampered with. If the token is valid and not expired, the `userId` is extracted and passed to the route.

## Request / Data Flow
Client Request with `Authorization: Bearer <token>`
→ Route triggers `Depends(get_current_user)`
→ `HTTPBearer` extracts token string
→ `jwt_utils` decodes using `HS256` + Secret
→ Payload verified
→ Extract `userId`
→ Route executes with known user identity

## Important Concepts Learned
- **Authentication**: Verifying *who* you are (Is this JWT mathematically valid?).
- **Authorization**: Verifying *what* you are allowed to do (we will use the extracted `userId` for this in future steps).
- **Stateless Authentication**: Avoiding database session lookups.
- **JWT Cryptography**: Understanding how symmetric signing (HS256) protects data integrity without encrypting the data itself.
- **FastAPI Dependencies (`Depends`)**: A powerful injection system to run middleware (like auth checks) right before a specific route executes.

## Verification
A protected test endpoint `/api/auth-test` was created.

## Actual Result
Code review verified that `get_current_user()` correctly uses `HTTPBearer` and throws explicit 401 exceptions on missing or invalid tokens, successfully echoing the `userId` on success.

## What I Learned From This Step
I learned how to protect an API cryptographically and how FastAPI's dependency injection system makes it effortless to apply security gates to specific endpoints without polluting the business logic with header-parsing code.

==================================================

# Step 4 — Posts API

## Status
Completed & Verified

## Why We Needed This Step
We needed to expose HTTP endpoints to allow clients to Create, Read, Update, and Delete (CRUD) blog articles. We also needed to enforce strict authorization so that a user could only modify articles they explicitly owned.

## What We Built
We implemented the full Posts API utilizing our N-Tier architecture. We created Pydantic schemas for data validation (`PostCreate`, `PostUpdate`, `PostResponse`), a Repository layer (`PostRepository`) for raw PostgreSQL interactions, a Service layer (`PostService`) for business/ownership rules, and a Router (`posts.py`) to map HTTP verbs to the logic. 

## Files Created / Modified
- `src/schemas/post.py`
- `src/repositories/post_repository.py`
- `src/services/post_service.py`
- `src/routes/posts.py`
- `src/app.py` (mounted `posts_router`)

## Why We Chose This Technology / Approach
Separating the logic into Routes → Services → Repositories firmly decouples HTTP concerns from SQL logic. This makes the code highly testable and readable. Pydantic was leveraged because it catches malformed client data and returns a `422 Unprocessable Entity` error automatically before our application logic ever runs.

## How It Works
The `POST /api/posts` endpoint requires authentication. The route injects the authenticated `userId` and the Pydantic-validated `post_data`. The Service converts the `userId` to a UUID and calls the Repository. The Repository executes an `INSERT ... RETURNING` query via `asyncpg`.
For `PUT` and `DELETE`, the Service first fetches the post, checks if `post.author_id == UUID(user_id)`. If they match, the repository performs the update/delete. If they don't, the Service halts execution and raises a `403 Forbidden` exception.

## Request / Data Flow
Client `PUT /api/posts/{id}` (with JWT)
→ Route injects user identity & data payload
→ Service fetches existing post via Repository
→ Service checks `author_id == userId`
→ If False: abort (403 Forbidden)
→ If True: Repository executes SQL `UPDATE`
→ PostgreSQL persists and returns new row
→ Route serializes row via Pydantic `PostResponse`
→ HTTP 200 OK

## Important Concepts Learned
- **UUIDs**: Using Universally Unique Identifiers to represent users system-wide.
- **Authentication vs Authorization**: JWT proves *who* sent the request; the Service layer proves they are *allowed* to edit the post.
- **HTTP Status Codes**: Using proper vocabulary (`201 Created`, `204 No Content`, `401 Unauthorized`, `403 Forbidden`, `404 Not Found`, `422 Unprocessable Entity`).
- **Dynamic SQL Updates**: Constructing safe parameterized queries in the repository when some update fields are optional.

## Verification
A comprehensive end-to-end Python test script was written using the `requests` library to test the live server.

## Actual Result
All tests passed.
- `GET /health` and `GET /api/posts` returned 200.
- Invalid IDs returned 404.
- Creating a post returned 201.
- Updating a post returned 200.
- Ownership test: attempting to update/delete another user's post correctly returned 403.
- Invalid payloads returned 422.
- Missing tokens returned 401.

## What I Learned From This Step
I learned how to enforce authorization rules securely in a multi-tenant API. I also resolved a complex issue during testing where launching the server in a subprocess caused import errors; this was fixed by injecting the correct `PYTHONPATH` into the test script environment.

==================================================

# Step 5 — Comments API

## Status
Completed & Verified

## Why We Needed This Step
A blog is interactive. We needed a way for users to leave comments, which conceptually exist as a child resource to a specific blog post.

## What We Built
We implemented the Comments API, mirroring the architecture established in Step 4. We built `schemas/comment.py`, `repositories/comment_repository.py`, `services/comment_service.py`, and `routes/comments.py`. The API allows users to create comments on posts, retrieve all comments for a post, and strictly update/delete only their own comments.

## Files Created / Modified
- `src/schemas/comment.py`
- `src/repositories/comment_repository.py`
- `src/services/comment_service.py`
- `src/routes/comments.py`
- `src/app.py` (mounted `comments_router`)

## Why We Chose This Technology / Approach
We mounted the comments router at `/api` to cleanly map nested URLs (`/api/posts/{post_id}/comments`) without colliding with the existing Posts router. We utilized the database's existing `ON DELETE CASCADE` constraint on the `post_id` foreign key, meaning we did not have to write manual cleanup code—if a post is deleted, PostgreSQL automatically wipes out the associated comments.

## How It Works
When creating a comment via `POST /api/posts/{post_id}/comments`, the `CommentService` first explicitly asks the `PostRepository` if the post exists. If it doesn't, it cleanly returns a `404`. If it does, it passes the user's UUID and the comment content to the `CommentRepository` to execute the `INSERT`. When retrieving comments, the SQL query uses `ORDER BY created_at ASC, id ASC` to naturally sort the discussion from oldest to newest.

## Request / Data Flow
Client `POST /api/posts/1/comments` (with JWT)
→ Route extracts `userId` and `CommentCreate` schema
→ Service checks if post #1 exists (404 if not)
→ Service validates user UUID
→ Repository executes parameterized `INSERT`
→ PostgreSQL persists and returns new comment row
→ Route serializes via `CommentResponse` (HTTP 201)

## Important Concepts Learned
- **Child Resources**: Modeling URLs to represent nested relationships (`/parent/{id}/child`).
- **Post-Existence Validation**: The importance of verifying foreign key targets exist before attempting inserts, resulting in clean API errors (404) rather than raw database crash logs.
- **ON DELETE CASCADE**: Utilizing relational database engine features to handle data lifecycle cleanup automatically.

## Verification
A 13-point end-to-end Python test script was written and executed against a live instance. It validated:
1. Health check.
2. Fetch comments for a valid post.
3. Fetch comments for an invalid post (404).
4. Create comment (201).
5. Fetch comments includes the new comment.
6. Owner update (200).
7. Non-owner update rejection (403).
8. Non-owner delete rejection (403).
9. Owner delete (204).
10. Missing JWT (401).
11. Invalid schema body (422).
12. Modify nonexistent comment (404).
13. Create comment on nonexistent post (404).

## Actual Result
All 13 integration scenarios executed perfectly and passed verification.

## What I Learned From This Step
I learned the best practice of layering validations (Check Post exists → Check Comment exists → Check Ownership) inside the Service layer. I also experienced how strict architectural patterns established in Step 4 make implementing new features (Step 5) highly predictable and rapid.

==================================================

# Step 6 — Likes API

## Status
Completed & Verified

## Why We Needed This Step
Users need the ability to "like" a post. Unlike Posts (which are independent) and Comments (which are one-to-many), Likes represent a pure many-to-many relationship where one user can like many posts, and one post can be liked by many users, but a user can only like a specific post once.

## What We Built
We implemented the Likes API. We built a schema for returning like counts (`LikeCountResponse`), a repository (`LikeRepository`) to handle duplicate-safe inserts and aggregate queries, a service (`LikeService`) to enforce post existence and duplicate-like rejection, and routes (`likes.py`) to expose `POST` and `DELETE` endpoints.

## Files Created / Modified
- `src/schemas/like.py`
- `src/repositories/like_repository.py`
- `src/services/like_service.py`
- `src/routes/likes.py`
- `src/app.py`

## Why We Chose This Design
We continued to use the N-Tier layered architecture without a controllers layer to keep the codebase consistent and thin at the HTTP boundary. 
The database uses a pure junction table (`likes`) without a surrogate `id` column. Because a like is uniquely identified by the combination of `post_id` and `user_id`, we rely on a **composite primary key**. A local users table is not needed because we extract the globally unique `userId` from the JWT directly.

## How It Works
When a user likes a post, the `LikeService` first verifies that the post exists via the `PostRepository`. Then it checks the `LikeRepository` to see if a like from this user on this post already exists. If so, it cleanly rejects it with a `409 Conflict`. If not, it executes an `INSERT`. To get the like count, the repository runs an aggregate `SELECT COUNT(*) FROM likes WHERE post_id = $1`. When a user unlikes a post, the `LikeService` ensures the like exists before issuing a `DELETE` explicitly bound to the `user_id`, ensuring a user can never delete another user's like.

## Many-to-Many Relationship
```text
          ┌──────────┐
          │  User A  │
          └────┬─────┘
               │
               │
             likes
               │
          ┌────┴─────┐
          │          │
       Post 1     Post 2
          ▲          ▲
          │          │
         User B     User C
```
The `likes` table acts as a junction or relationship table bridging the stateless user (from the JWT) and the `posts` table.

## Composite Primary Key
```sql
PRIMARY KEY (post_id, user_id)
```
A single `id` column is completely unnecessary here because the relationship itself is unique. By defining `(post_id, user_id)` as the composite primary key, the PostgreSQL engine natively enforces that the same user cannot insert a second like for the same post. 

## Duplicate Like Handling
The API handles duplication gracefully in the service layer by first checking if the like exists and returning a `409 Conflict`. If a race condition bypasses the service layer check, the database's composite primary key constraint will throw a hard exception, acting as an absolute last line of defense against duplicate data. If a user tries to unlike a post that isn't liked, the API cleanly returns a `404 Not Found`.

## Request / Data Flow
Client `POST /api/posts/1/like`
→ Route extracts `userId` from JWT
→ Service verifies post exists
→ Service checks if like already exists (returns 409 if true)
→ Repository executes `INSERT INTO likes (post_id, user_id)`
→ PostgreSQL persists the junction row
→ Route returns `201 Created`

## Important Concepts Learned
- **Many-to-Many Relationships**: Understanding junction tables and how they bridge entities.
- **Composite Primary Keys**: Enforcing uniqueness across two columns instead of using a standalone `id`.
- **Aggregate Queries**: Using `COUNT(*)` in SQL to aggregate data.
- **Idempotency and Duplicate Handling**: Returning correct HTTP semantics (like `409 Conflict`) when attempting to recreate an existing unique resource.

## Verification
A 15-point end-to-end Python test script was written and executed against a live instance. It validated duplicate handling, successful deletes, unauthenticated responses, and non-existent resource behavior across the entire API boundary.

## Actual Result
All 15 integration scenarios executed perfectly and passed verification. The database composite key and service-level duplicate checks functioned exactly as intended.

## What I Learned From This Step
I learned how to manage pure relationship tables in SQL using composite primary keys and how to surface safe, predictable duplicate-handling behavior (409 Conflict) through a REST API.

==================================================

# Step 7 — Pagination

## Status
Completed & Verified

## Why We Needed This Step
As the blog platform grows, returning every post from the database in a single HTTP request becomes increasingly inefficient, consuming massive amounts of bandwidth and memory. We needed a way to fetch posts in manageable chunks (pages) so clients can sequentially load data as needed.

## What We Built
We converted the existing `/api/posts` listing endpoint to support page-based offset pagination via query parameters:
`GET /api/posts?page=1&limit=10`

## Why We Chose Offset Pagination
Offset pagination is highly intuitive for users and developers since it explicitly maps to standard "Page 1", "Page 2" numerical navigation. It is simple to implement and straightforward for the current phase of this project where dataset mutation frequency is moderate.

## How Page-Based Pagination Works
The API accepts human-readable `page` and `limit` values, which are translated into a mathematical database offset using the formula:
`offset = (page - 1) * limit`
- If `page=1, limit=10` → `offset = 0` (Skip 0 rows, take 10)
- If `page=2, limit=10` → `offset = 10` (Skip 10 rows, take 10)
- If `page=5, limit=20` → `offset = 80` (Skip 80 rows, take 20)

## Database Query
We updated the repository to fetch paginated rows alongside the total count:
- **ORDER BY**: We use `ORDER BY created_at DESC, id DESC`. We sort by timestamp to show newest posts first, but explicitly use `id DESC` as a deterministic tie-breaker so identical timestamps do not cause random sorting which ruins pagination boundaries.
- **OFFSET**: Instructs the database to skip a specific number of rows.
- **LIMIT**: Restricts the maximum number of rows returned in the page.
- **COUNT(*)**: We perform a separate lightweight query to count all posts in the table, without transmitting the actual rows, to inform the client of the total dataset size.

## Pagination Metadata
The API now returns a structured JSON payload outlining the exact state of the paginated resource:
- **items**: The array of actual posts.
- **page**: The current page number requested.
- **limit**: The maximum page size requested.
- **total**: The absolute total count of posts in the database.
- **total_pages**: The mathematical ceiling of total divided by limit (`ceil(total / limit)`), indicating the absolute end of the dataset.

## Offset vs Cursor Pagination

### Offset
**Advantages:**
- Extremely simple to implement on the backend.
- Simple for frontend clients to navigate (e.g., clicking a button for "Page 4").
- Straightforward REST API design (`?page=4`).

**Limitations:**
- Large `OFFSET` values require the database engine to scan and discard thousands of rows before returning the requested page, degrading performance on massive tables.
- If data is actively being inserted or deleted, page boundaries shift, causing items to either be skipped or duplicated as the user navigates between pages.

### Cursor / Keyset
*(Conceptually only, not implemented in Step 7)*
Cursor pagination uses a unique pointer (like the last seen `id` or timestamp) instead of skipping rows mathematically. It is extremely fast even on billions of rows because it seeks directly to the index pointer (`WHERE id < X`), and it prevents missing or duplicate data when the dataset mutates. However, it is harder to implement and removes the ability to jump to an arbitrary page number.

## Request / Data Flow
Client `GET /api/posts?page=2&limit=10`
→ FastAPI Route (validates `page >= 1`, `limit <= 100`)
→ Post Service (calculates `total_pages` metadata)
→ Post Repository (executes `OFFSET` query & `COUNT(*)` query)
→ PostgreSQL
→ JSON Pagination response returned to Client

## Important Concepts Learned
- **Page-Based Pagination**: Mathematical conversion of pages to database offsets.
- **Deterministic Ordering**: Using secondary sort columns (`id DESC`) to prevent unstable sorts.
- **Total Result Counts**: Using separate lightweight aggregate queries to provide frontend metadata.
- **Offset Tradeoffs**: Understanding why `OFFSET` degrades at high scale.

## Verification
A specialized targeted Python script verified:
- Pagination page 1 (`limit=5`)
- Pagination page 2 (`limit=5`)
- Page overlap verification (asserted Page 1 and Page 2 share no IDs)
- Metadata verification (asserted `page`, `limit`, `total`, `total_pages` present)
- `total_pages` calculation verification (asserted mathematical ceiling calculation against an uneven dataset of 19 posts: `ceil(19/5) = 4`)
- Deterministic ordering verification (asserted IDs strictly descending on identical timestamps)
- Invalid page rejection (`page=0`, `page=-1` returned 422)
- Invalid limit rejection (`limit=0`, `limit=101` returned 422)
- Out-of-range page (`page=9999` returned empty items, HTTP 200, correct metadata)
- Maximum limit behavior (`limit=100` returned HTTP 200)
- Post CRUD regression (asserted creating, retrieving, updating, and deleting a post still functions perfectly)

## Test Harness Issue
During the initial run, the temporary Python test harness hung indefinitely. The Uvicorn subprocess was initialized using `stdout=subprocess.PIPE` and `stderr=subprocess.PIPE` without actually consuming those streams. Rapid access logs filled the 64KB OS pipe buffer and blocked the subprocess, freezing the test suite. 

This was a critical process-management issue, not a pagination implementation bug.
The fix was to stop piping unconsumed server logs (letting them flow to the terminal instead), enforce explicit HTTP request timeouts in `requests.get(timeout=10)`, and flush test outputs aggressively. 

## Actual Results
The live local API perfectly executed mathematical offset pagination. Invalid parameters were intercepted by FastAPI and resulted in `422 Unprocessable Entity` errors before reaching business logic. The `total_pages` correctly calculated as `4` for `19` items with `limit=5`. No overlap occurred between adjacent pages, and deterministic ordering behaved exactly as intended.

## What I Learned From This Step
I learned that REST API pagination requires strict boundary validation at the HTTP layer, deterministic tie-breakers at the database layer, and lightweight aggregate metadata queries. Furthermore, I learned a crucial process-management lesson regarding OS pipe buffers when scripting subprocess tests.

==================================================

# 5. Current Backend Architecture

As of Step 7, this is the functional, implemented backend system:

```text
Client
↓
FastAPI
├── Public routes (GET posts (Paginated), GET comments, GET likes, /health)
└── Protected routes (POST/PUT/DELETE via HTTPBearer)
↓
JWT Authentication (intercepts and extracts userId)
↓
Services (Post, Comment, and Like services enforce business rules & metadata calculations)
↓
Repositories (Post, Comment, and Like repositories handle SQL offset constraints)
↓
Neon PostgreSQL (async connection pool)
```

**Currently Active Resources:**
- **Posts**: Full CRUD, protected mutations, paginated fetching.
- **Comments**: Full CRUD, child to posts, protected mutations.
- **Likes**: Many-to-many mapping, protected mutations, duplicate prevention.

==================================================

# 6. Current Project Structure

The repository structure reflecting the current architecture:

```text
c:\Users\deore\projects\blog-platform-api\
├── .env                  # Environment variables & secrets (NOT in source control)
├── PROJECT_PROGRESS.md   # This master documentation file
├── README.md             # Project summary and API endpoint lists
├── requirements.txt      # Python package dependencies
├── scripts/
│   ├── init_db.py        # Database schema initialization script
│   └── test_connection.py# Database connectivity test script
└── src/
    ├── app.py            # FastAPI application instance and router mounting
    ├── server.py         # Uvicorn entry point
    ├── config/
    │   └── db.py         # asyncpg connection pool logic
    ├── controllers/
    │   └── .gitkeep      # (Intentionally unused to adhere to thin-route architecture)
    ├── db/
    │   └── schema.sql    # Raw PostgreSQL schema definitions
    ├── middleware/
    │   └── auth.py       # JWT extraction and Depends(get_current_user)
    ├── repositories/
    │   ├── post_repository.py
    │   ├── comment_repository.py
    │   └── like_repository.py
    ├── routes/
    │   ├── posts.py
    │   ├── comments.py
    │   └── likes.py
    ├── schemas/
    │   ├── post.py       # Pydantic validation models
    │   ├── comment.py
    │   └── like.py
    ├── services/
    │   ├── post_service.py
    │   ├── comment_service.py
    │   └── like_service.py
    └── utils/
        └── jwt_utils.py  # Cryptographic token decoding
```

==================================================

# 7. Backend Concepts Learned So Far

- **REST API**: Representational State Transfer. A standard for structuring network endpoints using HTTP nouns and verbs.
- **HTTP methods**: Semantic verbs for actions: GET (read), POST (create), PUT (update), DELETE (remove).
- **FastAPI**: A modern Python framework that parses HTTP requests quickly and natively supports asynchronous execution.
- **Uvicorn**: An ASGI server that translates raw TCP socket HTTP traffic into Python events for FastAPI.
- **ASGI**: Asynchronous Server Gateway Interface. The protocol that allows Python web servers to process multiple requests concurrently without blocking.
- **Dependency Injection**: FastAPI's `Depends()` allows routes to dynamically require logic (like database pools or authentication) to run before the route executes, keeping code DRY.
- **APIRouter**: A tool to modularize and organize related endpoints (like `/posts`) into separate files before attaching them to the main app.
- **Pydantic**: A data validation library that ensures JSON request bodies match strict Python schemas, rejecting bad data automatically.
- **JWT**: JSON Web Tokens. A cryptographic standard for stateless user authentication.
- **Authentication**: The act of validating *who* a user is (checking the JWT signature).
- **Authorization**: The act of validating *what* a user can do (checking if `userId` matches `author_id`).
- **PostgreSQL**: A powerful, open-source relational database engine.
- **Relational tables**: Storing data in grids of columns and rows that relate to one another.
- **Primary keys**: A unique identifier for a row (`id`).
- **Foreign keys**: A column linking to a primary key in another table (`post_id`).
- **Composite primary keys**: Using two columns together to enforce uniqueness (e.g., `post_id` + `user_id` in the likes table).
- **Many-to-Many Relationships**: Using junction tables without surrogate IDs to bridge relationships between objects.
- **Aggregate SQL**: Using functions like `COUNT(*)` to summarize table states.
- **ON DELETE CASCADE**: A database rule that automatically deletes child rows (comments) when a parent row (post) is deleted.
- **Indexes**: Database structures that make sorting and searching specific columns extremely fast.
- **Offset Pagination**: Transforming `page` and `limit` into `OFFSET` SQL queries to partition huge datasets.
- **Deterministic Sorts**: Relying on unique secondary identifiers in `ORDER BY` to make query offsets behave reliably.
- **Process Management**: Avoiding pipe buffer deadlocks when routing subprocess standard output logs.
- **Async programming**: Using `async`/`await` in Python so the CPU can handle other web requests while waiting for network/database responses.
- **Connection pooling**: Maintaining a cache of open database connections to handle thousands of requests without the overhead of establishing new TCP connections.
- **asyncpg**: The fastest asyncio driver for communicating with PostgreSQL in Python.
- **Parameterized SQL**: Passing variables to queries using `$1`, `$2` to completely eliminate SQL injection attacks.
- **CRUD**: Create, Read, Update, Delete. The four fundamental operations of persistent storage.
- **UUIDs**: Universally Unique Identifiers. 128-bit identifiers used for decentralized, non-guessable user IDs.
- **HTTP status codes**: Standardized response numbers. (e.g., 200 OK, 201 Created, 204 No Content, 401 Unauthorized, 403 Forbidden, 404 Not Found, 409 Conflict, 422 Unprocessable Entity).
- **Layered architecture**: Decoupling logic into thin Routes, orchestrating Services, and dedicated Repositories to create a maintainable, testable codebase.

==================================================

# 8. Interview Understanding

Based on the implementation up to Step 7, a developer should be able to articulate:

- **What the project does**: It is a high-concurrency RESTful API for a blog platform, handling users, posts, comments, and likes securely via JWT authentication, natively supporting paginated data retrieval.
- **Current architecture**: It uses an N-Tier architecture where HTTP requests hit FastAPI Routes, undergo JWT validation middleware, route to Services for business logic (like ownership checks and paginated metadata calculation), and pass down to Repositories for raw SQL execution.
- **Why FastAPI**: Selected over Flask because its native async support drastically increases throughput for database-heavy APIs, and Pydantic provides free data validation.
- **Why PostgreSQL/Neon**: Relational data requires strict integrity (like cascading deletes). Neon was chosen for serverless connection pooling capabilities.
- **How authentication works**: Clients send an `Authorization: Bearer` token. A FastAPI dependency intercepts the request, uses `PyJWT` with a symmetric secret (`HS256`) to mathematically prove the token was issued by us, and extracts the `userId`.
- **How authorization works**: Inside the Service layer, the target resource (Post or Comment) is fetched. The system compares the resource's `author_id` to the authenticated JWT `userId`. If they mismatch, the service returns a `403 Forbidden`.
- **How Posts work**: Posts are the primary resource, managed via full CRUD endpoints utilizing Pydantic schemas for data shaping and parameterized `INSERT`/`UPDATE` SQL queries. Collections of posts are retrieved via page-based offset pagination with deterministic tie-breakers on unique IDs.
- **How Comments work**: Comments are child resources mapped to Posts via a foreign key. The API checks for post existence before creating comments and relies on PostgreSQL's `ON DELETE CASCADE` to clean them up if the parent post is removed.
- **How Likes work**: Likes use a many-to-many junction table relying on a `(post_id, user_id)` composite primary key to enforce uniqueness, which is cleanly handled and mapped to `409 Conflict` errors when duplicates are attempted in the API.
- **How Route → Service → Repository works**: Routes handle HTTP parsing. Services handle rules (auth, existence checks). Repositories handle SQL. This prevents massive spaghetti functions and makes testing isolation possible.
- **How the database is accessed asynchronously**: A global `asyncpg` connection pool is initialized at startup. Repositories asynchronously `acquire()` a connection, await the SQL execution, and release it back to the pool without blocking the main Python thread.

==================================================

# 9. Future Roadmap

| Step | Feature | Status |
|------|---------|--------|
| Step 8 | Redis Integration | Not Implemented |
| Step 9 | Cache Invalidation + TTL | Not Implemented |
| Step 10 | Automated Testing | Not Implemented |
| Step 11 | Performance Measurement | Not Implemented |
| Step 12 | Deployment | Not Implemented |

==================================================

# 10. Development Log

- **Step 1**: Created the foundational server structure. Transitioned from synchronous Flask to asynchronous FastAPI + Uvicorn to support high concurrency. Verified via `/health` endpoint. Learned the ASGI request lifecycle.
- **Step 2**: Integrated Neon PostgreSQL. Set up `asyncpg` connection pooling and executed table schema creation. Verified via a custom information schema test script. Learned why connection pools are mandatory for backend scale.
- **Step 3**: Integrated JWT authentication. Built middleware to extract and validate Bearer tokens. Verified via a protected `/api/auth-test` echo endpoint. Learned how stateless cryptography reduces database load.
- **Step 4**: Implemented Posts API. Built the core layered architecture (Routes/Services/Repositories) for full CRUD operations. Enforced ownership authorization. Verified via comprehensive custom Python E2E script. Learned how to firmly decouple SQL logic from HTTP routing.
- **Step 5**: Implemented Comments API. Handled nested child-resource logic and pre-validation (verifying post existence). Maintained strict ownership checks. Verified via a 13-point E2E Python script testing business logic and error propagation (403, 404, 422). Learned how to leverage database foreign-key constraints (ON DELETE CASCADE) to minimize application code.
- **Step 6**: Implemented Likes API. Handled many-to-many relationships and composite primary keys `(post_id, user_id)` directly enforcing uniqueness on the database layer. Verified via a 15-point E2E testing duplicate prevention (`409 Conflict`) and aggregate queries. Learned how to handle non-identifying relationships (junction tables without surrogate ids).
- **Step 7**: Implemented Pagination. Transformed list endpoints into paginated boundaries using offset limits and aggregate total queries. Overcame a rigorous process-management `stdout` pipeline deadlock during E2E verification. Learned how to design extensible API responses natively handling data constraints and limits.
